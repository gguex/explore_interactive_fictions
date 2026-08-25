"""Extract reusable paragraph coordinates from a Project Aon SVG/SVGZ graph."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_BOOK_ID = "LW01"
DEFAULT_SOURCES = {
    "LW01": "https://www.projectaon.org/en/svg/lw/01fftd.svgz",
}
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
COORDINATE_SCALE = 100.0
OUTPUT_FIELDS = [
    "node_id",
    "x",
    "y",
    "layer",
    "order",
    "component_id",
    "source_node_id",
    "source_cx",
    "source_cy",
    "source_rx",
    "source_ry",
]


@dataclass(frozen=True)
class SourceNode:
    """Geometry extracted from one numbered SVG node."""

    source_node_id: str
    node_id: str
    cx: float
    cy: float
    rx: float
    ry: float


def read_source(source: str) -> tuple[bytes, str]:
    """Read an SVG/SVGZ from a local path or an HTTP(S) URL."""
    if source.startswith(("https://", "http://")):
        request = urllib.request.Request(
            source,
            headers={"User-Agent": "explore-interactive-fictions/0.1"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            return response.read(), source
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Missing Project Aon graph: {path}")
    return path.read_bytes(), str(path)


def decoded_svg(payload: bytes) -> bytes:
    """Return uncompressed SVG bytes from SVG or SVGZ input."""
    if payload.startswith(b"\x1f\x8b"):
        return gzip.decompress(payload)
    return payload


def extract_nodes(svg: bytes) -> tuple[list[SourceNode], dict[str, str]]:
    """Extract all numbered node centers and source canvas metadata."""
    root = ET.fromstring(svg)
    namespace = {"svg": SVG_NAMESPACE}
    result = []
    for group in root.findall('.//svg:g[@class="node"]', namespace):
        title = group.find("svg:title", namespace)
        if title is None or title.text is None or not title.text.isdigit():
            continue
        ellipse = group.find(".//svg:ellipse", namespace)
        if ellipse is None:
            raise ValueError(f"Project Aon node {title.text} has no ellipse")
        source_node_id = title.text
        result.append(
            SourceNode(
                source_node_id=source_node_id,
                node_id=str(int(source_node_id)),
                cx=float(ellipse.attrib["cx"]),
                cy=float(ellipse.attrib["cy"]),
                rx=float(ellipse.attrib["rx"]),
                ry=float(ellipse.attrib["ry"]),
            )
        )
    result.sort(key=lambda node: int(node.node_id))
    if len({node.node_id for node in result}) != len(result):
        raise ValueError("Project Aon SVG contains duplicate numbered nodes")
    metadata = {
        "width": root.attrib.get("width", ""),
        "height": root.attrib.get("height", ""),
        "viewBox": root.attrib.get("viewBox", ""),
    }
    return result, metadata


def canonical_node_ids(path: Path) -> set[str]:
    """Read the expected narrative-node set from the canonical pregraph."""
    if not path.exists():
        raise FileNotFoundError(f"Missing canonical nodes: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return {
            row["node_id"]
            for row in csv.DictReader(handle)
            if row["node_id"] not in {"Death", "Win"}
        }


def formatted(value: float) -> str:
    """Format coordinates reproducibly."""
    return format(value, ".10g")


def layout_rows(nodes: list[SourceNode]) -> list[dict[str, str | int]]:
    """Normalize source coordinates while preserving the original geometry."""
    if not nodes:
        raise ValueError("Project Aon SVG contains no numbered nodes")
    minimum_x = min(node.cx for node in nodes)
    x_values = sorted({node.cx for node in nodes})
    layer_of = {value: layer for layer, value in enumerate(x_values)}
    by_layer: dict[int, list[SourceNode]] = {}
    for node in nodes:
        by_layer.setdefault(layer_of[node.cx], []).append(node)
    order_of: dict[str, int] = {}
    for values in by_layer.values():
        values.sort(key=lambda node: (-node.cy, int(node.node_id)))
        for order, node in enumerate(values):
            order_of[node.node_id] = order

    return [
        {
            "node_id": node.node_id,
            "x": formatted((node.cx - minimum_x) / COORDINATE_SCALE),
            "y": formatted(-node.cy / COORDINATE_SCALE),
            "layer": layer_of[node.cx],
            "order": order_of[node.node_id],
            "component_id": -1,
            "source_node_id": node.source_node_id,
            "source_cx": formatted(node.cx),
            "source_cy": formatted(node.cy),
            "source_rx": formatted(node.rx),
            "source_ry": formatted(node.ry),
        }
        for node in nodes
    ]


def write_csv(path: Path, rows: list[dict[str, str | int]]) -> None:
    """Write extracted coordinates deterministically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    """Write provenance and extraction metadata."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    """Parse arguments, extract coordinates and record their provenance."""
    parser = argparse.ArgumentParser(
        description="Extract a paragraph layout from a Project Aon SVG or SVGZ graph."
    )
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument(
        "--source",
        help="Local SVG/SVGZ path or URL; LW01 has a built-in Project Aon URL.",
    )
    parser.add_argument("--nodes", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()

    book_id = str(args.book)
    source = args.source or DEFAULT_SOURCES.get(book_id)
    if source is None:
        raise ValueError(f"No default Project Aon source for {book_id}; pass --source")
    graph_root = Path("data/processed/graph") / book_id
    nodes_path = args.nodes or (
        Path("data/processed/pregraph") / book_id / "pregraph_nodes.csv"
    )
    output_path = args.output or graph_root / "project_aon_layout.csv"
    manifest_path = args.manifest or graph_root / "project_aon_layout_manifest.json"

    payload, resolved_source = read_source(str(source))
    svg = decoded_svg(payload)
    source_nodes, canvas = extract_nodes(svg)
    extracted_ids = {node.node_id for node in source_nodes}
    expected_ids = canonical_node_ids(nodes_path)
    if extracted_ids != expected_ids:
        missing = sorted(expected_ids - extracted_ids, key=int)
        extra = sorted(extracted_ids - expected_ids, key=int)
        raise ValueError(
            f"Project Aon/canonical node mismatch; missing={missing[:10]}, "
            f"extra={extra[:10]}"
        )

    rows = layout_rows(source_nodes)
    write_csv(output_path, rows)
    write_manifest(
        manifest_path,
        {
            "book_id": book_id,
            "layout_method": "project_aon_svg_node_centers",
            "node_count": len(rows),
            "source": resolved_source,
            "source_sha256": hashlib.sha256(payload).hexdigest(),
            "source_canvas": canvas,
            "coordinate_transform": {
                "x": "(source_cx - min_source_cx) / 100",
                "y": "-source_cy / 100",
            },
            "output": str(output_path),
        },
    )
    print(f"Source: {resolved_source}")
    print(f"Project Aon nodes: {len(rows)}")
    print(f"Layout: {output_path}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
