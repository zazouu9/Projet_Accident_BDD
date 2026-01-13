from flask import Flask, request, render_template_string
import pandas as pd
import os

app = Flask(__name__)

def charger_donnees(nom_fichier):
    if os.path.exists(nom_fichier):
        df = pd.read_csv(nom_fichier)
        return df.to_dict(orient='records')
    return []

HTML_PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Analyse Accidents</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; margin: 0; display: flex; height: 100vh; overflow: hidden; }
        
        /* Barre latérale - Style conservé */
        #sidebar { width: 300px; padding: 15px; background: #f4f4f4; border-right: 1px solid #ccc; overflow-y: auto; flex-shrink: 0; }
        
        #main-content { flex-grow: 1; display: flex; flex-direction: column; }
        
        /* Carte : Prend le maximum d'espace possible */
        #map-container { flex-grow: 1; width: 100%; }
        
        /* Zone information TRÈS RÉDUITE */
        #info-panel { 
            height: 80px; 
            padding: 5px 15px; 
            background: #fff; 
            border-top: 1px solid #ccc; 
            display: flex; 
            align-items: center; 
        }
        
        .stats-grid { 
            display: grid; 
            grid-template-columns: repeat(5, 1fr); 
            gap: 20px; 
            width: 100%; 
            text-align: center; 
        }
        
        .stat-box { border-left: 1px solid #eee; }
        .stat-box:first-child { border-left: none; }
        
        .stat-box h4 { margin: 0; font-size: 0.75em; color: #666; text-transform: uppercase; }
        .stat-number { font-size: 1.3em; font-weight: bold; color: #d9534f; }
        
        label { display: block; margin-top: 8px; font-size: 0.9em; }
        fieldset { margin-top: 10px; padding: 8px; font-size: 0.85em; }
        button { margin-top: 10px; padding: 10px; width: 100%; background: #28a745; color: white; border: none; cursor: pointer; border-radius: 4px; }
    </style>
</head>
<body>

<div id="sidebar">
    <h3>Filtres</h3>
    {% if message %}<p style="color:green; font-size:0.8em; font-weight:bold;">{{ message }}</p>{% endif %}
    <form method="post">
        <label>Heure : <input type="number" name="heure" min="0" max="23" style="width:50px;" required></label>
        <fieldset>
            <legend>Gravité</legend>
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
                <option value="07">VL seul</option>
                <option value="01">Bicyclette</option>
                <option value="33">Moto > 125 cm3</option>
                <option value="14">PL > 7,5T</option>
            </select>
        </label>
        <fieldset>
            <legend>Sexe</legend>
            <label><input type="radio" name="sexe" value="1" required> Masculin</label>
            <label><input type="radio" name="sexe" value="2"> Féminin</label>
        </fieldset>
        <button type="submit">Appliquer les filtres</button>
    </form>
</div>

<div id="main-content">
    <div id="map-container">
        <iframe src="{{ url_for('static', filename='carte_accidents.html') }}" width="100%" height="100%" style="border:none;"></iframe>
    </div>

    <div id="info-panel">
        <div class="stats-grid">
            <div class="stat-box">
                <h4>Gravité (Total)</h4>
                <div class="stat-number">{{ gravite_data|sum(attribute='nombre_accidents') }}</div>
            </div>
            <div class="stat-box">
                <h4>Heure (Total)</h4>
                <div class="stat-number">{{ heure_data|sum(attribute='nombre_accidents') }}</div>
            </div>
            <div class="stat-box">
                <h4>Hommes</h4>
                <div class="stat-number">
                    {% for s in sexe_data %}{% if s.sexe == 1 %}{{ s.nombre_accidents }}{% endif %}{% endfor %}
                </div>
            </div>
            <div class="stat-box">
                <h4>Routes</h4>
                <div class="stat-number">{{ route_data|sum(attribute='nombre_accidents') }}</div>
            </div>
            <div class="stat-box">
                <h4>Véhicules</h4>
                <div class="stat-number">{{ vehicule_data|sum(attribute='nombre_accidents') }}</div>
            </div>
        </div>
    </div>
</div>

</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    message = None
    if request.method == "POST":
        # ... (Logique de sauvegarde inchangée)
        message = "Fichier mis à jour."

    return render_template_string(
        HTML_PAGE, 
        message=message,
        gravite_data=charger_donnees('accidents_par_gravite.csv'),
        heure_data=charger_donnees('accidents_par_heure.csv'),
        sexe_data=charger_donnees('accidents_par_sexe.csv'),
        route_data=charger_donnees('accidents_par_type_route.csv'),
        vehicule_data=charger_donnees('accidents_par_type_vehicule.csv')
    )

if __name__ == "__main__":
    app.run(debug=True)