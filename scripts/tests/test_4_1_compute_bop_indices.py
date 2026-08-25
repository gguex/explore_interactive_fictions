"""Independently validate every phase-4 Random-Walk BoP index table."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_BOOK_ID = "LW01"
DEFAULT_PROFILES_PATH = Path("data/for_graph_model/behavioral_profiles.json")
ABSORBING_IDS = ("Death", "Win")
ATOL = 5e-9
PROFILE_FIELDS = ["profile_id", "risk", "morality", "action"]
EXPECTED_HEADERS = {
    "profile_metrics.csv": [
        *PROFILE_FIELDS,
        "death_probability",
        "win_probability",
        "expected_transitions",
        "expected_transitions_given_death",
        "expected_transitions_given_win",
        "trajectory_entropy_nats",
        "entropy_per_transition_nats",
        "expected_distinct_nodes",
        "expected_coverage",
        "expected_shared_nodes_same_profile",
        "replay_overlap_ratio",
        "replayability",
        "choice_exposure",
        "global_agency_total",
        "global_agency_mean",
    ],
    "node_metrics.csv": [
        *PROFILE_FIELDS,
        "node_id",
        "node_kind",
        "outcome",
        "is_combat",
        "is_player_choice",
        "expected_visits",
        "visit_probability",
        "expected_visits_given_death",
        "expected_visits_given_win",
        "visit_probability_given_death",
        "visit_probability_given_win",
        "death_potential",
        "win_potential",
        "death_contribution",
        "win_contribution",
        "local_entropy_nats",
        "entropy_contribution_nats",
        "choice_impact",
        "choice_win_range",
    ],
    "edge_metrics.csv": [
        *PROFILE_FIELDS,
        "edge_id",
        "source_id",
        "target_id",
        "transition_kind",
        "compiled_weight",
        "source_is_transient",
        "expected_flow",
        "expected_flow_given_death",
        "expected_flow_given_win",
    ],
    "node_profile_summary.csv": [
        "node_id",
        "node_kind",
        "outcome",
        "is_combat",
        "profile_count",
        "mean_visit_probability",
        "std_visit_probability",
        "min_visit_probability",
        "max_visit_probability",
        "range_visit_probability",
        "min_visit_profile",
        "max_visit_profile",
        "mean_expected_visits",
        "range_expected_visits",
    ],
    "profile_pair_metrics.csv": [
        "profile_a",
        "profile_b",
        "node_visit_js_divergence_nats",
        "edge_flow_js_divergence_nats",
        "win_probability_gap",
        "trajectory_entropy_gap_nats",
    ],
}


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read one required CSV artifact."""
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header: {path}")
        return list(reader.fieldnames), [dict(row) for row in reader]


def close(actual: float, expected: float, label: str) -> None:
    """Require two finite scalar results to agree within serialization error."""
    if not math.isfinite(actual) or not math.isfinite(expected):
        raise ValueError(f"Non-finite value for {label}: {actual}, {expected}")
    if not math.isclose(actual, expected, rel_tol=ATOL, abs_tol=ATOL):
        raise ValueError(f"{label}: got {actual:.12g}, expected {expected:.12g}")


def close_vector(
    actual: np.ndarray[Any, np.dtype[np.float64]],
    expected: np.ndarray[Any, np.dtype[np.float64]],
    label: str,
) -> None:
    """Require two numerical vectors or matrices to agree."""
    if actual.shape != expected.shape or not np.isfinite(actual).all():
        raise ValueError(f"Invalid shape or value for {label}")
    if not np.allclose(actual, expected, rtol=ATOL, atol=ATOL):
        difference = float(np.max(np.abs(actual - expected)))
        raise ValueError(f"{label}: maximum difference is {difference:.3g}")


def values(rows: list[dict[str, str]], field: str) -> np.ndarray[Any, Any]:
    """Extract one float column as an array."""
    return np.array([float(row[field]) for row in rows], dtype=float)


def entropy(row: np.ndarray[Any, np.dtype[np.float64]]) -> float:
    """Calculate Shannon entropy in nats."""
    positive = row[row > 0]
    return float(-np.sum(positive * np.log(positive)))


def js_divergence(
    first: np.ndarray[Any, np.dtype[np.float64]],
    second: np.ndarray[Any, np.dtype[np.float64]],
) -> float:
    """Calculate Jensen-Shannon divergence between two non-negative vectors."""
    first = first / first.sum()
    second = second / second.sum()
    midpoint = 0.5 * (first + second)
    result = 0.0
    for distribution in (first, second):
        mask = distribution > 0
        result += 0.5 * float(
            np.sum(distribution[mask] * np.log(distribution[mask] / midpoint[mask]))
        )
    return result


