"""Validate the extracted Project Aon paragraph layout and provenance."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

DEFAULT_BOOK_ID = "LW01"
ABSORBING_IDS = frozenset({"Death", "Win"})
COORDINATE_SCALE = 100.0


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read one required CSV file."""
    if not path.exists():
        raise FileNotFoundError(f"Missing extracted layout: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def read_json(path: Path) -> Any:
    """Read one required JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Missing extraction manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    """Check node mapping, coordinate transform and source provenance."""
    parser = argparse.ArgumentParser(description="Validate Project Aon layout import.")
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    args = parser.parse_args()

    book_id = str(args.book)
    graph_root = Path("data/processed/graph") / book_id
    nodes_path = Path("data/processed/pregraph") / book_id / "pregraph_nodes.csv"
    layout_path = graph_root / "project_aon_layout.csv"
    manifest_path = graph_root / "project_aon_layout_manifest.json"
    canonical = {
        row["node_id"]
        for row in read_csv(nodes_path)
        if row["node_id"] not in ABSORBING_IDS
    }
    layout = read_csv(layout_path)
    manifest = read_json(manifest_path)

    if len(layout) != len(canonical) or len(canonical) != 350:
        raise ValueError("Expected exactly 350 Project Aon narrative nodes")
    if {row["node_id"] for row in layout} != canonical:
        raise ValueError("Project Aon layout differs from canonical node identifiers")
    if int(manifest["node_count"]) != len(layout):
        raise ValueError("Manifest node count differs from extracted layout")
    if manifest["layout_method"] != "project_aon_svg_node_centers":
        raise ValueError("Unexpected Project Aon layout method")
    if len(str(manifest["source_sha256"])) != 64:
        raise ValueError("Manifest lacks a SHA-256 source fingerprint")

    minimum_cx = min(float(row["source_cx"]) for row in layout)
    positions: set[tuple[float, float]] = set()
    for row in layout:
        node_id = row["node_id"]
        if row["source_node_id"] != f"{int(node_id):03d}":
            raise ValueError(f"Wrong zero-padded source identifier for {node_id}")
        cx = float(row["source_cx"])
        cy = float(row["source_cy"])
        x = float(row["x"])
        y = float(row["y"])
        if not all(math.isfinite(value) for value in (cx, cy, x, y)):
            raise ValueError(f"Non-finite Project Aon coordinates for {node_id}")
        if not math.isclose(x, (cx - minimum_cx) / COORDINATE_SCALE, abs_tol=1e-9):
            raise ValueError(f"Wrong horizontal transform for {node_id}")
        if not math.isclose(y, -cy / COORDINATE_SCALE, abs_tol=1e-9):
            raise ValueError(f"Wrong vertical transform for {node_id}")
        if (x, y) in positions:
            raise ValueError(f"Duplicate Project Aon position for {node_id}")
        positions.add((x, y))

    print(f"OK: {book_id} Project Aon layout")
    print(
        f"Nodes={len(layout)}; source={manifest['source']}; "
        f"sha256={str(manifest['source_sha256'])[:12]}…"
    )


if __name__ == "__main__":
    main()
