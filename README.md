# 📊 Toulouse Rent Yield Bot

**Toulouse‑Renta‑Bot** est une application Streamlit tout‑en‑un qui :

1. Se connecte à votre compte **Jinka** et récupère les dernières annonces de votre alerte (ID configurable).
2. Applique vos filtres (prix max, surface mini, rendement brut mini…).
3. Calcule la **rentabilité brute** à partir :

   * du prix du bien ;
   * d’un loyer théorique (loyer médian €/m² tiré d’un CSV local ou distant) ;
   * d’une hypothèse de frais de notaire (%).
4. Affiche en temps réel les annonces éligibles (tableau interactif), avec bouton **Télécharger CSV**.

---

## 🚀 Lancer l’appli en local

```bash
# 1. Cloner le repo puis placer‑vous dedans
pip install -r requirements.txt
streamlit run streamlit_jinka_app.py
```

> Les variables d’environnement `JINKA_MAIL`, `JINKA_PASS` ou `JINKA_TOKEN` peuvent être mises dans un fichier **.env** (chargé automatiquement par *python‑dotenv*).

```
JINKA_MAIL=you@example.com
JINKA_PASS=YourSuperSecretPwd
# ou
JINKA_TOKEN=<token JWT fourni par Jinka>
FRAIS_NOTAIRE_PERC=0.07
```

Ouvrez ensuite `http://localhost:8501` dans votre navigateur.

---

## ☁️ Déploiement Streamlit Cloud

1. Créez un nouveau projet **Streamlit Community Cloud** → pointez vers ce dépôt.
2. Définissez vos *Secrets* dans **Settings > Secrets** :

```
JINKA_MAIL="…"
JINKA_PASS="…"   # ou JINKA_TOKEN
FRAIS_NOTAIRE_PERC="0.07"
```

3. Laissez le champ “Main file” sur `streamlit_jinka_app.py` et déployez.

---

## 📂 Structure minimale du dépôt

```
streamlit_jinka_app.py   # application Streamlit
requirements.txt         # dépendances Python
README.md                # ce fichier
loyers_tlse_2024.csv     # loyers médian €/m² par secteur ou CP
└── data/
    └── seen_ids.json    # créé par l’appli si besoin (liste d’annonces déjà vues)
```

---

## 🔧 Personnaliser les loyers

Remplacez `loyers_tlse_2024.csv` par votre propre table :

| secteur (str) | med\_m2 (float) |
| ------------- | --------------- |
| 31500         | 11.7            |
| 31200         | 11.2            |
| …             | …               |

Le programme fait un *lookup* sur la colonne **secteur** à partir du code postal de l’annonce ; adaptez si vous préférez un découpage IRIS/quartier.

---

## ✉️ Contact & licence

Libre d’usage pour un usage personnel (MIT). Contribs bienvenues ! 🔥
