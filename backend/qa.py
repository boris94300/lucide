"""Questions-réponses sur le document (recherche de passage + calculs ; LLM si disponible)."""
import re

from . import llm
from .rules import fold, norm

STOP = set("le la les un une des de du d l a au aux et ou en est ce que qui quoi quel quelle quels quelles je j "
           "me mon ma mes tu te ton ta vous votre vos il elle on y si pour par sur dans avec pas ne plus combien "
           "comment est-ce estce faut peut puis dois".split())


SYN = {"avance": ["anticip"], "tot": ["anticip"], "anticipe": ["anticip"], "paie": ["defaillance", "impaye"],
       "paye": ["defaillance", "impaye"], "rembourse": ["rembours"], "arreter": ["resiliation"],
       "resilier": ["resiliation"], "annuler": ["retractation", "resiliation"], "changer": ["retractation"],
       "malade": ["exclu", "garantie"], "couvert": ["garantie", "exclu"], "litige": ["litige", "tribunal"],
       "taux": ["taux"], "frais": ["frais"], "assurance": ["assurance"], "obligatoire": ["obligatoire"]}


def _passages(text: str) -> list[str]:
    out = []
    for p in re.split(r"(?<=[.!?])\s+", norm(text)):
        words = p.split()
        for i in range(0, len(words), 40):
            chunk = " ".join(words[i:i + 40])
            if len(chunk.split()) >= 4:
                out.append(chunk)
    return out


def _keywords(q: str) -> list[str]:
    kws = [w for w in re.findall(r"[a-z0-9]+", fold(q)) if w not in STOP and len(w) > 2]
    extra = [s for w in kws for s in SYN.get(w, [])]
    return list(dict.fromkeys(extra + kws))


SYN_TARGETS = {t for v in SYN.values() for t in v}


def ask(question: str, text: str, analysis: dict, level: str) -> dict:
    if llm.enabled():
        out = llm.answer(question, text, level)
        if out and out.get("reponse"):
            return {"reponse": out["reponse"], "citation": out.get("citation", ""), "moteur": "IA Mistral"}

    fq = fold(question)
    if analysis.get("mode") == "arnaque":
        canned = scam_answer(fq, analysis)
        if canned:
            return canned
    cost = analysis.get("cout") or {}
    if cost and re.search(r"cout|coute|total|combien.*(payer|rembourse)|prix", fq):
        e = lambda v: f"{v:,.0f}".replace(",", " ") + " €"
        return {"reponse": (f"Au total, vous rembourserez environ {e(cost['total_rembourse'])} pour {e(cost['capital'])} empruntés, "
                            f"soit un coût de {e(cost['cout_total'])} (intérêts {e(cost['total_interets'])}, assurance "
                            f"{e(cost['total_assurance'])}, frais {e(cost['frais_dossier'])})."),
                "citation": "", "moteur": "calcul"}
    if cost and re.search(r"mensualite|par mois|chaque mois", fq):
        return {"reponse": f"Votre mensualité est d'environ {cost['mensualite_avec_assurance']:.2f} € par mois assurance comprise ".replace(".", ",")
                           + f"({cost['mensualite_hors_assurance']:.2f} € hors assurance)".replace(".", ",") + f", pendant {cost['duree_mois']} mois.",
                "citation": "", "moteur": "calcul"}

    kws = _keywords(question)
    passages = _passages(text)
    best, best_score = None, 0
    for i, p in enumerate(passages):
        window = p
        j = i + 1
        while len(window) < 120 and j < len(passages):
            window += " " + passages[j]
            j += 1
        fp = fold(p)
        s = sum(2 if k in SYN_TARGETS else 1 for k in kws if k in fp) + sum(0.3 for k in kws if k[:5] in fp)
        if s > best_score:
            best, best_score = window, s
    if not best:
        return {"reponse": "Je n'ai pas trouvé d'information à ce sujet dans le document.", "citation": "", "moteur": "recherche"}
    intro = {"simple": "Voici ce que dit le document à ce sujet :",
             "normal": "Le passage le plus pertinent du document est le suivant :",
             "expert": "Extrait contractuel pertinent :"}[level]
    return {"reponse": intro, "citation": best, "moteur": "recherche"}


def scam_answer(fq: str, a: dict) -> dict | None:
    if re.search(r"clique|paye|donne|communique|rempli|saisi|trop tard", fq):
        return {"reponse": "Pas de panique, agissez vite : 1) appelez votre banque (numéro au dos de la carte) ou faites opposition "
                           "(0 892 705 705, serveur interbancaire) ; 2) changez vos mots de passe bancaires et email ; 3) surveillez "
                           "vos comptes et contestez toute opération non autorisée (vous avez 13 mois, art. L133-24 CMF) ; "
                           "4) portez plainte et signalez sur cybermalveillance.gouv.fr ou au 17Cyber.",
                "citation": "", "moteur": "base de connaissances"}
    if re.search(r"lien|url|site|qr", fq):
        bad = [u for u in a.get("liens", []) if u["risque"] in ("dangereux", "suspect")]
        if bad:
            u = bad[0]
            return {"reponse": f"Le lien mène vers « {u['domaine']} », qui n'est pas un site officiel : " + " ; ".join(u["raisons"]) + ".",
                    "citation": u["url"], "moteur": "analyse de lien"}
        return {"reponse": "Aucun lien dangereux n'a été détecté dans ce message.", "citation": "", "moteur": "analyse de lien"}
    if re.search(r"verifi|vraiment|sur que|authentique|ma banque", fq):
        return {"reponse": "Raccrochez ou ignorez le message, puis contactez vous-même l'organisme via son appli officielle ou le "
                           "numéro que vous connaissez (au dos de votre carte, sur votre relevé). Une banque ne vous demandera "
                           "jamais un code, un virement « de sécurité » ou d'installer une application.",
                "citation": "", "moteur": "base de connaissances"}
    return None
