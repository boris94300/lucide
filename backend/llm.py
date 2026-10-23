"""Client Mistral optionnel (OCR + analyse + Q&A). Inactif sans MISTRAL_API_KEY."""
import base64
import json
import os

import httpx

API = "https://api.mistral.ai/v1"
MODEL = os.environ.get("MISTRAL_MODEL", "mistral-large-latest")


def enabled() -> bool:
    return bool(os.environ.get("MISTRAL_API_KEY"))


def _headers():
    return {"Authorization": f"Bearer {os.environ['MISTRAL_API_KEY']}"}


def ocr(data: bytes, mime: str) -> str:
    b64 = base64.b64encode(data).decode()
    doc = ({"type": "document_url", "document_url": f"data:{mime};base64,{b64}"} if mime == "application/pdf"
           else {"type": "image_url", "image_url": f"data:{mime};base64,{b64}"})
    try:
        r = httpx.post(f"{API}/ocr", headers=_headers(), timeout=90,
                       json={"model": "mistral-ocr-latest", "document": doc})
        r.raise_for_status()
        return "\n\n".join(p.get("markdown", "") for p in r.json().get("pages", []))
    except Exception as e:
        print("OCR Mistral indisponible:", e)
        return ""


def chat_json(system: str, user: str) -> dict | None:
    try:
        r = httpx.post(f"{API}/chat/completions", headers=_headers(), timeout=90, json={
            "model": MODEL, "temperature": 0.1, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
        r.raise_for_status()
        return json.loads(r.json()["choices"][0]["message"]["content"])
    except Exception as e:
        print("Mistral indisponible:", e)
        return None


LEVELS = {"simple": "très simple, tutoiement, comme à un enfant de 12 ans, sans jargon",
          "normal": "clair et accessible pour un adulte non spécialiste, vouvoiement",
          "expert": "technique et précis pour un professionnel, avec références juridiques (Code de la consommation, etc.)"}

SYSTEM = """Tu es Lucide, un assistant qui protège les particuliers des pièges financiers.
Tu analyses soit un CONTRAT financier (crédit, assurance, placement), soit un MESSAGE potentiellement frauduleux.
Règles : ne jamais inventer ; chaque alerte doit citer un extrait EXACT du document (champ "citation") ou laisser "" si l'alerte vient d'un calcul ;
réponds uniquement en JSON valide, en français."""


def enrich(base: dict, text: str, level: str) -> dict:
    """Le LLM complète l'analyse des règles (résumé, alertes supplémentaires, chiffres manquants)."""
    mode = base["mode"]
    schema = {
        "resume": "string (3-4 phrases)",
        "alertes_supplementaires": [{"titre": "string", "categorie": "string", "gravite": "haute|moyenne|faible",
                                     "explication": "string", "citation": "extrait exact"}],
    }
    if mode == "contrat":
        schema["chiffres"] = {k: "number|null" for k in base["chiffres"]}
        schema["questions"] = ["string"]
    else:
        schema["verdict"] = "arnaque|suspect|légitime"
        schema["score"] = "0-100"
    user = (f"Mode : {mode}. Niveau de langage : {LEVELS[level]}.\n"
            f"Alertes déjà détectées par le moteur de règles (ne pas répéter) : "
            f"{json.dumps([a['titre'] for a in base['alertes']], ensure_ascii=False)}\n"
            f"Schéma JSON attendu : {json.dumps(schema, ensure_ascii=False)}\n\nDOCUMENT :\n{text[:30000]}")
    out = chat_json(SYSTEM, user)
    if not out:
        return base
    res = dict(base)
    res["resume"] = out.get("resume") or base["resume"]
    known = {a["titre"].lower() for a in base["alertes"]}
    for a in out.get("alertes_supplementaires", [])[:8]:
        if a.get("titre") and a["titre"].lower() not in known and a.get("gravite") in ("haute", "moyenne", "faible"):
            cit = a.get("citation", "")
            if cit and " ".join(cit.split())[:40].lower() not in " ".join(text.split()).lower():
                cit = ""
            res["alertes"].append({**a, "citation": cit, "source": "IA Mistral"})
    if mode == "contrat":
        for k, v in (out.get("chiffres") or {}).items():
            if res["chiffres"].get(k) is None and isinstance(v, (int, float)):
                res["chiffres"][k] = v
        if out.get("questions"):
            res["questions"] = list(dict.fromkeys(out["questions"][:4] + base["questions"]))[:6]
    else:
        s = out.get("score")
        if isinstance(s, (int, float)):
            res["score"] = int(max(base["score"], (base["score"] + s) / 2))
            res["verdict"] = "arnaque" if res["score"] >= 60 else "suspect" if res["score"] >= 30 else "légitime"
    order = {"haute": 0, "moyenne": 1, "faible": 2}
    res["alertes"].sort(key=lambda a: order.get(a["gravite"], 3))
    return res


def answer(question: str, text: str, level: str) -> dict | None:
    user = (f"Niveau de langage : {LEVELS[level]}.\nRéponds à la question en t'appuyant UNIQUEMENT sur le document. "
            f"Si l'info n'y est pas, dis-le. Schéma : {{\"reponse\": string, \"citation\": \"extrait exact ou ''\"}}\n\n"
            f"QUESTION : {question}\n\nDOCUMENT :\n{text[:30000]}")
    return chat_json(SYSTEM, user)
