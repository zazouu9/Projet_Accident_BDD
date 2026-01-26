#!/bin/bash

# Création de l'environnement virtuel (si non existant)
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activation de l'environnement virtuel
source venv/bin/activate

# Mise à jour de pip
pip install --upgrade pip

# Installation des dépendances
pip install pandas folium flask polyline

# Lancement du script de statistiques
python stat_1.py

# Lancement de l'application web Flask en arrière-plan
python page_web.py &

# Petite pause pour laisser le serveur démarrer
sleep 2

# Ouverture automatique de la page web
if command -v xdg-open &> /dev/null
then
    xdg-open http://127.0.0.1:5001
elif command -v open &> /dev/null
then
    open http://127.0.0.1:5001
elif command -v start &> /dev/null
then
    start http://127.0.0.1:5001
fi
