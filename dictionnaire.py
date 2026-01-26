# dictionnaires.py

# --- ROUTES ---
CATR_TO_ROUTE = {
    1: "Autoroute",
    2: "Nationale",
    3: "Départementale",
    4: "Communale",
    5: "Hors réseau public",
    6: "Parc de stationnement ouvert à la circulation publique",
    7: "Routes de métropole urbaine",
    9: "Autre",
}

# Texte venant du fichier filtre -> code catr
# (on accepte plusieurs variantes)
ROUTE_TO_CATR = {
    "Autoroute": 1,
    "Nationale": 2,
    "Route nationale": 2,
    "Départementale": 3,
    "Route Départementale": 3,
    "Communale": 4,
    "Voie Communales": 4,
    "Hors réseau public": 5,
    "Parc de stationnement ouvert à la circulation publique": 6,
    "Routes de métropole urbaine": 7,
    "Route de métropole urbaine": 7,
    "Autre": 9,
    "autre": 9,
}

# --- VEHICULES ---
CATV_TO_LABEL = {
    0: "Indéterminable",
    1: "Bicyclette",
    2: "Cyclomoteur <50cm3",
    3: "Voiturette (Quadricycle à moteur carrossé)",
    4: "Réf. inutilisée depuis 2006 (scooter immatriculé)",
    5: "Réf. inutilisée depuis 2006 (motocyclette)",
    6: "Réf. inutilisée depuis 2006 (side-car)",
    7: "VL seul",
    8: "Réf. inutilisée depuis 2006 (VL + caravane)",
    9: "Réf. inutilisée depuis 2006 (VL + remorque)",
    10: "VU seul 1,5T <= PTAC <= 3,5T (avec ou sans remorque)",
    11: "Réf. inutilisée depuis 2006 (VU + caravane)",
    12: "Réf. inutilisée depuis 2006 (VU + remorque)",
    13: "PL seul 3,5T <PTCA <= 7,5T",
    14: "PL seul > 7,5T",
    15: "PL > 3,5T + remorque",
    16: "Tracteur routier seul",
    17: "Tracteur routier + semi-remorque",
    18: "Réf. inutilisée depuis 2006 (transport en commun)",
    19: "Réf. inutilisée depuis 2006 (tramway)",
    20: "Engin spécial",
    21: "Tracteur agricole",
    30: "Scooter < 50 cm3",
    31: "Motocyclette > 50 cm3 et <= 125 cm3",
    32: "Scooter > 50 cm3 et <= 125 cm3",
    33: "Motocyclette > 125 cm3",
    34: "Scooter > 125 cm3",
    35: "Quad léger <= 50 cm3",
    36: "Quad lourd > 50 cm3",
    37: "Autobus",
    38: "Autocar",
    39: "Train",
    40: "Tramway",
    41: "3RM <= 50 cm3",
    42: "3RM > 50 cm3 <= 125 cm3",
    43: "3RM > 125 cm3",
    50: "EDP à moteur",
    60: "EDP sans moteur",
    80: "VAE",
    99: "Autre véhicule",
}

# --- GRAVITE ---
GRAV_TO_LABEL = {
    1: "Indemne",
    2: "Tué",
    3: "Hospitalisé",
    4: "Léger",
}

# --- SEXE ---
SEXE_TO_LABEL = {
    1: "Homme",
    2: "Femme",
}

# --- ZONE ---
ZONE_TO_LABEL = {
    1: "Agglomération",
    2: "Hors agglomération",
    3: "Autre",
}

GRAV_TO_COLOR = {
    1: "blue",     # Indemne
    2: "black",    # Mort
    3: "green",    # Hospitalisé
    4: "orange",   # Blessés léger
}

# --- DEPARTEMENTS ---
# afficher dans le filtre département avec le numéro et le nom
#NB: on garde les codes en string pour gérer 2A/2B et DOM-TOM.

DEP_TO_NAME = {
    "01": "Ain",
    "02": "Aisne",
    "03": "Allier",
    "04": "Alpes-de-Haute-Provence",
    "05": "Hautes-Alpes",
    "06": "Alpes-Maritimes",
    "07": "Ardèche",
    "08": "Ardennes",
    "09": "Ariège",
    "10": "Aube",
    "11": "Aude",
    "12": "Aveyron",
    "13": "Bouches-du-Rhône",
    "14": "Calvados",
    "15": "Cantal",
    "16": "Charente",
    "17": "Charente-Maritime",
    "18": "Cher",
    "19": "Corrèze",
    "2A": "Corse-du-Sud",
    "2B": "Haute-Corse",
    "21": "Côte-d'Or",
    "22": "Côtes-d'Armor",
    "23": "Creuse",
    "24": "Dordogne",
    "25": "Doubs",
    "26": "Drôme",
    "27": "Eure",
    "28": "Eure-et-Loir",
    "29": "Finistère",
    "30": "Gard",
    "31": "Haute-Garonne",
    "32": "Gers",
    "33": "Gironde",
    "34": "Hérault",
    "35": "Ille-et-Vilaine",
    "36": "Indre",
    "37": "Indre-et-Loire",
    "38": "Isère",
    "39": "Jura",
    "40": "Landes",
    "41": "Loir-et-Cher",
    "42": "Loire",
    "43": "Haute-Loire",
    "44": "Loire-Atlantique",
    "45": "Loiret",
    "46": "Lot",
    "47": "Lot-et-Garonne",
    "48": "Lozère",
    "49": "Maine-et-Loire",
    "50": "Manche",
    "51": "Marne",
    "52": "Haute-Marne",
    "53": "Mayenne",
    "54": "Meurthe-et-Moselle",
    "55": "Meuse",
    "56": "Morbihan",
    "57": "Moselle",
    "58": "Nièvre",
    "59": "Nord",
    "60": "Oise",
    "61": "Orne",
    "62": "Pas-de-Calais",
    "63": "Puy-de-Dôme",
    "64": "Pyrénées-Atlantiques",
    "65": "Hautes-Pyrénées",
    "66": "Pyrénées-Orientales",
    "67": "Bas-Rhin",
    "68": "Haut-Rhin",
    "69": "Rhône",
    "70": "Haute-Saône",
    "71": "Saône-et-Loire",
    "72": "Sarthe",
    "73": "Savoie",
    "74": "Haute-Savoie",
    "75": "Paris",
    "76": "Seine-Maritime",
    "77": "Seine-et-Marne",
    "78": "Yvelines",
    "79": "Deux-Sèvres",
    "80": "Somme",
    "81": "Tarn",
    "82": "Tarn-et-Garonne",
    "83": "Var",
    "84": "Vaucluse",
    "85": "Vendée",
    "86": "Vienne",
    "87": "Haute-Vienne",
    "88": "Vosges",
    "89": "Yonne",
    "90": "Territoire de Belfort",
    "91": "Essonne",
    "92": "Hauts-de-Seine",
    "93": "Seine-Saint-Denis",
    "94": "Val-de-Marne",
    "95": "Val-d'Oise",
    # DOM
    "971": "Guadeloupe",
    "972": "Martinique",
    "973": "Guyane",
    "974": "La Réunion",
    "976": "Mayotte",
}


# --- MOIS ---
MOIS_TO_LABEL = {
    1: "Janvier",
    2: "Février",
    3: "Mars",
    4: "Avril",
    5: "Mai",
    6: "Juin",
    7: "Juillet",
    8: "Août",
    9: "Septembre",
    10: "Octobre",
    11: "Novembre",
    12: "Décembre",
}

