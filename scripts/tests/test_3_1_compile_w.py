"""Independent validation of one or all matrices produced by phase 3.1.

This script checks edge coverage, local probability distributions, aggregation into W,
absorbing states and eventual absorption. It does not re-evaluate symbolic expressions.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

DEFAULT_BOOK_ID = "LW01"
DEFAULT_PROFILE_ID = "neutral_neutral_neutral"
DEFAULT_PROFILES_PATH = Path("data/for_graph_model/behavioral_profiles.json")

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


@dataclass(frozen=True)
class ValidationResult:
    """Key diagnostics returned after validating one profile."""

    profile_id: str
    node_count: int
    edge_count: int
    maximum_row_error: float
    death_probability: float
    win_probability: float


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


def load_profile_ids(path: Path) -> list[str]:
    """Read the authoritative ordered list of configured profile identifiers."""
    if not path.exists():
        raise FileNotFoundError(f"Missing profile design: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"{path} must contain a non-empty JSON list")
    result = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict) or "profile_id" not in item:
            raise ValueError(f"{path} profile {index} lacks profile_id")
        result.append(str(item["profile_id"]))
    if len(result) != len(set(result)):
        raise ValueError(f"{path} contains duplicate profile identifiers")
    return result


def validate_combat_roles(pregraph_edges: list[dict[str, str]]) -> None:
    """Check the generic categorical-combat representation once per book."""
    combat_roles: dict[str, list[str]] = defaultdict(list)
    for edge in pregraph_edges:
        if not edge["weight_expression"].startswith("combat_outcome("):
            continue
        match = re.fullmatch(
            r'combat_outcome\((\d+), "(survive|escape|death)"\)',
            edge["weight_expression"],
        )
        if match is None:
            raise ValueError(
                f"Edge {edge['edge_id']} uses a non-generic combat outcome"
            )
        if match[1] != edge["source_id"]:
            raise ValueError(f"Edge {edge['edge_id']} has a combat source mismatch")
        if (
            edge["condition_kind"] != "combat_outcome"
            or edge["condition_value"] != match[2]
        ):
            raise ValueError(f"Edge {edge['edge_id']} has inconsistent combat metadata")
        combat_roles[edge["source_id"]].append(match[2])
    for source_id, roles in combat_roles.items():
        if "survive" not in roles or "death" not in roles:
            raise ValueError(
                f"Combat source {source_id} lacks a survive or death role"
            )


def validate_profile(
    book_id: str,
    profile_id: str,
    nodes: list[dict[str, str]],
    pregraph_edges: list[dict[str, str]],
) -> ValidationResult:
    """Run structural and probabilistic checks on one compiled profile."""
    profile_dir = Path("data/processed/graph") / book_id / profile_id
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
    maximum_row_error = float(row_errors.max())
    if maximum_row_error > 1e-12:
        raise ValueError(f"W row-sum error reaches {maximum_row_error}")

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
    return ValidationResult(
        profile_id=profile_id,
        node_count=len(nodes),
        edge_count=len(compiled_edges),
        maximum_row_error=maximum_row_error,
        death_probability=float(death_probability),
        win_probability=float(win_probability),
    )


def main() -> None:
    """Validate one selected profile or the complete configured design."""
    parser = argparse.ArgumentParser(description="Validate phase-3 matrices W.")
    parser.add_argument(
        "--book", default=DEFAULT_BOOK_ID, help="Book identifier (default: LW01)."
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--profile",
        help=f"Compiled profile identifier (default: {DEFAULT_PROFILE_ID}).",
    )
    selection.add_argument(
        "--all-profiles",
        action="store_true",
        help="Validate every profile in the configured design.",
    )
    parser.add_argument(
        "--profiles",
        type=Path,
        default=DEFAULT_PROFILES_PATH,
        help=f"Profile design JSON (default: {DEFAULT_PROFILES_PATH}).",
    )
    args = parser.parse_args()

    book_id = str(args.book)
    pregraph_dir = Path("data/processed/pregraph") / book_id
    nodes = read_csv(pregraph_dir / "pregraph_nodes.csv", PREGRAPH_NODE_FIELDS)
    pregraph_edges = read_csv(
        pregraph_dir / "pregraph_edges.csv", PREGRAPH_EDGE_FIELDS
    )
    validate_combat_roles(pregraph_edges)

    if args.all_profiles:
        profile_ids = load_profile_ids(Path(args.profiles))
    else:
        profile_ids = [str(args.profile or DEFAULT_PROFILE_ID)]

    results = [
        validate_profile(book_id, profile_id, nodes, pregraph_edges)
        for profile_id in profile_ids
    ]
    for result in results:
        print(
            f"OK: {book_id}/{result.profile_id} — "
            f"Death={result.death_probability:.6f}, "
            f"Win={result.win_probability:.6f}"
        )

    maximum_row_error = max(result.maximum_row_error for result in results)
    print(
        f"Validated {len(results)} profile(s): {len(nodes)} nodes and "
        f"{len(pregraph_edges)} edges each"
    )
    print(f"Maximum W row-sum error: {maximum_row_error:.3g}")


if __name__ == "__main__":
    main()
