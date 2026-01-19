from flask import Flask, request, render_template_string, redirect, url_for
from folium.plugins import MarkerCluster
import pandas as pd
import os
import subprocess
import folium
import sys

app = Flask(__name__)

def ensure_map_exists():
    """
    Si aucune carte filtrée n'existe, on génère une carte vierge
    pour éviter un iframe cassé.
    """
    os.makedirs("static", exist_ok=True)

    # si la carte existe déjà, rien à faire
    if os.path.exists("static/carte_accidents.html"):
        return

    # carte vierge centrée France
    m = folium.Map(location=[46.2276, 2.2137], zoom_start=6)
    m.save("static/carte_accidents.html")


def lire_filtres():
    """Lit les derniers filtres enregistrés."""
    filtres = {}
    if os.path.exists("resultat_filtre.txt"):
        with open("resultat_filtre.txt", "r", encoding="utf-8") as f:
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
        "03": "Voiturette", "07": "VL seul", "10": "VU seul 1,5T-3,5T",
        "13": "PL seul 3,5T-7,5T", "14": "PL seul > 7,5T", "15": "PL > 3,5T + rem.",
        "16": "Tracteur seul", "17": "Tracteur + semi", "20": "Engin spécial",
        "21": "Tracteur agricole", "30": "Scooter < 50 cm3", "31": "Moto 50-125 cm3",
        "32": "Scooter 50-125 cm3", "33": "Moto > 125 cm3", "34": "Scooter > 125 cm3",
        "35": "Quad léger", "36": "Quad lourd", "37": "Autobus", "38": "Autocar",
        "39": "Train", "40": "Tramway", "41": "3RM <= 50 cm3", "42": "3RM 50-125 cm3",
        "43": "3RM > 125 cm3", "50": "EDP à moteur", "60": "EDP sans moteur",
        "80": "VAE", "99": "Autre"
    }

    blocs_actifs = []
    stats = {
        "cumul_total": 0, "hommes_filtres": 0, "femmes_filtres": 0, "blocs": blocs_actifs,
        "show_chart": False, "chart_labels": [], "chart_values": []
    }
    
    if not filtres:
        return stats

    try:
        if os.path.exists("results/accidents_carte_complet.csv"):
            df_all = pd.read_csv("results/accidents_carte_complet.csv")
            
            h_min = filtres.get("h_min", "")
            h_max = filtres.get("h_max", "")
            grav_filtre = filtres.get("gravite", "")
            catv_filtre = filtres.get("catv", "")
            route_filtre = filtres.get("route", "")
            sexe_filtre = filtres.get("sexe", "")

            # --- CALCULS INDIVIDUELS ---
            if h_min != "" or h_max != "":
                h_mask = pd.Series([True] * len(df_all))
                if h_min != "" and h_max == "":
                    h_mask &= (df_all['heure'] == int(h_min))
                    lbl = f"À {h_min}h"
                else:
                    if h_min != "": h_mask &= (df_all['heure'] >= int(h_min))
                    if h_max != "": h_mask &= (df_all['heure'] <= int(h_max))
                    lbl = f"De {h_min or 0}h à {h_max or 23}h"
                blocs_actifs.append({"titre": "Heure / Plage", "label": lbl, "valeur": len(df_all[h_mask])})

            if grav_filtre:
                codes = [int(x) for x in grav_filtre.split(";") if x]
                val = len(df_all[df_all['grav'].isin(codes)])
                lbl = ", ".join([label_gravite.get(str(c)) for c in codes])
                blocs_actifs.append({"titre": "Gravité", "label": lbl, "valeur": val})

            if catv_filtre:
                val = len(df_all[df_all['catv'] == int(catv_filtre)])
                lbl = label_vehicule.get(catv_filtre, "Inconnu")
                blocs_actifs.append({"titre": "Véhicule", "label": lbl, "valeur": val})

            if route_filtre:
                mapping_r = {"Autoroute": 1, "Nationale": 2, "Départementale": 3, "Communale": 4}
                val = len(df_all[df_all['catr'] == mapping_r.get(route_filtre)])
                blocs_actifs.append({"titre": "Route", "label": route_filtre, "valeur": val})

            if sexe_filtre:
                val = len(df_all[df_all['sexe'] == int(sexe_filtre)])
                lbl = label_sexe.get(sexe_filtre)
                blocs_actifs.append({"titre": "Sexe", "label": lbl, "valeur": val})

            # --- CALCUL CUMULÉ ---
            mask_global = pd.Series([True] * len(df_all))
            if h_min != "" and h_max == "":
                mask_global &= (df_all['heure'] == int(h_min))
            else:
                if h_min != "": mask_global &= (df_all['heure'] >= int(h_min))
                if h_max != "": mask_global &= (df_all['heure'] <= int(h_max))
            
            if grav_filtre: mask_global &= (df_all['grav'].isin([int(x) for x in grav_filtre.split(";") if x]))
            if catv_filtre: mask_global &= (df_all['catv'] == int(catv_filtre))
            if route_filtre:
                mapping_r = {"Autoroute": 1, "Nationale": 2, "Départementale": 3, "Communale": 4}
                mask_global &= (df_all['catr'] == mapping_r.get(route_filtre))
            if sexe_filtre: mask_global &= (df_all['sexe'] == int(sexe_filtre))

            df_filtre = df_all[mask_global]
            stats["cumul_total"] = len(df_filtre)
            stats["hommes_filtres"] = len(df_filtre[df_filtre['sexe'] == 1])
            stats["femmes_filtres"] = len(df_filtre[df_filtre['sexe'] == 2])

            # --- DONNÉES GRAPHIQUE ---
            if (h_min != "" or h_max != "") and not df_filtre.empty:
                chart_group = df_filtre.groupby('heure').size().reset_index(name='count')
                chart_group = chart_group.sort_values('heure')
                stats["chart_labels"] = [f"{int(h)}h" for h in chart_group['heure'].tolist()]
                stats["chart_values"] = chart_group['count'].tolist()
                stats["show_chart"] = True

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
        
        #chart-container { 
            width: 100%;
            height: 250px; 
            margin-top: 20px;
            padding: 10px 5px;
            background: white;
            border-radius: 8px;
            border: 1px solid #ddd;
            display: {% if stats.show_chart %}block{% else %}none{% endif %};
        }

        .sidebar-stats { margin-top: 15px; }
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
        .page-title { width: 100%; text-align: center; background: #2c3e50; color: white; padding: 15px 0; margin: 0; font-size: 22px; letter-spacing: 1px; }
        .grav { display: block; margin-bottom: 6px; font-weight: 600; }
        .grav-1 { color: blue; } .grav-2 { color: black; } .grav-3 { color: green; } .grav-4 { color: orange; }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        function updateMaxMin() {
            const hMin = document.getElementsByName('h_min')[0];
            const hMax = document.getElementsByName('h_max')[0];
            hMax.min = hMin.value;
            if (hMax.value !== "" && parseInt(hMax.value) < parseInt(hMin.value)) {
                hMax.value = hMin.value;
            }
        }
    </script>
</head>
<body>

<div id="sidebar">
    <div class="filter-section">
        <h1 class="page-title">Accident routier 2024</h1>
        <h3>Filtres</h3>
        <form method="post">
            <label>Plage Horaire :</label>
            <div class="range-container">
                <input type="number" name="h_min" min="0" max="23" placeholder="Début" oninput="updateMaxMin()">
                <span>à</span>
                <input type="number" name="h_max" min="0" max="23" placeholder="Fin">
            </div>
            
            <fieldset><legend>Gravité</legend>
                <label class="grav grav-1"><input type="checkbox" name="gravite" value="1"> Indemne</label>
                <label class="grav grav-2"><input type="checkbox" name="gravite" value="2"> Tué</label>
                <label class="grav grav-3"><input type="checkbox" name="gravite" value="3"> Hospitalisé</label>
                <label class="grav grav-4"><input type="checkbox" name="gravite" value="4"> Léger</label>
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
                <option value="07">07 – VL seul</option>
                <option value="33">33 – Moto > 125 cm3</option>
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
        <label>Statistiques Globales :</label>
        {% for bloc in stats.blocs %}
        <div class="sidebar-stat-item">
            <h4>{{ bloc.titre }}</h4>
            <span class="stat-label-active">{{ bloc.label }}</span>
            <div class="sidebar-stat-value">{{ bloc.valeur }} accidents</div>
        </div>
        {% endfor %}
    </div>

    <div id="chart-container">
        <canvas id="accidentChart"></canvas>
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
            <div style="font-size: 0.75em; opacity: 0.8;">TOTAL FILTRÉ (CROISEMENT)</div>
            <div class="total-value">{{ stats.cumul_total }}</div>
        </div>
    </div>
</div>

<script>
    {% if stats.show_chart %}
    const ctx = document.getElementById('accidentChart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: {{ stats.chart_labels | tojson }},
            datasets: [{
                label: 'Accidents',
                data: {{ stats.chart_values | tojson }},
                borderColor: '#e74c3c',
                backgroundColor: 'rgba(231, 76, 60, 0.2)',
                fill: true,
                tension: 0.4,
                pointRadius: 3,
                pointBackgroundColor: 'white'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { 
                legend: { display: false },
                title: {
                    display: true,
                    text: 'Évolution temporelle',
                    font: { size: 14, family: 'Segoe UI' },
                    padding: { bottom: 10 }
                },
                tooltip: { backgroundColor: '#2c3e50' }
            },
            scales: {
                y: { 
                    beginAtZero: true, 
                    ticks: { font: { size: 10 } },
                    title: {
                        display: true,
                        text: 'Nombre accidents',
                        font: { size: 11, weight: 'bold' }
                    }
                },
                x: { 
                    ticks: { font: { size: 10 } },
                    title: {
                        display: true,
                        text: 'Heure',
                        font: { size: 11, weight: 'bold' }
                    }
                }
            }
        }
    });
    {% endif %}
</script>

</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def page_principale():
    if request.method == "POST":
        h_min = request.form.get("h_min", "")
        h_max = request.form.get("h_max", "")
        
        if h_min != "" and h_max != "" and int(h_max) < int(h_min):
            h_max = h_min 

        g = ";".join(request.form.getlist("gravite"))
        r = request.form.get("route", "")
        v = request.form.get("catv", "")
        s = request.form.get("sexe", "")

        with open("resultat_filtre.txt", "w", encoding="utf-8") as f:
            f.write(f"h_min:{h_min}\nh_max:{h_max}\ngravite:{g}\nroute:{r}\ncatv:{v}\nsexe:{s}\n")

        try:
            subprocess.run([sys.executable, "visualisation.py"], check=True)
        except Exception as e:
            print(f"Erreur génération carte: {e}")

        return redirect(url_for("page_principale"))
    
    ensure_map_exists()
    return render_template_string(HTML_PAGE, stats=obtenir_stats_completes())

if __name__ == "__main__":
    app.run(debug=True, port=5001)