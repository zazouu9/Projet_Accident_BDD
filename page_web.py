from flask import Flask, request, render_template_string, redirect, url_for
import pandas as pd
import os
import subprocess
import sys
from dictionnaire import DEP_TO_NAME, MOIS_TO_LABEL, CATV_TO_LABEL, GRAV_TO_LABEL, SEXE_TO_LABEL, ROUTE_TO_CATR, MOIS_TO_LABEL
import folium

# on initialisation de l'application Flask
app = Flask(__name__)

def ensure_map_exists():
    # si aucune carte filtrée n'existe, on génère une carte vierge
    os.makedirs("static", exist_ok=True)

    # le nouveau visualisation.py génère 2 cartes
    cluster_path = "static/carte_accidents_cluster.html"
    anime_path = "static/carte_accidents_anime.html"

    # si les cartes existent déjà, rien à faire on recup le fichier
    if os.path.exists(cluster_path) and os.path.exists(anime_path):
        return

    # fallback : cartes vides si jamais
    m = folium.Map(location=[46.2276, 2.2137], zoom_start=6)
    m.save(cluster_path)
    m.save(anime_path)


# Lire les filtres stockés dans resultat_filtre.txt
def lire_filtres():
    # on lit les derniers filtres enregistrés
    filtres = {}
    if os.path.exists("resultat_filtre.txt"):
        with open("resultat_filtre.txt", "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    cle, valeur = line.strip().split(":", 1)
                    filtres[cle] = valeur
    return filtres

def load_df(csv_path="results/accidents_carte_complet.csv", dtype=str):
    """
    Charge le CSV des accidents et fait un petit nettoyage standard.
    - Renvoie un DataFrame Pandas (ou None si fichier absent/illisible)
    - Par défaut dtype=str pour éviter les soucis de zéros (ex: "07") et de NaN
    """
    if not os.path.exists(csv_path):
        return None

    try:
        df = pd.read_csv(csv_path, dtype=dtype)
    except Exception as e:
        print(f"[load_df] Erreur lecture CSV: {e}")
        return None

    # Normalisation simple des chaînes
    if dtype is str:
        for col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].astype(str).str.strip()
        df = df.replace({"nan": ""})

    return df

# Liste des départements possibles (pour remplir le <select>)
# On lit le CSV carte et on récupère les valeurs uniques de la colonne dep.
def get_departements_options(df = load_df()):
    """
    Renvoie une liste de tuples (code_dep, label)
    ex: ("85", "85 - Vendée")
    """
    if df is None or "dep" not in df.columns:
        return []

    deps = (
        df["dep"]
        .astype(str)
        .str.strip()
        .replace({"nan": ""}, regex=True)
    )

    deps = [d for d in deps.unique().tolist() if d]

    # Tri personnalisé des départements
    def dep_sort_key(d):
        # CAS 1 : départements DOM (ex: 971, 972, 973, 974, 976)
        if d.isdigit() and len(d) == 3:
            return (3, int(d), d)   # DOM
        # CAS 2 : départements métropolitains numériques (01 à 95)
        if d.isdigit():
            return (1, int(d), d)   # 01..95
        # CAS 3 : départements spéciaux 2A/2B
        return (2, 0, d)            # 2A/2B

    deps_sorted = sorted(deps, key=dep_sort_key)

    options = []
    for code in deps_sorted:
        name = DEP_TO_NAME.get(code.zfill(2), DEP_TO_NAME.get(code, ""))
        label = f"{code} - {name}" if name else code
        options.append((code, label))

    return options

def get_mois_options(df = load_df()):
    if df is None or "mois" not in df.columns:
        return []

    codes = df["mois"].astype(str).str.strip().replace({"nan": ""})
    codes = [c for c in codes.unique().tolist() if c.isdigit()]

    codes_sorted = sorted(codes, key=lambda x: int(x))

    options = []
    for c in codes_sorted:
        ci = int(c)
        label = MOIS_TO_LABEL.get(ci, f"Mois {ci}")
        options.append((c, label))
    return options

