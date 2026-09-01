"""Build a stable longitudinal layout and render a phase-3 profile graph.

The canonical graph keeps the shared ``Death`` and ``Win`` absorbing nodes.  The
presentation projection omits their self-loops and draws transitions to them as local
terminal glyphs, avoiding dozens of long edges converging on one point.
"""

from __future__ import annotations

import argparse
import csv
import heapq
import math
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyArrowPatch  # noqa: E402

DEFAULT_BOOK_ID = "LW01"
DEFAULT_PROFILE_ID = "neutral_neutral_neutral"
ABSORBING_IDS = frozenset({"Death", "Win"})
LAYOUT_FIELDS = ["node_id", "x", "y", "layer", "order", "component_id"]

EDGE_COLORS = {
    "forced": "#9AA1A9",
    "choice": "#3568A8",
    "random": "#D79428",
    "kai": "#76549A",
    "condition": "#3B8C6E",
    "combat": "#B55454",
}


@dataclass(frozen=True)
class Node:
    """One canonical phase-2/phase-3 node."""

    node_id: str
    node_kind: str
    outcome: str
    absorbing: bool
    combat: bool


@dataclass(frozen=True)
class Edge:
    """One compiled phase-3 multiedge."""

    edge_id: str
    source_id: str
    target_id: str
    transition_kind: str
    weight: float


@dataclass(frozen=True)
class Position:
    """Stable coordinates and layered-layout metadata for one narrative node."""

    node_id: str
    x: float
    y: float
    layer: int
    order: int
    component_id: int


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a required UTF-8 CSV file."""
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def node_sort_key(node_id: str) -> tuple[int, int | str]:
    """Sort numbered paragraphs numerically before any special identifiers."""
    if node_id.isdigit():
        return (0, int(node_id))
    return (1, node_id)


def load_combat_node_ids(path: Path) -> set[str]:
    """Identify combat paragraphs from the phase-1 structured enemy field."""
    return {
        row["node_id"] for row in read_csv(path) if row.get("enemies", "").strip()
    }


def load_nodes(path: Path, combat_ids: set[str]) -> list[Node]:
    """Load the canonical nodes and validate their identifiers."""
    result = []
    seen: set[str] = set()
    for row in read_csv(path):
        node_id = row["node_id"]
        if node_id in seen:
            raise ValueError(f"Duplicate node identifier in {path}: {node_id}")
        seen.add(node_id)
        result.append(
            Node(
                node_id=node_id,
                node_kind=row["node_kind"],
                outcome=row["outcome"],
                absorbing=row["absorbing"].lower() == "true",
                combat=node_id in combat_ids,
            )
        )
    if "1" not in seen or ABSORBING_IDS - seen:
        raise ValueError(f"{path} must contain 1, Death and Win")
    return result


def load_edges(path: Path, valid_nodes: set[str]) -> list[Edge]:
    """Load positive compiled edges for one profile."""
    result = []
    seen: set[str] = set()
    for row in read_csv(path):
        edge_id = row["edge_id"]
        if edge_id in seen:
            raise ValueError(f"Duplicate edge identifier in {path}: {edge_id}")
        seen.add(edge_id)
        if row["source_id"] not in valid_nodes or row["target_id"] not in valid_nodes:
            raise ValueError(f"Edge {edge_id} refers to an unknown node")
        weight = float(row["compiled_weight"])
        if not math.isfinite(weight) or weight < 0:
            raise ValueError(f"Edge {edge_id} has invalid weight {weight}")
        if weight == 0:
            continue
        result.append(
            Edge(
                edge_id=edge_id,
                source_id=row["source_id"],
                target_id=row["target_id"],
                transition_kind=row["transition_kind"],
                weight=weight,
            )
        )
    return result


def narrative_adjacency(
    node_ids: list[str], edges: list[Edge]
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Return forward and reverse simple adjacency without absorbing outcomes."""
    narrative = set(node_ids)
    forward: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    reverse: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    for edge in edges:
        if edge.source_id not in narrative or edge.target_id not in narrative:
            continue
        if edge.source_id == edge.target_id:
            continue
        forward[edge.source_id].add(edge.target_id)
        reverse[edge.target_id].add(edge.source_id)
    return forward, reverse


