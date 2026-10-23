# Lucide – l'IA qui vous protège des pièges financiers

> **Ne signez plus à l'aveugle. Ne cliquez plus au hasard.**
> Hackathon Finaxys « Hack the Bank » 2026 – track Carte blanche.

Lucide analyse en quelques secondes :
- **un contrat financier** (crédit, assurance, placement) → clauses piège, frais cachés, coût réel, questions à poser ;
- **un message suspect** (SMS, email, capture d'écran, QR code) → verdict arnaque / suspect / légitime, signaux de manipulation, liens piégés, que faire.

## Fonctionnalités

| | |
|---|---|
| 📄 **Décodage de contrat** | 16 familles de clauses à risque (pénalités de remboursement anticipé, assurance imposée, crédit renouvelable, modification unilatérale, déchéance du terme, vente liée…) avec citation exacte surlignée dans le document |
| 💶 **Coût réel** | extraction automatique (montant, durée, taux, TAEG, frais, assurance) → calculateur interactif « et si ? » |
| 🚨 **Bouclier anti-arnaque** | 12 signaux d'ingénierie sociale (urgence, menace, demande de code, faux conseiller, changement de RIB, faux proche…) |
| 🔗 **Liens & QR codes** | détection de typosquatting, imitation de marque, extensions douteuses, raccourcisseurs ; décodage des QR codes dans les images |
| 🧒🙂🎓 **Niveau d'explication** | Simple / Normal / Expert |
| 💬 **Questions-réponses** | réponses ancrées sur le document, avec citation |
| ⬇️ **Rapport PDF** | synthèse à imprimer ou à apporter à son banquier |

## Architecture

```
Fichier (PDF / image / texte)
   │  PyMuPDF · OCR (Mistral OCR, ou Tesseract hors-ligne) · décodage QR (OpenCV)
   ▼
Texte ──► Moteur de règles déterministe (backend/rules.py, urls.py, finance.py)
   │            = garde-fou factuel : citations exactes, calculs exacts
   ▼
IA Mistral (optionnelle, backend/llm.py) : résumé, alertes supplémentaires,
   chiffres manquants, Q&A — citations vérifiées contre le texte source
   ▼
API FastAPI (backend/app.py) ──► Interface web (frontend/) + rapport PDF (backend/report.py)
```

**IA responsable** : approche hybride règles + LLM (pas d'hallucination sur les chiffres : calculs déterministes ; citations du LLM vérifiées), score et sources affichés, aucune donnée conservée, mention « pas un conseil juridique ».

## Lancer en local

```bash
sudo apt install tesseract-ocr tesseract-ocr-fra   # OCR hors-ligne (optionnel)
pip install -r requirements.txt
export MISTRAL_API_KEY=...                          # optionnel
uvicorn backend.app:app --reload --port 8000
# → http://localhost:8000
```

Les documents de démonstration sont dans `demo/` (regénérables : `python scripts/make_demos.py`).

## Déployer en ligne (lien permanent, gratuit)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/boris94300/lucide)

1. Créer un compte gratuit sur https://render.com (connexion avec GitHub).
2. Cliquer sur le bouton ci-dessus (ou New → Blueprint → choisir ce repo) : Render lit `render.yaml` et construit le `Dockerfile`.
3. Optionnel : renseigner `MISTRAL_API_KEY` pour activer l'IA (sinon moteur de règles).
4. L'appli est disponible sur `https://lucide-xxxx.onrender.com`. En offre gratuite, elle se met en veille après 15 min sans visite : le premier chargement prend environ 1 min.

Avec Docker : `docker build -t lucide . && docker run -p 8000:8000 lucide`

## API

- `POST /api/analyze` (multipart : `file` | `text` | `demo`, `mode` = auto|contrat|arnaque, `level` = simple|normal|expert)
- `POST /api/ask` `{question, texte, analyse, niveau}`
- `POST /api/report` (JSON d'analyse) → PDF
- `GET /api/health`, `GET /api/demos`

## Pitch (7 min) – trame

1. **Problème (1 min)** – On perd de l'argent de deux façons : ce qu'on ne lit pas (petites lignes des contrats) et ce qu'on croit trop vite (arnaques par SMS, faux conseillers).
2. **Pour qui (30 s)** – Grand public, en particulier jeunes (premier crédit) et seniors (cibles des arnaques) ; à terme, intégré dans l'appli d'une banque.
3. **Solution (1 min)** – Lucide : un seul geste, déposer le document → verdict, explication adaptée, actions.
4. **Démo (3 min)** – Contrat « Crédit Facile » → score 5/100, revolving caché, coût réel 4 278 € → curseur durée → question « si je rembourse en avance ? » → PDF. Puis SMS colis avec QR code → lien piégé détecté → que faire.
5. **L'IA (1 min)** – OCR, analyse Mistral + moteur de règles garde-fou, citations vérifiées, niveau de langage adaptatif.
6. **Demain (30 s)** – Bot WhatsApp, extension navigateur, API B2B pour banques (réduction de la fraude, devoir de conseil).
