import os
import re
import warnings
from pathlib import Path

import polars as pl
from bs4 import BeautifulSoup, Tag


def parse_for_edge_extraction(html_dir: str, book_prefix: str, output_dir: str) -> None:

    # To store the extracted data
    nodes_data = []

    # Create a Path object for the HTML directory
    html_dir_path = Path(html_dir)

    # Loop on files
    for file_path in html_dir_path.glob("sect*.htm"):
        # Open the HTML file and parse it with BeautifulSoup
        with open(file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "lxml")

        # --- NODE EXTRACTION  ---

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

        # --- ADDING CHOICES  ---

        for choice_p in maintext_div.find_all("p", class_="choice"):
            link = choice_p.find_all("a")

            # No link : continue with a warning
            if not link or all("href" not in l.attrs for l in link):
                print(link)
                warnings.warn(
                    f"No valid link found in choice paragraph in {file_path}. Skipping."
                )
                continue

            # Extract the target node ID from the link
            target_id = None
            if len(link) > 1:
                for l in link:
                    if "href" in l.attrs and "sect" in l["href"]:
                        target_id = (
                            str(l["href"]).replace("sect", "").replace(".htm", "")
                        )
                        break
            else:
                if "href" in link[0].attrs and "sect" in link[0]["href"]:
                    target_id = (
                        str(link[0]["href"]).replace("sect", "").replace(".htm", "")
                    )

            if target_id is None:
                warnings.warn(
                    f"No valid 'sect' link found in choice paragraph in {file_path}. Skipping."
                )

            # Extract the choice text
            edge_text = choice_p.get_text(strip=False).replace("\xa0", " ")
            # Add to choice text to node text with <choice> tags
            text_content += f" <choice>{edge_text}</choice>"

        # Store the extracted data with type for polars df
        nodes_data.append(
            {
                "id": f"{node_id}",
                "text": text_content,
            }
        )

    # Convert the lists of dictionaries to Polars DataFrames
    df_nodes = pl.DataFrame(nodes_data)

    # Sort by node_id and source_node_id as int for better readability
    df_nodes = (
        df_nodes.with_columns(pl.col("id").cast(pl.Int64))
        .sort(["id"])
        .with_columns(pl.col("id").cast(pl.Utf8))
    )

    # Make sure the output directory exists
    full_output_dir = os.path.join(output_dir, book_prefix)
    os.makedirs(full_output_dir, exist_ok=True)

    # Save the DataFrames to JSON files
    nodes_json_path = os.path.join(
        full_output_dir, f"{book_prefix}_for_edges_extraction.json"
    )

    df_nodes.write_json(nodes_json_path)


# Test the function with a sample HTML directory, book prefix, and output directory
parse_for_edge_extraction(
    html_dir="data/raw/LW01/sections",
    book_prefix="LW01",
    output_dir="data/processed/nodes_edges_csv/",
)