def require_reachable(node_ids: list[str], forward: dict[str, set[str]]) -> None:
    """Ensure the layout contains no paragraph disconnected from the start."""
    reached = {"1"}
    queue = deque(["1"])
    while queue:
        source = queue.popleft()
        for target in forward[source]:
            if target not in reached:
                reached.add(target)
                queue.append(target)
    missing = sorted(set(node_ids) - reached, key=node_sort_key)
    if missing:
        raise ValueError(f"Narrative nodes unreachable from 1: {missing[:10]}")


def strong_components(
    node_ids: list[str], forward: dict[str, set[str]]
) -> tuple[list[list[str]], dict[str, int]]:
    """Calculate deterministic strongly connected components with SciPy."""
    index = {node_id: position for position, node_id in enumerate(node_ids)}
    row_indices: list[int] = []
    column_indices: list[int] = []
    for source in node_ids:
        for target in sorted(forward[source], key=node_sort_key):
            row_indices.append(index[source])
            column_indices.append(index[target])
    matrix = csr_matrix(
        (
            np.ones(len(row_indices), dtype=float),
            (row_indices, column_indices),
        ),
        shape=(len(node_ids), len(node_ids)),
    )
    count, labels = connected_components(
        matrix, directed=True, connection="strong", return_labels=True
    )
    raw: dict[int, list[str]] = defaultdict(list)
    for node_id, label in zip(node_ids, labels, strict=True):
        raw[int(label)].append(node_id)
    ordered = sorted(
        (sorted(values, key=node_sort_key) for values in raw.values()),
        key=lambda values: node_sort_key(values[0]),
    )
    if len(ordered) != int(count):
        raise ValueError("Strong-component count is inconsistent")
    component_of = {
        node_id: component_id
        for component_id, values in enumerate(ordered)
        for node_id in values
    }
    return ordered, component_of


def component_layers(
    components: list[list[str]],
    component_of: dict[str, int],
    forward: dict[str, set[str]],
) -> dict[int, int]:
    """Assign each component its longest-path rank in the condensation DAG."""
    adjacency: dict[int, set[int]] = {
        component_id: set() for component_id in range(len(components))
    }
    indegree = {component_id: 0 for component_id in range(len(components))}
    for source, targets in forward.items():
        source_component = component_of[source]
        for target in targets:
            target_component = component_of[target]
            if source_component == target_component:
                continue
            if target_component not in adjacency[source_component]:
                adjacency[source_component].add(target_component)
                indegree[target_component] += 1

    queue = [component_id for component_id, degree in indegree.items() if degree == 0]
    heapq.heapify(queue)
    order: list[int] = []
    while queue:
        component_id = heapq.heappop(queue)
        order.append(component_id)
        for component_target in sorted(adjacency[component_id]):
            indegree[component_target] -= 1
            if indegree[component_target] == 0:
                heapq.heappush(queue, component_target)
    if len(order) != len(components):
        raise ValueError("Component condensation is not acyclic")

    ranks = {component_id: 0 for component_id in range(len(components))}
    for component_source in order:
        for component_target in adjacency[component_source]:
            ranks[component_target] = max(
                ranks[component_target], ranks[component_source] + 1
            )
    if ranks[component_of["1"]] != 0:
        raise ValueError("The start component is not in the first layer")
    return ranks


def normalized_orders(layers: dict[int, list[str]]) -> dict[str, float]:
    """Return comparable vertical positions in [0, 1] for all layers."""
    result: dict[str, float] = {}
    for values in layers.values():
        denominator = max(1, len(values) - 1)
        for position, node_id in enumerate(values):
            result[node_id] = position / denominator
    return result


