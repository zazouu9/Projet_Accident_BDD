import os
import pandas as pd
import folium
from folium.plugins import MarkerCluster, TimestampedGeoJson
import html
from dictionnaire import *
import requests
import polyline
from math import radians, cos, sin, asin, sqrt

CSV_PATH = "results/accidents_carte_complet.csv"
FILTRE_PATH = "resultat_filtre.txt"

OUT_CLUSTER = "static/carte_accidents_cluster.html"
OUT_ANIME   = "static/carte_accidents_anime.html"

def get_geocode(city_name):
    """Transforme un nom de ville en coordonnées [lat, lon]"""
    if not city_name or len(city_name) < 2: return None
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        r = requests.get(url, headers={'User-Agent': 'MonAppSecurite/1.0'}, timeout=5)
        data = r.json()
        return [float(data[0]['lat']), float(data[0]['lon'])] if data else None
    except: return None

def haversine(lon1, lat1, lon2, lat2):
    """Calcule la distance en km entre deux points"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 2 * asin(sqrt(a)) * 6371

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
    if x is None: return None
    x = str(x).strip()
    if x == "": return None
    try: return int(x)
    except: return None

def grav_to_color(grav):
    try: return GRAV_TO_COLOR.get(int(grav), "gray")
    except: return "gray"

def popup_pre(row):
    dep = str(row.get("dep", "")).strip()
    # Sécurité si jour/mois manquent
    jour = to_int(row.get("jour"))
    mois = to_int(row.get("mois"))
    heure = to_int(row.get("heure"))
    zone = to_int(row.get("zone"))
    catr = to_int(row.get("catr"))
    grav = to_int(row.get("grav"))
    sexe = to_int(row.get("sexe"))
    catv = to_int(row.get("catv"))

    date_str = f"{jour:02d}/{mois:02d}/2024" if (jour and mois) else "Inconnue"

    lines = [
        f"Date : {date_str}",
        f"Département : {dep if dep else 'Inconnu'}",
        f"Heure : {heure if heure is not None else '?'}h",
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

def load_and_filter_df():
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Fichier introuvable: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH, dtype=str)

    # On ne met que les colonnes vitales ici (sans jour/mois qui causaient l'erreur)
    required_cols = ["heure", "dep", "zone", "catr", "grav", "sexe", "catv", "lat", "long"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes dans le CSV: {missing}")

    # Conversions
    cols_to_convert = ["heure", "jour", "mois", "zone", "catr", "grav", "sexe", "catv"]
    for c in cols_to_convert:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

    df["dep"] = df["dep"].astype(str).str.strip()
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["long"] = pd.to_numeric(df["long"], errors="coerce")
    df = df.dropna(subset=["lat", "long"]).copy()

    f = read_filters_txt(FILTRE_PATH)
    mask = pd.Series(True, index=df.index)

    # Application des filtres classiques
    if "jour" in df.columns and to_int(f.get("jour")):
        mask &= (df["jour"] == to_int(f.get("jour")))
    if "mois" in df.columns and to_int(f.get("mois")):
        mask &= (df["mois"] == to_int(f.get("mois")))

    hmin, hmax = to_int(f.get("h_min")), to_int(f.get("h_max"))
    if hmin is not None:
        mask &= (df["heure"] >= hmin) if hmax is not None else (df["heure"] == hmin)
    if hmax is not None:
        mask &= (df["heure"] <= hmax)

    grav_txt = f.get("gravite", "").strip()
    if grav_txt:
        grav_list = [to_int(p) for p in grav_txt.split(";") if to_int(p) is not None]
        if grav_list: mask &= df["grav"].isin(grav_list)

    route_txt = f.get("route", "").strip()
    if route_txt and ROUTE_TO_CATR.get(route_txt) is not None:
        mask &= (df["catr"] == ROUTE_TO_CATR.get(route_txt))

    if to_int(f.get("catv")): mask &= (df["catv"] == to_int(f.get("catv")))
    if to_int(f.get("sexe")): mask &= (df["sexe"] == to_int(f.get("sexe")))
    if f.get("dep"): mask &= (df["dep"] == f.get("dep").strip())

    # LOGIQUE ITINÉRAIRE
    start_city = f.get("start_city", "").strip()
    end_city = f.get("end_city", "").strip()
    route_line = None

    if start_city and end_city:
        c_start, c_end = get_geocode(start_city), get_geocode(end_city)
        if c_start and c_end:
            url = f"http://router.project-osrm.org/route/v1/driving/{c_start[1]},{c_start[0]};{c_end[1]},{c_end[0]}?overview=full"
            try:
                r = requests.get(url).json()
                if 'routes' in r:
                    route_line = polyline.decode(r['routes'][0]['geometry'])
                    def is_near(lat_acc, lon_acc):
                        for lp in route_line[::15]: # Pas de 15 pour performance
                            if haversine(lon_acc, lat_acc, lp[1], lp[0]) <= 0.8: return True
                        return False
                    
                    df_base = df[mask].copy()
                    mask_trajet = df_base.apply(lambda row: is_near(row['lat'], row['long']), axis=1)
                    df_res = df_base[mask_trajet]
                    with open("total_trajet.txt", "w") as f_score: f_score.write(str(len(df_res)))
                    return df_res, f, route_line
            except: pass

    if os.path.exists("total_trajet.txt"): os.remove("total_trajet.txt")
    return df[mask].copy(), f, None

# =========================
# MAIN
# =========================
os.makedirs("static", exist_ok=True)

df_filtre, f, route_line = load_and_filter_df()
print("Filtres lus :", f)
print("Total lignes filtrées :", len(df_filtre))

center = [46.2276, 2.2137]
if not df_filtre.empty:
    center = [df_filtre["lat"].mean(), df_filtre["long"].mean()]

# 1) CARTE CLUSTER
m_cluster = folium.Map(location=center, zoom_start=6)
cluster = MarkerCluster(name="Accidents", options={"disableClusteringAtZoom": 14}).add_to(m_cluster)

if df_filtre.empty:
    folium.Marker(center, popup="Aucun accident trouvé.").add_to(m_cluster)
else:
    for _, row in df_filtre.iterrows():
        popup_html, w = popup_pre(row)
        folium.CircleMarker(
            location=[row["lat"], row["long"]],
            radius=4, color=grav_to_color(row["grav"]),
            fill=True, fill_opacity=0.7,
            popup=folium.Popup(popup_html, max_width=w)
        ).add_to(cluster)

# Ajout du tracé bleu si itinéraire
if route_line:
    folium.PolyLine(route_line, color="blue", weight=5, opacity=0.7, tooltip="Trajet").add_to(m_cluster)
    folium.Marker(route_line[0], popup="Départ", icon=folium.Icon(color='green')).add_to(m_cluster)
    folium.Marker(route_line[-1], popup="Arrivée", icon=folium.Icon(color='red')).add_to(m_cluster)

m_cluster.save(OUT_CLUSTER)

# 2) CARTE ANIMÉE
m_anime = folium.Map(location=center, zoom_start=6)
if route_line:
    folium.PolyLine(route_line, color="blue", weight=5, opacity=0.7).add_to(m_anime)

features = []
base_date = "2024-01-01"
for _, row in df_filtre.iterrows():
    popup_html, _ = popup_pre(row)
    hr = int(row["heure"]) if pd.notna(row["heure"]) else 0
    features.append({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [float(row["long"]), float(row["lat"])]},
        "properties": {
            "times": [f"{base_date}T{hr:02d}:00:00"],
            "popup": popup_html,
            "icon": "circle",
            "iconstyle": {
                "fillColor": grav_to_color(row["grav"]), "fillOpacity": 0.7,
                "stroke": True, "radius": 4, "color": grav_to_color(row["grav"])
            },
        },
    })

if features:
    TimestampedGeoJson(
        data={"type": "FeatureCollection", "features": features},
        period="PT1H", add_last_point=True, auto_play=False, date_options="HH:mm",
    ).add_to(m_anime)

m_anime.save(OUT_ANIME)
print(f"Succès : {OUT_CLUSTER} et {OUT_ANIME}")