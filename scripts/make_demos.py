"""Génère les documents de démonstration dans demo/."""
import os

import qrcode
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(ROOT, "demo")
FONTS = os.path.join(ROOT, "backend", "fonts")
os.makedirs(DEMO, exist_ok=True)

# ------------------------------------------------------------------ contrat PDF
pdf = FPDF()
pdf.add_font("dj", "", os.path.join(FONTS, "DejaVuSans.ttf"))
pdf.add_font("dj", "B", os.path.join(FONTS, "DejaVuSans-Bold.ttf"))
pdf.add_page()
W = pdf.w - 2 * pdf.l_margin
pdf.set_font("dj", "B", 15)
pdf.cell(W, 9, "CRÉDIT FACILE SA", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("dj", "", 10)
pdf.cell(W, 6, "Offre préalable de contrat de crédit personnel", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(4)
pdf.set_font("dj", "B", 11)
pdf.cell(W, 7, "ENCADRÉ – Caractéristiques essentielles du crédit", border=1, new_x="LMARGIN", new_y="NEXT")
pdf.set_font("dj", "", 10)
for k, v in [("Emprunteur", "M. Thomas Durand"), ("Co-emprunteur", "Mme Léa Durand"),
             ("Montant total du crédit", "15 000,00 €"), ("Durée du crédit", "60 mois"),
             ("Taux débiteur annuel fixe", "5,90 %"), ("Taux annuel effectif global (TAEG) fixe", "8,45 %"),
             ("Remboursement", "60 mensualités de 289,29 € (hors assurance)"),
             ("Frais de dossier", "450,00 €"), ("Coût de l'assurance emprunteur", "24,50 € par mois")]:
    pdf.cell(W * 0.5, 7, k, border=1)
    pdf.cell(W * 0.5, 7, v, border=1, new_x="LMARGIN", new_y="NEXT")
pdf.ln(4)
clauses = [
    ("Article 1 – Objet", "Le prêteur consent à l'emprunteur un crédit personnel non affecté aux conditions définies dans l'encadré ci-dessus. Le présent contrat est conclu pour la durée indiquée."),
    ("Article 2 – Assurance emprunteur", "L'adhésion à l'assurance groupe décès-invalidité proposée par le prêteur est obligatoire pour l'octroi du crédit. Sont exclus de la garantie les affections dorsales, les troubles psychiques et les sinistres liés à la pratique d'un sport. Un délai de carence de 90 jours s'applique à compter de la signature."),
    ("Article 3 – Remboursement anticipé", "L'emprunteur peut rembourser tout ou partie du crédit par anticipation. Une indemnité de remboursement anticipé égale à 1 % du capital remboursé sera alors exigée, ainsi que des frais de gestion de 80 € par opération."),
    ("Article 4 – Réserve d'argent associée", "Une réserve d'argent (crédit renouvelable) d'un montant de 3 000 € est ouverte gratuitement au nom de l'emprunteur et utilisable avec la carte Facile+. Elle est reconduite tacitement chaque année. Les utilisations sont rémunérées au taux variable en vigueur, actuellement de 19,90 %."),
    ("Article 5 – Modification des conditions", "Le prêteur se réserve le droit de modifier les conditions tarifaires de la réserve d'argent et les frais annexes, après simple information de l'emprunteur."),
    ("Article 6 – Défaillance", "En cas de défaillance de l'emprunteur, le prêteur pourra prononcer la déchéance du terme et exiger le remboursement immédiat du capital restant dû, majoré des intérêts échus et d'une indemnité de 8 %. Les co-emprunteurs sont tenus solidairement au remboursement de l'intégralité des sommes dues."),
    ("Article 7 – Domiciliation", "L'octroi du crédit est conditionné à la domiciliation des revenus de l'emprunteur auprès d'un établissement partenaire pendant toute la durée du prêt."),
    ("Article 8 – Litiges", "Pour tout litige, le tribunal de commerce de Paris sera seul compétent, l'emprunteur renonçant à toute autre juridiction."),
]
for t, body in clauses:
    pdf.set_font("dj", "B", 10)
    pdf.cell(W, 6, t, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("dj", "", 9.5)
    pdf.multi_cell(W, 5, body, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
pdf.ln(4)
pdf.cell(W, 6, "Fait à Paris, le 23/10/2026.          Signature de l'emprunteur :", new_x="LMARGIN", new_y="NEXT")
pdf.output(os.path.join(DEMO, "contrat_credit_facile.pdf"))

# ------------------------------------------------------------------ messages texte
open(os.path.join(DEMO, "sms_ameli.txt"), "w").write(
    "Assurance Maladie : vous avez droit à un remboursement de 148,52€ suite à une erreur de calcul. "
    "Pour le recevoir, confirmez vos coordonnées bancaires sous 48h, sinon votre dossier sera clôturé : "
    "https://ameli-remboursement-securise.com/dossier\n")
open(os.path.join(DEMO, "faux_conseiller.txt"), "w").write(
    "[Transcription d'un appel reçu du 01 44 XX XX XX, affiché « Ma Banque »]\n"
    "Bonjour Madame, ici Julien du service fraude de votre banque. Nous avons détecté une opération suspecte "
    "de 1 450 € sur votre compte, vers un site en Lituanie. Pour l'annuler immédiatement, je vais vous envoyer "
    "un code de validation par SMS : il faudra me le communiquer. Ensuite, pour mettre votre épargne en sécurité, "
    "nous ferons un virement vers un compte sécurisé. Surtout ne raccrochez pas, et n'en parlez à personne, "
    "l'enquête est confidentielle.\n")
open(os.path.join(DEMO, "message_legitime.txt"), "w").write(
    "Bonjour Madame Martin, votre rendez-vous avec votre conseiller est confirmé le mardi 3 novembre à 14h00 "
    "dans votre agence de Lyon Bellecour. Pour le modifier, rendez-vous dans votre application mobile, rubrique "
    "« Mes rendez-vous ». Bonne journée.\n")

# ------------------------------------------------------------------ image SMS + QR
img = Image.new("RGB", (900, 1250), (242, 242, 247))
d = ImageDraw.Draw(img)
fb = ImageFont.truetype(os.path.join(FONTS, "DejaVuSans-Bold.ttf"), 34)
fr = ImageFont.truetype(os.path.join(FONTS, "DejaVuSans.ttf"), 30)
fs = ImageFont.truetype(os.path.join(FONTS, "DejaVuSans.ttf"), 24)
d.rectangle([0, 0, 900, 120], fill=(255, 255, 255))
d.text((450, 40), "COLIS-INFO", font=fb, fill=(0, 0, 0), anchor="mt")
d.text((450, 135), "Aujourd'hui 09:41", font=fs, fill=(120, 120, 120), anchor="mt")
d.rounded_rectangle([40, 180, 860, 1200], radius=40, fill=(229, 229, 234))
lines = ["Colissimo : votre colis n° 8R0423", "est en attente de livraison.", "",
         "Des frais de réexpédition de 1,99€", "sont à régler avant ce soir,", "sinon il sera retourné.", "",
         "Scannez le QR code ci-dessous pour", "payer et choisir un créneau :"]
y = 220
for l in lines:
    d.text((80, y), l, font=fr, fill=(0, 0, 0))
    y += 44
qr = qrcode.make("https://colissimo-suivi-livraison.xyz/paiement?id=8R0423").resize((480, 480))
img.paste(qr, (210, y + 20))
img.save(os.path.join(DEMO, "sms_colis_qr.png"))
print("démos générées dans", DEMO)

# ------------------------------------------------------------------ faux PDF : changement de RIB fournisseur
EX = os.path.join(DEMO, "exemples")
os.makedirs(EX, exist_ok=True)


def letter(path, header, sub, body_lines, footer):
    p = FPDF()
    p.add_font("dj", "", os.path.join(FONTS, "DejaVuSans.ttf"))
    p.add_font("dj", "B", os.path.join(FONTS, "DejaVuSans-Bold.ttf"))
    p.add_page()
    w = p.w - 2 * p.l_margin
    p.set_fill_color(0, 51, 102)
    p.rect(0, 0, p.w, 24, "F")
    p.set_text_color(255, 255, 255)
    p.set_font("dj", "B", 16)
    p.set_xy(10, 6)
    p.cell(0, 8, header)
    p.set_font("dj", "", 9)
    p.set_xy(10, 14)
    p.cell(0, 6, sub)
    p.set_text_color(0, 0, 0)
    p.set_y(34)
    for kind, txt in body_lines:
        p.set_font("dj", "B" if kind == "b" else "", 11 if kind == "b" else 10)
        p.multi_cell(w, 6, txt, new_x="LMARGIN", new_y="NEXT")
        p.ln(2)
    p.ln(6)
    p.set_font("dj", "", 9)
    p.set_text_color(90, 90, 90)
    p.multi_cell(w, 5, footer, new_x="LMARGIN", new_y="NEXT")
    p.output(path)


letter(os.path.join(EX, "7_faux_pdf_changement_rib.pdf"), "LOGITRANS SERVICES", "Transport & logistique · Siège : 12 rue des Docks, 69007 Lyon",
       [("n", "Lyon, le 22 octobre 2026"), ("n", "À l'attention du service comptabilité"),
        ("b", "Objet : Changement de coordonnées bancaires – URGENT et CONFIDENTIEL"),
        ("n", "Madame, Monsieur,"),
        ("n", "Suite à un audit interne, notre banque a changé. Nous vous informons que nos coordonnées bancaires ont été modifiées. Merci d'utiliser dès aujourd'hui notre nouveau RIB pour le règlement de toutes les factures en attente, notamment la facture n° F-2026-0912 d'un montant de 18 450,00 €, à régler immédiatement."),
        ("n", "Nouvel IBAN : LT12 3456 7890 1234 5678   BIC : LTBKLT2X   Banque : Baltic Trust Bank, Vilnius"),
        ("n", "Pour des raisons de confidentialité liées à l'audit, merci de ne pas contacter nos services par téléphone et de traiter cette demande avec la plus grande discrétion. Toute question doit être adressée uniquement par email à : comptabilite@logitrans-services-fr.com"),
        ("n", "Nous vous remercions de votre réactivité. Sans règlement sous 48h, des pénalités de retard seront appliquées."),
        ("n", "Jean-Marc Lefèvre\nDirecteur administratif et financier")],
       "LOGITRANS SERVICES SAS – Document fictif généré pour la démonstration Lucide.")

letter(os.path.join(EX, "8_faux_pdf_avis_impots.pdf"), "DGFiP – impots.gouv", "Direction Générale des Finances Publiques · Service des remboursements",
       [("n", "Paris, le 21 octobre 2026"), ("b", "AVIS DE REMBOURSEMENT – Dossier n° 2026-FR-48213"),
        ("n", "Madame, Monsieur,"),
        ("n", "Suite à une erreur de calcul sur votre déclaration de revenus, vous avez droit à un remboursement de 327,40 €."),
        ("n", "Pour recevoir ce montant, vous devez valider votre dossier en ligne sous 48h en indiquant votre numéro de carte bancaire, sa date d'expiration et son cryptogramme :"),
        ("b", "https://impots-gouv-remboursement.fr/dossier-48213"),
        ("n", "Sans validation dans ce délai, votre remboursement sera définitivement annulé et une amende pourra être appliquée."),
        ("n", "Le Directeur du service des remboursements")],
       "Document fictif généré pour la démonstration Lucide.")
print("exemples générés dans", EX)
