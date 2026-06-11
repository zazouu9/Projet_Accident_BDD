"""
Raspberry Pi — Serveur Flask + MQTT
Arrosage intelligent avec base de données plantes

Endpoints pour MIT App Inventor :
  GET  /api/plantes              → liste des espèces (pour la liste déroulante)
  GET  /api/status/<plant_id>    → état capteurs + recommandation
  POST /api/arroser/<plant_id>   → déclenche la pompe
  GET  /api/capteurs/<plant_id>  → dernières valeurs brutes des capteurs
  POST /api/setplante/<plant_id> → assigner une espèce à un ESP32
"""

from flask import Flask, jsonify, request
import paho.mqtt.client as mqtt
import json
import csv
import threading
import time
import statistics

app = Flask(__name__)

# ─── CONFIG ────────────────────────────────────────────────────────────────────
MQTT_BROKER   = 'localhost'
MQTT_PORT     = 1883
DB_PATH       = 'plant_health_db.txt'   # chemin vers la base de données sur la Pi

# Topics MQTT (un par ESP32, identifié par plant_id ex: "esp01")
# ESP32 publie sur : capteurs/<plant_id>/data
# Pi commande sur  : led/<plant_id>/control  et  pompe/<plant_id>/control
# ────────────────────────────────────────────────────────────────────────────────

# ─── BASE DE DONNÉES PLANTES ───────────────────────────────────────────────────
# Valeurs idéales calculées en moyennant les entrées saines (Health_Score >= 3)
# par espèce dans plant_health_db.txt

plant_ideals = {}   # { "Monstera deliciosa": { "soil_min": x, ... } }

def load_plant_db(path):
    """
    Lit plant_health_db.txt et calcule les valeurs idéales (moyenne des plantes
    avec Health_Score >= 3) pour chaque espèce.
    Champs utilisés : Soil_Moisture_%, Room_Temperature_C, Humidity_%,
                      Watering_Amount_ml, Watering_Frequency_days
    """
    species_data = {}   # { espèce: { champ: [valeurs...] } }

    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                score = int(row['Health_Score'])
            except (ValueError, KeyError):
                continue
            if score < 3:
                continue

            esp = row['Plant_ID'].strip()
            if esp not in species_data:
                species_data[esp] = {
                    'soil': [], 'temp': [], 'humidity': [],
                    'water_ml': [], 'freq_days': []
                }
            try:
                species_data[esp]['soil'].append(float(row['Soil_Moisture_%']))
                species_data[esp]['temp'].append(float(row['Room_Temperature_C']))
                species_data[esp]['humidity'].append(float(row['Humidity_%']))
                species_data[esp]['water_ml'].append(float(row['Watering_Amount_ml']))
                species_data[esp]['freq_days'].append(float(row['Watering_Frequency_days']))
            except (ValueError, KeyError):
                continue

    ideals = {}
    for esp, vals in species_data.items():
        if not vals['soil']:
            continue
        # Marge ±15% autour de la moyenne pour les seuils min/max
        soil_avg  = statistics.mean(vals['soil'])
        temp_avg  = statistics.mean(vals['temp'])
        hum_avg   = statistics.mean(vals['humidity'])
        water_avg = statistics.mean(vals['water_ml'])
        freq_avg  = statistics.mean(vals['freq_days'])

        ideals[esp] = {
            'soil_min':    round(soil_avg * 0.75, 1),
            'soil_max':    round(soil_avg * 1.25, 1),
            'soil_ideal':  round(soil_avg, 1),
            'temp_min':    round(temp_avg - 4, 1),
            'temp_max':    round(temp_avg + 4, 1),
            'temp_ideal':  round(temp_avg, 1),
            'hum_min':     round(hum_avg * 0.80, 1),
            'hum_max':     round(hum_avg * 1.20, 1),
            'hum_ideal':   round(hum_avg, 1),
            'water_ml':    round(water_avg, 0),
            'freq_days':   round(freq_avg, 1),
        }

    return ideals

# Charge la BDD au démarrage
try:
    plant_ideals = load_plant_db(DB_PATH)
    print(f"[DB] {len(plant_ideals)} especes chargees.")
