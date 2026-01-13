from flask import Flask, request, render_template_string
import pandas as pd
import os

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
    """Calcule les stats individuelles ET le total cumulé."""
    filtres = lire_filtres()
    # Structure pour stocker les résultats
    stats = {"gravite": 0, "heure": 0, "sexe": 0, "route": 0, "vehicule": 0, "cumul_total": 0}
    
    if not filtres:
        return stats

    try:
        # --- 1. CALCULS INDIVIDUELS (POUR LA GAUCHE) ---
        if os.path.exists("results/accidents_par_heure.csv"):
            df_h = pd.read_csv("results/accidents_par_heure.csv")
            h_cible = str(filtres.get("heure", "")).zfill(2)
            stats["heure"] = df_h[df_h['heure'].astype(str).str.zfill(2) == h_cible]['nb_accidents'].sum()

        if os.path.exists("results/accidents_par_gravite.csv"):
            df_g = pd.read_csv("results/accidents_par_gravite.csv")
            codes_g = filtres.get("gravite", "").split(";")
            stats["gravite"] = df_g[df_g['grav'].astype(str).isin(codes_g)]['nb_accidents'].sum()

        if os.path.exists("results/accidents_par_sexe.csv"):
            df_s = pd.read_csv("results/accidents_par_sexe.csv")
            stats["sexe"] = df_s[df_s['sexe'].astype(str) == str(filtres.get("sexe", ""))]['nb_accidents'].sum()

        if os.path.exists("results/accidents_par_type_route.csv"):
            mapping = {"Autoroute": "1", "Nationale": "2", "Départementale": "3", "Communale": "4"}
            code_r = mapping.get(filtres.get("route", ""))
            df_r = pd.read_csv("results/accidents_par_type_route.csv")
            stats["route"] = df_r[df_r['catr'].astype(str) == code_r]['nb_accidents'].sum()

        if os.path.exists("results/accidents_par_type_vehicule.csv"):
            df_v = pd.read_csv("results/accidents_par_type_vehicule.csv")
            v_cible = str(filtres.get("catv", "")).lstrip('0')
            stats["vehicule"] = df_v[df_v['catv'].astype(str).str.lstrip('0') == v_cible]['nb_accidents'].sum()

        # --- 2. CALCUL CUMULÉ (POUR LE BAS A DROITE) ---
        if os.path.exists("results/accidents_carte_complet.csv"):
            df_all = pd.read_csv("results/accidents_carte_complet.csv")
            
            # Application de TOUS les filtres en même temps
            mask = (df_all['heure'] == int(filtres["heure"])) & \
                   (df_all['grav'].isin([int(x) for x in filtres["gravite"].split(";")])) & \
                   (df_all['sexe'] == int(filtres["sexe"])) & \
                   (df_all['catv'] == int(filtres["catv"]))
            
            mapping_r = {"Autoroute": 1, "Nationale": 2, "Départementale": 3, "Communale": 4}
            mask &= (df_all['catr'] == mapping_r.get(filtres["route"]))
            
            stats["cumul_total"] = len(df_all[mask])

    except Exception as e:
        print(f"Erreur de calcul : {e}")
        
    return stats

