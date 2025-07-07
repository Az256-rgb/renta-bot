# -------------------------------------------------------------
# Streamlit – Jinka Rentabilité Bot (tout‑en‑un, un seul fichier)
# -------------------------------------------------------------
# Dépendances :  
#   pip install streamlit pandas requests python-dotenv
#            (et facultatif : kajin pour requête simplifiée API Jinka)
# Lancer localement :  streamlit run streamlit_jinka_app.py
# Hébergement : push ce fichier sur Streamlit Cloud ; ajouter vos
# variables d’environnement dans "Secrets" :
#   JINKA_MAIL, JINKA_PASS  (ou JINKA_TOKEN)
#   FRAIS_NOTAIRE_PERC      (optionnel, ex 0.07)
#   SMTP_* inutiles ici car on n’envoie pas de mail depuis Streamlit.
# -------------------------------------------------------------
import os, json, requests, datetime as dt
import pandas as pd
import streamlit as st

# ---------- Fonctions utilitaires -----------------------------------------
@st.cache_data(show_spinner=False)
def load_rent_table(csv_url_or_path: str) -> pd.DataFrame:
    """Charge le CSV loyers (cols: secteur, med_m2)."""
    return pd.read_csv(csv_url_or_path, dtype={"secteur": str, "med_m2": float})


def auth_jinka(email: str, password: str) -> str:
    """Retourne un token Bearer Jinka via l’API publique."""
    login_url = "https://api.jinka.fr/apiv2/auth/login"
    r = requests.post(login_url, json={"email": email, "password": password}, timeout=12)
    r.raise_for_status()
    return r.json()["token"]


def fetch_ads(token: str, alert_id: str) -> list[dict]:
    """Récupère les annonces liées à l’alerte Jinka."""
    url = f"https://api.jinka.fr/apiv2/alert/{alert_id}/ads"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
    r.raise_for_status()
    return r.json().get("ads", [])


def compute_yield(ad: dict, med_m2: float, frais_notaire: float) -> float:
    """Calcule le rendement brut pour l’annonce."""
    loyer_theo = med_m2 * ad["surface"]
    return (loyer_theo * 12) / (ad["price"] * (1 + frais_notaire))


# ---------- Interface Streamlit -------------------------------------------
st.set_page_config(page_title="Jinka ▶ Rentabilité Toulouse", page_icon="📊", layout="wide")
st.title("📊 Analyse instantanée de rentabilité – Jinka ➜ Toulouse")

with st.sidebar:
    st.header("🔑 Connexion Jinka")
    email = st.text_input("Email", value=os.getenv("JINKA_MAIL", ""))
    pwd = st.text_input("Mot de passe", type="password", value=os.getenv("JINKA_PASS", ""))
    token_env = os.getenv("JINKA_TOKEN", "")
    st.divider()

    st.header("⚙️  Paramètres")
    alert_id = st.text_input("ID de l'alerte", placeholder="ex : 123456")
    max_price = st.number_input("Prix max (€)", 50000, 300000, 150000, 5000)
    min_surface = st.number_input("Surface min (m²)", 10, 120, 60, 5)
    min_yield = st.slider("Rendement brut min (%)", 4.0, 15.0, 9.0, 0.1)
    frais_notaire = float(os.getenv("FRAIS_NOTAIRE_PERC", 0.07))

    st.divider()
    csv_url = st.text_input("CSV loyers (URL ou chemin)",
                            "https://raw.githubusercontent.com/user/loyers/main/toulouse_2024.csv")
    refresh = st.button("🚀 Analyser maintenant")

# ---------- Corps ---------------------------------------------------------
if refresh:
    try:
        loyers_df = load_rent_table(csv_url)
    except Exception as e:
        st.error(f"Erreur chargement loyers : {e}")
        st.stop()

    # Auth Jinka
    try:
        token = token_env or auth_jinka(email, pwd)
    except Exception as e:
        st.error(f"Échec authentification Jinka : {e}")
        st.stop()

    # Fetch ads
    try:
        ads = fetch_ads(token, alert_id)
    except Exception as e:
        st.error(f"Erreur appel API : {e}")
        st.stop()

    if not ads:
        st.info("Aucune annonce renvoyée (alerte vide ou ID incorrect).")
        st.stop()

    # Prépare DataFrame
    rows = []
    for ad in ads:
        if ad["price"] > max_price or ad["surface"] < min_surface:
            continue
        cp = str(ad.get("zipcode") or ad.get("postal_code"))
        med_row = loyers_df.loc[loyers_df["secteur"] == cp]
        if med_row.empty:
            continue
        med_m2 = med_row.iloc[0]["med_m2"]
        brut = compute_yield(ad, med_m2, frais_notaire)
        if brut < min_yield/100:
            continue
        rows.append({
            "Titre": ad["title"],
            "Prix (€)": ad["price"],
            "Surf (m²)": ad["surface"],
            "CP": cp,
            "Loyer théorique (€)": round(med_m2*ad["surface"]),
            "Rdt brut %": round(brut*100,2),
            "URL": ad["url"]
        })

    if not rows:
        st.warning("Aucune annonce ne remplit les critères.")
        st.stop()

    df = pd.DataFrame(rows).sort_values("Rdt brut %", ascending=False)
    st.success(f"💡 {len(df)} opportunité(s) ≥ {min_yield}% brut trouvées le {dt.datetime.now().strftime('%d/%m/%Y %H:%M')}")
    st.dataframe(df, use_container_width=True)

    # Téléchargement CSV
    csv = df.to_csv(index=False).encode()
    st.download_button("📂 Télécharger CSV", csv, "opportunites.csv", "text/csv")

else:
    st.info("Remplis tes paramètres dans la barre latérale puis clique sur **Analyser maintenant**.")
