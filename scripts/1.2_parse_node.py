import argparse
import json
import os
import re
import warnings
from pathlib import Path

import polars as pl
from bs4 import BeautifulSoup, Tag


def parse_nodes(html_dir: str, book_prefix: str, output_dir: str) -> None:

    # To store the extracted data
    nodes_data = []

    # Create a Path object for the HTML directory
    html_dir_path = Path(html_dir)

    # Patterns for extracting combat information, damage, and healing
    combat_pattern = re.compile(r"(.*?):\s*COMBAT\s*SKILL\s*(\d+)\s*ENDURANCE\s*(\d+)")
    damage_pattern = re.compile(r"lose\s+(\d+)\s+ENDURANCE")
    healing_pattern = re.compile(r"gain\s+(\d+)\s+ENDURANCE")

    # The number of nodes
    num_nodes = len(list(html_dir_path.glob("sect*.htm")))

    # Loop on files
    for file_path in html_dir_path.glob("sect*.htm"):
        # Open the HTML file and parse it with BeautifulSoup
        with open(file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "lxml")

        # Extract the node ID and the main text div
        node_id = file_path.stem.replace("sect", "")
        maintext_div = soup.find("div", class_=re.compile(r"maintext"))

        # If the main text div is not found, skip this file
        if not maintext_div:
            warnings.warn(f"No main text div found in {file_path}. Skipping.")
            continue

        # Extract the narrative text
        narrative_paragraphs = []
        for child in maintext_div.children:
            if (
                isinstance(child, Tag)
                and child.name == "p"
                and child.get("class") != ["choice"]
            ):
                narrative_paragraphs.append(
                    child.get_text(strip=False).replace("\xa0", " ")
                )
        text_content = " ".join(narrative_paragraphs)

        # Determine if the node is absorbing
        absorbing_status = "none"
        if maintext_div.find("p", class_="deadend"):
            absorbing_status = "death"
        elif maintext_div.find("p", class_="combat"):
            absorbing_status = "potential_death"
        elif node_id == str(num_nodes):
            absorbing_status = "win"

        # Extract enemies
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

        # Extract health modifications
        health_mod = 0
        damage_match = damage_pattern.search(text_content)
        healing_match = healing_pattern.search(text_content)
        if damage_match:
            health_mod -= int(damage_match.group(1))
        if healing_match:
            health_mod += int(healing_match.group(1))
        if health_mod < 0:
            absorbing_status = "potential_death"

        # Extract images
        images: list[str] = []
        for img in maintext_div.find_all("img"):
            src = img.get("src")
            if isinstance(src, str):
                images.append(src)
            elif isinstance(src, list):
                images.extend(str(v) for v in src)

        # Store the extracted data with type for polars df
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

    # Convert the list of dictionaries to a Polars DataFrame
    df_nodes = pl.DataFrame(nodes_data)

    # Sort by node_id as int for better readability
    df_nodes = df_nodes.with_columns(pl.col("node_id").cast(pl.Int64)).sort("node_id")

    # Make sure the output directory exists
    full_output_dir = os.path.join(output_dir, book_prefix)
    os.makedirs(full_output_dir, exist_ok=True)

    # Save the DataFrame to a CSV file
    nodes_csv_path = os.path.join(full_output_dir, f"{book_prefix}_nodes.csv")
    df_nodes.write_csv(nodes_csv_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract the node table for one Lone Wolf book."
    )
    parser.add_argument(
        "--book",
        default="LW01",
        help="Book identifier used in data/raw/<BOOK>/sections (default: LW01).",
    )
    args = parser.parse_args()
    book_id = str(args.book)

    parse_nodes(
        html_dir=f"data/raw/{book_id}/sections",
        book_prefix=book_id,
        output_dir="data/processed/nodes_edges",
    )


if __name__ == "__main__":
    main()
