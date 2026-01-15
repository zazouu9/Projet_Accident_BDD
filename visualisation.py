# visualisation.py
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
    """Lit un fichier clé:valeur (1 filtre par ligne)."""
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
    """Convertit '01' -> 1, ' 7 ' -> 7, sinon None."""
    if x is None:
        return None
    x = str(x).strip()
    if x == "":
        return None
    try:
        return int(x)
    except:
        return None

# --- chargement CSV ---
df = pd.read_csv(CSV_PATH, dtype=str)

needed = ["heure", "catr", "grav", "sexe", "catv", "lat", "long"]
missing = [c for c in needed if c not in df.columns]
if missing:
    raise ValueError(f"Colonnes manquantes dans le CSV: {missing}")

# conversions
for c in ["heure", "catr", "grav", "sexe", "catv"]:
    df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
df["long"] = pd.to_numeric(df["long"], errors="coerce")
df = df.dropna(subset=["lat", "long"]).copy()

# --- lecture filtres txt ---
f = read_filters_txt(FILTRE_PATH)

# --- application filtres (SEULEMENT si présent et non vide) ---
mask = pd.Series(True, index=df.index)

# heure
hv = to_int(f.get("heure"))
if hv is not None:
    mask &= (df["heure"] == hv)

# gravité (une valeur, ou plusieurs séparées par ';' si jamais tu reviens à ça)
grav_txt = f.get("gravite", "").strip()
if grav_txt != "":
    grav_list = []
    for part in grav_txt.split(";"):
        gi = to_int(part)
        if gi is not None:
            grav_list.append(gi)
    if grav_list:
        mask &= df["grav"].isin(grav_list)

# route (texte -> catr)
route_txt = f.get("route", "").strip()
if route_txt != "":
    catr = ROUTE_TO_CATR.get(route_txt)
    if catr is not None:
        mask &= (df["catr"] == catr)

# catv
cv = to_int(f.get("catv"))
if cv is not None:
    mask &= (df["catv"] == cv)

# sexe
sv = to_int(f.get("sexe"))
if sv is not None:
    mask &= (df["sexe"] == sv)

df_filtre = df[mask].copy()

# --- debug utile ---
print("Filtres lus :", f)
print("Total lignes CSV :", len(df))
print("Total lignes filtrées :", len(df_filtre))

# --- génération carte ---
if df_filtre.empty:
    map_center = [df["lat"].mean(), df["long"].mean()]
    m = folium.Map(location=map_center, zoom_start=6)
    folium.Marker(map_center, popup="Aucun accident ne correspond au filtre.").add_to(m)
else:
    map_center = [df_filtre["lat"].mean(), df_filtre["long"].mean()]
    m = folium.Map(location=map_center, zoom_start=6)

    for _, row in df_filtre.iterrows():
        popup_txt = popup_texte_ligne(row)

        folium.CircleMarker(
            location=[row["lat"], row["long"]],
            radius=4,
            color="red",
            fill=True,
            fill_opacity=0.7,
            popup=popup_txt
        ).add_to(m)


def popup_texte_ligne(row):
    """
    Retourne une popup en texte brut (pas d'HTML) qui contient toute la ligne.
    Ajoute aussi les libellés pour catr et catv.
    """
    # Valeurs brutes
    heure = int(row["heure"]) if pd.notna(row["heure"]) else row["heure"]
    zone  = int(row["zone"])  if "zone" in row and pd.notna(row["zone"]) else row.get("zone", "")
    catr  = int(row["catr"])  if pd.notna(row["catr"]) else row["catr"]
    grav  = int(row["grav"])  if pd.notna(row["grav"]) else row["grav"]
    sexe  = int(row["sexe"])  if pd.notna(row["sexe"]) else row["sexe"]
    catv  = int(row["catv"])  if pd.notna(row["catv"]) else row["catv"]

    # Libellés
    route_lbl = CATR_TO_ROUTE.get(catr, f"Inconnu ({catr})") if catr is not None else "Inconnu"
    veh_lbl   = CATV_TO_LABEL.get(catv, f"Inconnu ({catv})") if catv is not None else "Inconnu"

    # Coordonnées (on garde tel quel)
    lat = row["lat"]
    lon = row["long"]

    # Texte brut multi-lignes
    return (
        "ACCIDENT (ligne complète)\n"
        f"heure: {heure}\n"
        f"zone: {zone}\n"
        f"catr: {catr} ({route_lbl})\n"
        f"grav: {grav}\n"
        f"sexe: {sexe}\n"
        f"catv: {catv} ({veh_lbl})\n"
        f"lat: {lat}\n"
        f"long: {lon}"
    )


m.save(OUT_HTML)
print(f"Carte générée : {OUT_HTML}")

#test