HTML_PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Analyse Accidents</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; margin: 0; display: flex; height: 100vh; overflow: hidden; }
        
        /* Barre latérale gauche */
        #sidebar { width: 300px; padding: 15px; background: #f4f4f4; border-right: 1px solid #ccc; overflow-y: auto; display: flex; flex-direction: column; }
        
        /* Zone de filtres */
        .filter-section { flex-shrink: 0; border-bottom: 2px solid #ddd; padding-bottom: 15px; margin-bottom: 15px; }
        
        /* Zone stats individuelles (Flèche verte) */
        .sidebar-stats { flex-grow: 1; }
        .sidebar-stat-item { background: #fff; padding: 10px; margin-bottom: 8px; border-radius: 4px; border: 1px solid #ddd; }
        .sidebar-stat-item h4 { margin: 0; font-size: 0.75em; color: #666; text-transform: uppercase; }
        .sidebar-stat-value { font-size: 1.1em; font-weight: bold; color: #28a745; }

        /* Contenu principal */
        #main-content { flex-grow: 1; display: flex; flex-direction: column; }
        #map-container { flex-grow: 1; width: 100%; }
        
        /* Zone cumulée (Bas droite) */
        #info-panel-cumul { height: 75px; padding: 5px 20px; background: #2c3e50; color: white; display: flex; align-items: center; justify-content: flex-end; }
        .cumul-box { text-align: right; }
        .cumul-label { font-size: 0.8em; text-transform: uppercase; opacity: 0.8; }
        .cumul-value { font-size: 1.8em; font-weight: bold; color: #f1c40f; }

        label { display: block; margin-top: 8px; font-size: 0.9em; }
        button { margin-top: 15px; padding: 10px; width: 100%; background: #28a745; color: white; border: none; cursor: pointer; border-radius: 4px; font-weight: bold; }
        fieldset { border: 1px solid #ccc; border-radius: 4px; margin-top: 10px; }
    </style>
</head>
<body>

<div id="sidebar">
    <div class="filter-section">
        <h3>Filtres</h3>
        <form method="post">
            <label>Heure : <input type="number" name="heure" min="0" max="23" required></label>
            <fieldset><legend>Gravité</legend>
                <label><input type="checkbox" name="gravite" value="1"> 1 - Indemne</label>
                <label><input type="checkbox" name="gravite" value="2"> 2 - Tué</label>
                <label><input type="checkbox" name="gravite" value="3"> 3 - Hospitalisé</label>
                <label><input type="checkbox" name="gravite" value="4"> 4 - Léger</label>
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
                    <option value="07">07 – VL seul</option>
                    <option value="01">01 – Bicyclette</option>
                    <option value="33">33 – Moto</option>
                    <option value="14">14 – PL</option>
                </select>
            </label>
            <fieldset><legend>Sexe</legend>
                <label><input type="radio" name="sexe" value="1" required> Masculin</label>
                <label><input type="radio" name="sexe" value="2"> Féminin</label>
            </fieldset>
            <button type="submit">APPLIQUER</button>
        </form>
    </div>

    <div class="sidebar-stats">
        <div class="sidebar-stat-item">
            <h4>Gravité (Total sélection)</h4>
            <div class="sidebar-stat-value">{{ stats.gravite }}</div>
        </div>
        <div class="sidebar-stat-item">
            <h4>Heure (Total sélection)</h4>
            <div class="sidebar-stat-value">{{ stats.heure }}</div>
        </div>
        <div class="sidebar-stat-item">
            <h4>Sexe (Total sélection)</h4>
            <div class="sidebar-stat-value">{{ stats.sexe }}</div>
        </div>
        <div class="sidebar-stat-item">
            <h4>Route (Total sélection)</h4>
            <div class="sidebar-stat-value">{{ stats.route }}</div>
        </div>
        <div class="sidebar-stat-item">
            <h4>Véhicule (Total sélection)</h4>
            <div class="sidebar-stat-value">{{ stats.vehicule }}</div>
        </div>
    </div>
</div>

<div id="main-content">
    <div id="map-container">
        <iframe src="{{ url_for('static', filename='carte_accidents.html') }}" width="100%" height="100%" style="border:none;"></iframe>
    </div>
    
    <div id="info-panel-cumul">
        <div class="cumul-box">
            <div class="cumul-label">Total accidents (tous filtres cumulés)</div>
            <div class="cumul-value">{{ stats.cumul_total }}</div>
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
            f.write(f"heure:{h}\ngravite:{g}\nroute:{r}\ncatv:{v}\nsexe:{s}")

    return render_template_string(HTML_PAGE, stats=obtenir_stats_completes())

if __name__ == "__main__":
    app.run(debug=True)