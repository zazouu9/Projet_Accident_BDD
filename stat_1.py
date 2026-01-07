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

    # 2 ACCIDENTS PAR MOIS
    
    query_mois = """
    SELECT
        mois,
        COUNT(DISTINCT Num_Acc) AS nb_accidents
    FROM caracteristiques
    WHERE mois IS NOT NULL AND mois != ''
    GROUP BY mois
    ORDER BY CAST(mois AS INTEGER);
    """
    df_mois = pd.read_sql_query(query_mois, conn)
    df_mois.to_csv(
        os.path.join(OUT_DIR, "accidents_par_mois.csv"),
        index=False,
        encoding="utf-8"
    )
    print("accidents_par_mois.csv bien créé")


    # 3 ACCIDENTS PAR JOUR
    
    query_jour = """
    SELECT
        jour,
        COUNT(DISTINCT Num_Acc) AS nb_accidents
    FROM caracteristiques
    WHERE jour IS NOT NULL AND jour != ''
    GROUP BY jour
    ORDER BY CAST(jour AS INTEGER);
    """
    df_jour = pd.read_sql_query(query_jour, conn)
    df_jour.to_csv(
        os.path.join(OUT_DIR, "accidents_par_jour.csv"),
        index=False,
        encoding="utf-8"
    )
    print("accidents_par_jour.csv est bien créé")


    # 4 STATISTIQUES PAR GRAVITÉ
    
    query_gravite = """
    SELECT
        grav,
        COUNT(DISTINCT Num_Acc) AS nb_accidents
    FROM usagers
    GROUP BY grav;
    """
    
    df_grav = pd.read_sql_query(query_gravite, conn)
    df_grav.to_csv(
        os.path.join(OUT_DIR, "accidents_par_gravite.csv"),
        index=False,
        encoding="utf-8"
    )
    print("accidents_par_gravite.csv créé")

    # 5. ACCIDENTS PAR TYPE DE ROUTE
    query_route = """
    SELECT
        catr,
        COUNT(DISTINCT Num_Acc) AS nb_accidents
    FROM lieux
    WHERE catr IS NOT NULL AND catr != ''
    GROUP BY catr
    ORDER BY catr;
    """
    
    df_route = pd.read_sql_query(query_route, conn)
    df_route.to_csv(
        os.path.join(OUT_DIR, "accidents_par_type_route.csv"),
        index=False,
        encoding="utf-8"
    )
    print("accidents_par_type_route.csv créé")
    
    # 6. ACCIDENTS PAR SEXE
    query_sexe = """
    SELECT
        sexe,
        COUNT(DISTINCT Num_Acc) AS nb_accidents
    FROM usagers
    WHERE sexe IN ('1', '2')
    GROUP BY sexe
    ORDER BY sexe;
    """
    df_sexe = pd.read_sql_query(query_sexe, conn)
    df_sexe.to_csv(
        os.path.join(OUT_DIR, "accidents_par_sexe.csv"),
        index=False,
        encoding="utf-8"
    )
    print("accidents_par_sexe.csv créé")

# 7. DONNÉES COMPLÈTES POUR LA CARTE
    query_carte = """
    SELECT DISTINCT
        SUBSTR(c.hrmn, 1, 2) AS heure,
        c.agg AS zone,
        l.catr,
        u.grav,
        c.lat,
        c.long
    FROM caracteristiques c
    LEFT JOIN lieux l ON c.Num_Acc = l.Num_Acc
    LEFT JOIN usagers u ON c.Num_Acc = u.Num_Acc
    WHERE c.lat IS NOT NULL 
        AND c.long IS NOT NULL
        AND c.lat != ''
        AND c.long != ''
    ORDER BY c.Num_Acc;
    """
    
    df_carte = pd.read_sql_query(query_carte, conn)
    df_carte.to_csv(
        os.path.join(OUT_DIR, "accidents_carte_complet.csv"),
        index=False,
        encoding="utf-8"
    )
    print("accidents_carte_complet.csv créé")
    
    # 7. ACCIDENTS PAR TYPE DE VÉHICULE
    query_vehicule = """
    SELECT
        catv,
        COUNT(DISTINCT Num_Acc) AS nb_accidents
    FROM vehicules
    WHERE catv IS NOT NULL 
        AND catv != '' 
        AND catv != '-1' 
        AND catv != '0'
    GROUP BY catv
    ORDER BY CAST(catv AS INTEGER);
    """
    df_vehicule = pd.read_sql_query(query_vehicule, conn)
    df_vehicule.to_csv(
        os.path.join(OUT_DIR, "accidents_par_type_vehicule.csv"),
        index=False,
        encoding="utf-8"
    )
    print("accidents_par_type_vehicule.csv créé")

    conn.close()
    
if __name__ == "__main__":
    main()
