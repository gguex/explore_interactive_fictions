"""Validate the stable longitudinal layout and phase-3 graph renditions."""

from __future__ import annotations

import argparse
import csv
import math
import struct
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

DEFAULT_BOOK_ID = "LW01"
DEFAULT_PROFILE_ID = "neutral_neutral_neutral"
ABSORBING_IDS = frozenset({"Death", "Win"})


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read one required CSV artifact."""
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact; run phase 4.0 first: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def png_dimensions(path: Path) -> tuple[int, int]:
    """Read the width and height from a standard PNG IHDR chunk."""
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Invalid PNG header: {path}")
    return struct.unpack(">II", header[16:24])


def validate_layout(
    node_rows: list[dict[str, str]],
    edge_rows: list[dict[str, str]],
    layout_rows: list[dict[str, str]],
    enforce_algorithmic_layers: bool,
) -> tuple[int, int, int]:
    """Check coverage, coordinates, SCC layers and progression direction."""
    narrative_ids = [
        row["node_id"] for row in node_rows if row["node_id"] not in ABSORBING_IDS
    ]
    layout_ids = [row["node_id"] for row in layout_rows]
    if len(layout_ids) != len(set(layout_ids)):
        raise ValueError("Layout contains duplicate node identifiers")
    if set(layout_ids) != set(narrative_ids):
        raise ValueError("Layout differs from the canonical narrative-node set")

    positions: set[tuple[float, float]] = set()
    layers: dict[str, int] = {}
    for row in layout_rows:
        x = float(row["x"])
        y = float(row["y"])
        layer = int(row["layer"])
        if not math.isfinite(x) or not math.isfinite(y) or layer < 0:
            raise ValueError(f"Invalid layout row for {row['node_id']}")
        if (x, y) in positions:
            raise ValueError(f"Overlapping coordinates at node {row['node_id']}")
        positions.add((x, y))
        layers[row["node_id"]] = layer
    if layers["1"] != 0:
        raise ValueError("The initial paragraph is not in layer zero")

    index = {node_id: position for position, node_id in enumerate(narrative_ids)}
    source_indices: list[int] = []
    target_indices: list[int] = []
    narrative_edges = []
    for edge in edge_rows:
        source = edge["source_id"]
        target = edge["target_id"]
        if source not in index or target not in index or source == target:
            continue
        source_indices.append(index[source])
        target_indices.append(index[target])
        narrative_edges.append((source, target))
    matrix = csr_matrix(
        (
            np.ones(len(source_indices), dtype=float),
            (source_indices, target_indices),
        ),
        shape=(len(narrative_ids), len(narrative_ids)),
    )
    component_count, labels = connected_components(
        matrix, directed=True, connection="strong", return_labels=True
    )
    if enforce_algorithmic_layers:
        for source, target in narrative_edges:
            same_component = labels[index[source]] == labels[index[target]]
            if same_component and layers[source] != layers[target]:
                raise ValueError(f"SCC edge {source}->{target} crosses layout layers")
            if not same_component and layers[target] <= layers[source]:
                raise ValueError(f"Forward edge {source}->{target} does not progress")
    return len(narrative_ids), len(narrative_edges), int(component_count)


def main() -> None:
    """Validate the layout and both presentation artifacts."""
    parser = argparse.ArgumentParser(description="Validate phase-4.0 graph figures.")
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument("--profile", default=DEFAULT_PROFILE_ID)
    args = parser.parse_args()

    book_id = str(args.book)
    profile_id = str(args.profile)
    graph_root = Path("data/processed/graph") / book_id
    results_root = Path("results/phase4") / book_id
    nodes_path = Path("data/processed/pregraph") / book_id / "pregraph_nodes.csv"
    edges_path = graph_root / profile_id / "compiled_edges.csv"
    project_aon_layout = graph_root / "project_aon_layout.csv"
    layout_path = (
        project_aon_layout
        if project_aon_layout.exists()
        else graph_root / "graph_layout.csv"
    )
    prefix = f"graph_{profile_id}"
    full_svg = results_root / f"{prefix}_full.svg"
    slide_svg = results_root / f"{prefix}_slide.svg"
    slide_png = results_root / f"{prefix}_slide.png"

    node_rows = read_csv(nodes_path)
    edge_rows = read_csv(edges_path)
    layout_rows = read_csv(layout_path)
    node_count, edge_count, component_count = validate_layout(
        node_rows,
        edge_rows,
        layout_rows,
        enforce_algorithmic_layers=layout_path.name == "graph_layout.csv",
    )

    for path in (full_svg, slide_svg, slide_png):
        if not path.exists() or path.stat().st_size == 0:
            raise ValueError(f"Missing or empty graph rendition: {path}")
    for path in (full_svg, slide_svg):
        contents = path.read_text(encoding="utf-8")
        if "<svg" not in contents or book_id not in contents:
            raise ValueError(f"Invalid SVG rendition: {path}")
    width, height = png_dimensions(slide_png)
    if not math.isclose(width / height, 16 / 9, abs_tol=1e-9):
        raise ValueError(f"Slide PNG is not 16:9: {width}x{height}")

    print(f"OK: {book_id}/{profile_id} longitudinal graph")
    print(
        f"Narrative nodes={node_count}; narrative edges={edge_count}; "
        f"SCCs={component_count}; slide={width}x{height}"
    )


if __name__ == "__main__":
    main()
