import csv
import json

# 1. Configuration des chemins
fichier_json = "data/for_edge_extraction/LW01_calibration_gold.json"
fichier_csv = "data/for_edge_extraction/LW01_calibration_edges_gold_new.csv"  # Le nom de l'export voulu

# 2. Définition stricte des colonnes (ton schéma Pydantic)
colonnes = [
    "source_id",
    "target_id",
    "edge_text",
    "transition_type",
    "realisation_value",
    "semantic_risk",
    "semantic_morality",
    "semantic_action",
    "parsing_confidence",
]

if __name__ == "__main__":
    print(f"Lecture du fichier {fichier_json}...")

    # Chargement du JSON en mémoire
    with open(fichier_json, "r", encoding="utf-8") as f_in:
        corpus_resultats = json.load(f_in)

    print(f"Écriture dans {fichier_csv}...")

    # Ouverture du CSV en mode écriture brute ("w")
    with open(fichier_csv, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=colonnes)
        writer.writeheader()

        compteur_aretes = 0

        # Parcours de ta structure imbriquée
        for section in corpus_resultats:
            # On descend d'un étage en toute sécurité vers "output" puis "edges"
            output_data = section.get("output", {})
            edges = output_data.get("edges", [])

            # Écriture de chaque arête trouvée
            for edge in edges:
                writer.writerow(edge)
                compteur_aretes += 1

    print(
        f"✅ Conversion terminée ! {compteur_aretes} arêtes ont été écrites avec succès."
    )