def barycentric_order(
    layers: dict[int, list[str]],
    forward: dict[str, set[str]],
    reverse: dict[str, set[str]],
    sweeps: int = 16,
) -> dict[int, list[str]]:
    """Reduce crossings with deterministic forward/backward barycentric sweeps."""
    result = {layer: list(values) for layer, values in layers.items()}
    layer_of = {
        node_id: layer for layer, values in result.items() for node_id in values
    }
    ordered_layers = sorted(result)

    def reorder(layer: int, neighbors: dict[str, set[str]], earlier: bool) -> None:
        normalized = normalized_orders(result)
        previous = {node_id: position for position, node_id in enumerate(result[layer])}

        def key(node_id: str) -> tuple[float, int, tuple[int, int | str]]:
            candidates = [
                neighbor
                for neighbor in neighbors[node_id]
                if (
                    layer_of[neighbor] < layer
                    if earlier
                    else layer_of[neighbor] > layer
                )
            ]
            if candidates:
                center = sum(normalized[value] for value in candidates) / len(
                    candidates
                )
            else:
                denominator = max(1, len(result[layer]) - 1)
                center = previous[node_id] / denominator
            return center, previous[node_id], node_sort_key(node_id)

        result[layer].sort(key=key)

    for _ in range(sweeps):
        for layer in ordered_layers[1:]:
            reorder(layer, reverse, True)
        for layer in reversed(ordered_layers[:-1]):
            reorder(layer, forward, False)
    return result


def compute_layout(nodes: list[Node], edges: list[Edge]) -> list[Position]:
    """Compute a stable left-to-right layout for all narrative paragraphs."""
    narrative_ids = sorted(
        (node.node_id for node in nodes if node.node_id not in ABSORBING_IDS),
        key=node_sort_key,
    )
    forward, reverse = narrative_adjacency(narrative_ids, edges)
    require_reachable(narrative_ids, forward)
    components, component_of = strong_components(narrative_ids, forward)
    ranks = component_layers(components, component_of, forward)
    layers: dict[int, list[str]] = defaultdict(list)
    for node_id in narrative_ids:
        layers[ranks[component_of[node_id]]].append(node_id)
    for values in layers.values():
        values.sort(key=node_sort_key)
    layers = barycentric_order(dict(layers), forward, reverse)

    positions = []
    for layer, values in sorted(layers.items()):
        center = (len(values) - 1) / 2
        for order, node_id in enumerate(values):
            component = component_of[node_id]
            component_values = components[component]
            intra = component_values.index(node_id)
            intra_offset = (intra - (len(component_values) - 1) / 2) * 0.08
            positions.append(
                Position(
                    node_id=node_id,
                    x=layer * 1.7 + intra_offset,
                    y=center - order,
                    layer=layer,
                    order=order,
                    component_id=component,
                )
            )
    return sorted(positions, key=lambda value: node_sort_key(value.node_id))


def formatted(value: float) -> str:
    """Format layout coordinates reproducibly."""
    return format(value, ".10g")


