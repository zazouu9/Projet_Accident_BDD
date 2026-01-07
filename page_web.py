from flask import Flask, request, render_template_string

app = Flask(__name__)

HTML_PAGE = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Filtres accidents</title>

<style>
body {
    font-family: Arial;
    margin: 20px;
}
label {
    display: block;
    margin-top: 10px;
}
fieldset {
    margin-top: 15px;
    padding: 10px;
}
button {
    margin-top: 15px;
    padding: 8px;
}
.success {
    color: green;
    font-weight: bold;
}
</style>
</head>

<body>
<div id="container">
<h2>Filtres accidents</h2>

{% if message %}
<p class="success">{{ message }}</p>
{% endif %}

<form method="post">

<label>
Heure :
<input type="number" name="heure" min="0" max="23" required>
</label>

<fieldset>
<legend>Gravité</legend>
<label><input type="checkbox" name="gravite" value="1"> 1 – Indemne</label>
<label><input type="checkbox" name="gravite" value="2"> 2 – Tué</label>
<label><input type="checkbox" name="gravite" value="3"> 3 – Blessé hospitalisé</label>
<label><input type="checkbox" name="gravite" value="4"> 4 – Blessé léger</label>
</fieldset>

<label>
Type de route :
<select name="route" required>
<option value="Autoroute">Autoroute</option>
<option value="Nationale">Nationale</option>
<option value="Départementale">Départementale</option>
<option value="Communale">Communale</option>
</select>
</label>

<label>
Catégorie véhicule (catv) :
<select name="catv" required>
<option value="00">00 – Indéterminable</option>
<option value="01">01 – Bicyclette</option>
<option value="02">02 – Cyclomoteur &lt;50cm3</option>
<option value="03">03 – Voiturette</option>
<option value="07">07 – VL seul</option>
<option value="10">10 – VU seul</option>
<option value="13">13 – PL 3,5T–7,5T</option>
<option value="14">14 – PL &gt; 7,5T</option>
<option value="30">30 – Scooter &lt; 50 cm3</option>
<option value="31">31 – Moto 50–125 cm3</option>
<option value="33">33 – Moto &gt; 125 cm3</option>
<option value="80">80 – VAE</option>
<option value="99">99 – Autre véhicule</option>
</select>
</label>

<fieldset>
<legend>Sexe</legend>
<label><input type="radio" name="sexe" value="1" required> Masculin</label>
<label><input type="radio" name="sexe" value="2"> Féminin</label>
</fieldset>

<button type="submit">Créer le fichier résultat</button>

</form>
</div>

<!-- CARTE -->
<div>
<iframe src="{{ url_for('static', filename='carte_accidents.html') }}"
        width="100%"
        height="100%"
        style="border:none;">
</iframe>
</div>

<!-- INFO -->
<div id="info">
<h3>Informations</h3>
<p>Le fichier TXT contient les filtres sélectionnés.</p>
</div>

</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    message = None

    if request.method == "POST":
        heure = request.form.get("heure")
        gravites = request.form.getlist("gravite")
        route = request.form.get("route")
        catv = request.form.get("catv")
        sexe = request.form.get("sexe")

        gravite_str = ";".join(gravites)

        contenu = "heure,gravite,type_route,categorie_vehicule,sexe\n"
        contenu += f"{heure},{gravite_str},{route},{catv},{sexe}\n"

        with open("resultat_filtre.txt", "w", encoding="utf-8") as f:
            f.write(contenu)

        message = "✔ Fichier resultat_filtre.txt créé dans le répertoire courant"

    return render_template_string(HTML_PAGE, message=message)

if __name__ == "__main__":
    app.run(debug=True)
