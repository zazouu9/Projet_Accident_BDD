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

def obtenir_valeur_filtree():
    """Cherche les totaux dans chaque CSV selon les filtres sélectionnés."""
    filtres = lire_filtres()
    stats = {"gravite": 0, "heure": 0, "sexe": 0, "route": 0, "vehicule": 0}
    
    if not filtres:
        return stats

    try:
        # 1. HEURE (Format attendu dans CSV: 00, 01, 02...)
        if "heure" in filtres:
            df = pd.read_csv("results/accidents_par_heure.csv")
            # On force en texte et on ajoute un 0 si besoin (ex: "8" -> "08")
            h_cible = str(filtres["heure"]).zfill(2)
            stats["heure"] = df[df['heure'].astype(str).str.zfill(2) == h_cible]['nb_accidents'].sum()

        # 2. GRAVITÉ (Codes: 1, 2, 3, 4)
        if "gravite" in filtres and filtres["gravite"]:
            df = pd.read_csv("results/accidents_par_gravite.csv")
            codes = filtres["gravite"].split(";")
            stats["gravite"] = df[df['grav'].astype(str).isin(codes)]['nb_accidents'].sum()

        # 3. SEXE (1 ou 2)
        if "sexe" in filtres:
            df = pd.read_csv("results/accidents_par_sexe.csv")
            stats["sexe"] = df[df['sexe'].astype(str) == str(filtres["sexe"])]['nb_accidents'].sum()

        # 4. TYPE DE ROUTE (Mapping Nom -> Code catr)
        if "route" in filtres:
            mapping = {"Autoroute": "1", "Nationale": "2", "Départementale": "3", "Communale": "4"}
            code_route = mapping.get(filtres["route"])
            df = pd.read_csv("results/accidents_par_type_route.csv")
            stats["route"] = df[df['catr'].astype(str) == code_route]['nb_accidents'].sum()

        # 5. TYPE DE VÉHICULE (Code catv)
        if "catv" in filtres:
            df = pd.read_csv("results/accidents_par_type_vehicule.csv")
            v_cible = str(filtres["catv"])
            # On compare en ignorant les zéros inutiles au début pour plus de sécurité
            stats["vehicule"] = df[df['catv'].astype(str).str.lstrip('0') == v_cible.lstrip('0')]['nb_accidents'].sum()

    except Exception as e:
        print(f"Erreur de lecture : {e}")
        
    return stats

# --- Le reste du code (HTML_PAGE et route index) reste identique ---

HTML_PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Analyse Accidents</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; margin: 0; display: flex; height: 100vh; overflow: hidden; }
        #sidebar { width: 300px; padding: 15px; background: #f4f4f4; border-right: 1px solid #ccc; overflow-y: auto; flex-shrink: 0; }
        #main-content { flex-grow: 1; display: flex; flex-direction: column; }
        #map-container { flex-grow: 1; width: 100%; }
        #info-panel { height: 75px; padding: 5px 15px; background: #fff; border-top: 1px solid #ccc; display: flex; align-items: center; }
        .stats-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; width: 100%; text-align: center; }
        .stat-box h4 { margin: 0; font-size: 0.7em; color: #666; text-transform: uppercase; }
        .stat-number { font-size: 1.25em; font-weight: bold; color: #d9534f; }
        label { display: block; margin-top: 8px; font-size: 0.9em; }
        button { margin-top: 15px; padding: 10px; width: 100%; background: #28a745; color: white; border: none; cursor: pointer; border-radius: 4px; }
    </style>
</head>
<body>
<div id="sidebar">
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
        <label>Véhicule (catv) :
            <select name="catv" required>
                <option value="07">07 – VL seul</option>
                <option value="01">01 – Bicyclette</option>
                <option value="33">33 – Moto > 125 cm3</option>
                <option value="14">14 – PL > 7,5T</option>
            </select>
        </label>
        <fieldset><legend>Sexe</legend>
            <label><input type="radio" name="sexe" value="1" required> Masculin</label>
            <label><input type="radio" name="sexe" value="2"> Féminin</label>
        </fieldset>
        <button type="submit">Appliquer et Filtrer</button>
    </form>
</div>

<div id="main-content">
    <div id="map-container">
        <iframe src="{{ url_for('static', filename='carte_accidents.html') }}" width="100%" height="100%" style="border:none;"></iframe>
    </div>
    <div id="info-panel">
        <div class="stats-grid">
            <div class="stat-box"><h4>Gravité</h4><div class="stat-number">{{ stats.gravite }}</div></div>
            <div class="stat-box"><h4>Heure</h4><div class="stat-number">{{ stats.heure }}</div></div>
            <div class="stat-box"><h4>Sexe</h4><div class="stat-number">{{ stats.sexe }}</div></div>
            <div class="stat-box"><h4>Route</h4><div class="stat-number">{{ stats.route }}</div></div>
            <div class="stat-box"><h4>Véhicule</h4><div class="stat-number">{{ stats.vehicule }}</div></div>
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

    return render_template_string(HTML_PAGE, stats=obtenir_valeur_filtree())

if __name__ == "__main__":
    app.run(debug=True)