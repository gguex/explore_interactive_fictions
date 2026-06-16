import polars as pl

# --- Configuration ---
FICHIER_GOLD = "data/for_edge_extraction/LW01_calibration_edges_gold_2.csv"
FICHIER_LLM = "results/curnagl_results/csv/LW01_calibration_edges_final.csv"
FICHIER_RAPPORT = "results/curnagl_results/csv/rapport_erreurs_final.csv"


def evaluer_graphes() -> None:
    print("Chargement des fichiers avec Polars...")

    # 1. Chargement sécurisé
    # Polars gère nativement et très proprement les valeurs manquantes (null)
    df_gold = pl.read_csv(FICHIER_GOLD)
    df_llm = pl.read_csv(FICHIER_LLM)

    # Création de l'ID unique (source -> target). On cast en String pour éviter les conflits
    df_gold = df_gold.with_columns(
        (
            pl.col("source_id").cast(pl.String)
            + "->"
            + pl.col("target_id").cast(pl.String)
        ).alias("edge_id")
    )
    df_llm = df_llm.with_columns(
        (
            pl.col("source_id").cast(pl.String)
            + "->"
            + pl.col("target_id").cast(pl.String)
        ).alias("edge_id")
    )

    # 2. Analyse de la Topologie (Existence)
    gold_edges = set(df_gold["edge_id"].to_list())
    llm_edges = set(df_llm["edge_id"].to_list())

    arêtes_manquantes = gold_edges - llm_edges  # Faux Négatifs
    arêtes_inventees = llm_edges - gold_edges  # Faux Positifs
    arêtes_communes = gold_edges.intersection(llm_edges)  # Vrais Positifs

    print("\n--- 1. BILAN TOPOLOGIQUE ---")
    print(f"Arêtes dans le Gold  : {len(gold_edges)}")
    print(f"Arêtes trouvées (LLM): {len(llm_edges)}")
    print(f"Arêtes communes (OK) : {len(arêtes_communes)}")
    print(f"Oublis (Faux Négatifs): {len(arêtes_manquantes)}")
    print(f"Détails des oublis : {arêtes_manquantes}")
    print(f"Inventions (Faux Positifs): {len(arêtes_inventees)}")
    print(f"Détails des inventions : {arêtes_inventees}")

    # 3. Analyse détaillée via Jointure Vectorisée
    # On lie les deux tables sur les arêtes communes. Les colonnes du LLM auront le suffixe "_llm"
    df_common = df_gold.join(df_llm, on="edge_id", suffix="_llm")

    liste_erreurs = []

    # --- A. Erreurs de Type (Gravité Moyenne) ---
    # On filtre les lignes où les types diffèrent, et on sélectionne les colonnes pour le rapport
    df_erreurs_type = df_common.filter(
        pl.col("transition_type") != pl.col("transition_type_llm")
    ).select(
        pl.col("edge_id"),
        pl.lit("transition_type").alias("champ"),
        pl.col("transition_type").alias("gold"),
        pl.col("transition_type_llm").alias("llm"),
        pl.lit("MOYENNE").alias("gravite"),
    )
    liste_erreurs.append(df_erreurs_type)

    # --- B. Erreurs Sémantiques (Gravité Douce) ---
    # On ne regarde la sémantique QUE si le LLM a trouvé le bon type de transition
    df_type_valide = df_common.filter(
        pl.col("transition_type") == pl.col("transition_type_llm")
    )

    champs_semantiques = ["semantic_risk", "semantic_morality", "semantic_action"]
    for champ in champs_semantiques:
        # On garde les lignes où le Gold n'est pas vide ET où les valeurs sont différentes
        df_err_sem = df_type_valide.filter(
            pl.col(champ).is_not_null() & (pl.col(champ) != pl.col(f"{champ}_llm"))
        ).select(
            pl.col("edge_id"),
            pl.lit(champ).alias("champ"),
            pl.col(champ).alias("gold"),
            pl.col(f"{champ}_llm").alias("llm"),
            pl.lit("DOUCE").alias("gravite"),
        )
        liste_erreurs.append(df_err_sem)

    # 4. Compilation et Sauvegarde
    print("\n--- 2. BILAN QUALITATIF (Sur les arêtes communes) ---")

    # On empile (concat) tous les DataFrames d'erreurs en un seul tableau final
    df_toutes_erreurs = pl.concat(liste_erreurs)

    if df_toutes_erreurs.height > 0:
        # Affichage d'un tableau récapitulatif via un "Group By"
        resume = df_toutes_erreurs.group_by(["champ", "gravite"]).len(
            name="nombre_erreurs"
        )
        print(resume)

        # Sauvegarde ultra-rapide en CSV
        df_toutes_erreurs.write_csv(FICHIER_RAPPORT)
        print(f"\nRapport détaillé sauvegardé dans {FICHIER_RAPPORT}")
    else:
        print("C'est un miracle ! Extraction 100% parfaite sur les arêtes communes.")


if __name__ == "__main__":
    evaluer_graphes()