def load_matrix(path: Path) -> tuple[list[str], np.ndarray[Any, Any]]:
    """Load a compiled transition matrix in its canonical node order."""
    fields, rows = read_csv(path)
    if fields[0] != "node_id":
        raise ValueError(f"Unexpected matrix header: {path}")
    node_ids = fields[1:]
    if [row["node_id"] for row in rows] != node_ids:
        raise ValueError(f"Matrix row and column orders differ: {path}")
    matrix = np.array(
        [[float(row[target]) for target in node_ids] for row in rows], dtype=float
    )
    close_vector(matrix.sum(axis=1), np.ones(len(node_ids)), f"row sums in {path}")
    return node_ids, matrix


def validate_profile(
    book_id: str,
    profile: dict[str, str],
    profile_row: dict[str, str],
    node_rows: list[dict[str, str]],
    edge_rows: list[dict[str, str]],
    phase3_row: dict[str, str],
) -> tuple[np.ndarray[Any, Any], np.ndarray[Any, Any]]:
    """Recompute and validate every metric for a single profile."""
    profile_id = profile["profile_id"]
    graph_root = Path("data/processed/graph") / book_id / profile_id
    node_ids, matrix = load_matrix(graph_root / "W.csv")
    _, compiled_edges = read_csv(graph_root / "compiled_edges.csv")
    index = {node_id: position for position, node_id in enumerate(node_ids)}
    transient_ids = [node_id for node_id in node_ids if node_id not in ABSORBING_IDS]
    transient_indices = [index[node_id] for node_id in transient_ids]
    absorbing_indices = [index[node_id] for node_id in ABSORBING_IDS]
    transient_index = {
        node_id: position for position, node_id in enumerate(transient_ids)
    }
    if "1" not in transient_index:
        raise ValueError("Initial paragraph 1 is absent")

    q_matrix = matrix[np.ix_(transient_indices, transient_indices)]
    r_matrix = matrix[np.ix_(transient_indices, absorbing_indices)]
    fundamental = np.linalg.inv(np.eye(len(transient_ids)) - q_matrix)
    absorption = fundamental @ r_matrix
    start = transient_index["1"]
    expected_visits = fundamental[start]
    visit_probability = expected_visits / np.diag(fundamental)
    death_potential = absorption[:, 0]
    win_potential = absorption[:, 1]
    death_probability = float(death_potential[start])
    win_probability = float(win_potential[start])

    if [row["node_id"] for row in node_rows] != transient_ids:
        raise ValueError(f"Node order or coverage differs for {profile_id}")
    if [row["edge_id"] for row in edge_rows] != [
        row["edge_id"] for row in compiled_edges
    ]:
        raise ValueError(f"Edge order or coverage differs for {profile_id}")
    for field in ("risk", "morality", "action"):
        if profile_row[field] != profile[field]:
            raise ValueError(f"Profile metadata differs for {profile_id}/{field}")

    local_entropy = np.array(
        [entropy(matrix[index[node_id]]) for node_id in transient_ids], dtype=float
    )
    expected_death = expected_visits * death_potential / death_probability
    expected_win = expected_visits * win_potential / win_probability
    visit_death = visit_probability * death_potential / death_probability
    visit_win = visit_probability * win_potential / win_probability

    comparisons = {
        "expected_visits": expected_visits,
        "visit_probability": visit_probability,
        "expected_visits_given_death": expected_death,
        "expected_visits_given_win": expected_win,
        "visit_probability_given_death": visit_death,
        "visit_probability_given_win": visit_win,
        "death_potential": death_potential,
        "win_potential": win_potential,
        "local_entropy_nats": local_entropy,
        "entropy_contribution_nats": expected_visits * local_entropy,
    }
    for field, expected in comparisons.items():
        close_vector(values(node_rows, field), expected, f"{profile_id}/{field}")

    all_death = {"Death": 1.0, "Win": 0.0}
    all_win = {"Death": 0.0, "Win": 1.0}
    all_death.update(dict(zip(transient_ids, death_potential, strict=True)))
    all_win.update(dict(zip(transient_ids, win_potential, strict=True)))
    reconstructed = np.zeros_like(matrix)
    # Absorbing self-loops belong to W but are not narrative compiled edges.
    for node_id in ABSORBING_IDS:
        reconstructed[index[node_id], index[node_id]] = 1.0
    expected_flow: list[float] = []
    death_flow: list[float] = []
    win_flow: list[float] = []
    choice_successors: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for produced, compiled in zip(edge_rows, compiled_edges, strict=True):
        for field in ("edge_id", "source_id", "target_id", "transition_kind"):
            if produced[field] != compiled[field]:
                raise ValueError(f"Compiled edge mismatch for {profile_id}/{field}")
        weight = float(compiled["compiled_weight"])
        close(float(produced["compiled_weight"]), weight, "compiled edge weight")
        source_id = compiled["source_id"]
        target_id = compiled["target_id"]
        reconstructed[index[source_id], index[target_id]] += weight
        if source_id in transient_index:
            source_position = transient_index[source_id]
            flow = float(expected_visits[source_position] * weight)
            conditional_death = (
                flow * float(all_death[target_id]) / death_probability
            )
            conditional_win = flow * float(all_win[target_id]) / win_probability
            if compiled["transition_kind"] == "profile_choice" and weight > 0:
                choice_successors[source_id].append(
                    (weight, float(all_win[target_id]))
                )
            if produced["source_is_transient"] != "true":
                raise ValueError(
                    f"Transient source flag differs on {produced['edge_id']}"
                )
        else:
            flow = conditional_death = conditional_win = 0.0
            if produced["source_is_transient"] != "false":
                raise ValueError(
                    f"Absorbing source flag differs on {produced['edge_id']}"
                )
        expected_flow.append(flow)
        death_flow.append(conditional_death)
        win_flow.append(conditional_win)

    close_vector(reconstructed, matrix, f"edge aggregation for {profile_id}")
    edge_expected = np.array(expected_flow)
    edge_death = np.array(death_flow)
    edge_win = np.array(win_flow)
    close_vector(values(edge_rows, "expected_flow"), edge_expected, "edge flow")
    close_vector(
        values(edge_rows, "expected_flow_given_death"), edge_death, "death flow"
    )
    close_vector(values(edge_rows, "expected_flow_given_win"), edge_win, "win flow")

    node_by_id = {row["node_id"]: row for row in node_rows}
    for node_id in transient_ids:
        outgoing = [
            position
            for position, edge in enumerate(compiled_edges)
            if edge["source_id"] == node_id
        ]
        position = transient_index[node_id]
        close(edge_expected[outgoing].sum(), expected_visits[position], "source flow")
        close(edge_death[outgoing].sum(), expected_death[position], "death source flow")
        close(edge_win[outgoing].sum(), expected_win[position], "win source flow")

        successors = choice_successors.get(node_id, [])
        if successors:
            total = sum(weight for weight, _ in successors)
            mean = sum(weight * potential for weight, potential in successors) / total
            variance = sum(
                weight / total * (potential - mean) ** 2
                for weight, potential in successors
            )
            impact = math.sqrt(max(variance, 0.0))
            potentials = [potential for _, potential in successors]
            impact_range = max(potentials) - min(potentials)
            expected_choice = "true"
        else:
            impact = impact_range = 0.0
            expected_choice = "false"
        row = node_by_id[node_id]
        if row["is_player_choice"] != expected_choice:
            raise ValueError(f"Player-choice flag differs at {profile_id}/{node_id}")
        close(float(row["choice_impact"]), impact, "choice impact")
        close(float(row["choice_win_range"]), impact_range, "choice range")

    death_direct = np.array(
        [matrix[index[node_id], index["Death"]] for node_id in transient_ids]
    )
    win_direct = np.array(
        [matrix[index[node_id], index["Win"]] for node_id in transient_ids]
    )
    close_vector(
        values(node_rows, "death_contribution"),
        expected_visits * death_direct,
        "death contribution",
    )
    close_vector(
        values(node_rows, "win_contribution"),
        expected_visits * win_direct,
        "win contribution",
    )

    trajectory_entropy = float(np.dot(expected_visits, local_entropy))
    expected_transitions = float(expected_visits.sum())
    expected_distinct = float(visit_probability.sum())
    expected_shared = float(np.square(visit_probability).sum())
    overlap = expected_shared / expected_distinct
    choice_rows = [row for row in node_rows if row["is_player_choice"] == "true"]
    choice_exposure = sum(float(row["expected_visits"]) for row in choice_rows)
    agency_total = sum(
        float(row["expected_visits"]) * float(row["choice_impact"])
        for row in choice_rows
    )
    scalar_expectations = {
        "death_probability": death_probability,
        "win_probability": win_probability,
        "expected_transitions": expected_transitions,
        "expected_transitions_given_death": float(expected_death.sum()),
        "expected_transitions_given_win": float(expected_win.sum()),
        "trajectory_entropy_nats": trajectory_entropy,
        "entropy_per_transition_nats": trajectory_entropy / expected_transitions,
        "expected_distinct_nodes": expected_distinct,
        "expected_coverage": expected_distinct / len(transient_ids),
        "expected_shared_nodes_same_profile": expected_shared,
        "replay_overlap_ratio": overlap,
        "replayability": 1 - overlap,
        "choice_exposure": choice_exposure,
        "global_agency_total": agency_total,
        "global_agency_mean": agency_total / choice_exposure,
    }
    for field, expected in scalar_expectations.items():
        close(float(profile_row[field]), expected, f"{profile_id}/{field}")
    close(death_probability + win_probability, 1.0, "total absorption")
    close(
        float(values(node_rows, "death_contribution").sum()),
        death_probability,
        "death total",
    )
    close(
        float(values(node_rows, "win_contribution").sum()),
        win_probability,
        "win total",
    )
    close(float(edge_expected.sum()), expected_transitions, "total edge flow")
    close(float(edge_death.sum()), float(expected_death.sum()), "total death flow")
    close(float(edge_win.sum()), float(expected_win.sum()), "total win flow")
    close(float(phase3_row["death_probability"]), death_probability, "phase-3 death")
    close(float(phase3_row["win_probability"]), win_probability, "phase-3 win")
    close(
        float(phase3_row["expected_steps_to_absorption"]),
        expected_transitions,
        "phase-3 duration",
    )
    return visit_probability, edge_expected


