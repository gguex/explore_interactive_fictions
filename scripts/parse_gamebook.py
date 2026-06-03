import json
import os
import re
from pathlib import Path

import polars as pl
from bs4 import BeautifulSoup


def parse_gamebook(html_dir: str, book_prefix: str = "LW01") -> None:
    nodes_data = []
    edges_data = []

    html_dir_path = Path(html_dir)

    # Expressions régulières pré-compilées pour les performances
    # Gère les espaces insecables (\xa0 ou \s) générés par le HTML
    combat_pattern = re.compile(r"(.*?):\s*COMBAT\s*SKILL\s*(\d+)\s*ENDURANCE\s*(\d+)")
    damage_pattern = re.compile(r"lose\s+(\d+)\s+ENDURANCE")
    healing_pattern = re.compile(r"gain\s+(\d+)\s+ENDURANCE")

    for file_path in html_dir_path.glob("sect*.htm"):
        with open(file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "lxml")

        # --- 1. EXTRACTION DU NŒUD ---
        node_id = file_path.stem.replace("sect", "")
        maintext_div = soup.find("div", class_=re.compile(r"maintext"))

        if not maintext_div:
            continue

        # Déterminer le statut absorbant
        absorbing_status = "none"
        if maintext_div.find("p", class_="deadend"):
            absorbing_status = "death"
        elif maintext_div.find("p", class_="combat"):
            absorbing_status = "potential_death"

        # Extraire les ennemis
        enemies = []
        for combat_p in maintext_div.find_all("p", class_="combat"):
            text_combat = combat_p.get_text(strip=True).replace("\xa0", " ")
            match = combat_pattern.search(text_combat)
            if match:
                enemies.append(
                    {
                        "name": match.group(1).strip(),
                        "cs": int(match.group(2)),
                        "ep": int(match.group(3)),
                    }
                )

        # Isoler le texte narratif (en ignorant les choix)
        narrative_paragraphs = []
        for child in maintext_div.children:
            if child.name == "p" and child.get("class") != ["choice"]:
                narrative_paragraphs.append(child.get_text(strip=True))
        text_content = " ".join(narrative_paragraphs)

        # Chercher les modificateurs de santé dans le texte
        health_mod = 0
        damage_match = damage_pattern.search(text_content)
        healing_match = healing_pattern.search(text_content)
        if damage_match:
            health_mod -= int(damage_match.group(1))
        if healing_match:
            health_mod += int(healing_match.group(1))

        # Extraire les images
        images = [
            img["src"] for img in maintext_div.find_all("img") if "src" in img.attrs
        ]

        nodes_data.append(
            {
                "node_id": node_id,
                "text_content": text_content,
                "absorbing_status": absorbing_status,
                "enemies": json.dumps(enemies) if enemies else None,
                "health_modifier": health_mod,
                "special_mechanic": None,
                "image_refs": ",".join(images) if images else None,
                "items_granted": None,
            }
        )

        # --- 2. EXTRACTION DES ARÊTES ---
        for choice_p in maintext_div.find_all("p", class_="choice"):
            link = choice_p.find("a")
            if not link or "sect" not in link.get("href", ""):
                continue

            target_id = link["href"].replace("sect", "").replace(".htm", "")
            edge_text = choice_p.get_text(strip=True).replace("\xa0", " ")

            # Heuristiques de classification
            transition_type = "explicit_choice"
            condition_type = "none"
            condition_value = None
            stochastic_trigger = None

            text_lower = edge_text.lower()

            if (
                "random number" in text_lower
                or "number is" in text_lower
                or "pick a number" in text_lower
            ):
                transition_type = "stochastic"
                # Extraction basique du trigger (ex: "5 to 9")
                trigger_match = re.search(
                    r"(\d+\s*to\s*\d+|\d+|below\s*\d+|above\s*\d+)", text_lower
                )
                if trigger_match:
                    stochastic_trigger = trigger_match.group(1)

            elif "kai discipline" in text_lower:
                transition_type = "conditional"
                condition_type = "skill"
            elif "endurance" in text_lower:
                transition_type = "conditional"
                condition_type = "stat_check"
            elif "if you have" in text_lower:
                transition_type = "conditional"
                condition_type = "item"

            edges_data.append(
                {
                    "source_id": node_id,
                    "target_id": target_id,
                    "edge_text": edge_text,
                    "transition_type": transition_type,
                    "stochastic_trigger": stochastic_trigger,
                    "condition_type": condition_type,
                    "condition_value": condition_value,
                }
            )

    # --- 3. CRÉATION DES DATAFRAMES POLARS ET EXPORT ---
    df_nodes = pl.DataFrame(nodes_data)
    df_edges = pl.DataFrame(edges_data)

    # Assurer le dossier de sortie
    os.makedirs("data/processed", exist_ok=True)

    df_nodes.write_csv(f"data/processed/{book_prefix}_nodes.csv")
    df_edges.write_csv(f"data/processed/{book_prefix}_edges.csv")

    print(
        f"Extraction terminée : {len(df_nodes)} nœuds et {len(df_edges)} arêtes extraits."
    )


# --- Point d'entrée ---
if __name__ == "__main__":
    # Assurez-vous que le dossier pointe vers l'emplacement de vos fichiers HTML
    # parse_gamebook("data/raw/")
    pass
