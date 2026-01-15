import os
import pandas as pd
import folium
import html
from dictionnaire import *

CSV_PATH = "results/accidents_carte_complet.csv"
FILTRE_PATH = "resultat_filtre.txt"
OUT_HTML = "static/carte_accidents.html"

def read_filters_txt(path: str) -> dict:
    filtres = {}
    if not os.path.exists(path):
        return filtres
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or ":" in line == False:
                continue
            parts = line.split(":", 1)
            if len(parts) == 2:
                filtres[parts[0].strip()] = parts[1].strip()
    return filtres

def to_int(x):
    if x is None: return None
    x = str(x).strip()
    try:
        return int(x)
    except:
        return None

def popup_html(row):
    heure = int(row["heure"])
    zone = int(row["zone"])
    catr = int(row["catr"])
    grav = int(row["grav"])
    sexe = int(row["sexe"])
    catv = int(row["catv"])

    lines = [
        f"Heure : {heure}h",
        f"Zone : {ZONE_TO_LABEL.get(zone, 'Inconnu')} ({zone})",
        f"Type de route : {CATR_TO_ROUTE.get(catr, 'Inconnu')} ({catr})",
        f"Gravité : {GRAV_TO_LABEL.get(grav, 'Inconnu')} ({grav})",
        f"Sexe : {SEXE_TO_LABEL.get(sexe, 'Inconnu')} ({sexe})",
        f"Type de vehicule : {CATV_TO_LABEL.get(catv, 'Inconnu')} ({catv})",
        f"Lat : {row['lat']}",
        f"Long : {row['long']}",
    ]

    # largeur dynamique estimée via la ligne la plus longue
    longest = max(len(s) for s in lines)
    max_width = min(max(340, longest * 8), 1200)

    # HTML minimal: <pre> = 1 ligne par champ garanti
    txt = "\n".join(lines)
    popup = f"<pre style='margin:0'>{html.escape(txt)}</pre>"

    return popup, max_width



# --- chargement CSV ---
if not os.path.exists(CSV_PATH):
    print(f"Erreur : Le fichier {CSV_PATH} est introuvable.")
    exit(1)

df = pd.read_csv(CSV_PATH, dtype=str)

# conversions
for c in ["heure", "catr", "grav", "sexe", "catv"]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
df["long"] = pd.to_numeric(df["long"], errors="coerce")
df = df.dropna(subset=["lat", "long"]).copy()

# --- lecture filtres txt ---
f = read_filters_txt(FILTRE_PATH)

# --- application filtres ---
mask = pd.Series(True, index=df.index)

hv = to_int(f.get("heure"))
if hv is not None:
    mask &= (df["heure"] == hv)

grav_txt = f.get("gravite", "").strip()
if grav_txt != "":
    grav_list = [to_int(p) for p in grav_txt.split(";") if to_int(p) is not None]
    if grav_list:
        mask &= df["grav"].isin(grav_list)

route_txt = f.get("route", "").strip()
if route_txt != "" and route_txt in CATR_TO_ROUTE:
    mask &= (df["catr"] == CATR_TO_ROUTE[route_txt])

cv = to_int(f.get("catv"))
if cv is not None:
    mask &= (df["catv"] == cv)

sv = to_int(f.get("sexe"))
if sv is not None:
    mask &= (df["sexe"] == sv)

df_filtre = df[mask].copy()

# --- génération carte ---
# Centre par défaut sur la France si vide
center = [46.2276, 2.2137]
if not df_filtre.empty:
    center = [df_filtre["lat"].mean(), df_filtre["long"].mean()]

m = folium.Map(location=center, zoom_start=6)

if df_filtre.empty:
    folium.Marker(center, popup="Aucun accident trouvé pour ces filtres.").add_to(m)
else:
    for _, row in df_filtre.iterrows():
        popup, width = popup_html(row)

        folium.CircleMarker(
            location=[row["lat"], row["long"]],
            radius=4,
            color="red",
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(popup, max_width=width),
        ).add_to(m)



m.save(OUT_HTML)
print(f"Succès : Carte générée avec {len(df_filtre)} points dans {OUT_HTML}")