def validate_node_summaries(
    profiles: list[dict[str, str]],
    grouped_nodes: dict[str, list[dict[str, str]]],
    summary_rows: list[dict[str, str]],
) -> None:
    """Rebuild every cross-profile local sensitivity summary."""
    profile_ids = [profile["profile_id"] for profile in profiles]
    by_node_profile = {
        node_id: {row["profile_id"]: row for row in rows}
        for node_id, rows in grouped_nodes.items()
    }
    if set(by_node_profile) != {row["node_id"] for row in summary_rows}:
        raise ValueError("Node-summary coverage differs from local metrics")
    for summary in summary_rows:
        node_id = summary["node_id"]
        rows = [by_node_profile[node_id][profile_id] for profile_id in profile_ids]
        visits = values(rows, "visit_probability")
        expected = values(rows, "expected_visits")
        scalar_expectations = {
            "mean_visit_probability": float(visits.mean()),
            "std_visit_probability": float(visits.std()),
            "min_visit_probability": float(visits.min()),
            "max_visit_probability": float(visits.max()),
            "range_visit_probability": float(visits.max() - visits.min()),
            "mean_expected_visits": float(expected.mean()),
            "range_expected_visits": float(expected.max() - expected.min()),
        }
        for field, value in scalar_expectations.items():
            close(float(summary[field]), value, f"node summary {node_id}/{field}")
        if int(summary["profile_count"]) != len(profiles):
            raise ValueError(f"Profile count differs in node summary {node_id}")
        if summary["min_visit_profile"] != profile_ids[int(np.argmin(visits))]:
            raise ValueError(f"Minimum profile differs at node {node_id}")
        if summary["max_visit_profile"] != profile_ids[int(np.argmax(visits))]:
            raise ValueError(f"Maximum profile differs at node {node_id}")


