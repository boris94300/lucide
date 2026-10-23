import os

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import extract, llm, qa, report, rules

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_DIR = os.path.join(ROOT, "demo")
FRONT = os.path.join(ROOT, "frontend")

DEMOS = {
    "credit": ("Crédit conso « Crédit Facile »", "contrat_credit_facile.pdf"),
    "ameli": ("SMS faux remboursement Ameli", "sms_ameli.txt"),
    "conseiller": ("Faux conseiller bancaire", "faux_conseiller.txt"),
    "colis": ("SMS colis avec QR code (image)", "sms_colis_qr.png"),
    "legit": ("Message légitime", "message_legitime.txt"),
}

app = FastAPI(title="Lucide")


@app.get("/api/health")
def health():
    return {"ok": True, "ia": llm.enabled()}


@app.get("/api/demos")
def demos():
    return [{"id": k, "label": v[0]} for k, v in DEMOS.items()]


@app.post("/api/analyze")
async def analyze(file: UploadFile | None = File(None), text: str = Form(""), demo: str = Form(""),
                  mode: str = Form("auto"), level: str = Form("normal"), qr: str = Form("")):
    level = level if level in ("simple", "normal", "expert") else "normal"
    qr_codes = [q for q in qr.split("\n") if q] if qr else []
    source, filename = "texte", ""
    if demo in DEMOS:
        filename = DEMOS[demo][1]
        with open(os.path.join(DEMO_DIR, filename), "rb") as fh:
            data = fh.read()
        ex = extract.extract(filename, data)
        text, qr_codes, source = ex["text"], ex["qr"], ex["source"]
    elif file is not None and file.filename:
        filename = file.filename
        ex = extract.extract(filename, await file.read())
        text, qr_codes, source = ex["text"], ex["qr"], ex["source"]
    if not text.strip() and not qr_codes:
        return JSONResponse({"erreur": "Aucun texte n'a pu être extrait du document."}, status_code=400)

    if mode not in ("contrat", "arnaque"):
        mode = "contrat" if rules.is_contract(text) else "arnaque"
    base = rules.analyze_contract(text, level) if mode == "contrat" else rules.analyze_message(text, level, qr_codes)
    moteur = "Moteur de règles"
    if llm.enabled():
        enriched = llm.enrich(base, text, level)
        if enriched is not base:
            base, moteur = enriched, "IA Mistral + moteur de règles"
            if mode == "contrat":
                from .finance import cout_credit
                base["cout"] = cout_credit(base["chiffres"])
    base.update({"texte": text, "source": source, "fichier": filename, "niveau": level, "moteur": moteur,
                 "qr": qr_codes})
    return base


class AskBody(BaseModel):
    question: str
    texte: str
    analyse: dict = {}
    niveau: str = "normal"


@app.post("/api/ask")
def ask(b: AskBody):
    return qa.ask(b.question, b.texte, b.analyse, b.niveau if b.niveau in ("simple", "normal", "expert") else "normal")


@app.post("/api/report")
def make_report(a: dict):
    return Response(report.build(a), media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="rapport-lucide.pdf"'})


@app.get("/")
def index():
    return FileResponse(os.path.join(FRONT, "index.html"))


app.mount("/static", StaticFiles(directory=FRONT), name="static")
app.mount("/demo", StaticFiles(directory=DEMO_DIR), name="demo")