def get_jours_options(df = load_df()):
    if df is None or "jour" not in df.columns:
        return []

    codes = df["jour"].astype(str).str.strip().replace({"nan": ""})
    codes = [c for c in codes.unique().tolist() if c.isdigit()]

    codes_sorted = sorted(codes, key=lambda x: int(x))
    return [(c, c) for c in codes_sorted]


def get_vehicules_options(df = load_df()):
    """
    Liste des véhicules pour le <select>.
    - On lit les codes catv présents dans le CSV carte
    - On les affiche sous la forme : "10 - VU seul ..."
    """
    if df is None or "catv" not in df.columns:
        return []

    # On récupère les codes catv existants
    codes = (
        df["catv"]
        .astype(str)
        .str.strip()
        .replace({"nan": ""})
    )
    codes = [c for c in codes.unique().tolist() if c != ""]

    # Tri numérique des codes
    def sort_key(c):
        try:
            return int(c)
        except:
            return float('inf')  # en cas de code non convertible, le mettre à la fin
            

    codes_sorted = sorted(codes, key=sort_key)

    options = []
    for c in codes_sorted:
        # CATV_TO_LABEL a des clés en int, donc on convertit
        try:
            ci = int(c)
            nom = CATV_TO_LABEL.get(ci, "Inconnu")
        except:
            nom = "Inconnu"

        label = f"{c} - {nom}"
        options.append((c, label))

    return options


