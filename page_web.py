from flask import Flask, request, render_template_string, redirect, url_for
import pandas as pd
import os
import subprocess
import sys

app = Flask(__name__)

def lire_filtres():
    """Lit les derniers filtres enregistrés."""
    filtres = {}
    if os.path.exists("resultat_filter.txt"):
        with open("resultat_filter.txt", "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    cle, valeur = line.strip().split(":", 1)
                    filtres[cle] = valeur
    return filtres

def obtenir_stats_completes():
    filtres = lire_filtres()
    
    label_gravite = {"1": "Indemne", "2": "Tué", "3": "Hospit.", "4": "Léger"}
    label_sexe = {"1": "Masculin", "2": "Féminin"}
    label_vehicule = {
        "00": "Indéterminable", "01": "Bicyclette", "02": "Cyclomoteur <50cm3",
        "03": "Voiturette", "07": "VL seul", "10": "VU seul", "13": "PL 3,5T-7,5T",
        "14": "PL > 7,5T", "15": "PL > 3,5T + rem.", "16": "Tracteur seul",
        "17": "Tracteur + semi", "20": "Engin spécial", "21": "Tracteur agricole",
        "30": "Scooter < 50cm3", "31": "Moto 50-125cm3", "32": "Scooter 50-125cm3",
        "33": "Moto > 125cm3", "34": "Scooter > 125cm3", "35": "Quad léger",
        "36": "Quad lourd", "37": "Autobus", "38": "Autocar", "39": "Train",
        "40": "Tramway", "41": "3RM <= 50cm3", "42": "3RM 50-125cm3",
        "43": "3RM > 125cm3", "50": "EDP à moteur", "60": "EDP sans moteur",
        "80": "VAE", "99": "Autre"
    }

    stats = {
        "gravite": 0, "heure": 0, "sexe": 0, "route": 0, "vehicule": 0, 
        "cumul_total": 0, "hommes_filtres": 0, "femmes_filtres": 0,
        "l_grav": "Tous", "l_heure": "Toutes", "l_sexe": "Tous", "l_route": "Toutes", "l_veh": "Tous"
    }
    
    if not filtres:
        return stats

    try:
        # --- RÉCUPÉRATION DES LABELS ---
        if filtres.get("gravite"):
            codes_g = filtres["gravite"].split(";")
            stats["l_grav"] = ", ".join([label_gravite.get(c, c) for c in codes_g if c])
        
        h_min = filtres.get("h_min")
        h_max = filtres.get("h_max")
        if h_min and h_max: stats["l_heure"] = f"De {h_min}h à {h_max}h"
        elif h_min: stats["l_heure"] = f"Dès {h_min}h"
        elif h_max: stats["l_heure"] = f"Jusqu'à {h_max}h"

        if filtres.get("sexe"): stats["l_sexe"] = label_sexe.get(filtres["sexe"], "Tous")
        if filtres.get("route"): stats["l_route"] = filtres["route"]
        if filtres.get("catv"): stats["l_veh"] = label_vehicule.get(filtres["catv"], "Tous")

        # --- FILTRAGE CUMULÉ (Bas) ---
        if os.path.exists("results/accidents_carte_complet.csv"):
            df_all = pd.read_csv("results/accidents_carte_complet.csv")
            mask = pd.Series([True] * len(df_all))

            if h_min: mask &= (df_all['heure'] >= int(h_min))
            if h_max: mask &= (df_all['heure'] <= int(h_max))
            if filtres.get("gravite"): mask &= (df_all['grav'].isin([int(x) for x in filtres["gravite"].split(";")]))
            if filtres.get("catv"): mask &= (df_all['catv'] == int(filtres["catv"]))
            if filtres.get("route"):
                mapping_r = {"Autoroute": 1, "Nationale": 2, "Départementale": 3, "Communale": 4}
                mask &= (df_all['catr'] == mapping_r.get(filtres["route"]))
            if filtres.get("sexe"): mask &= (df_all['sexe'] == int(filtres["sexe"]))
            
            df_filtre = df_all[mask]
            stats["hommes_filtres"] = len(df_filtre[df_filtre['sexe'] == 1])
            stats["femmes_filtres"] = len(df_filtre[df_filtre['sexe'] == 2])
            stats["cumul_total"] = len(df_filtre)
            stats["heure"] = len(df_filtre) # Affiche le nbr d'accidents de la plage

    except Exception as e:
        print(f"Erreur : {e}")
    return stats

HTML_PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Dashboard Accidents</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; margin: 0; display: flex; height: 100vh; overflow: hidden; }
        #sidebar { width: 340px; padding: 15px; background: #f4f4f4; border-right: 1px solid #ccc; overflow-y: auto; display: flex; flex-direction: column; }
        .filter-section { flex-shrink: 0; border-bottom: 2px solid #ddd; padding-bottom: 15px; margin-bottom: 15px; }
        .sidebar-stats { flex-grow: 1; }
        .sidebar-stat-item { background: #fff; padding: 10px; margin-bottom: 8px; border-radius: 4px; border: 1px solid #ddd; }
        .sidebar-stat-item h4 { margin: 0; font-size: 0.75em; color: #666; text-transform: uppercase; border-bottom: 1px solid #eee; padding-bottom: 3px; }
        .stat-label-active { font-weight: bold; color: #007bff; font-size: 0.9em; display: block; margin-top: 2px; }
        .sidebar-stat-value { font-size: 1.1em; font-weight: bold; color: #28a745; margin-top: 5px; }
        #main-content { flex-grow: 1; display: flex; flex-direction: column; }
        #map-container { flex-grow: 1; width: 100%; }
        #info-panel-cumul { height: 80px; padding: 5px 25px; background: #2c3e50; color: white; display: flex; align-items: center; justify-content: space-between; }
        .stat-box-bottom { text-align: center; }
        .total-value { color: #f1c40f; font-size: 1.8em; font-weight: bold; }
        .gender-blue { color: #3498db; font-size: 1.5em; font-weight: bold; }
        .range-container { display: flex; align-items: center; gap: 5px; margin-top: 5px; }
        .range-container input { width: 70px; padding: 4px; }
        button { margin-top: 15px; padding: 10px; width: 100%; background: #28a745; color: white; border: none; cursor: pointer; border-radius: 4px; font-weight: bold; }
        fieldset { border: 1px solid #ccc; border-radius: 4px; margin-top: 10px; padding: 10px; }
        select { width: 100%; padding: 4px; margin-top: 5px; }
    </style>
</head>
<body>
<div id="sidebar">
    <div class="filter-section">
        <h3>Filtres</h3>
        <form method="post">
            <label>Plage Horaire :</label>
            <div class="range-container">
                <input type="number" name="h_min" min="0" max="23" placeholder="Début">
                <span>à</span>
                <input type="number" name="h_max" min="0" max="23" placeholder="Fin">
            </div>
            
            <fieldset><legend>Gravité</legend>
                <label><input type="checkbox" name="gravite" value="1"> Indemne</label>
                <label><input type="checkbox" name="gravite" value="2"> Tué</label>
                <label><input type="checkbox" name="gravite" value="3"> Hospitalisé</label>
                <label><input type="checkbox" name="gravite" value="4"> Léger</label>
            </fieldset>

            <label>Route :
                <select name="route">
                    <option value="">-- Toutes les routes --</option>
                    <option value="Autoroute">Autoroute</option>
                    <option value="Nationale">Nationale</option>
                    <option value="Départementale">Départementale</option>
                    <option value="Communale">Communale</option>
                </select>
            </label>

            <label>Véhicule :</label>
            <select name="catv">
                <option value="">-- Tous les véhicules --</option>
                <option value="00">00 – Indéterminable</option>
                <option value="01">01 – Bicyclette</option>
                <option value="02">02 – Cyclomoteur <50cm3</option>
                <option value="03">03 – Voiturette</option>
                <option value="07">07 – VL seul</option>
                <option value="10">10 – VU seul 1,5T-3,5T</option>
                <option value="13">13 – PL seul 3,5T-7,5T</option>
                <option value="14">14 – PL seul > 7,5T</option>
                <option value="15">15 – PL > 3,5T + remorque</option>
                <option value="16">16 – Tracteur routier seul</option>
                <option value="17">17 – Tracteur + semi</option>
                <option value="20">20 – Engin spécial</option>
                <option value="21">21 – Tracteur agricole</option>
                <option value="30">30 – Scooter < 50 cm3</option>
                <option value="31">31 – Moto 50-125 cm3</option>
                <option value="32">32 – Scooter 50-125 cm3</option>
                <option value="33">33 – Moto > 125 cm3</option>
                <option value="34">34 – Scooter > 125 cm3</option>
                <option value="35">35 – Quad léger <= 50 cm3</option>
                <option value="36">36 – Quad lourd > 50 cm3</option>
                <option value="37">37 – Autobus</option>
                <option value="38">38 – Autocar</option>
                <option value="39">39 – Train</option>
                <option value="40">40 – Tramway</option>
                <option value="41">41 – 3RM <= 50 cm3</option>
                <option value="42">42 – 3RM 50-125 cm3</option>
                <option value="43">43 – 3RM > 125 cm3</option>
                <option value="50">50 – EDP à moteur</option>
                <option value="60">60 – EDP sans moteur</option>
                <option value="80">80 – VAE</option>
                <option value="99">99 – Autre véhicule</option>
            </select>

            <fieldset><legend>Sexe</legend>
                <label><input type="radio" name="sexe" value=""> Tous</label>
                <label><input type="radio" name="sexe" value="1"> Masculin</label>
                <label><input type="radio" name="sexe" value="2"> Féminin</label>
            </fieldset>
            
            <button type="submit">FILTRER LES DONNÉES</button>
        </form>
    </div>
    
    <div class="sidebar-stats">
        <div class="sidebar-stat-item">
            <h4>Heure / Plage</h4>
            <span class="stat-label-active">{{ stats.l_heure }}</span>
            <div class="sidebar-stat-value">{{ stats.heure }} accidents</div>
        </div>
        <div class="sidebar-stat-item">
            <h4>Gravité</h4>
            <span class="stat-label-active">{{ stats.l_grav }}</span>
            <div class="sidebar-stat-value">{{ stats.gravite }} accidents</div>
        </div>
        <div class="sidebar-stat-item">
            <h4>Véhicule</h4>
            <span class="stat-label-active">{{ stats.l_veh }}</span>
        </div>
    </div>
</div>

<div id="main-content">
    <div id="map-container">
        <iframe src="{{ url_for('static', filename='carte_accidents.html') }}" width="100%" height="100%" style="border:none;"></iframe>
    </div>
    <div id="info-panel-cumul">
        <div style="display: flex; gap: 40px;">
            <div class="stat-box-bottom">
                <div style="font-size: 0.75em; opacity: 0.8;">HOMMES</div>
                <div class="gender-blue">{{ stats.hommes_filtres }}</div>
            </div>
            <div class="stat-box-bottom">
                <div style="font-size: 0.75em; opacity: 0.8;">FEMMES</div>
                <div class="gender-blue">{{ stats.femmes_filtres }}</div>
            </div>
        </div>
        <div class="stat-box-bottom">
            <div style="font-size: 0.75em; opacity: 0.8;">TOTAL FILTRÉ</div>
            <div class="total-value">{{ stats.cumul_total }}</div>
        </div>
    </div>
</div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        h_min = request.form.get("h_min", "")
        h_max = request.form.get("h_max", "")
        g = ";".join(request.form.getlist("gravite"))
        r = request.form.get("route", "")
        v = request.form.get("catv", "")
        s = request.form.get("sexe", "")

        with open("resultat_filter.txt", "w", encoding="utf-8") as f:
            f.write(f"h_min:{h_min}\nh_max:{h_max}\ngravite:{g}\nroute:{r}\ncatv:{v}\nsexe:{s}\n")

        try:
            subprocess.run([sys.executable, "visualisation.py"], check=True)

        except Exception as e:
            print(f"Erreur génération carte: {e}")

        return redirect(url_for("index"))

    return render_template_string(HTML_PAGE, stats=obtenir_stats_completes())

if __name__ == "__main__":
    app.run(debug=True)