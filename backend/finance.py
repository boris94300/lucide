"""Calculs financiers déterministes : coût réel d'un crédit."""


def mensualite(capital: float, taux_annuel_pct: float, duree_mois: int) -> float:
    if duree_mois <= 0:
        return 0.0
    r = taux_annuel_pct / 100 / 12
    if r == 0:
        return capital / duree_mois
    return capital * r / (1 - (1 + r) ** -duree_mois)


def taux_depuis_mensualite(capital: float, mens: float, duree_mois: int) -> float:
    lo, hi = 0.0, 100.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if mensualite(capital, mid, duree_mois) > mens:
            hi = mid
        else:
            lo = mid
    return round((lo + hi) / 2, 2)


def cout_credit(figures: dict) -> dict | None:
    capital = figures.get("montant")
    duree = figures.get("duree_mois")
    taux = figures.get("taux_nominal")
    mens = figures.get("mensualite")
    if not capital or not duree:
        return None
    duree = int(duree)
    if taux is None and mens:
        taux = taux_depuis_mensualite(capital, mens, duree)
    if taux is None:
        taux = figures.get("taeg")
    if taux is None:
        return None
    m = mensualite(capital, taux, duree)
    assurance_m = figures.get("assurance_mensuelle") or 0.0
    frais = figures.get("frais_dossier") or 0.0
    interets = m * duree - capital
    assurance = assurance_m * duree
    cout_total = interets + assurance + frais

    restant, cumul_int, serie = capital, 0.0, []
    r = taux / 100 / 12
    for mois in range(1, duree + 1):
        i = restant * r
        cumul_int += i
        restant -= m - i
        if mois % 12 == 0 or mois == duree:
            serie.append({"mois": mois, "capital_restant": round(max(restant, 0), 2),
                          "interets_cumules": round(cumul_int, 2)})

    return {
        "capital": round(capital, 2),
        "taux_utilise": round(taux, 2),
        "duree_mois": duree,
        "mensualite_hors_assurance": round(m, 2),
        "mensualite_avec_assurance": round(m + assurance_m, 2),
        "total_interets": round(interets, 2),
        "total_assurance": round(assurance, 2),
        "frais_dossier": round(frais, 2),
        "cout_total": round(cout_total, 2),
        "total_rembourse": round(capital + cout_total, 2),
        "pourcentage_du_capital": round(cout_total / capital * 100, 1),
        "serie": serie,
    }