def obtenir_stats_completes():
    # on récup les filtres
    filtres = lire_filtres()

    #  on utilise tes dictionnaires au lieu des mappings en dur
    # (GRAV_TO_LABEL, SEXE_TO_LABEL, CATV_TO_LABEL, ROUTE_TO_CATR, CATR_TO_ROUTE, MOIS_TO_LABEL)

    # liste qui contiendra les blocs de statistiques à afficher à gauche (affichage dynamique)
    blocs_actifs = []

    # structure par défaut des statistiques envoyées à la page HTML
    stats = {
        "cumul_total": 0, "hommes_filtres": 0, "femmes_filtres": 0,
        "blocs": blocs_actifs,
        "show_chart": False, "chart_labels": [], "chart_values": []
    }

    # si le fichier de filtre est vide, on renvoie les stats à zéro
    if not filtres:
        return stats

    try:
        # vérification de l'existence du fichier CSV généré par stat_1.py
        if os.path.exists("results/accidents_carte_complet.csv"):
            # chargement des données complètes
            df_all = pd.read_csv("results/accidents_carte_complet.csv")

            # extraction des valeurs des filtres depuis le dictionnaire
            mois_filtre = filtres.get("mois", "")
            jour_filtre = filtres.get("jour", "")
            h_min = filtres.get("h_min", "")
            h_max = filtres.get("h_max", "")
            grav_filtre = filtres.get("gravite", "")
            catv_filtre = filtres.get("catv", "")
            route_filtre = filtres.get("route", "")
            sexe_filtre = filtres.get("sexe", "")
            dep_filtre = filtres.get("dep", "").strip()

            #### CALCULS INDIVIDUELS POUR LES BLOCS DE GAUCHE ####

            # traitement du bloc "Heure" si une heure ou plage est saisie
            if h_min != "" or h_max != "":
                h_mask = pd.Series([True] * len(df_all))
                if h_min != "" and h_max == "":
                    # cas d'une heure précise unique
                    h_mask &= (df_all['heure'] == int(h_min))
                    lbl = f"À {h_min}h"
                else:
                    # cas d'une plage horaire
                    if h_min != "": h_mask &= (df_all['heure'] >= int(h_min))
                    if h_max != "": h_mask &= (df_all['heure'] <= int(h_max))
                    lbl = f"De {h_min or 0}h à {h_max or 23}h"
                # ajout du bloc à la liste si des données existent
                blocs_actifs.append({"titre": "Heure / Plage", "label": lbl, "valeur": int(h_mask.sum())})

            # traitement du bloc "Gravité" si une ou plusieurs cochées
            if grav_filtre:
                codes = [int(x) for x in grav_filtre.split(";") if x]
                val = int(df_all["grav"].isin(codes).sum())
                lbl = ", ".join([GRAV_TO_LABEL.get(c, str(c)) for c in codes])
                blocs_actifs.append({"titre": "Gravité", "label": lbl, "valeur": val})

            # Traitement du bloc "Véhicule"
            if catv_filtre:
                val = int((df_all["catv"] == int(catv_filtre)).sum())
                lbl = CATV_TO_LABEL.get(int(catv_filtre), "Inconnu")
                blocs_actifs.append({"titre": "Véhicule", "label": lbl, "valeur": val})

            # Traitement du bloc "Jour"
            if jour_filtre:
                val = int((df_all["jour"] == int(jour_filtre)).sum())
                lbl = f"Le {jour_filtre}"
                blocs_actifs.append({"titre": "Jour", "label": lbl, "valeur": val})

            # Traitement du bloc "Mois"
            if mois_filtre:
                val = int((df_all["mois"] == int(mois_filtre)).sum())
                lbl = MOIS_TO_LABEL.get(int(mois_filtre), "Inconnu")
                blocs_actifs.append({"titre": "Mois", "label": lbl, "valeur": val})

            # Traitement du bloc "Type de route"
            if route_filtre:
                # route_filtre est un texte (Autoroute, Nationale, ...)
                code_r = ROUTE_TO_CATR.get(route_filtre)
                if code_r is not None:
                    val = int((df_all["catr"] == code_r).sum())
                    lbl = route_filtre
                    blocs_actifs.append({"titre": "Route", "label": lbl, "valeur": val})

            # Traitement du bloc "Sexe"
            if sexe_filtre:
                val = int((df_all["sexe"] == int(sexe_filtre)).sum())
                lbl = SEXE_TO_LABEL.get(int(sexe_filtre), "Inconnu")
                blocs_actifs.append({"titre": "Sexe", "label": lbl, "valeur": val})

            # bloc : département
            if dep_filtre:
                val = int((df_all["dep"] == dep_filtre).sum())
                # affichage "code - nom" si connu
                nom_dep = DEP_TO_NAME.get(dep_filtre.zfill(2), DEP_TO_NAME.get(dep_filtre, ""))
                lbl = f"{dep_filtre} - {nom_dep}" if nom_dep else dep_filtre
                blocs_actifs.append({"titre": "Département", "label": lbl, "valeur": val})

            # --- CUMUL GLOBAL (croisement de tous les filtres) ---
            #### CALCUL CUMULÉ EN BAS A DROITE STAT ####
            # on initialise un masque (filtre) qui accepte tout par défaut
            mask_global = pd.Series([True] * len(df_all))

            # application successive de tous les filtres actifs pour le bandeau du bas et la carte
            if h_min != "" and h_max == "":
                mask_global &= (df_all["heure"] == int(h_min))
            else:
                if h_min != "":
                    mask_global &= (df_all["heure"] >= int(h_min))
                if h_max != "":
                    mask_global &= (df_all["heure"] <= int(h_max))

            if grav_filtre:
                mask_global &= df_all["grav"].isin([int(x) for x in grav_filtre.split(";") if x])

            if catv_filtre:
                mask_global &= (df_all["catv"] == int(catv_filtre))
            
            if jour_filtre:
                mask_global &= (df_all["jour"] == int(jour_filtre))
            
            if mois_filtre:
                mask_global &= (df_all["mois"] == int(mois_filtre))

            if route_filtre:
                code_r = ROUTE_TO_CATR.get(route_filtre)
                if code_r is not None:
                    mask_global &= (df_all["catr"] == code_r)

            if sexe_filtre:
                mask_global &= (df_all["sexe"] == int(sexe_filtre))

            # filtre dep dans le cumul global
            if dep_filtre and "dep" in df_all.columns:
                mask_global &= (df_all["dep"] == dep_filtre)

            df_filtre = df_all[mask_global]

            # remplissage des statistiques pour le bandeau bleu/jaune en bas
            stats["cumul_total"] = len(df_filtre)
            stats["hommes_filtres"] = len(df_filtre[df_filtre['sexe'] == 1])
            stats["femmes_filtres"] = len(df_filtre[df_filtre['sexe'] == 2])

            ####  DONNÉES GRAPHIQUE ####
            # le graphique n'apparaît que si une plage horaire est sélectionnée
            if (h_min != "" or h_max != "") and not df_filtre.empty:
                # groupement des données par heure pour compter les accidents
                chart_group = df_filtre.groupby('heure').size().reset_index(name='count')
                # tri chronologique des heures
                chart_group = chart_group.sort_values('heure')
                # préparation des étiquettes (X) et des valeurs (Y)
                stats["chart_labels"] = [f"{int(h)}h" for h in chart_group['heure'].tolist()]
                stats["chart_values"] = chart_group['count'].tolist()
                stats["show_chart"] = True

    except Exception as e:
        # En cas d'erreur (fichier manquant, erreur de calcul) en console
        print(f"Erreur : {e}")

    return stats


