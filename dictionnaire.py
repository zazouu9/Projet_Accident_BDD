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
# Ajuste si ton référentiel diffère
ZONE_TO_LABEL = {
    1: "Agglomération",
    2: "Hors agglomération",
    3: "Autre",
}
