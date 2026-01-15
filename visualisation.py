import os
import pandas as pd
import folium

CSV_PATH = "results/accidents_carte_complet.csv"
FILTRE_PATH = "resultat_filtre.txt"
OUT_HTML = "static/carte_accidents.html"

# route libellé -> catr
ROUTE_TO_CATR = {
    "Autoroute": 1,
    "Nationale": 2,
    "Départementale": 3,
    "Communale": 4,
    "Hors réseau public": 5,
    "Parc de stationnement ouvert à la circulation publique": 6,
    "Routes de métropole urbaine": 7,
    "Autre": 9,
}
CATR_TO_ROUTE = {v: k for k, v in ROUTE_TO_CATR.items()}

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
if route_txt != "" and route_txt in ROUTE_TO_CATR:
    mask &= (df["catr"] == ROUTE_TO_CATR[route_txt])

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
        # On prépare les variables proprement AVANT la f-string pour éviter les erreurs de guillemets
        h = f"{int(row['heure'])}h" if not pd.isna(row['heure']) else "N/A"
        g = f"{int(row['grav'])}" if not pd.isna(row['grav']) else "N/A"
        
        # Gestion propre du libellé de la route
        r_val = to_int(row['catr'])
        r_txt = CATR_TO_ROUTE.get(r_val, f"Code {r_val}") if r_val is not None else "N/A"
        
        v = f"{int(row['catv'])}" if not pd.isna(row['catv']) else "N/A"
        s = "Masculin" if row['sexe'] == 1 else "Féminin" if row['sexe'] == 2 else "N/A"

        popup_txt = f"Heure: {h} | Gravité: {g} | Route: {r_txt} | Véhicule: {v} | Sexe: {s}"

        folium.CircleMarker(
            location=[row["lat"], row["long"]],
            radius=4,
            color="red",
            fill=True,
            fill_opacity=0.7,
            popup=popup_txt
        ).add_to(m)

# Créer le dossier static s'il n'existe pas
os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
m.save(OUT_HTML)
print(f"Succès : Carte générée avec {len(df_filtre)} points dans {OUT_HTML}")