except FileNotFoundError:
    print(f"[DB] ERREUR : fichier introuvable.")

# Valeurs de test fixes — utilisees quand aucune espece n'est selectionnee
# Modifie ces valeurs pour ajuster les seuils pendant les tests
global_ideal = {
    'soil_min':   30.0,   # % humidite minimale avant d'arroser
    'soil_max':   70.0,   # % humidite maximale (trop arrose)
    'soil_ideal': 50.0,   # % humidite ideale
    'temp_min':   15.0,   # temperature minimale (C)
    'temp_max':   30.0,   # temperature maximale (C)
    'temp_ideal': 22.0,   # temperature ideale (C)
    'hum_min':    40.0,   # humidite air minimale (%)
    'hum_max':    80.0,   # humidite air maximale (%)
    'hum_ideal':  60.0,   # humidite air ideale (%)
    'water_ml':   200.0,  # quantite d'eau recommandee (ml)
    'freq_days':  3.0,    # frequence d'arrosage (jours)
}
print(f"[TEST] Seuils fixes — sol: {global_ideal['soil_min']}% - {global_ideal['soil_max']}% | temp: {global_ideal['temp_min']}C - {global_ideal['temp_max']}C")


# ─── ÉTAT GLOBAL ───────────────────────────────────────────────────────────────
# Dernières données capteurs reçues par ESP32
# sensor_data[plant_id] = { 'sol': %, 'temp': °C, 'lum': raw, 'ts': timestamp }
sensor_data = {}

# Association plant_id → espèce (choisie par l'utilisateur via l'app)
# plant_assignment[plant_id] = "Monstera deliciosa"
plant_assignment = {}

# Verrou pour accès thread-safe
lock = threading.Lock()

# ─── MQTT ──────────────────────────────────────────────────────────────────────
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connecté (rc={rc})")
    # Abonnement générique : capteurs de tous les ESP32
    client.subscribe('capteurs/+/data')

def on_message(client, userdata, msg):
    """Reçoit les données capteurs d'un ESP32 et les stocke."""
    # Topic = capteurs/<plant_id>/data
    parts = msg.topic.split('/')
    if len(parts) != 3:
        return
    plant_id = parts[1]

    try:
        payload = json.loads(msg.payload.decode())
    except Exception:
        return

    with lock:
        premiere_fois = plant_id not in sensor_data
        sensor_data[plant_id] = {
            'sol':  payload.get('sol', 0),
            'temp': payload.get('temp', 0),
            'lum':  payload.get('lum', 0),
            'ts':   time.time()
        }
    # Éteindre la LED si c'est la première connexion de cet ESP32
    if premiere_fois:
        mqtt_client.publish(f'led/{plant_id}/control', 'OFF')
        print(f'[LED] {plant_id} → OFF (première connexion)')
    print(f"[MQTT] {plant_id} → sol={payload.get('sol')}% temp={payload.get('temp')}°C lum={payload.get('lum')}")

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

# ─── LOGIQUE DE RECOMMANDATION ─────────────────────────────────────────────────

