from flask import Flask, request, render_template_string, redirect, url_for
import pandas as pd
import os
import subprocess
import sys

app = Flask(__name__)

def lire_filtres():
    """Lit les derniers filtres enregistrés dans le fichier texte."""
    filtres = {}
    if os.path.exists("resultat_filtre.txt"):
        with open("resultat_filtre.txt", "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    cle, valeur = line.strip().split(":", 1)
                    filtres[cle] = valeur
    return filtres

def obtenir_stats_completes():
    """Calcule les stats individuelles (gauche) et le cumulé avec détail genre (bas)."""
    filtres = lire_filtres()
    
    # Dictionnaires pour les labels d'affichage (Mise à jour avec la liste complète)
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
        "l_grav": "Aucun", "l_heure": "N/A", "l_sexe": "N/A", "l_route": "N/A", "l_veh": "N/A"
    }
    
    if not filtres:
        return stats

    try:
        # --- RÉCUPÉRATION DES LABELS ---
        codes_g = filtres.get("gravite", "").split(";")
        stats["l_grav"] = ", ".join([label_gravite.get(c, c) for c in codes_g if c])
        stats["l_heure"] = f"{filtres.get('heure')}h"
        stats["l_sexe"] = label_sexe.get(filtres.get("sexe"), "N/A")
        stats["l_route"] = filtres.get("route", "N/A")
        stats["l_veh"] = label_vehicule.get(filtres.get("catv"), filtres.get("catv"))

        # --- 1. STATS INDIVIDUELLES (À GAUCHE) ---
        if os.path.exists("results/accidents_par_heure.csv"):
            df_h = pd.read_csv("results/accidents_par_heure.csv")
            h_cible = str(filtres.get("heure")).zfill(2)
            stats["heure"] = df_h[df_h['heure'].astype(str).str.zfill(2) == h_cible]['nb_accidents'].sum()

        if os.path.exists("results/accidents_par_gravite.csv"):
            df_g = pd.read_csv("results/accidents_par_gravite.csv")
            stats["gravite"] = df_g[df_g['grav'].astype(str).isin(codes_g)]['nb_accidents'].sum()

        if os.path.exists("results/accidents_par_sexe.csv"):
            df_s = pd.read_csv("results/accidents_par_sexe.csv")
            stats["sexe"] = df_s[df_s['sexe'].astype(str) == str(filtres.get("sexe"))]['nb_accidents'].sum()

        if os.path.exists("results/accidents_par_type_route.csv"):
            mapping_r_code = {"Autoroute": "1", "Nationale": "2", "Départementale": "3", "Communale": "4"}
            code_r = mapping_r_code.get(filtres.get("route"))
            df_r = pd.read_csv("results/accidents_par_type_route.csv")
            stats["route"] = df_r[df_r['catr'].astype(str) == str(code_r)]['nb_accidents'].sum()

        if os.path.exists("results/accidents_par_type_vehicule.csv"):
            df_v = pd.read_csv("results/accidents_par_type_vehicule.csv")
            v_cible = str(filtres.get("catv")).lstrip('0')
            if v_cible == "": v_cible = "0"
            stats["vehicule"] = df_v[df_v['catv'].astype(str).str.lstrip('0').replace('', '0') == v_cible]['nb_accidents'].sum()

        # --- 2. STATS CUMULÉES (EN BAS) ---
        if os.path.exists("results/accidents_carte_complet.csv"):
            df_all = pd.read_csv("results/accidents_carte_complet.csv")
            mapping_r_int = {"Autoroute": 1, "Nationale": 2, "Départementale": 3, "Communale": 4}
            
            f_h = int(filtres["heure"])
            f_g = [int(x) for x in codes_g if x]
            f_v = int(filtres["catv"])
            f_r = mapping_r_int.get(filtres["route"])
            f_s = int(filtres["sexe"])

            mask = (df_all['heure'] == f_h) & \
                   (df_all['grav'].isin(f_g)) & \
                   (df_all['catv'] == f_v) & \
                   (df_all['catr'] == f_r) & \
                   (df_all['sexe'] == f_s)
            
            df_filtre = df_all[mask]
            
            if f_s == 1:
                stats["hommes_filtres"] = len(df_filtre)
                stats["femmes_filtres"] = 0
            else:
                stats["hommes_filtres"] = 0
                stats["femmes_filtres"] = len(df_filtre)
            
            stats["cumul_total"] = len(df_filtre)

    except Exception as e:
        print(f"Erreur de calcul : {e}")
        
    return stats

