#!/usr/bin/env python3
"""Render the phase-1 annotated topology without profile-dependent weights."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyArrowPatch  # noqa: E402

EDGE_COLORS = {
    "explicit_choice": "#3568A8",
    "forced": "#9AA1A9",
    "stochastic": "#D79428",
    "conditional": "#3B8C6E",
    "complex": "#76549A",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render the unweighted annotated topology of one gamebook."
    )
    parser.add_argument("--book", default="LW01", help="Book identifier.")
    parser.add_argument("--nodes", type=Path, help="Phase-1 nodes CSV.")
    parser.add_argument("--edges", type=Path, help="Phase-1 edges CSV.")
    parser.add_argument("--layout", type=Path, help="Longitudinal layout CSV.")
    parser.add_argument("--output-dir", type=Path, help="Output directory.")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def curve_radius(
    source: dict[str, float | int | str],
    target: dict[str, float | int | str],
) -> float:
    source_layer = int(source["layer"])
    target_layer = int(target["layer"])
    span = target_layer - source_layer
    if span <= 0:
        return 0.16 if float(source["y"]) <= float(target["y"]) else -0.16
    if span >= 8:
        source_id = str(source["node_id"])
        target_id = str(target["node_id"])
        sign = 1 if (int(source_id) + int(target_id)) % 2 else -1
        return sign * min(0.1, 0.02 + span * 0.0015)
    return 0.0


def node_category(row: dict[str, str]) -> str:
    if row["node_id"] == "1":
        return "start"
    if row["absorbing_status"] == "death":
        return "death"
    if row["absorbing_status"] == "win":
        return "win"
    if row.get("enemies", "").strip():
        return "combat"
    return "ordinary"


def render(
    book_id: str,
    nodes: list[dict[str, str]],
    edges: list[dict[str, str]],
    layout_rows: list[dict[str, str]],
    output_path: Path,
) -> None:
    positions: dict[str, dict[str, float | int | str]] = {
        row["node_id"]: {
            "node_id": row["node_id"],
            "x": float(row["x"]),
            "y": float(row["y"]),
            "layer": int(row["layer"]),
        }
        for row in layout_rows
    }
    node_ids = {row["node_id"] for row in nodes}
    if set(positions) != node_ids:
        raise ValueError("Layout nodes differ from the phase-1 paragraph nodes")

    for edge in edges:
        if edge["source_id"] not in node_ids or edge["target_id"] not in node_ids:
            msg = (
                "Transition refers to an unknown paragraph: "
                f"{edge['source_id']} -> {edge['target_id']}"
            )
            raise ValueError(msg)

    figure, axis = plt.subplots(figsize=(16, 9), dpi=180)
    figure.patch.set_facecolor("#FFFFFF")
    axis.set_facecolor("#FFFFFF")

    for edge in edges:
        source = positions[edge["source_id"]]
        target = positions[edge["target_id"]]
        color = EDGE_COLORS.get(edge["transition_type"], EDGE_COLORS["complex"])
        arrow = FancyArrowPatch(
            (float(source["x"]), float(source["y"])),
            (float(target["x"]), float(target["y"])),
            arrowstyle="-|>",
            connectionstyle=f"arc3,rad={curve_radius(source, target):.4f}",
            color=color,
            linewidth=0.62,
            alpha=0.34,
            mutation_scale=3.0,
            shrinkA=2.0,
            shrinkB=2.0,
            zorder=1,
        )
        axis.add_patch(arrow)

    styles: dict[str, dict[str, Any]] = {
        "ordinary": {
            "marker": "o",
            "fill": "#FFFFFF",
            "edge": "#4E5965",
            "size": 17,
        },
        "combat": {
            "marker": "D",
            "fill": "#E59A3A",
            "edge": "#9B5B12",
            "size": 31,
        },
        "death": {
            "marker": "X",
            "fill": "#B33A3A",
            "edge": "#7D2020",
            "size": 38,
        },
        "win": {
            "marker": "*",
            "fill": "#2E8B57",
            "edge": "#1D623D",
            "size": 55,
        },
        "start": {
            "marker": "o",
            "fill": "#173F5F",
            "edge": "#173F5F",
            "size": 42,
        },
    }

    for category, style in styles.items():
        selected = [row for row in nodes if node_category(row) == category]
        axis.scatter(
            [float(positions[row["node_id"]]["x"]) for row in selected],
            [float(positions[row["node_id"]]["y"]) for row in selected],
            s=float(style["size"]),
            marker=str(style["marker"]),
            c=str(style["fill"]),
            edgecolors=str(style["edge"]),
            linewidths=0.5,
            zorder=3,
        )

    for node_id in ("1", "350"):
        if node_id not in positions:
            continue
        position = positions[node_id]
        axis.text(
            float(position["x"]),
            float(position["y"]),
            node_id,
            ha="center",
            va="center",
            fontsize=5.2,
            color="white" if node_id == "1" else "#1F2933",
            fontweight="bold",
            zorder=5,
        )

    axis.set_title(
        f"{book_id} — annotated topology",
        loc="left",
        fontsize=15,
        fontweight="bold",
        color="#243447",
        pad=14,
    )
    legend_items: list[Any] = [
        Line2D(
            [0],
            [0],
            color=EDGE_COLORS["explicit_choice"],
            lw=2,
            label="Explicit choice",
        ),
        Line2D([0], [0], color=EDGE_COLORS["forced"], lw=2, label="Forced"),
        Line2D(
            [0], [0], color=EDGE_COLORS["stochastic"], lw=2, label="Stochastic"
        ),
        Line2D(
            [0], [0], color=EDGE_COLORS["conditional"], lw=2, label="Conditional"
        ),
        Line2D(
            [0],
            [0],
            marker="D",
            color="none",
            markerfacecolor="#E59A3A",
            markeredgecolor="#9B5B12",
            markersize=6,
            label="Combat paragraph",
        ),
        Line2D(
            [0],
            [0],
            marker="X",
            color="none",
            markerfacecolor="#B33A3A",
            markeredgecolor="#7D2020",
            markersize=7,
            label="Death ending",
        ),
        Line2D(
            [0],
            [0],
            marker="*",
            color="none",
            markerfacecolor="#2E8B57",
            markeredgecolor="#1D623D",
            markersize=9,
            label="Victory ending",
        ),
    ]
    axis.legend(
        handles=legend_items,
        loc="upper left",
        bbox_to_anchor=(0.0, 1.01),
        ncol=7,
        frameon=False,
        fontsize=7,
        handlelength=1.8,
        columnspacing=1.15,
    )

    xs = [float(position["x"]) for position in positions.values()]
    ys = [float(position["y"]) for position in positions.values()]
    axis.set_xlim(min(xs) - 0.8, max(xs) + 1.0)
    axis.set_ylim(min(ys) - 1.0, max(ys) + 1.0)
    axis.axis("off")
    axis.text(
        0,
        -0.045,
        f"{len(nodes)} paragraph nodes and {len(edges)} directed transitions. "
        "Colors show phase-1 annotations; no profile or probability is applied. "
        "Layout coordinates: Project Aon.",
        transform=axis.transAxes,
        ha="left",
        va="top",
        fontsize=6.5,
        color="#59636E",
    )
    figure.subplots_adjust(left=0.02, right=0.99, bottom=0.09, top=0.78)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, facecolor="#FFFFFF", dpi=180)
    plt.close(figure)


def main() -> None:
    args = parse_args()
    book_id = str(args.book)
    graph_root = Path("data/processed/graph") / book_id
    nodes_path = args.nodes or (
        Path("data/processed/nodes_edges") / book_id / f"{book_id}_nodes.csv"
    )
    edges_path = args.edges or (
        Path("data/processed/nodes_edges") / book_id / f"{book_id}_edges.csv"
    )
    layout_path = args.layout or graph_root / "project_aon_layout.csv"
    output_dir = args.output_dir or Path("results/presentation")

    nodes = read_csv(nodes_path)
    edges = read_csv(edges_path)
    layout = read_csv(layout_path)
    for extension in ("png", "svg"):
        output_path = output_dir / f"{book_id}_phase1_unweighted_graph.{extension}"
        render(book_id, nodes, edges, layout, output_path)
        print(f"Written to {output_path}")


if __name__ == "__main__":
    main()
