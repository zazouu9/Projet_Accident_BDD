import os
import pandas as pd
import folium
from folium.plugins import MarkerCluster
import html
from dictionnaire import *

CSV_PATH = "results/accidents_carte_complet.csv"
FILTRE_PATH = "resultat_filtre.txt"
OUT_HTML = "static/carte_accidents.html"


def read_filters_txt(path: str) -> dict:
    """Lit resultat_filtre.txt : une ligne = cle:valeur."""
    filtres = {}
    if not os.path.exists(path):
        return filtres
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or ":" not in line:
                continue
            k, v = line.split(":", 1)
            filtres[k.strip()] = v.strip()
    return filtres


def to_int(x):
    if x is None:
        return None
    x = str(x).strip()
    if x == "":
        return None
    try:
        return int(x)
    except:
        return None


def grav_to_color(grav):
    try:
        return GRAV_TO_COLOR.get(int(grav), "gray")
    except:
        return "gray"


def popup_pre(row):
    # Ajout dep dans le popup (plus clair pour l’utilisateur)
    dep = str(row.get("dep", "")).strip()

    heure = int(row["heure"])
    zone = int(row["zone"])
    catr = int(row["catr"])
    grav = int(row["grav"])
    sexe = int(row["sexe"])
    catv = int(row["catv"])

    lines = [
        f"Département : {dep if dep else 'Inconnu'}",
        f"Heure : {heure}h",
        f"Zone : {ZONE_TO_LABEL.get(zone, 'Inconnu')} ({zone})",
        f"Type de route : {CATR_TO_ROUTE.get(catr, 'Inconnu')} ({catr})",
        f"Gravité : {GRAV_TO_LABEL.get(grav, 'Inconnu')} ({grav})",
        f"Sexe : {SEXE_TO_LABEL.get(sexe, 'Inconnu')} ({sexe})",
        f"Type de vehicule : {CATV_TO_LABEL.get(catv, 'Inconnu')} ({catv})",
        f"Lat : {row['lat']}",
        f"Long : {row['long']}",
    ]

    txt = "\r\n".join(lines)
    popup_html = (
        "<pre style='margin:0; white-space:pre; font-family:inherit;'>"
        f"{html.escape(txt)}"
        "</pre>"
    )
    return popup_html, 600


# CHARGEMENT CSV
if not os.path.exists(CSV_PATH):
    raise FileNotFoundError(f"Fichier introuvable: {CSV_PATH}")

df = pd.read_csv(CSV_PATH, dtype=str)

# Ajout dep dans les colonnes obligatoires
required_cols = ["heure", "dep", "zone", "catr", "grav", "sexe", "catv", "lat", "long"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise ValueError(f"Colonnes manquantes dans le CSV: {missing}")

# conversions (on garde dep en string pour préserver 2A/2B/971 etc.)
for c in ["heure", "zone", "catr", "grav", "sexe", "catv"]:
    df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

df["dep"] = df["dep"].astype(str).str.strip()

df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
df["long"] = pd.to_numeric(df["long"], errors="coerce")
df = df.dropna(subset=["lat", "long"]).copy()

# LECTURE FILTRES
f = read_filters_txt(FILTRE_PATH)
mask = pd.Series(True, index=df.index)

#FILTRE HEURE MIN/MAX 
hmin = to_int(f.get("h_min"))
hmax = to_int(f.get("h_max"))

if hmin is not None and hmax is None:
    mask &= (df["heure"] == hmin)
else:
    if hmin is not None:
        mask &= (df["heure"] >= hmin)
    if hmax is not None:
        mask &= (df["heure"] <= hmax)

# --- GRAVITE ---
grav_txt = f.get("gravite", "").strip()
if grav_txt:
    grav_list = []
    for p in grav_txt.split(";"):
        gi = to_int(p)
        if gi is not None:
            grav_list.append(gi)
    if grav_list:
        mask &= df["grav"].isin(grav_list)

# ROUTE 
route_txt = f.get("route", "").strip()
if route_txt:
    code = ROUTE_TO_CATR.get(route_txt)
    if code is not None:
        mask &= (df["catr"] == code)

# CATV
cv = to_int(f.get("catv"))
if cv is not None:
    mask &= (df["catv"] == cv)

# SEXE
sv = to_int(f.get("sexe"))
if sv is not None:
    mask &= (df["sexe"] == sv)

# DEPARTEMENT 
dep_txt = f.get("dep", "").strip()
if dep_txt:
    # comparaison simple (dep est en string)
    mask &= (df["dep"] == dep_txt)

df_filtre = df[mask].copy()

print("Filtres lus :", f)
print("Total lignes CSV :", len(df))
print("Total lignes filtrées :", len(df_filtre))

# CARTE
os.makedirs("static", exist_ok=True)

center = [46.2276, 2.2137]
if not df_filtre.empty:
    center = [df_filtre["lat"].mean(), df_filtre["long"].mean()]

m = folium.Map(location=center, zoom_start=6)

cluster = MarkerCluster(
    name="Accidents",
    options={"disableClusteringAtZoom": 14}
).add_to(m)

if df_filtre.empty:
    folium.Marker(center, popup="Aucun accident trouvé pour ces filtres.").add_to(m)
else:
    for _, row in df_filtre.iterrows():
        popup_html, w = popup_pre(row)
        color = grav_to_color(row["grav"])

        folium.CircleMarker(
            location=[row["lat"], row["long"]],
            radius=4,
            color=color,
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(popup_html, max_width=w),
        ).add_to(cluster)

m.save(OUT_HTML)
print(f"Succès : Carte générée avec {len(df_filtre)} points dans {OUT_HTML}")