def validate_pairs(
    profiles: list[dict[str, str]],
    profile_rows: dict[str, dict[str, str]],
    distributions: dict[str, tuple[np.ndarray[Any, Any], np.ndarray[Any, Any]]],
    pair_rows: list[dict[str, str]],
) -> None:
    """Recalculate all unordered profile divergences and scalar gaps."""
    expected_pairs = list(
        combinations([profile["profile_id"] for profile in profiles], 2)
    )
    if [(row["profile_a"], row["profile_b"]) for row in pair_rows] != expected_pairs:
        raise ValueError("Profile-pair order or coverage differs")
    for pair, row in zip(expected_pairs, pair_rows, strict=True):
        first, second = pair
        node_first, edge_first = distributions[first]
        node_second, edge_second = distributions[second]
        expectations = {
            "node_visit_js_divergence_nats": js_divergence(
                node_first, node_second
            ),
            "edge_flow_js_divergence_nats": js_divergence(
                edge_first, edge_second
            ),
            "win_probability_gap": abs(
                float(profile_rows[first]["win_probability"])
                - float(profile_rows[second]["win_probability"])
            ),
            "trajectory_entropy_gap_nats": abs(
                float(profile_rows[first]["trajectory_entropy_nats"])
                - float(profile_rows[second]["trajectory_entropy_nats"])
            ),
        }
        for field, expected in expectations.items():
            actual = float(row[field])
            close(actual, expected, f"{first}/{second}/{field}")
            if "js_divergence" in field and not 0 <= actual <= math.log(2) + ATOL:
                raise ValueError(f"Jensen-Shannon divergence is out of range: {actual}")


