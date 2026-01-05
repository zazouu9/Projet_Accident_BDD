import sqlite3
import pandas as pd
import os

DB_PATH = "database/accidents_routiers.db"
OUT_DIR = "results"

os.makedirs(OUT_DIR, exist_ok=True)

def main():
    # connexion à la base
    conn = sqlite3.connect(DB_PATH)
    print("Connexion à la base OK")

    # ACCIDENTS PAR HEURE

    query_heure = """
    SELECT
        SUBSTR(hrmn, 1, 2) AS heure,
        COUNT(DISTINCT Num_Acc) AS nb_accidents
    FROM caracteristiques
    WHERE hrmn IS NOT NULL AND hrmn != ''
    GROUP BY heure
    ORDER BY heure;
    """
    df_heure = pd.read_sql_query(query_heure, conn)
    df_heure.to_csv(
        os.path.join(OUT_DIR, "accidents_par_heure.csv"),
        index=False,
        encoding="utf-8"
    )
    print(" accidents_par_heure.csv est bien créé")



if __name__ == "__main__":
    main()