def write_layout(path: Path, positions: list[Position]) -> None:
    """Write the reusable longitudinal layout."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LAYOUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        for position in positions:
            writer.writerow(
                {
                    "node_id": position.node_id,
                    "x": formatted(position.x),
                    "y": formatted(position.y),
                    "layer": position.layer,
                    "order": position.order,
                    "component_id": position.component_id,
                }
            )


def load_layout(path: Path) -> list[Position]:
    """Load a previously generated layout."""
    result = []
    for row in read_csv(path):
        result.append(
            Position(
                node_id=row["node_id"],
                x=float(row["x"]),
                y=float(row["y"]),
                layer=int(row["layer"]),
                order=int(row["order"]),
                component_id=int(row["component_id"]),
            )
        )
    return result


def edge_family(transition_kind: str) -> str:
    """Map detailed transition types to a compact visual vocabulary."""
    if transition_kind == "profile_choice":
        return "choice"
    if transition_kind == "random":
        return "random"
    if transition_kind == "kai":
        return "kai"
    if transition_kind == "state_condition":
        return "condition"
    if transition_kind in {"combat", "escape"}:
        return "combat"
    return "forced"


def aggregate_narrative_edges(
    edges: list[Edge], positions: dict[str, Position]
) -> list[tuple[str, str, str, float]]:
    """Aggregate visual parallel edges while retaining their dominant family."""
    weights: dict[tuple[str, str], float] = defaultdict(float)
    families: dict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    for edge in edges:
        if edge.source_id not in positions or edge.target_id not in positions:
            continue
        key = edge.source_id, edge.target_id
        family = edge_family(edge.transition_kind)
        weights[key] += edge.weight
        families[key][family] += edge.weight
    result = []
    for (source, target), weight in weights.items():
        family = max(
            families[(source, target)],
            key=lambda value: (families[(source, target)][value], value),
        )
        result.append((source, target, family, min(1.0, weight)))
    return sorted(result, key=lambda value: (value[3], node_sort_key(value[0])))


def termination_weights(edges: list[Edge]) -> dict[tuple[str, str], float]:
    """Aggregate local transitions to shared absorbing outcomes."""
    result: dict[tuple[str, str], float] = defaultdict(float)
    for edge in edges:
        if edge.target_id in ABSORBING_IDS and edge.source_id not in ABSORBING_IDS:
            result[(edge.source_id, edge.target_id)] += edge.weight
    return result


def curve_radius(source: Position, target: Position) -> float:
    """Choose a small deterministic curvature for long and non-forward edges."""
    span = target.layer - source.layer
    if span <= 0:
        return 0.22 if source.y <= target.y else -0.22
    if span >= 8:
        sign = 1 if (int(source.node_id) + int(target.node_id)) % 2 else -1
        return sign * min(0.12, 0.025 + span * 0.002)
    return 0.0


def important_labels(
    nodes: list[Node], edges: list[Edge], limit: int = 10
) -> set[str]:
    """Select a small deterministic label set for the slide rendition."""
    degree: dict[str, int] = defaultdict(int)
    for edge in edges:
        if edge.source_id not in ABSORBING_IDS and edge.target_id not in ABSORBING_IDS:
            degree[edge.source_id] += 1
            degree[edge.target_id] += 1
    ranked = sorted(
        degree, key=lambda node_id: (-degree[node_id], node_sort_key(node_id))
    )
    result = {"1", "350"}
    result.update(ranked[:limit])
    result.update(node.node_id for node in nodes if node.outcome == "win")
    return result


def render_graph(
    nodes: list[Node],
    edges: list[Edge],
    positions: list[Position],
    output_path: Path,
    book_id: str,
    profile_id: str,
    slide: bool,
    layout_credit: str | None,
) -> None:
    """Render the phase-3 narrative projection using fixed layout coordinates."""
    position = {value.node_id: value for value in positions}
    narrative_nodes = [node for node in nodes if node.node_id in position]
    narrative_edges = aggregate_narrative_edges(edges, position)
    terminal_edges = termination_weights(edges)
    labels = important_labels(nodes, edges) if slide else set(position)

    xs = [value.x for value in positions]
    ys = [value.y for value in positions]
    x_span = max(xs) - min(xs)
    y_span = max(ys) - min(ys)
    if slide:
        figure_size = (16.0, 9.0)
        dpi = 180
    else:
        figure_size = (
            min(72.0, max(24.0, x_span * 0.46)),
            min(18.0, max(9.0, y_span * 0.52)),
        )
        dpi = 120
    figure, axis = plt.subplots(figsize=figure_size, dpi=dpi)
    figure.patch.set_facecolor("#FFFFFF")
    axis.set_facecolor("#FFFFFF")

    for source_id, target_id, family, weight in narrative_edges:
        source = position[source_id]
        target = position[target_id]
        patch = FancyArrowPatch(
            (source.x, source.y),
            (target.x, target.y),
            arrowstyle="-|>",
            connectionstyle=f"arc3,rad={curve_radius(source, target):.4f}",
            color=EDGE_COLORS[family],
            linewidth=(0.28 if slide else 0.36) + 1.15 * math.sqrt(weight),
            alpha=(0.16 if slide else 0.2) + 0.46 * math.sqrt(weight),
            mutation_scale=3.2 if slide else 4.0,
            shrinkA=2.1,
            shrinkB=2.1,
            zorder=1,
        )
        axis.add_patch(patch)

    for (source_id, outcome), weight in sorted(terminal_edges.items()):
        if source_id not in position:
            continue
        if outcome == "Win":
            continue
        source = position[source_id]
        color = "#B33A3A"
        offset_y = 0.24
        terminal_x = source.x + 0.30
        terminal_y = source.y + offset_y
        axis.plot(
            [source.x, terminal_x],
            [source.y, terminal_y],
            color=color,
            linewidth=0.5 + 1.3 * math.sqrt(min(1.0, weight)),
            alpha=0.65,
            zorder=2,
        )
        axis.scatter(
            [terminal_x],
            [terminal_y],
            marker="x",
            s=(13 if slide else 20) + 22 * math.sqrt(min(1.0, weight)),
            color=color,
            linewidths=0.8,
            zorder=4,
        )

    node_styles = {
        "ordinary": {
            "marker": "o",
            "fill": "#FFFFFF",
            "edge": "#4E5965",
            "size": 17 if slide else 38,
        },
        "combat": {
            "marker": "D",
            "fill": "#E59A3A",
            "edge": "#9B5B12",
            "size": 31 if slide else 56,
        },
        "death": {
            "marker": "X",
            "fill": "#B33A3A",
            "edge": "#7D2020",
            "size": 38 if slide else 64,
        },
        "win": {
            "marker": "*",
            "fill": "#2E8B57",
            "edge": "#1D623D",
            "size": 55 if slide else 82,
        },
        "start": {
            "marker": "o",
            "fill": "#173F5F",
            "edge": "#173F5F",
            "size": 42 if slide else 66,
        },
    }

    def node_category(node: Node) -> str:
        if node.node_id == "1":
            return "start"
        if node.outcome == "death":
            return "death"
        if node.outcome == "win":
            return "win"
        if node.combat:
            return "combat"
        return "ordinary"

    for category, style in node_styles.items():
        values = [node for node in narrative_nodes if node_category(node) == category]
        if not values:
            continue
        axis.scatter(
            [position[node.node_id].x for node in values],
            [position[node.node_id].y for node in values],
            s=float(style["size"]),
            marker=str(style["marker"]),
            c=str(style["fill"]),
            edgecolors=str(style["edge"]),
            linewidths=0.45 if slide else 0.65,
            zorder=3,
        )

    for node in narrative_nodes:
        if node.node_id not in labels:
            continue
        value = position[node.node_id]
        text_color = (
            "white" if node.node_id == "1" or node.outcome == "death" else "#1F2933"
        )
        axis.text(
            value.x,
            value.y,
            node.node_id,
            ha="center",
            va="center",
            fontsize=4.1 if not slide else 5.2,
            color=text_color,
            fontweight="bold" if node.node_id in {"1", "350"} else "normal",
            zorder=5,
        )

    axis.set_title(
        f"{book_id} - graph",
        loc="left",
        fontsize=15 if slide else 18,
        fontweight="bold",
        color="#243447",
        pad=14,
    )
    legend_items: list[Any] = [
        Line2D([0], [0], color=EDGE_COLORS["choice"], lw=2, label="Profile choice"),
        Line2D([0], [0], color=EDGE_COLORS["random"], lw=2, label="Random"),
        Line2D([0], [0], color=EDGE_COLORS["kai"], lw=2, label="Kai discipline"),
        Line2D([0], [0], color=EDGE_COLORS["condition"], lw=2, label="Condition"),
        Line2D([0], [0], color=EDGE_COLORS["combat"], lw=2, label="Combat / escape"),
        Line2D([0], [0], color=EDGE_COLORS["forced"], lw=2, label="Forced transition"),
        Line2D(
            [0],
            [0],
            marker="x",
            color="none",
            markerfacecolor="#B33A3A",
            markeredgecolor="#B33A3A",
            markersize=7,
            label="Transition to Death",
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
            markerfacecolor="#2E7D52",
            markeredgecolor="white",
            markersize=9,
            label="Victory ending",
        ),
    ]
    axis.legend(
        handles=legend_items,
        loc="upper left",
        bbox_to_anchor=(0.0, 1.01),
        ncol=5,
        frameon=False,
        fontsize=7 if slide else 8,
        handlelength=1.8,
        columnspacing=1.2,
    )
    credit = f" Layout coordinates: {layout_credit}." if layout_credit else ""
    axis.text(
        0.0,
        -0.045 if slide else -0.025,
        "Narrative projection of 350 sections. The canonical model contains 352 nodes "
        "and 602 multiedges; shared Death/Win outcomes are represented locally. "
        f"Edge opacity follows the compiled weights of {profile_id}.{credit}",
        transform=axis.transAxes,
        ha="left",
        va="top",
        fontsize=6.5 if slide else 7.5,
        color="#59636E",
    )
    axis.set_xlim(min(xs) - 0.8, max(xs) + 1.0)
    axis.set_ylim(min(ys) - 1.0, max(ys) + 1.0)
    axis.axis("off")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if slide:
        figure.subplots_adjust(left=0.02, right=0.99, bottom=0.09, top=0.78)
    figure.savefig(
        output_path,
        bbox_inches=None if slide else "tight",
        facecolor=figure.get_facecolor(),
        dpi=dpi,
    )
    plt.close(figure)


def main() -> None:
    """Parse CLI arguments, build/reuse the layout and render both outputs."""
    parser = argparse.ArgumentParser(
        description="Render one phase-3 profile on a stable longitudinal graph layout."
    )
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument("--profile", default=DEFAULT_PROFILE_ID)
    parser.add_argument("--layout", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--recompute-layout",
        action="store_true",
        help="Replace an existing graph_layout.csv from the canonical topology.",
    )
    args = parser.parse_args()

    book_id = str(args.book)
    profile_id = str(args.profile)
    graph_root = Path("data/processed/graph") / book_id
    nodes_path = Path("data/processed/pregraph") / book_id / "pregraph_nodes.csv"
    source_nodes_path = (
        Path("data/processed/nodes_edges") / book_id / f"{book_id}_nodes.csv"
    )
    edges_path = graph_root / profile_id / "compiled_edges.csv"
    project_aon_layout = graph_root / "project_aon_layout.csv"
    if args.layout is not None:
        layout_path = args.layout
    elif project_aon_layout.exists() and not args.recompute_layout:
        layout_path = project_aon_layout
    else:
        layout_path = graph_root / "graph_layout.csv"
    output_dir = args.output_dir or Path("results/phase4") / book_id

    combat_ids = load_combat_node_ids(source_nodes_path)
    nodes = load_nodes(nodes_path, combat_ids)
    valid_nodes = {node.node_id for node in nodes}
    edges = load_edges(edges_path, valid_nodes)
    if layout_path.exists() and not args.recompute_layout:
        positions = load_layout(layout_path)
    else:
        positions = compute_layout(nodes, edges)
        write_layout(layout_path, positions)

    expected_layout_nodes = valid_nodes - ABSORBING_IDS
    actual_layout_nodes = {position.node_id for position in positions}
    if actual_layout_nodes != expected_layout_nodes:
        raise ValueError("Layout nodes differ from the canonical narrative nodes")

    prefix = f"graph_{profile_id}"
    full_svg = output_dir / f"{prefix}_full.svg"
    slide_svg = output_dir / f"{prefix}_slide.svg"
    slide_png = output_dir / f"{prefix}_slide.png"
    layout_credit = (
        "Project Aon" if layout_path.name == "project_aon_layout.csv" else None
    )
    render_graph(
        nodes,
        edges,
        positions,
        full_svg,
        book_id,
        profile_id,
        slide=False,
        layout_credit=layout_credit,
    )
    render_graph(
        nodes,
        edges,
        positions,
        slide_svg,
        book_id,
        profile_id,
        slide=True,
        layout_credit=layout_credit,
    )
    render_graph(
        nodes,
        edges,
        positions,
        slide_png,
        book_id,
        profile_id,
        slide=True,
        layout_credit=layout_credit,
    )

    print(f"Layout: {layout_path} ({len(positions)} narrative nodes)")
    print(f"Full SVG: {full_svg}")
    print(f"Slide SVG: {slide_svg}")
    print(f"Slide PNG: {slide_png}")


if __name__ == "__main__":
    main()