def analyze(plant_id):
    """
    Compare les capteurs avec les valeurs idéales de l'espèce assignée.
    Retourne un dict avec status, alertes, recommandation, score santé (0-100).
    """
    with lock:
        data    = sensor_data.get(plant_id)
        espece  = plant_assignment.get(plant_id)

    result = {
        'plant_id':   plant_id,
        'espece':     espece or 'Non définie',
        'capteurs':   data,
        'alertes':    [],
        'score':      None,
        'arroser':    False,
        'message':    '',
        'ideals':     None,
    }

    if not data:
        result['message'] = "Aucune donnee capteur recue pour cet ESP32."
        return result

    # Sans espece assignee : utiliser la moyenne generale de la BDD
    if not espece or espece not in plant_ideals:
        if not global_ideal:
            result['message'] = "Espece non configuree et BDD indisponible."
            return result
        ideal = global_ideal
        result['espece'] = "Moyenne generale (toutes plantes)"
        result['mode_test'] = True
    else:
        ideal = plant_ideals[espece]
        result['mode_test'] = False
    result['ideals'] = ideal
    alertes = []
    score_pts = 100

    # --- Sol (humidité %) ---
    sol = data['sol']
    if sol < ideal['soil_min']:
        manque = round(ideal['soil_ideal'] - sol, 1)
        alertes.append(f"Sol trop sec ({sol}% < min {ideal['soil_min']}%)")
        result['arroser'] = True
        score_pts -= 30
    elif sol > ideal['soil_max']:
        alertes.append(f"Sol trop humide ({sol}% > max {ideal['soil_max']}%)")
        score_pts -= 20
    else:
        pass  # OK

    # --- Température ---
    temp = data['temp']
    if temp < ideal['temp_min']:
        alertes.append(f"Température trop basse ({temp}°C < min {ideal['temp_min']}°C)")
        score_pts -= 20
    elif temp > ideal['temp_max']:
        alertes.append(f"Température trop haute ({temp}°C > max {ideal['temp_max']}°C)")
        score_pts -= 20

    # --- Score final ---
    score_pts = max(0, score_pts)

    if score_pts >= 80:
        status = "✅ Plante en bonne santé"
    elif score_pts >= 50:
        status = "⚠️ Attention requise"
    else:
        status = "🚨 Plante en danger"

    # ROUGE si arrosage nécessaire, sinon selon le score
    if result['arroser']:
        couleur = "ROUGE"
    elif score_pts >= 80:
        couleur = "VERT"
    else:
        couleur = "ORANGE"

    result['couleur'] = couleur

    # Envoie toujours la couleur des qu'on a des donnees
    mqtt_client.publish(f'led/{plant_id}/control', couleur)
    print(f'[LED] {plant_id} couleur={couleur} arroser={result["arroser"]} score={score_pts}')

    if result['arroser']:
        eau_ml = ideal['water_ml']
        result['message'] = (
            f"{status}. Arrosage recommandé ({int(eau_ml)} ml). "
            f"Fréquence idéale : tous les {ideal['freq_days']} jours."
        )
    elif alertes:
        result['message'] = f"{status}. " + " | ".join(alertes)
    else:
        result['message'] = f"{status}. Tous les paramètres sont dans les normes."

    result['alertes'] = alertes
    result['score']   = score_pts
    return result

# ─── ENDPOINTS API ─────────────────────────────────────────────────────────────

@app.route('/api/plantes', methods=['GET'])
def liste_plantes():
    """
    Retourne la liste des espèces disponibles dans la BDD.
    MIT App Inventor : utiliser pour remplir la liste déroulante (ListPicker).
    """
    return jsonify({
        'especes': sorted(plant_ideals.keys()),
        'count':   len(plant_ideals)
    })


@app.route('/api/setplante/<plant_id>', methods=['POST'])
def set_plante(plant_id):
    """
    Assigne une espèce à un ESP32.
    Corps JSON : { "espece": "Monstera deliciosa" }
    MIT App Inventor : appeler quand l'utilisateur valide son choix dans la liste déroulante.
    """
    body = request.get_json(force=True, silent=True) or {}
    espece = body.get('espece', '').strip()

    if not espece:
        return jsonify({'ok': False, 'erreur': 'Champ "espece" manquant'}), 400
    if espece not in plant_ideals:
        return jsonify({'ok': False, 'erreur': f'Espèce "{espece}" inconnue dans la BDD'}), 404

    with lock:
        plant_assignment[plant_id] = espece

    print(f"[CONFIG] {plant_id} → {espece}")
    return jsonify({'ok': True, 'plant_id': plant_id, 'espece': espece})


@app.route('/api/status/<plant_id>', methods=['GET'])
def status(plant_id):
    """
    Retourne l'état complet : capteurs, idéaux, alertes, score, recommandation.
    MIT App Inventor : appeler toutes les 10s pour rafraîchir l'affichage.
    """
    return jsonify(analyze(plant_id))


@app.route('/api/capteurs/<plant_id>', methods=['GET'])
def capteurs_raw(plant_id):
    """
    Retourne uniquement les dernières valeurs brutes des capteurs.
    MIT App Inventor : affichage léger si pas besoin de l'analyse complète.
    """
    with lock:
        data = sensor_data.get(plant_id)
    if not data:
        return jsonify({'ok': False, 'erreur': 'Aucune donnée'}), 404
    return jsonify({'ok': True, 'plant_id': plant_id, **data})


