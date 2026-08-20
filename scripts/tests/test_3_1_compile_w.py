"""Independent validation of a matrix produced by phase 3.1.

This script checks edge coverage, local probability distributions, aggregation into W,
absorbing states and eventual absorption. It does not re-evaluate symbolic expressions.
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

DEFAULT_BOOK_ID = "LW01"
DEFAULT_PROFILE_ID = "neutral_neutral_neutral"

PREGRAPH_NODE_FIELDS = [
    "node_id",
    "node_kind",
    "outcome",
    "absorbing",
    "source_ref",
]
PREGRAPH_EDGE_FIELDS = [
    "edge_id",
    "source_id",
    "target_id",
    "transition_kind",
    "weight_rule",
    "weight_value",
    "weight_expression",
    "condition_kind",
    "condition_value",
    "semantic_risk",
    "semantic_morality",
    "semantic_action",
    "origin",
    "source_ref",
    "note",
]
COMPILED_EDGE_FIELDS = [*PREGRAPH_EDGE_FIELDS, "profile_id", "compiled_weight"]


def read_csv(path: Path, expected_fields: list[str]) -> list[dict[str, str]]:
    """Read a CSV and enforce its header."""
    if not path.exists():
        raise FileNotFoundError(f"Missing output; run phase 3.1 first: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected_fields:
            raise ValueError(
                f"Unexpected header in {path}: {reader.fieldnames}; "
                f"expected {expected_fields}"
            )
        return [
            {field: (row.get(field) or "").strip() for field in expected_fields}
            for row in reader
        ]


def main() -> None:
    """Run structural and probabilistic checks on one compiled profile."""
    parser = argparse.ArgumentParser(description="Validate one phase-3 matrix W.")
    parser.add_argument(
        "--book", default=DEFAULT_BOOK_ID, help="Book identifier (default: LW01)."
    )
    parser.add_argument(
        "--profile",
        default=DEFAULT_PROFILE_ID,
        help=f"Compiled profile identifier (default: {DEFAULT_PROFILE_ID}).",
    )
    args = parser.parse_args()

    book_id = str(args.book)
    profile_id = str(args.profile)
    pregraph_dir = Path("data/processed/pregraph") / book_id
    profile_dir = Path("data/processed/graph") / book_id / profile_id

    nodes = read_csv(pregraph_dir / "pregraph_nodes.csv", PREGRAPH_NODE_FIELDS)
    pregraph_edges = read_csv(
        pregraph_dir / "pregraph_edges.csv", PREGRAPH_EDGE_FIELDS
    )
    compiled_edges = read_csv(
        profile_dir / "compiled_edges.csv", COMPILED_EDGE_FIELDS
    )
    node_ids = [node["node_id"] for node in nodes]
    matrix_rows = read_csv(profile_dir / "W.csv", ["node_id", *node_ids])

    if len(compiled_edges) != len(pregraph_edges):
        raise ValueError("Compiled edge count differs from the pregraph")
    for pregraph_edge, compiled in zip(
        pregraph_edges, compiled_edges, strict=True
    ):
        if any(
            compiled[field] != pregraph_edge[field]
            for field in PREGRAPH_EDGE_FIELDS
        ):
            raise ValueError(
                f"Compiled edge {compiled['edge_id']} changed the pregraph"
            )
        if compiled["profile_id"] != profile_id:
            raise ValueError(f"Edge {compiled['edge_id']} has the wrong profile_id")

    outgoing: dict[str, float] = defaultdict(float)
    aggregated: dict[tuple[str, str], float] = defaultdict(float)
    for edge in compiled_edges:
        weight = float(edge["compiled_weight"])
        if not math.isfinite(weight) or not -1e-12 <= weight <= 1 + 1e-12:
            raise ValueError(f"Edge {edge['edge_id']} has invalid weight {weight}")
        outgoing[edge["source_id"]] += weight
        aggregated[(edge["source_id"], edge["target_id"])] += weight

    absorbing_ids = {
        node["node_id"] for node in nodes if node["absorbing"].casefold() == "true"
    }
    if absorbing_ids != {"Death", "Win"}:
        raise ValueError(f"Unexpected absorbing nodes in pregraph: {absorbing_ids}")
    for node_id in node_ids:
        if node_id not in absorbing_ids and not math.isclose(
            outgoing[node_id], 1.0, abs_tol=1e-12
        ):
            raise ValueError(
                f"Compiled outgoing weights for {node_id} sum to {outgoing[node_id]}"
            )

    if [row["node_id"] for row in matrix_rows] != node_ids:
        raise ValueError("W row identifiers differ from pregraph node order")
    matrix = np.array(
        [[float(row[target_id]) for target_id in node_ids] for row in matrix_rows],
        dtype=float,
    )
    if not np.isfinite(matrix).all() or (matrix < -1e-12).any():
        raise ValueError("W contains non-finite or negative entries")
    row_errors = np.abs(matrix.sum(axis=1) - 1)
    if float(row_errors.max()) > 1e-12:
        raise ValueError(f"W row-sum error reaches {float(row_errors.max())}")

    index = {node_id: position for position, node_id in enumerate(node_ids)}
    for source_id in node_ids:
        for target_id in node_ids:
            expected = aggregated[(source_id, target_id)]
            if source_id in absorbing_ids and source_id == target_id:
                expected = 1.0
            actual = matrix[index[source_id], index[target_id]]
            if not math.isclose(actual, expected, abs_tol=1e-12):
                raise ValueError(
                    f"W[{source_id}, {target_id}]={actual}, expected {expected}"
                )

    for node_id in node_ids:
        row = matrix[index[node_id]]
        is_absorbing_row = math.isclose(row[index[node_id]], 1.0, abs_tol=1e-12)
        is_absorbing_row = is_absorbing_row and math.isclose(
            float(row.sum()), 1.0, abs_tol=1e-12
        )
        if is_absorbing_row != (node_id in absorbing_ids):
            raise ValueError(f"Unexpected absorbing behavior for node {node_id}")

    transient_ids = [node_id for node_id in node_ids if node_id not in absorbing_ids]
    transient_index = [index[node_id] for node_id in transient_ids]
    absorbing_index = [index["Death"], index["Win"]]
    q_matrix = matrix[np.ix_(transient_index, transient_index)]
    r_matrix = matrix[np.ix_(transient_index, absorbing_index)]
    try:
        absorption = np.linalg.solve(np.eye(len(transient_ids)) - q_matrix, r_matrix)
    except np.linalg.LinAlgError as error:
        raise ValueError(
            "Transient system is singular; absorption is not guaranteed"
        ) from error
    if not np.isfinite(absorption).all():
        raise ValueError("Absorption probabilities are not finite")
    absorption_errors = np.abs(absorption.sum(axis=1) - 1)
    if float(absorption_errors.max()) > 1e-9:
        raise ValueError("Some transient states do not eventually reach Death or Win")
    if (absorption < -1e-9).any() or (absorption > 1 + 1e-9).any():
        raise ValueError("Absorption probabilities fall outside [0, 1]")

    start_position = transient_ids.index("1")
    death_probability, win_probability = absorption[start_position]
    print(f"OK: {book_id}/{profile_id}")
    print(f"Nodes: {len(nodes)}; compiled edges: {len(compiled_edges)}")
    print(f"Maximum W row-sum error: {float(row_errors.max()):.3g}")
    print(
        "Absorption from paragraph 1: "
        f"Death={death_probability:.6f}, Win={win_probability:.6f}"
    )


if __name__ == "__main__":
    main()
