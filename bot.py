#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bot.py – Jinka ▶ Mail + Notion alertes ≥ 9 % brut
Exécuté par GitHub Actions toutes les 30 minutes.
"""

import os, json, smtplib, ssl, datetime as dt, requests
from email.message import EmailMessage
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Paramètres personnalisables
# ---------------------------------------------------------------------------
ALERT_ID   = "123456"          # <-- ton ID d’alerte Jinka
MAX_PRICE  = 150_000           # € max
MIN_SURF   = 60                # m² min
MIN_YIELD  = 0.09              # 9 % brut mini
F_NOTAIRE  = 0.07              # 7 % frais actes
# ---------------------------------------------------------------------------

# charges non récupérables (utilisées pour éventuel calcul futur)
CHARGES_AN = 2_700             

# loyers médians €/m² codé en dur
MEDIAN_RENTS = {
    "31000": 14.1,
    "31300": 12.4,
    "31400": 12.9,
    "31200": 11.2,
    "31500": 11.7,
    "31100": 11.5,
    # ajoute ou modifie selon tes données...
}

# fichiers & dossiers
ROOT  = Path(__file__).parent
DATA_DIR = ROOT / "data"
SEENF = DATA_DIR / "seen_ids.json"
DATA_DIR.mkdir(exist_ok=True)
SEEN = json.loads(SEENF.read_text()) if SEENF.exists() else []

# ---------------------------------------------------------------------------
# 2. Auth Jinka + récupération des annonces
# ---------------------------------------------------------------------------
LOGIN_URL = "https://api.jinka.fr/apiv2/auth/login"
ALERT_URL = f"https://api.jinka.fr/apiv2/alert/{ALERT_ID}/ads"

def jinka_token(email: str, pwd: str) -> str:
    r = requests.post(LOGIN_URL, json={"email": email, "password": pwd}, timeout=12)
    r.raise_for_status()
    return r.json()["token"]

def fetch_ads(token: str) -> list[dict]:
    r = requests.get(ALERT_URL,
                     headers={"Authorization": f"Bearer {token}"}, timeout=15)
    r.raise_for_status()
    return r.json().get("ads", [])

token = jinka_token(os.environ["JINKA_MAIL"], os.environ["JINKA_PASS"])
ads   = fetch_ads(token)

# ---------------------------------------------------------------------------
# 3. Filtrage + calcul rentabilité
# ---------------------------------------------------------------------------
def brut_rentability(price: int, surface: float, med_m2: float) -> float:
    loyer_th = med_m2 * surface
    return (loyer_th * 12) / (price * (1 + F_NOTAIRE))

nouveaux = []
for ad in ads:
    if ad["id"] in SEEN:
        continue
    price, surf = ad["price"], ad["surface"]
    if price > MAX_PRICE or surf < MIN_SURF:
        continue
    cp = str(ad.get("zipcode") or ad.get("postal_code"))
    med_m2 = MEDIAN_RENTS.get(cp)
    if med_m2 is None:
        continue
    brut = brut_rentability(price, surf, med_m2)
    if brut < MIN_YIELD:
        continue
    # stocke pour mail
    nouveaux.append({
        "id": ad["id"],
        "title": ad["title"],
        "price": price,
        "surface": surf,
        "brut": brut,
        "url": ad["url"]
    })
    SEEN.append(ad["id"])

# ---------------------------------------------------------------------------
# 4. Envoi de l'e-mail si besoin
# ---------------------------------------------------------------------------
if nouveaux:
    now = dt.datetime.now().strftime("%d/%m/%Y %H:%M")
    lines = [
        f"{n['title']} | {n['surface']} m² | {n['price']} € | {round(n['brut']*100,2)} % brut\n{n['url']}"
        for n in nouveaux
    ]
    body = "\n\n".join(lines)

    msg = EmailMessage()
    msg["Subject"] = f"[Jinka] {len(nouveaux)} annonce(s) ≥ 9 % brut ({now})"
    msg["From"]    = os.environ["SMTP_FROM"]
    msg["To"]      = os.environ["SMTP_TO"]
    msg.set_content(body)

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(os.environ["SMTP_HOST"], 465, context=ctx) as s:
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
        s.send_message(msg)

# ---------------------------------------------------------------------------
# 5. Push vers Notion (optionnel)
# ---------------------------------------------------------------------------
NOTION_TOKEN      = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
if nouveaux and NOTION_TOKEN and NOTION_DATABASE_ID:
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    for n in nouveaux:
        payload = {
            "parent": { "database_id": NOTION_DATABASE_ID },
            "properties": {
                "Titre": {
                    "title": [ { "text": { "content": n["title"] } } ]
                },
                "Prix":   { "number": n["price"] },
                "Surface":{ "number": n["surface"] },
                "Rendement brut": { "number": round(n["brut"]*100,2) },
                "URL":     { "url": n["url"] }
            }
        }
        r = requests.post("https://api.notion.com/v1/pages",
                          headers=headers, json=payload)
        try: r.raise_for_status()
        except Exception as e:
            print("Erreur Notion:", e)

# ---------------------------------------------------------------------------
# 6. Sauvegarde des IDs déjà vus
# ---------------------------------------------------------------------------
SEENF.write_text(json.dumps(SEEN))
