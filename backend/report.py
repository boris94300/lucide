"""Génération du rapport PDF."""
import os
from datetime import datetime

from fpdf import FPDF

FONTS = os.path.join(os.path.dirname(__file__), "fonts")
COLORS = {"haute": (220, 38, 38), "moyenne": (234, 138, 0), "faible": (37, 99, 235)}
VERDICT_COLORS = {"arnaque": (220, 38, 38), "risqué": (220, 38, 38), "suspect": (234, 138, 0),
                  "vigilance": (234, 138, 0), "légitime": (22, 163, 74), "transparent": (22, 163, 74)}


def _eur(v):
    return f"{v:,.2f} €".replace(",", " ").replace(".", ",") if v is not None else "-"


def build(a: dict) -> bytes:
    pdf = FPDF()
    pdf.add_font("dj", "", os.path.join(FONTS, "DejaVuSans.ttf"))
    pdf.add_font("dj", "B", os.path.join(FONTS, "DejaVuSans-Bold.ttf"))
    pdf.set_auto_page_break(True, 15)
    pdf.add_page()
    W = pdf.w - 2 * pdf.l_margin

    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, pdf.w, 28, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("dj", "B", 20)
    pdf.set_xy(10, 7)
    pdf.cell(0, 8, "Lucide")
    pdf.set_font("dj", "", 9)
    pdf.set_xy(10, 16)
    titre = "Rapport d'analyse de contrat" if a["mode"] == "contrat" else "Rapport d'analyse de message suspect"
    pdf.cell(0, 6, f"{titre} · {datetime.now():%d/%m/%Y %H:%M}")
    pdf.set_text_color(0, 0, 0)
    pdf.set_y(34)

    c = VERDICT_COLORS.get(a["verdict"], (100, 100, 100))
    pdf.set_fill_color(*c)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("dj", "B", 13)
    label = "Score de transparence" if a["mode"] == "contrat" else "Score de risque"
    pdf.cell(W, 11, f"  Verdict : {a['verdict'].upper()}   ·   {label} : {a['score']}/100", fill=True,
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    def h(t):
        pdf.ln(2)
        pdf.set_font("dj", "B", 12)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(W, 7, t, new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(200, 200, 200)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + W, pdf.get_y())
        pdf.ln(2)
        pdf.set_text_color(0, 0, 0)

    def p(t, size=10, style=""):
        pdf.set_font("dj", style, size)
        pdf.multi_cell(W, 5, t, new_x="LMARGIN", new_y="NEXT")

    h("Résumé")
    p(a.get("resume", ""))

    cost = a.get("cout")
    if a["mode"] == "contrat" and cost:
        h("Coût réel du crédit")
        rows = [("Montant emprunté", _eur(cost["capital"])), ("Durée", f"{cost['duree_mois']} mois"),
                ("Taux utilisé", f"{cost['taux_utilise']} %".replace(".", ",")),
                ("Mensualité (avec assurance)", _eur(cost["mensualite_avec_assurance"])),
                ("Total des intérêts", _eur(cost["total_interets"])), ("Total assurance", _eur(cost["total_assurance"])),
                ("Frais de dossier", _eur(cost["frais_dossier"])),
                ("COÛT TOTAL DU CRÉDIT", f"{_eur(cost['cout_total'])} ({str(cost['pourcentage_du_capital']).replace('.', ',')} % du capital)"),
                ("Total remboursé", _eur(cost["total_rembourse"]))]
        for k, v in rows:
            bold = "B" if k.startswith("COÛT") else ""
            pdf.set_font("dj", bold, 10)
            pdf.cell(W * 0.55, 6, k, border="B")
            pdf.cell(W * 0.45, 6, v, border="B", align="R", new_x="LMARGIN", new_y="NEXT")

    h(f"Points de vigilance ({len(a.get('alertes', []))})")
    for al in a.get("alertes", []):
        col = COLORS.get(al["gravite"], (100, 100, 100))
        pdf.set_fill_color(*col)
        y = pdf.get_y()
        pdf.set_text_color(*col)
        pdf.set_font("dj", "B", 10)
        pdf.set_x(pdf.l_margin + 3)
        pdf.multi_cell(W - 3, 5, f"[{al['gravite'].upper()}] {al['titre']}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("dj", "", 9.5)
        pdf.set_x(pdf.l_margin + 3)
        pdf.multi_cell(W - 3, 4.8, al.get("explication", ""), new_x="LMARGIN", new_y="NEXT")
        if al.get("citation"):
            pdf.set_text_color(90, 90, 90)
            pdf.set_font("dj", "", 8.5)
            pdf.set_x(pdf.l_margin + 3)
            pdf.multi_cell(W - 3, 4.5, f"« {al['citation'][:400]} »", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
        pdf.rect(pdf.l_margin, y, 1.2, pdf.get_y() - y, "F")
        pdf.ln(2.5)

    if a.get("points_positifs"):
        h("Points positifs")
        for t in a["points_positifs"]:
            p(f"✓ {t}")
    if a.get("liens"):
        h("Analyse des liens et QR codes")
        for u in a["liens"]:
            p(f"{u['url']} → {u['risque'].upper()} ({u['score']}/100)" + (" [QR code]" if u.get("via_qr") else ""), 9.5, "B")
            p("   " + " ; ".join(u["raisons"]), 9)
    if a.get("questions"):
        h("Questions à poser à votre conseiller")
        for q in a["questions"]:
            p(f"• {q}")
    if a.get("actions"):
        h("Que faire maintenant ?")
        for i, t in enumerate(a["actions"], 1):
            p(f"{i}. {t}")

    pdf.ln(5)
    pdf.set_text_color(120, 120, 120)
    p("Analyse générée automatiquement par Lucide (moteur de règles"
      + (" + IA Mistral" if "Mistral" in a.get("moteur", "") else "")
      + "). Ceci n'est pas un conseil juridique ou financier. Aucune donnée n'est conservée.", 8)
    return bytes(pdf.output())
