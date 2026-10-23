"""Analyse heuristique des liens et QR codes."""
import re
from urllib.parse import urlparse

OFFICIAL = {
    "ameli": ["ameli.fr"], "assurance maladie": ["ameli.fr"], "caf": ["caf.fr"],
    "impots": ["impots.gouv.fr"], "laposte": ["laposte.fr", "laposte.net"],
    "colissimo": ["colissimo.fr", "laposte.fr"], "chronopost": ["chronopost.fr"],
    "antai": ["antai.gouv.fr"], "bnp": ["bnpparibas.net", "bnpparibas.com", "mabanque.bnpparibas"],
    "societegenerale": ["societegenerale.fr", "particuliers.sg.fr"], "credit-agricole": ["credit-agricole.fr"],
    "creditagricole": ["credit-agricole.fr"], "labanquepostale": ["labanquepostale.fr"], "lcl": ["lcl.fr"],
    "boursorama": ["boursorama.com", "boursobank.com"], "banquepopulaire": ["banquepopulaire.fr"],
    "caisse-epargne": ["caisse-epargne.fr"], "creditmutuel": ["creditmutuel.fr"], "revolut": ["revolut.com"],
    "paypal": ["paypal.com", "paypal.fr"], "netflix": ["netflix.com"], "amazon": ["amazon.fr", "amazon.com"],
    "vinted": ["vinted.fr", "vinted.com"], "ants": ["ants.gouv.fr"], "francetravail": ["francetravail.fr"],
}
OFFICIAL_DOMAINS = sorted({d for v in OFFICIAL.values() for d in v})
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "cutt.ly", "is.gd", "urlz.fr", "shorturl.at", "rb.gy",
              "ow.ly", "goo.gl", "tiny.cc", "s.id", "rebrand.ly", "t.ly"}
SUSPICIOUS_TLDS = {"xyz", "top", "info", "click", "shop", "online", "site", "live", "icu", "buzz", "cc",
                   "ru", "tk", "ml", "ga", "cf", "gq", "work", "support", "help", "app", "link", "vip"}
KEYWORDS = ["secure", "securite", "login", "verif", "update", "confirm", "compte", "rembours",
            "suivi", "colis", "facture", "paiement", "client", "auth", "valid"]

URL_RE = re.compile(
    r"(?:https?://[^\s<>\"')\]]+)|(?:www\.[^\s<>\"')\]]+)|"
    r"(?:\b[a-z0-9][a-z0-9\-]{1,62}(?:\.[a-z0-9\-]{1,62})*\.(?:fr|com|net|org|info|xyz|top|click|shop|online|site|live|icu|buzz|cc|ru|tk|io|me|ly|co|app|link|vip|support|help|gouv\.fr)(?:/[^\s<>\"')\]]*)?)",
    re.I)


def _lev(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def extract_urls(text: str) -> list[str]:
    seen, out = set(), []
    for m in URL_RE.finditer(text):
        u = m.group(0).rstrip(".,;:!?")
        if "@" in text[max(0, m.start() - 1):m.start()]:
            continue
        if u.lower() not in seen:
            seen.add(u.lower())
            out.append(u)
    return out


def _registered(host: str) -> str:
    parts = host.split(".")
    if host.endswith(".gouv.fr") and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def analyze_url(raw: str) -> dict:
    url = raw if re.match(r"^https?://", raw, re.I) else "http://" + raw
    p = urlparse(url)
    host = (p.hostname or "").lower()
    reg = _registered(host)
    reasons, score = [], 0

    official = any(host == d or host.endswith("." + d) for d in OFFICIAL_DOMAINS)
    if official:
        return {"url": raw, "domaine": host, "risque": "fiable", "score": 0,
                "raisons": ["Domaine officiel connu"]}

    if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", host):
        reasons.append("Adresse IP brute au lieu d'un nom de domaine"); score += 40
    if host in SHORTENERS or reg in SHORTENERS:
        reasons.append("Lien raccourci : la vraie destination est masquée"); score += 30
    if "xn--" in host:
        reasons.append("Domaine en punycode (caractères trompeurs)"); score += 40
    tld = host.rsplit(".", 1)[-1] if "." in host else ""
    if tld in SUSPICIOUS_TLDS:
        reasons.append(f"Extension .{tld} très utilisée par les arnaqueurs"); score += 20
    flat = host.replace("-", "").replace(".", "")
    for brand, domains in OFFICIAL.items():
        b = brand.replace(" ", "").replace("-", "")
        if b in flat:
            reasons.append(f"Imite la marque « {brand} » mais n'est pas son site officiel ({domains[0]})")
            score += 45
            break
    else:
        name = reg.split(".")[0]
        for d in OFFICIAL_DOMAINS:
            dn = d.split(".")[0]
            if len(dn) >= 4 and 0 < _lev(name, dn) <= 2:
                reasons.append(f"Ressemble fortement à {d} (typosquatting)"); score += 45
                break
    if host.count("-") >= 2:
        reasons.append("Nombreux tirets dans le domaine"); score += 10
    if host.count(".") >= 3:
        reasons.append("Beaucoup de sous-domaines"); score += 10
    kws = [k for k in KEYWORDS if k in (host + p.path).lower()]
    if kws:
        reasons.append("Mots-clés d'hameçonnage : " + ", ".join(kws[:4])); score += 10 + 5 * min(len(kws), 3)
    if p.scheme == "http" and raw.lower().startswith("http://"):
        reasons.append("Connexion non chiffrée (http)"); score += 10

    score = min(score, 100)
    risque = "dangereux" if score >= 45 else "suspect" if score >= 20 else "inconnu"
    if not reasons:
        reasons.append("Aucun signal évident, mais domaine inconnu : prudence")
    return {"url": raw, "domaine": host, "risque": risque, "score": score, "raisons": reasons}
