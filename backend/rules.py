"""Moteur de règles : détection déterministe des pièges (contrats) et arnaques (messages).

Sert de mode hors-ligne et de garde-fou factuel pour le LLM.
"""
import re
import unicodedata

from . import finance, urls


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).replace("\u202f", " ").replace("\xa0", " ")
    return " ".join(s.split())


def fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def fr(v) -> str:
    return f"{v:g}".replace(".", ",")


def to_float(s: str) -> float | None:
    s = s.replace(" ", "").replace("\u202f", "").replace("\xa0", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def quote_around(text: str, start: int, end: int, maxlen: int = 200) -> str:
    left = text.rfind(". ", 0, start)
    left = left + 2 if left >= 0 and start - left < maxlen else max(0, start - 40)
    right = text.find(".", end)
    right = right + 1 if right != -1 and right - end < maxlen else min(len(text), end + 60)
    if right - left > 320:
        left, right = max(left, start - 40), min(right, end + 60)
    return text[left:right].strip()


def _find(text: str, folded: str, patterns: list[str]):
    for p in patterns:
        m = re.search(p, folded)
        if m:
            return quote_around(text, m.start(), m.end())
    return None


# --------------------------------------------------------------------------- contrats

CONTRACT_RULES = [
    dict(id="remb_anticipe", cat="Frais cachés", sev="haute", w=12,
         pat=[r"indemnite[s]? (de|pour|en cas de) remboursement anticipe", r"remboursement anticipe[^.]{0,120}(indemnite|penalite|frais)"],
         title="Pénalités de remboursement anticipé",
         txt={"simple": "Si tu veux rembourser plus tôt (par exemple après un héritage), la banque te fait payer une amende.",
              "normal": "Rembourser par anticipation entraîne des indemnités. Vérifiez le montant et s'il existe une franchise.",
              "expert": "Indemnités de remboursement anticipé (IRA). En crédit conso, plafonnées à 1 % du capital remboursé (0,5 % si < 1 an restant) et interdites sous 10 000 € remboursés sur 12 mois (art. L312-34 C. conso)."}),
    dict(id="assurance_imposee", cat="Assurance", sev="haute", w=12,
         pat=[r"assurance[^.]{0,80}(obligatoire|imposee|exigee)[^.]{0,120}(aupres du preteur|groupe|souscrite par l.intermediaire|proposee par)", r"(adhesion|souscription) obligatoire[^.]{0,80}assurance", r"assurance[^.]{0,60}(groupe|du preteur)[^.]{0,60}obligatoire"],
         title="Assurance imposée par le prêteur",
         txt={"simple": "On t'oblige à prendre l'assurance de la banque, souvent plus chère qu'ailleurs. Tu as le droit d'en choisir une autre.",
              "normal": "L'assurance emprunteur proposée est présentée comme obligatoire. Vous pouvez la comparer et en choisir une autre à garanties équivalentes.",
              "expert": "Atteinte possible au principe de libre choix de l'assurance (délégation, loi Lagarde) ; résiliation à tout moment (loi Lemoine) pour l'immobilier. Vérifier l'équivalence de garanties exigée."}),
    dict(id="taux_variable", cat="Taux", sev="haute", w=12,
         pat=[r"taux (variable|revisable)", r"taux[^.]{0,40}(pourra|peut) (etre )?(modifie|revise|evoluer)", r"indexe sur (l.)?(euribor|indice)"],
         title="Taux variable ou révisable",
         txt={"simple": "Le taux peut augmenter : tes mensualités pourraient grimper sans prévenir.",
              "normal": "Le taux n'est pas fixe : il peut évoluer selon un indice. Le coût final est donc incertain.",
              "expert": "Taux révisable indexé : vérifier l'indice de référence, la marge, la périodicité de révision et la présence d'un cap (plafond)."}),
    dict(id="reconduction", cat="Engagement", sev="moyenne", w=8,
         pat=[r"tacite reconduction", r"reconduit (tacitement|automatiquement)", r"renouvel(le|lement)[^.]{0,30}(automatique|tacite)"],
         title="Reconduction automatique",
         txt={"simple": "Le contrat se renouvelle tout seul si tu ne l'arrêtes pas à temps.",
              "normal": "Le contrat est reconduit tacitement : notez la date limite de résiliation.",
              "expert": "Clause de tacite reconduction : l'information préalable du consommateur est obligatoire (loi Chatel, art. L215-1 C. conso)."}),
    dict(id="frais_dossier", cat="Frais cachés", sev="faible", w=4,
         pat=[r"frais de dossier"],
         title="Frais de dossier",
         txt={"simple": "Tu paies des frais juste pour ouvrir le dossier. Ça se négocie souvent !",
              "normal": "Des frais de dossier s'ajoutent au coût du crédit. Ils sont souvent négociables.",
              "expert": "Frais de dossier inclus dans le TAEG ; levier de négociation classique."}),
    dict(id="modif_unilaterale", cat="Engagement", sev="haute", w=12,
         pat=[r"(se reserve|reserve) le droit de modifier", r"modifi(er|cation)[^.]{0,60}(unilateral|sans preavis|a tout moment)"],
         title="Modification unilatérale des conditions",
         txt={"simple": "La banque peut changer les règles du jeu en cours de route.",
              "normal": "Le prêteur se réserve le droit de modifier certaines conditions. C'est potentiellement abusif.",
              "expert": "Clause présumée abusive si elle permet au professionnel de modifier unilatéralement les termes du contrat (art. R212-1 C. conso)."}),
    dict(id="revolving", cat="Produit risqué", sev="haute", w=14,
         pat=[r"credit renouvelable", r"reserve (d.argent|disponible)", r"revolving"],
         title="Crédit renouvelable (revolving)",
         txt={"simple": "C'est un crédit qui se recharge tout seul, avec des taux très élevés : un piège classique de surendettement.",
              "normal": "Crédit renouvelable : taux élevés, remboursement lent. Principale cause de surendettement.",
              "expert": "Crédit renouvelable (L312-57 s.) : TAEG souvent proche du taux d'usure, amortissement minimum obligatoire, reconduction annuelle."}),
    dict(id="decheance", cat="Engagement", sev="moyenne", w=8,
         pat=[r"decheance du terme", r"exigibilite (immediate|anticipee)", r"immediatement exigible"],
         title="Déchéance du terme",
         txt={"simple": "Si tu rates des paiements, la banque peut exiger tout l'argent d'un coup.",
              "normal": "En cas d'impayé, la totalité du capital restant peut devenir immédiatement exigible.",
              "expert": "Clause de déchéance du terme : vérifier la mise en demeure préalable et l'indemnité (max 8 % du capital restant dû, D312-16)."}),
    dict(id="solidarite", cat="Engagement", sev="moyenne", w=8,
         pat=[r"caution solidaire", r"solidairement", r"co.?emprunteur[^.]{0,40}solidai"],
         title="Engagement solidaire",
         txt={"simple": "Si l'autre personne ne paie pas, c'est toi qui dois tout rembourser.",
              "normal": "Engagement solidaire : chaque signataire peut être poursuivi pour la totalité de la dette.",
              "expert": "Solidarité passive : le créancier peut réclamer l'intégralité à un seul codébiteur ; bénéfice de discussion exclu."}),
    dict(id="frais_gestion", cat="Frais cachés", sev="moyenne", w=8,
         pat=[r"frais (de gestion|de tenue de compte|annuels|d.administration)", r"commission[s]? (de gestion|annuelle|d.intervention)"],
         title="Frais de gestion récurrents",
         txt={"simple": "Des frais reviennent tous les ans et grignotent ton argent.",
              "normal": "Des frais récurrents s'appliquent : calculez leur impact sur toute la durée.",
              "expert": "Frais récurrents : impact composé sur la performance nette ; à comparer avec le marché."}),
    dict(id="exclusions", cat="Assurance", sev="moyenne", w=8,
         pat=[r"exclusion[s]? de garantie", r"(sont|est) exclu[es]*[^.]{0,30}(garantie|couverture)", r"ne (sont|seront) pas (couverts|garantis)"],
         title="Exclusions de garantie",
         txt={"simple": "Certaines situations ne sont pas couvertes : l'assurance ne paiera pas.",
              "normal": "Le contrat liste des exclusions : vérifiez qu'elles ne concernent pas votre situation.",
              "expert": "Exclusions à apprécier (maladies antérieures, sports, affections dorsales/psychiques) ; doivent être formelles et limitées (L113-1 C. assur.)."}),
    dict(id="carence", cat="Assurance", sev="moyenne", w=6,
         pat=[r"delai de carence", r"franchise de \d+ jours", r"periode de carence"],
         title="Délai de carence / franchise",
         txt={"simple": "Pendant un certain temps au début, l'assurance ne marche pas encore.",
              "normal": "Un délai de carence ou une franchise retarde la prise en charge.",
              "expert": "Carence (pas de couverture initiale) et franchise (jours non indemnisés) : à intégrer au calcul de couverture réelle."}),
    dict(id="perte_capital", cat="Produit risqué", sev="haute", w=12,
         pat=[r"risque de perte (en|du|de) capital", r"capital (n.est )?non garanti", r"perte (totale|partielle) du capital"],
         title="Risque de perte en capital",
         txt={"simple": "Tu peux perdre une partie (ou tout) de l'argent que tu places.",
              "normal": "Le capital investi n'est pas garanti : vous pouvez perdre tout ou partie de votre mise.",
              "expert": "Capital non garanti : vérifier l'indicateur de risque SRI (1 à 7) du DIC PRIIPs et les scénarios de performance."}),
    dict(id="resiliation_frais", cat="Engagement", sev="moyenne", w=6,
         pat=[r"resiliation[^.]{0,80}(frais|penalite|indemnite)", r"(frais|penalite)[^.]{0,40}resiliation"],
         title="Frais de résiliation",
         txt={"simple": "Arrêter le contrat te coûtera de l'argent.",
              "normal": "Des frais sont prévus en cas de résiliation : sortir du contrat a un coût.",
              "expert": "Frais de sortie : vérifier leur proportionnalité et les cas légaux de résiliation sans frais."}),
    dict(id="juridiction", cat="Recours", sev="moyenne", w=6,
         pat=[r"renonce[^.]{0,40}(recours|action)", r"arbitrage obligatoire", r"tribunal[^.]{0,40}(exclusivement|seul) competent"],
         title="Limitation de vos recours",
         txt={"simple": "Le contrat essaie de t'empêcher de te défendre facilement en cas de problème.",
              "normal": "Une clause limite vos recours ou impose une juridiction : potentiellement abusive.",
              "expert": "Clause noire si elle supprime ou entrave l'exercice d'actions en justice par le consommateur (R212-1 12°)."}),
    dict(id="vente_liee", cat="Engagement", sev="moyenne", w=8,
         pat=[r"condition\w*[^.]{0,40}domiciliation", r"(ouverture|domiciliation)[^.]{0,60}(compte|revenus)[^.]{0,40}(obligatoire|condition)", r"souscription[^.]{0,40}(conditionnee|subordonnee)"],
         title="Vente liée / domiciliation imposée",
         txt={"simple": "On t'oblige à prendre un autre produit (ou à y verser ton salaire) pour avoir ce contrat.",
              "normal": "Le contrat est conditionné à un autre produit ou à la domiciliation des revenus.",
              "expert": "Domiciliation des revenus : limitée à 10 ans en crédit immobilier et doit être assortie d'un avantage individualisé (L313-25-1)."}),
]

POSITIVES = [
    (r"(delai|droit) de retractation", "Droit de rétractation mentionné (14 jours)"),
    (r"taux (debiteur |nominal |annuel )*fixe", "Taux fixe : mensualités stables"),
    (r"(sans|aucun)[^.]{0,20}(frais|indemnite)[^.]{0,30}remboursement anticipe", "Remboursement anticipé sans frais"),
    (r"delegation d.assurance|assurance de votre choix|libre choix de l.assurance", "Libre choix de l'assurance"),
    (r"mediateur", "Médiateur mentionné en cas de litige"),
]

CONTRACT_HINTS = [r"\btaeg\b", r"emprunteur", r"preteur", r"article \d", r"contrat", r"souscripteur",
                  r"assure", r"offre de (pret|credit)", r"conditions generales", r"mensualite", r"capital"]


def _num(pattern: str, folded: str):
    m = re.search(pattern, folded)
    return to_float(m.group(1)) if m else None


def extract_figures(text: str) -> dict:
    f = fold(norm(text))
    N = r"([\d][\d ]*(?:[.,]\d+)?)"
    fig = {
        "montant": _num(r"(?:montant (?:total )?du credit|capital emprunte|montant emprunte|montant du pret|montant finance)[^\d]{0,40}" + N, f),
        "taux_nominal": _num(r"taux (?:debiteur|nominal)[^\d]{0,40}" + N + r"\s*%", f),
        "taeg": _num(r"(?:taeg|taux annuel effectif global)[^\d]{0,40}" + N + r"\s*%", f),
        "mensualite": _num(r"mensualites?[^\d]{0,60}" + N + r"\s*(?:€|eur)", f),
        "frais_dossier": _num(r"frais de dossier[^\d]{0,40}" + N + r"\s*(?:€|eur)", f),
        "assurance_mensuelle": _num(r"assurance[^€]{0,80}?" + N + r"\s*(?:€|eur)\s*(?:par mois|/ ?mois|mensuel)", f),
        "duree_mois": None,
    }
    m = re.search(r"duree[^\d]{0,40}(\d{1,3})\s*mois", f)
    if m:
        fig["duree_mois"] = int(m.group(1))
    else:
        m = re.search(r"duree[^\d]{0,40}(\d{1,2})\s*ans", f)
        if m:
            fig["duree_mois"] = int(m.group(1)) * 12
    return fig


def is_contract(text: str) -> bool:
    f = fold(text)
    hits = sum(bool(re.search(p, f)) for p in CONTRACT_HINTS)
    return hits >= 3 or (hits >= 2 and len(text) > 1500)


def analyze_contract(text: str, level: str = "normal") -> dict:
    text = norm(text)
    f = fold(text)
    alerts, penalty = [], 0
    for r in CONTRACT_RULES:
        q = _find(text, f, r["pat"])
        if q:
            alerts.append({"id": r["id"], "titre": r["title"], "categorie": r["cat"], "gravite": r["sev"],
                           "explication": r["txt"][level], "citation": q, "source": "règles"})
            penalty += r["w"]
    positives = [label for p, label in POSITIVES if re.search(p, f)]
    if not re.search(r"retractation", f):
        alerts.append({"id": "no_retract", "titre": "Droit de rétractation non mentionné", "categorie": "Recours",
                       "gravite": "moyenne", "citation": "",
                       "explication": {"simple": "Normalement tu as 14 jours pour changer d'avis : ce n'est écrit nulle part ici.",
                                       "normal": "Le délai légal de rétractation de 14 jours n'apparaît pas dans le document.",
                                       "expert": "Absence de mention du délai de rétractation de 14 jours (L312-19 C. conso) : formulaire détachable obligatoire."}[level],
                       "source": "règles"})
        penalty += 8

    figures = extract_figures(text)
    cost = finance.cout_credit(figures)
    if figures.get("taeg") and figures.get("taux_nominal") and figures["taeg"] - figures["taux_nominal"] >= 1.5:
        alerts.append({"id": "ecart_taeg", "titre": "Gros écart entre taux affiché et TAEG", "categorie": "Taux",
                       "gravite": "haute", "citation": "",
                       "explication": {"simple": f"Le taux affiché ({fr(figures['taux_nominal'])} %) cache le vrai coût : avec les frais, c'est {fr(figures['taeg'])} %.",
                                       "normal": f"Le TAEG ({fr(figures['taeg'])} %) dépasse nettement le taux débiteur ({fr(figures['taux_nominal'])} %) : frais et assurance pèsent lourd.",
                                       "expert": f"Écart TAEG/taux débiteur de {fr(round(figures['taeg'] - figures['taux_nominal'], 2))} pts : frais annexes significatifs à décomposer."}[level],
                       "source": "calcul"})
        penalty += 10

    order = {"haute": 0, "moyenne": 1, "faible": 2}
    alerts.sort(key=lambda a: order[a["gravite"]])
    score = max(5, min(100, 100 - penalty + 3 * len(positives)))
    verdict = "transparent" if score >= 75 else "vigilance" if score >= 50 else "risqué"
    nb_h = sum(a["gravite"] == "haute" for a in alerts)

    cost_txt = ""
    if cost:
        cost_txt = (f" Coût total estimé du crédit : {cost['cout_total']:,.0f} € ({str(cost['pourcentage_du_capital']).replace('.', ',')} % du montant emprunté)."
                    .replace(",", " ", 1))
    summaries = {
        "simple": f"J'ai lu ce contrat pour toi. J'ai trouvé {len(alerts)} point(s) à surveiller, dont {nb_h} vraiment important(s).{cost_txt} Lis bien les alertes en rouge avant de signer !",
        "normal": f"Analyse du contrat : {len(alerts)} point(s) de vigilance détecté(s), dont {nb_h} critique(s). Score de transparence : {score}/100.{cost_txt}",
        "expert": f"{len(alerts)} clause(s) signalée(s) ({nb_h} à risque élevé), {len(positives)} élément(s) favorable(s). Indice de transparence {score}/100.{cost_txt} Références au Code de la consommation fournies à titre indicatif.",
    }
    questions = []
    ids = {a["id"] for a in alerts}
    if "assurance_imposee" in ids or figures.get("assurance_mensuelle"):
        questions.append("Puis-je souscrire une assurance emprunteur externe à garanties équivalentes ?")
    if "remb_anticipe" in ids:
        questions.append("Quel est le montant exact des pénalités si je rembourse dans 2 ans ?")
    if "frais_dossier" in ids:
        questions.append("Pouvez-vous supprimer ou réduire les frais de dossier ?")
    if "taux_variable" in ids:
        questions.append("Le taux variable est-il plafonné (cap) ? Quel est le pire scénario ?")
    if "revolving" in ids:
        questions.append("Pouvez-vous me proposer un crédit amortissable classique à la place ?")
    if "reconduction" in ids:
        questions.append("Quelle est la date limite pour résilier avant reconduction ?")
    questions.append("Pouvez-vous me remettre la fiche d'information standardisée européenne (FISE) ?")

    return {"mode": "contrat", "score": score, "verdict": verdict, "resume": summaries[level],
            "alertes": alerts, "points_positifs": positives, "chiffres": figures, "cout": cost,
            "questions": questions}


# --------------------------------------------------------------------------- arnaques

SCAM_RULES = [
    dict(id="urgence", cat="Pression", w=18, title="Urgence artificielle",
         pat=[r"\burgent", r"immediatement", r"dans les \d+ ?h", r"sous \d+ ?(h|heures|jours)", r"dernier (rappel|avis)", r"sans delai", r"avant ce soir", r"aujourd.hui (meme|seulement|dernier)", r"\bvite\b", r"expire"],
         txt={"simple": "On te presse pour que tu n'aies pas le temps de réfléchir. C'est LA technique n°1 des escrocs.",
              "normal": "Le message crée un sentiment d'urgence pour court-circuiter votre réflexion.",
              "expert": "Levier d'urgence (scarcity/time pressure) : réduit l'analyse critique, typique de l'ingénierie sociale."}),
    dict(id="menace", cat="Pression", w=15, title="Menace ou intimidation",
         pat=[r"suspendu", r"bloque", r"fermeture", r"poursuites", r"amende", r"majoration", r"desactive", r"cloture", r"penalite", r"huissier"],
         txt={"simple": "On te fait peur (compte bloqué, amende…) pour que tu obéisses.",
              "normal": "Le message utilise la menace (blocage, amende, poursuites) pour vous faire agir.",
              "expert": "Levier de peur/menace de sanction : fréquent dans les fraudes ANTAI, impôts, banque."}),
    dict(id="donnees", cat="Vol de données", w=30, title="Demande de codes ou données bancaires",
         pat=[r"code (de )?(confirmation|validation|securite|secret|sms|recu)", r"mot de passe", r"identifiant", r"\bcvv\b", r"cryptogramme", r"numero de (votre )?carte", r"cle (digitale|securite)", r"valider l.operation", r"communiquer[^.]{0,30}code", r"coordonnees bancaires"],
         txt={"simple": "Ta banque ne te demandera JAMAIS tes codes, ni par SMS, ni par téléphone. Jamais.",
              "normal": "Le message demande des codes ou des données bancaires : aucune institution légitime ne fait cela.",
              "expert": "Collecte de facteurs d'authentification (OTP, identifiants, PAN/CVV) : contournement de la DSP2/SCA."}),
    dict(id="petit_paiement", cat="Hameçonnage", w=20, title="Petit paiement à régler",
         pat=[r"frais (de )?(livraison|reexpedition|douane|port|reexpedition)", r"\b[0-3][,.]\d\d ?(€|eur)", r"regler[^.]{0,40}frais", r"paiement en attente", r"colis (en attente|bloque|retenu)"],
         txt={"simple": "On te demande quelques euros : c'est un prétexte pour voler ta carte bancaire.",
              "normal": "Un petit montant est demandé (frais de livraison, douane) : prétexte classique pour capturer votre carte.",
              "expert": "Micro-paiement leurre : capture des données carte puis enrôlement sur wallet mobile."}),
    dict(id="usurpation", cat="Usurpation", w=12, title="Se fait passer pour un organisme connu",
         pat=[r"\bameli\b", r"assurance maladie", r"\bcaf\b", r"impots", r"dgfip", r"chronopost", r"colissimo", r"la poste", r"\bantai\b", r"crit.air", r"vinted", r"netflix", r"service client", r"votre (banque|conseiller)", r"carte vitale", r"\bcpf\b", r"france travail"],
         txt={"simple": "Le message prétend venir d'un organisme connu. Les escrocs copient leurs logos et leurs noms.",
              "normal": "L'expéditeur se réclame d'un organisme connu : vérifiez via le site ou l'appli officiels, jamais via le lien reçu.",
              "expert": "Usurpation d'identité de marque (brand impersonation) : vérifier l'expéditeur, le domaine et l'alphanumeric sender ID."}),
    dict(id="rib", cat="Fraude au virement", w=30, title="Changement de RIB / IBAN",
         pat=[r"nouve(au|l) (rib|iban)", r"changement de (rib|coordonnees bancaires|banque)", r"(rib|iban)[^.]{0,30}(a change|modifie|mis a jour)"],
         txt={"simple": "On te demande de payer sur un nouveau compte : c'est l'arnaque au faux RIB. Appelle la personne pour vérifier.",
              "normal": "Un changement de coordonnées bancaires est annoncé : vérifiez par un autre canal (téléphone connu).",
              "expert": "Fraude au changement de RIB (BEC) : contre-appel sur numéro de référence obligatoire avant tout virement."}),
    dict(id="faux_conseiller", cat="Faux conseiller", w=30, title="Scénario « faux conseiller »",
         pat=[r"(operation|paiement|virement)s? (frauduleu|suspect)", r"service (des )?fraudes?", r"mettre[^.]{0,30}(fonds|argent|epargne) en securite", r"compte (de )?(securite|securise)", r"annuler (l.operation|le paiement)", r"virement de securite"],
         txt={"simple": "Un faux conseiller fait croire à une fraude pour te faire faire toi-même un virement. Raccroche et rappelle ta banque.",
              "normal": "Scénario du faux conseiller bancaire : on simule une fraude pour vous faire valider une opération.",
              "expert": "Spoofing + ingénierie sociale : la victime authentifie elle-même l'opération (fraude par manipulation, APP fraud)."}),
    dict(id="trop_beau", cat="Appât", w=18, title="Promesse trop belle",
         pat=[r"felicitation", r"vous avez gagne", r"gagnant", r"remboursement de \d", r"vous (avez droit|beneficiez) (a|d)", r"cadeau", r"rendement (garanti|de \d+ ?%)", r"investissement garanti", r"\bcrypto", r"sans risque", r"gains? (rapide|garanti)"],
         txt={"simple": "Si c'est trop beau pour être vrai… c'est que c'est faux.",
              "normal": "Le message promet un gain, un cadeau ou un remboursement inattendu : appât classique.",
              "expert": "Leurre d'appât (gain, remboursement, rendement garanti) : souvent associé à des plateformes d'investissement frauduleuses non agréées AMF."}),
    dict(id="acces_distance", cat="Prise de contrôle", w=30, title="Logiciel de prise en main à distance",
         pat=[r"anydesk", r"teamviewer", r"quicksupport", r"prise (en main|de controle) a distance", r"installer[^.]{0,30}application"],
         txt={"simple": "On veut contrôler ton téléphone ou ton ordi à distance : n'installe RIEN.",
              "normal": "Installation d'un logiciel de contrôle à distance demandée : l'escroc pourrait accéder à votre banque.",
              "expert": "RAT/outil d'administration à distance : compromission totale du terminal et des sessions bancaires."}),
    dict(id="secret", cat="Isolement", w=15, title="Demande de secret",
         pat=[r"confidentiel", r"n.en parle[sz]? a personne", r"discretion", r"ne (le )?dites? (rien|a personne)", r"entre nous"],
         txt={"simple": "On te demande de garder le secret : c'est pour que personne ne te dise que c'est une arnaque.",
              "normal": "Le message demande la discrétion : technique d'isolement de la victime.",
              "expert": "Isolement de la cible (arnaque au président, sentimentale) pour éviter toute contre-vérification."}),
    dict(id="proche", cat="Faux proche", w=25, title="Arnaque « Maman, j'ai changé de numéro »",
         pat=[r"nouveau numero", r"(telephone|portable) (est )?(casse|perdu|tombe)", r"\b(coucou )?(maman|papa)\b[^.]{0,80}(numero|telephone|virement|payer|argent)"],
         txt={"simple": "Un « enfant » qui a un nouveau numéro et besoin d'argent : appelle ton enfant sur son ancien numéro !",
              "normal": "Arnaque au faux proche : vérifiez en appelant la personne sur son numéro habituel.",
              "expert": "Fraude « Hi Mum » : usurpation d'un proche sur messagerie, demande de virement instantané."}),
    dict(id="rappel", cat="Hameçonnage", w=10, title="Vous invite à rappeler un numéro",
         pat=[r"(rappele[rz]|appele[rz]|contacte[rz])[^.]{0,30}(\+33|0[1-9])[\d .]{8,}", r"\b08 ?9\d"],
         txt={"simple": "Ne rappelle pas le numéro du message : utilise celui écrit au dos de ta carte bancaire.",
              "normal": "Un numéro à rappeler est fourni : utilisez uniquement les numéros officiels que vous connaissez.",
              "expert": "Callback phishing (vishing) : numéro contrôlé par l'escroc, souvent surtaxé."}),
]


def analyze_message(text: str, level: str = "normal", qr: list[str] | None = None) -> dict:
    text = norm(text)
    f = fold(text)
    alerts, score = [], 0
    for r in SCAM_RULES:
        q = _find(text, f, r["pat"])
        if q:
            sev = "haute" if r["w"] >= 25 else "moyenne" if r["w"] >= 15 else "faible"
            alerts.append({"id": r["id"], "titre": r["title"], "categorie": r["cat"], "gravite": sev,
                           "explication": r["txt"][level], "citation": q, "source": "règles"})
            score += r["w"]

    found = urls.extract_urls(text)
    qr = qr or []
    url_results = [urls.analyze_url(u) for u in found]
    for code in qr:
        res = urls.analyze_url(code) if re.search(r"[a-z0-9-]+\.[a-z]{2,}", code, re.I) else \
            {"url": code, "domaine": "", "risque": "inconnu", "score": 0, "raisons": ["Contenu QR non web"]}
        res["via_qr"] = True
        url_results.append(res)
    worst = max([u["score"] for u in url_results], default=0)
    if worst:
        score += worst * 0.6
        dangerous = [u for u in url_results if u["risque"] in ("dangereux", "suspect")]
        if dangerous:
            u = dangerous[0]
            alerts.append({"id": "lien", "titre": "Lien piégé détecté" + (" (via QR code)" if u.get("via_qr") else ""),
                           "categorie": "Lien", "gravite": "haute" if u["risque"] == "dangereux" else "moyenne",
                           "explication": {"simple": f"Le lien {u['domaine']} n'est pas un vrai site officiel. Ne clique pas !",
                                           "normal": f"Le lien {u['domaine']} présente des signaux d'hameçonnage : " + "; ".join(u["raisons"][:2]) + ".",
                                           "expert": f"Domaine {u['domaine']} (score {u['score']}/100) : " + "; ".join(u["raisons"]) + "."}[level],
                           "citation": u["url"], "source": "analyse de lien"})
    if url_results and len({a["categorie"] for a in alerts}) >= 2:
        score += 10
    score = int(min(100, score))
    if any(a["id"] in ("donnees", "faux_conseiller", "rib", "acces_distance") for a in alerts):
        score = max(score, 70)
    verdict = "arnaque" if score >= 60 else "suspect" if score >= 30 else "légitime"

    order = {"haute": 0, "moyenne": 1, "faible": 2}
    alerts.sort(key=lambda a: order[a["gravite"]])

    if verdict == "arnaque":
        actions = ["Ne cliquez sur aucun lien et ne répondez pas au message.",
                   "Ne communiquez jamais vos codes, mots de passe ou numéro de carte.",
                   "Contactez votre banque via le numéro au dos de votre carte ou votre appli officielle.",
                   "Signalez le SMS en le transférant gratuitement au 33700.",
                   "Signalez l'arnaque sur cybermalveillance.gouv.fr ou au 17Cyber.",
                   "Si vous avez déjà payé ou donné vos codes : faites opposition immédiatement et portez plainte."]
    elif verdict == "suspect":
        actions = ["Ne cliquez pas sur le lien : allez directement sur le site ou l'appli officiels.",
                   "Vérifiez l'information en contactant l'organisme par un canal que vous connaissez.",
                   "En cas de doute, demandez l'avis d'un proche ou de votre conseiller.",
                   "Signalez le message au 33700 s'il s'agit d'un SMS."]
    else:
        actions = ["Aucun signal d'arnaque majeur détecté.",
                   "Restez prudent : ne communiquez jamais vos codes, même à un interlocuteur de confiance.",
                   "Préférez toujours l'appli officielle aux liens reçus par message."]

    titles = ", ".join(a["titre"].lower() for a in alerts[:3])
    summaries = {
        "arnaque": {"simple": f"Attention, c'est très probablement une ARNAQUE ! Je vois : {titles}. Ne fais rien de ce que demande ce message.",
                    "normal": f"Ce message présente les caractéristiques d'une arnaque (risque {score}/100). Signaux principaux : {titles}.",
                    "expert": f"Score de risque {score}/100. {len(alerts)} indicateur(s) de fraude : {titles}. Recommandation : blocage et signalement."},
        "suspect": {"simple": f"Ce message est louche. Je vois : {titles}. Vérifie avant de faire quoi que ce soit.",
                    "normal": f"Message suspect (risque {score}/100). Signaux : {titles}. Vérifiez par un canal officiel.",
                    "expert": f"Score de risque {score}/100, signaux faibles à modérés : {titles}. Contre-vérification hors bande recommandée."},
        "légitime": {"simple": "Je n'ai pas trouvé de signe d'arnaque dans ce message. Mais reste toujours prudent !",
                     "normal": f"Aucun signal d'arnaque majeur détecté (risque {score}/100).",
                     "expert": f"Score de risque {score}/100 : pas d'indicateur de fraude significatif détecté par les règles."},
    }[verdict][level]

    return {"mode": "arnaque", "score": score, "verdict": verdict, "resume": summaries, "alertes": alerts,
            "liens": url_results, "qr": qr, "actions": actions}