HTML_PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Dashboard Accidents</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; margin: 0; display: flex; height: 100vh; overflow: hidden; }
        #sidebar { width: 320px; padding: 15px; background: #f4f4f4; border-right: 1px solid #ccc; overflow-y: auto; display: flex; flex-direction: column; }
        .filter-section { flex-shrink: 0; border-bottom: 2px solid #ddd; padding-bottom: 15px; margin-bottom: 15px; }
        .sidebar-stats { flex-grow: 1; }
        .sidebar-stat-item { background: #fff; padding: 10px; margin-bottom: 8px; border-radius: 4px; border: 1px solid #ddd; }
        .sidebar-stat-item h4 { margin: 0; font-size: 0.75em; color: #666; text-transform: uppercase; border-bottom: 1px solid #eee; padding-bottom: 3px; }
        .stat-label-active { font-weight: bold; color: #007bff; font-size: 0.9em; display: block; margin-top: 2px; }
        .sidebar-stat-value { font-size: 1.1em; font-weight: bold; color: #28a745; margin-top: 5px; }
        #main-content { flex-grow: 1; display: flex; flex-direction: column; }
        #map-container { flex-grow: 1; width: 100%; }
        #info-panel-cumul { height: 80px; padding: 5px 25px; background: #2c3e50; color: white; display: flex; align-items: center; justify-content: space-between; }
        .gender-stats-box { display: flex; gap: 40px; }
        .stat-box-bottom { text-align: center; }
        .bottom-label { font-size: 0.75em; text-transform: uppercase; opacity: 0.8; margin-bottom: 4px; }
        .bottom-value { font-size: 1.5em; font-weight: bold; }
        .total-value { color: #f1c40f; font-size: 1.8em; }
        .gender-blue { color: #3498db; }
        label { display: block; margin-top: 8px; font-size: 0.9em; }
        button { margin-top: 15px; padding: 10px; width: 100%; background: #28a745; color: white; border: none; cursor: pointer; border-radius: 4px; font-weight: bold; }
        fieldset { border: 1px solid #ccc; border-radius: 4px; margin-top: 10px; }
        select { width: 100%; padding: 4px; }
    </style>
</head>
<body>
<div id="sidebar">
    <div class="filter-section">
        <h3>Filtres</h3>
        <form method="post">
            <label>Heure : <input type="number" name="heure" min="0" max="23" required></label>
            <fieldset><legend>Gravité</legend>
                <label><input type="checkbox" name="gravite" value="1"> Indemne</label>
                <label><input type="checkbox" name="gravite" value="2"> Tué</label>
                <label><input type="checkbox" name="gravite" value="3"> Hospitalisé</label>
                <label><input type="checkbox" name="gravite" value="4"> Léger</label>
            </fieldset>
            <label>Route :
                <select name="route" required>
                    <option value="Autoroute">Autoroute</option>
                    <option value="Nationale">Nationale</option>
                    <option value="Départementale">Départementale</option>
                    <option value="Communale">Communale</option>
                </select>
            </label>
            <label>Véhicule :
                <select name="catv" required>
                    <option value="00">00 – Indéterminable</option>
                    <option value="01">01 – Bicyclette</option>
                    <option value="02">02 – Cyclomoteur <50cm3</option>
                    <option value="03">03 – Voiturette</option>
                    <option value="07">07 – VL seul</option>
                    <option value="10">10 – VU seul</option>
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
                    <option value="35">35 – Quad léger</option>
                    <option value="36">36 – Quad lourd</option>
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
            </label>
            <fieldset><legend>Sexe</legend>
                <label><input type="radio" name="sexe" value="1" required> Masculin</label>
                <label><input type="radio" name="sexe" value="2"> Féminin</label>
            </fieldset>
            <button type="submit">FILTRER LES DONNÉES</button>
        </form>
    </div>
    <div class="sidebar-stats">
        <div class="sidebar-stat-item">
            <h4>Gravité</h4>
            <span class="stat-label-active">{{ stats.l_grav }}</span>
            <div class="sidebar-stat-value">{{ stats.gravite }} accidents</div>
        </div>
        <div class="sidebar-stat-item">
            <h4>Heure</h4>
            <span class="stat-label-active">{{ stats.l_heure }}</span>
            <div class="sidebar-stat-value">{{ stats.heure }} accidents</div>
        </div>
        <div class="sidebar-stat-item">
            <h4>Sexe</h4>
            <span class="stat-label-active">{{ stats.l_sexe }}</span>
            <div class="sidebar-stat-value">{{ stats.sexe }} accidents</div>
        </div>
        <div class="sidebar-stat-item">
            <h4>Route</h4>
            <span class="stat-label-active">{{ stats.l_route }}</span>
            <div class="sidebar-stat-value">{{ stats.route }} accidents</div>
        </div>
        <div class="sidebar-stat-item">
            <h4>Véhicule</h4>
            <span class="stat-label-active">{{ stats.l_veh }}</span>
            <div class="sidebar-stat-value">{{ stats.vehicule }} accidents</div>
        </div>
    </div>
</div>
<div id="main-content">
    <div id="map-container">
        <iframe src="{{ url_for('static', filename='carte_accidents.html') }}" width="100%" height="100%" style="border:none;"></iframe>
    </div>
    <div id="info-panel-cumul">
        <div class="gender-stats-box">
            <div class="stat-box-bottom">
                <div class="bottom-label">Hommes</div>
                <div class="bottom-value gender-blue">{{ stats.hommes_filtres }}</div>
            </div>
            <div class="stat-box-bottom">
                <div class="bottom-label">Femmes</div>
                <div class="bottom-value gender-blue">{{ stats.femmes_filtres }}</div>
            </div>
        </div>
        <div class="stat-box-bottom">
            <div class="bottom-label">Total (Filtres croisés)</div>
            <div class="bottom-value total-value">{{ stats.cumul_total }}</div>
        </div>
    </div>
</div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        h = request.form.get("heure")
        g = ";".join(request.form.getlist("gravite"))
        r = request.form.get("route")
        v = request.form.get("catv")
        s = request.form.get("sexe")

        with open("resultat_filtre.txt", "w", encoding="utf-8") as f:
            f.write(f"heure:{h}\ngravite:{g}\nroute:{r}\ncatv:{v}\nsexe:{s}\n")

        try:
            subprocess.run([sys.executable, "visualisation.py"], check=True)
        except Exception as e:
            print(f"Erreur génération carte: {e}")

        return redirect(url_for("index"))

    return render_template_string(HTML_PAGE, stats=obtenir_stats_completes())

if __name__ == "__main__":
    app.run(debug=True)