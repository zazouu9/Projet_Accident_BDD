import pandas as pd
import sqlite3
import os

# config des chemins

db_path = 'database/accidents_routiers.db'
csv_files = {
    'caracteristiques': 'data/caract-2024.csv',
    'lieux': 'data/lieux-2024.csv',
    'usagers': 'data/usagers-2024.csv',
    'vehicules': 'data/vehicules-2024.csv'
}

def clean_and_import():
    # connexion a SQLite
    conn = sqlite3.connect(db_path)
    print(f"Connexion réussi à {db_path}")

    for table_name, file_path in csv_files.items():
        if os.path.exists(file_path):
            print(f"importation de {table_name}...")
            
            # lecture du csv avec séparateur ; 
            df = pd.read_csv(file_path, sep=';', encoding='utf-8', low_memory=False)

            # NETTOYAGE +++
            # convertir les colonnes lat/long en nombres
            if table_name == 'caracteristiques':
                df['lat'] = df['lat'].astype(str).str.replace(',', '.').astype(float)
                df['long'] = df['long'].astype(str).str.replace(',', '.').astype(float)
            
            # IMPORTATION SQL
            # écraser la table si script relancé
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            print(f"-> Table '{table_name}' importée ({len(df)} lignes).")
        else:
            print(f"/!\\ Fichier introuvable : {file_path}")

    conn.close()
    print("\nImportation terminée avec succès !")

if __name__ == "__main__":
    clean_and_import()