@app.route('/api/arroser/<plant_id>', methods=['POST'])
def arroser(plant_id):
    """
    Déclenche la pompe de l'ESP32 ciblé via MQTT.
    MIT App Inventor : appeler quand l'utilisateur appuie sur le bouton "Confirmer arrosage".
    Corps JSON optionnel : { "duree": 10 }  (durée en secondes, défaut=10)
    """
    body   = request.get_json(force=True, silent=True) or {}
    duree  = int(body.get('duree', 10))

    topic  = f'pompe/{plant_id}/control'
    mqtt_client.publish(topic, 'ON')
    print(f"[POMPE] {plant_id} → ON ({duree}s) via {topic}")

    # La pompe s'arrête automatiquement côté ESP32 après la durée configurée
    # (voir esp32_code.py : time.sleep(10) puis pompe_pin.off())
    # Si tu veux piloter la durée depuis la Pi, envoie la durée en JSON :
    # mqtt_client.publish(topic, json.dumps({'cmd': 'ON', 'duree': duree}))

    return jsonify({
        'ok':      True,
        'plant_id': plant_id,
        'message': f"Pompe activée pour {duree}s sur {plant_id}."
    })


@app.route('/api/led/<plant_id>/<action>', methods=['POST'])
def led(plant_id, action):
    """
    Contrôle la LED RGB. action = VERT | ORANGE | ROUGE | OFF
    La couleur est aussi mise à jour automatiquement à chaque /api/status.
    """
    ACTIONS_VALIDES = ('VERT', 'ORANGE', 'ROUGE', 'OFF')
    if action.upper() not in ACTIONS_VALIDES:
        return jsonify({'ok': False, 'erreur': f'Action invalide. Valeurs : {ACTIONS_VALIDES}'}), 400
    mqtt_client.publish(f'led/{plant_id}/control', action.upper())
    print(f'[LED] {plant_id} -> {action.upper()} (manuel)')
    return jsonify({'ok': True, 'plant_id': plant_id, 'led': action.upper()})


# ─── PAGE WEB DE DEBUG (optionnelle, accès navigateur) ─────────────────────────
@app.route('/')
def debug_ui():
    """Interface web simple pour tester sans MIT App Inventor."""
    ids_html = ''.join(
        f'<option value="{k}">{k}</option>'
        for k in sorted(sensor_data.keys()) or ['esp01']
    )
    return f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><title>Debug Arrosage</title>
<style>
  body{{font-family:monospace;background:#111;color:#0f0;padding:2rem}}
  button{{background:#0f0;color:#000;border:none;padding:.5rem 1rem;cursor:pointer;margin:.25rem}}
  select,input{{background:#222;color:#0f0;border:1px solid #0f0;padding:.3rem}}
  pre{{background:#1a1a1a;padding:1rem;border-radius:4px;overflow-x:auto}}
</style></head>
<body>
<h2>🌿 Debug Station Arrosage</h2>
<label>ESP32 ID : <input id="pid" value="esp01" style="width:120px"></label>
<br><br>
<button onclick="status()">📊 Voir statut</button>
<button onclick="arroser()">💧 Arroser</button>
<button onclick="led('ON')">💡 LED ON</button>
<button onclick="led('OFF')">💡 LED OFF</button>
<br><br>
<pre id="out">En attente...</pre>
<script>
const pid=()=>document.getElementById('pid').value;
const out=d=>document.getElementById('out').textContent=JSON.stringify(d,null,2);
async function status(){{const r=await fetch('/api/status/'+pid());out(await r.json())}}
async function arroser(){{const r=await fetch('/api/arroser/'+pid(),{{method:'POST'}});out(await r.json())}}
async function led(a){{const r=await fetch('/api/led/'+pid()+'/'+a,{{method:'POST'}});out(await r.json())}}
setInterval(status,10000);
</script>
</body></html>"""


if __name__ == '__main__':
    print("[Pi] Serveur démarré sur http://0.0.0.0:8080")
    app.run(host='0.0.0.0', port=8080, debug=False)