### CONFIGURATION DE LA PAGE HTML ###
HTML_PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Dashboard Accidents</title>
    <style>
        /* Mise en page globale avec Flexbox */
        body { font-family: 'Segoe UI', sans-serif; margin: 0; display: flex; height: 100vh; overflow: hidden; }
        
        /* Barre latérale gauche (Filtres et Stats) */
        #sidebar { width: 340px; padding: 15px; background: #f4f4f4; border-right: 1px solid #ccc; overflow-y: auto; display: flex; flex-direction: column; }
        
        /* Section des formulaires */
        .filter-section { flex-shrink: 0; border-bottom: 2px solid #ddd; padding-bottom: 15px; margin-bottom: 15px; }
        
        /* Style du conteneur de graphique */
        #chart-container { 
            width: 100%; height: 250px; margin-top: 20px; padding: 10px 5px; 
            background: white; border-radius: 8px; border: 1px solid #ddd; 
            display: {% if stats.show_chart %}block{% else %}none{% endif %};
        }

        /* Style des blocs de statistiques à gauche */
        .sidebar-stats { margin-top: 15px; }
        .sidebar-stat-item { background: #fff; padding: 10px; margin-bottom: 8px; border-radius: 4px; border: 1px solid #ddd; }
        .sidebar-stat-item h4 { margin: 0; font-size: 0.75em; color: #666; text-transform: uppercase; border-bottom: 1px solid #eee; padding-bottom: 3px; }
        .stat-label-active { font-weight: bold; color: #007bff; font-size: 0.9em; display: block; margin-top: 2px; }
        .sidebar-stat-value { font-size: 1.1em; font-weight: bold; color: #28a745; margin-top: 5px; }
        
        /* Zone centrale (Carte et Bandeau bas) */
        #main-content { flex-grow: 1; display: flex; flex-direction: column; }
        #map-container { flex-grow: 1; width: 100%; position: relative; }
        
        /* Style du bandeau de cumul en bas */
        #info-panel-cumul { height: 80px; padding: 5px 25px; background: #2c3e50; color: white; display: flex; align-items: center; justify-content: space-between; }
        .stat-box-bottom { text-align: center; }
        .total-value { color: #f1c40f; font-size: 1.8em; font-weight: bold; }
        .gender-blue { color: #3498db; font-size: 1.5em; font-weight: bold; }
        
        /* Style des inputs du formulaire */
        .range-container { display: flex; align-items: center; gap: 5px; margin-top: 5px; }
        .range-container input { width: 70px; padding: 4px; }
        button { margin-top: 15px; padding: 10px; width: 100%; background: #28a745; color: white; border: none; cursor: pointer; border-radius: 4px; font-weight: bold; }
        fieldset { border: 1px solid #ccc; border-radius: 4px; margin-top: 10px; padding: 10px; }
        select { width: 100%; padding: 4px; margin-top: 5px; }

        .page-title { width: 100%; text-align: center; background: #2c3e50; color: white; padding: 15px 0; margin: 0; font-size: 22px; letter-spacing: 1px; }
        
        /* Couleurs pour les labels de gravité */
        .grav { display: block; margin-bottom: 6px; font-weight: 600; }
        .grav-1 { color: blue; } .grav-2 { color: black; } .grav-3 { color: green; } .grav-4 { color: orange; }

        /* BOUTONS CARTE (Cluster / Animé) */
        #map-switch {
            position: absolute;
            top: 12px;
            right: 12px;
            z-index: 9999;
            display: flex;
            gap: 8px;
        }
        #map-switch button {
            width: auto;
            margin: 0;
            padding: 8px 10px;
            border-radius: 10px;
            border: 1px solid #d0d0d0;
            background: white;
            color: #2c3e50;
            font-weight: 700;
            cursor: pointer;
        }
        #map-switch button.active {
            background: #2c3e50;
            color: white;
            border-color: #2c3e50;
        }
    </style>
    
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <script>
        // Fonction pour empêcher de choisir une heure de fin < heure de début
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

            <label>Mois :</label>
                <select name="mois">
                    <option value=""> Tous les mois </option>
                    {% for code, label in mois_options %}
                        <option value="{{ code }}">{{ label }}</option>
                    {% endfor %}
                </select>
            
            <label>Jours :</label>
                <select name="jour">
                    <option value=""> Tous les jours </option>
                    {% for code, label in jours_options %}
                        <option value="{{ code }}">{{ label }}</option>
                    {% endfor %}
                </select>
                
            <label>Itinéraire :</label>
            <input type="text" name="start_city" placeholder="Ville de départ (ex: Paris)" style="width: 95%; padding: 5px; margin-bottom: 5px;">
            <input type="text" name="end_city" placeholder="Ville d'arrivée (ex: Lyon)" style="width: 95%; padding: 5px; margin-bottom: 10px;">

            <fieldset><legend>Gravité</legend>
                <label class="grav grav-1"><input type="checkbox" name="gravite" value="1"> Indemne</label>
                <label class="grav grav-2"><input type="checkbox" name="gravite" value="2"> Tué</label>
                <label class="grav grav-3"><input type="checkbox" name="gravite" value="3"> Hospitalisé</label>
                <label class="grav grav-4"><input type="checkbox" name="gravite" value="4"> Léger</label>
            </fieldset>

            <label>Route : </label>
                <select name="route">
                    <option value=""> Toutes les routes </option>
                    <option value="Autoroute">Autoroute</option>
                    <option value="Nationale">Nationale</option>
                    <option value="Départementale">Départementale</option>
                    <option value="Communale">Communale</option>
                </select>
            
            <label>Véhicule :</label>
            <select name="catv">
                <option value=""> Tous les véhicules </option>
                {% for code, label in vehicules %}
                    <option value="{{ code }}">
                        {{ label }}
                    </option>
                {% endfor %}
            </select>

            <fieldset><legend>Sexe</legend>
                <label><input type="radio" name="sexe" value=""> Tous</label>
                <label><input type="radio" name="sexe" value="1"> Masculin</label>
                <label><input type="radio" name="sexe" value="2"> Féminin</label>
            </fieldset>

            <label>Département :</label>
            <select name="dep">
                <option value=""> Tous les départements </option>
                {% for code, label in deps %}
                <option value="{{ code }}">
                    {{ label }}
                </option>
                {% endfor %}
            </select>
            

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

        <!-- boutons au dessus de l'iframe -->
        <div id="map-switch">
            <button type="button" id="btnCluster" class="active">Clusters</button>
            <button type="button" id="btnAnime">Animé</button>
        </div>

        <!-- iframe par défaut sur la carte cluster -->
        <iframe id="mapFrame"
                src="{{ url_for('static', filename='carte_accidents_cluster.html') }}"
                width="100%" height="100%" style="border:none;"></iframe>
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
                    title: { display: true, text: 'Nombre accidents', font: { size: 11, weight: 'bold' } }
                },
                x: {
                    ticks: { font: { size: 10 } },
                    title: { display: true, text: 'Heure', font: { size: 11, weight: 'bold' } }
                }
            }
        }
    });
    {% endif %}

    // bascule iframe cluster / animé
    // - on change juste l'URL du contenu embarqué dans l'iframe via src :contentReference[oaicite:3]{index=3}

    const frame = document.getElementById("mapFrame");
    const btnC = document.getElementById("btnCluster");
    const btnA = document.getElementById("btnAnime");

    function setActive(which){
        btnC.classList.remove("active");
        btnA.classList.remove("active");
        if(which === "cluster") btnC.classList.add("active");
        if(which === "anime") btnA.classList.add("active");
    }

    btnC.addEventListener("click", () => {
        frame.src = "{{ url_for('static', filename='carte_accidents_cluster.html') }}";
        setActive("cluster");
    });

    btnA.addEventListener("click", () => {
        frame.src = "{{ url_for('static', filename='carte_accidents_anime.html') }}";
        setActive("anime");
    });
</script>

</body>
</html>
"""


### GESTION DES ROUTES FLASK ###
@app.route("/", methods=["GET", "POST"])
def page_principale():
    # Gestion de la soumission du formulaire (clic sur le bouton Filtrer)
    if request.method == "POST":
        # recup des données du formulaire
        mois = request.form.get("mois", "")
        jour = request.form.get("jour", "")
        h_min = request.form.get("h_min", "")
        h_max = request.form.get("h_max", "")

        # si fin < debut, on ignore la fin pour faire une recherche d'heure précise
        if h_min != "" and h_max != "" and int(h_max) < int(h_min):
            h_max = h_min

        # Transformation de la liste de cases cochées pour la gravité en chaîne avec points-virgules
        g = ";".join(request.form.getlist("gravite"))
        r = request.form.get("route", "")
        v = request.form.get("catv", "")
        s = request.form.get("sexe", "")
        dep = request.form.get("dep", "")
        start_city = request.form.get("start_city", "")
        end_city = request.form.get("end_city", "")

        # on écrit les choix dans un fichier texte pour que visualisation.py puisse les lire
        with open("resultat_filtre.txt", "w", encoding="utf-8") as f:
            f.write(
                f"h_min:{h_min}\n"
                f"h_max:{h_max}\n"
                f"mois:{mois}\n"
                f"jour:{jour}\n"
                f"gravite:{g}\n"
                f"route:{r}\n"
                f"catv:{v}\n"
                f"sexe:{s}\n"
                f"dep:{dep}\n"
                f"start_city:{start_city}\n"
                f"end_city:{end_city}\n"
            )

        # Génération carte filtrée
        try:
            # on lance le script externe qui génère la carte HTML basée sur les nouveaux filtres
            subprocess.run([sys.executable, "visualisation.py"], check=True)
        except Exception as e:
            print(f"Erreur génération carte: {e}")

        # Une fois le traitement fini, on redirige vers la page pour afficher les nouveaux résultats
        return redirect(url_for("page_principale"))

    # Affichage de la page (GET)
    ensure_map_exists()

    # On prépare la liste des départements pour le select
    mois_options = get_mois_options()
    jours_options = get_jours_options()
    deps = get_departements_options()
    #dep_selected = lire_filtres().get("dep", "").strip()
    vehicules = get_vehicules_options()
    #catv_selected = lire_filtres().get("catv", "").strip()

    return render_template_string(
        HTML_PAGE,
        stats=obtenir_stats_completes(),
        deps=deps,
        vehicules=vehicules,
        mois_options=mois_options,
        jours_options=jours_options
    )

if __name__ == "__main__":
    app.run(debug=True, port=5001)