def main() -> None:
    """Validate schemas, counts and independently recomputed metrics."""
    parser = argparse.ArgumentParser(description="Validate all phase-4.1 BoP indices.")
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES_PATH)
    parser.add_argument("--input-dir", type=Path)
    args = parser.parse_args()

    book_id = str(args.book)
    input_dir = args.input_dir or Path("data/processed/bop") / book_id
    profiles_payload = json.loads(args.profiles.read_text(encoding="utf-8"))
    if not isinstance(profiles_payload, list):
        raise ValueError("Profile design must be a JSON list")
    profiles = [
        {key: str(value) for key, value in row.items()}
        for row in profiles_payload
    ]
    profile_ids = [profile["profile_id"] for profile in profiles]
    if len(profile_ids) != len(set(profile_ids)):
        raise ValueError("Duplicate configured profiles")

    loaded = {
        filename: read_csv(input_dir / filename) for filename in EXPECTED_HEADERS
    }
    for filename, expected_header in EXPECTED_HEADERS.items():
        if loaded[filename][0] != expected_header:
            raise ValueError(f"Unexpected output schema: {filename}")
    all_profile_rows = loaded["profile_metrics.csv"][1]
    all_node_rows = loaded["node_metrics.csv"][1]
    all_edge_rows = loaded["edge_metrics.csv"][1]
    summary_rows = loaded["node_profile_summary.csv"][1]
    pair_rows = loaded["profile_pair_metrics.csv"][1]
    _, phase3_rows = read_csv(
        Path("data/processed/graph") / book_id / "profile_summary.csv"
    )
    manifest_path = input_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    profile_rows = {row["profile_id"]: row for row in all_profile_rows}
    phase3_by_profile = {row["profile_id"]: row for row in phase3_rows}
    nodes_by_profile: dict[str, list[dict[str, str]]] = defaultdict(list)
    edges_by_profile: dict[str, list[dict[str, str]]] = defaultdict(list)
    nodes_by_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in all_node_rows:
        nodes_by_profile[row["profile_id"]].append(row)
        nodes_by_id[row["node_id"]].append(row)
    for row in all_edge_rows:
        edges_by_profile[row["profile_id"]].append(row)

    if list(profile_rows) != profile_ids:
        raise ValueError("Calculated profile order or coverage differs from design")
    if set(nodes_by_profile) != set(profile_ids) or set(edges_by_profile) != set(
        profile_ids
    ):
        raise ValueError("Local metric profile coverage differs from design")

    distributions = {}
    for profile in profiles:
        profile_id = profile["profile_id"]
        distributions[profile_id] = validate_profile(
            book_id,
            profile,
            profile_rows[profile_id],
            nodes_by_profile[profile_id],
            edges_by_profile[profile_id],
            phase3_by_profile[profile_id],
        )
    validate_node_summaries(profiles, nodes_by_id, summary_rows)
    validate_pairs(profiles, profile_rows, distributions, pair_rows)

    expected_counts = {
        "profile_metrics.csv": len(all_profile_rows),
        "node_metrics.csv": len(all_node_rows),
        "edge_metrics.csv": len(all_edge_rows),
        "node_profile_summary.csv": len(summary_rows),
        "profile_pair_metrics.csv": len(pair_rows),
    }
    if manifest.get("book_id") != book_id or manifest.get("outputs") != expected_counts:
        raise ValueError("Manifest identity or output counts differ")
    if manifest.get("output_schemas") != EXPECTED_HEADERS:
        raise ValueError("Manifest output schemas differ")
    if manifest.get("profile_count") != len(profiles):
        raise ValueError("Manifest profile count differs")
    if len(pair_rows) != len(profiles) * (len(profiles) - 1) // 2:
        raise ValueError("Unexpected profile-pair count")

    neutral = profile_rows["neutral_neutral_neutral"]
    print(f"OK: all {len(profiles)} {book_id} profiles independently validated")
    print(
        f"Rows: profiles={len(all_profile_rows)}; nodes={len(all_node_rows)}; "
        f"edges={len(all_edge_rows)}; pairs={len(pair_rows)}"
    )
    print(
        "Neutral: "
        f"Win={float(neutral['win_probability']):.6f}; "
        f"duration={float(neutral['expected_transitions']):.6f}; "
        f"entropy={float(neutral['trajectory_entropy_nats']):.6f} nats"
    )


if __name__ == "__main__":
    main()
