import sqlite3
import pandas as pd
import folium

# --- CONFIG ---
DB_PATH = "database/accidents_routiers.db"
TABLE_NAME = "caracteristiques"

# --- CONNEXION DB ---
conn = sqlite3.connect(DB_PATH)

# --- REQUÊTE SQL ---
query = f"""
SELECT
    Num_Acc,
    lat,
    long
FROM {TABLE_NAME}
WHERE lat IS NOT NULL
  AND long IS NOT NULL
"""

df = pd.read_sql_query(query, conn)
conn.close()

# Sécurité : on enlève les coordonnées invalides
df = df[(df["lat"] != 0) & (df["long"] != 0)]

# --- CRÉATION DE LA CARTE ---
map_center = [df["lat"].mean(), df["long"].mean()]
m = folium.Map(location=map_center, zoom_start=6)

# --- AJOUT DES POINTS ---
for _, row in df.iterrows():
    folium.CircleMarker(
        location=[row["lat"], row["long"]],
        radius=4,
        color="red",
        fill=True,
        fill_opacity=0.7,
        popup=f"Num_Acc : {row['Num_Acc']}"
        popup=
    ).add_to(m)

# --- EXPORT ---
m.save("carte_accidents.html")

print("Carte générée : carte_accidents.html")
