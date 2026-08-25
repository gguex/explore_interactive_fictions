"""Compute canonical Random-Walk Bag-of-Paths indices for every profile."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_BOOK_ID = "LW01"
DEFAULT_PROFILES_PATH = Path("data/for_graph_model/behavioral_profiles.json")
ABSORBING_IDS = ("Death", "Win")
PROFILE_FIELDS = ["profile_id", "risk", "morality", "action"]
PROFILE_METRIC_FIELDS = [
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
]
NODE_METRIC_FIELDS = [
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
]
EDGE_METRIC_FIELDS = [
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
]
NODE_PROFILE_SUMMARY_FIELDS = [
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
]
PROFILE_PAIR_FIELDS = [
    "profile_a",
    "profile_b",
    "node_visit_js_divergence_nats",
    "edge_flow_js_divergence_nats",
    "win_probability_gap",
    "trajectory_entropy_gap_nats",
]


@dataclass(frozen=True)
class ProfileResult:
    """All canonical tables and comparison vectors for one profile."""

    profile: dict[str, str]
    profile_row: dict[str, str]
    node_rows: list[dict[str, str]]
    edge_rows: list[dict[str, str]]
    node_visit_distribution: np.ndarray[Any, np.dtype[np.float64]]
    edge_flow_distribution: np.ndarray[Any, np.dtype[np.float64]]


def read_json(path: Path) -> Any:
    """Load one required JSON document."""
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Load one required CSV and return its header and rows."""
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header in {path}")
        return list(reader.fieldnames), [dict(row) for row in reader]


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    """Write a deterministic UTF-8 CSV table."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def formatted(value: float) -> str:
    """Format finite numerical results consistently."""
    if not math.isfinite(value):
        raise ValueError(f"Cannot serialize non-finite metric: {value}")
    if abs(value) < 5e-16:
        value = 0.0
    return format(value, ".12g")


def boolean(value: bool) -> str:
    """Serialize one boolean consistently in CSV outputs."""
    return "true" if value else "false"


def clamp_probability(value: float) -> float:
    """Remove harmless floating-point excursions outside [0, 1]."""
    if value < -1e-10 or value > 1 + 1e-10:
        raise ValueError(f"Probability outside [0,1]: {value}")
    return min(1.0, max(0.0, value))


def load_profiles(path: Path) -> list[dict[str, str]]:
    """Load and validate the fixed behavioral-profile design."""
    payload = read_json(path)
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"{path} must contain a non-empty JSON list")
    result = []
    seen: set[str] = set()
    for index, item in enumerate(payload):
        if not isinstance(item, dict) or set(item) != set(PROFILE_FIELDS):
            raise ValueError(
                f"{path} profile {index} must contain exactly {PROFILE_FIELDS}"
            )
        profile = {field: str(item[field]) for field in PROFILE_FIELDS}
        if profile["profile_id"] in seen:
            raise ValueError(f"Duplicate profile: {profile['profile_id']}")
        seen.add(profile["profile_id"])
        result.append(profile)
    return result


def load_node_metadata(
    book_id: str,
) -> tuple[list[str], dict[str, dict[str, str]], set[str]]:
    """Load canonical node metadata and phase-1 combat annotations."""
    pregraph_path = (
        Path("data/processed/pregraph") / book_id / "pregraph_nodes.csv"
    )
    _, pregraph = read_csv(pregraph_path)
    metadata = {row["node_id"]: row for row in pregraph}
    node_ids = [row["node_id"] for row in pregraph]
    if len(node_ids) != len(set(node_ids)) or set(ABSORBING_IDS) - set(node_ids):
        raise ValueError(f"Invalid canonical node set in {pregraph_path}")

    source_path = (
        Path("data/processed/nodes_edges") / book_id / f"{book_id}_nodes.csv"
    )
    _, source_nodes = read_csv(source_path)
    combat_ids = {
        row["node_id"] for row in source_nodes if row.get("enemies", "").strip()
    }
    return node_ids, metadata, combat_ids


def load_matrix(
    path: Path, expected_ids: list[str]
) -> np.ndarray[Any, np.dtype[np.float64]]:
    """Load and validate one dense transition matrix."""
    fields, rows = read_csv(path)
    if not fields or fields[0] != "node_id":
        raise ValueError(f"Unexpected W header in {path}")
    node_ids = fields[1:]
    if node_ids != expected_ids or [row["node_id"] for row in rows] != expected_ids:
        raise ValueError(f"W node order differs from the canonical order in {path}")
    matrix = np.array(
        [[float(row[target]) for target in node_ids] for row in rows], dtype=float
    )
    if matrix.shape != (len(node_ids), len(node_ids)):
        raise ValueError(f"W is not square in {path}")
    if not np.isfinite(matrix).all() or (matrix < -1e-12).any():
        raise ValueError(f"W has invalid entries in {path}")
    if not np.allclose(matrix.sum(axis=1), 1.0, atol=1e-10):
        raise ValueError(f"W rows do not sum to one in {path}")
    return matrix


def load_compiled_edges(path: Path) -> list[dict[str, str]]:
    """Load one complete compiled multiedge table."""
    _, rows = read_csv(path)
    edge_ids = [row["edge_id"] for row in rows]
    if len(edge_ids) != len(set(edge_ids)):
        raise ValueError(f"Duplicate edge identifiers in {path}")
    for row in rows:
        weight = float(row["compiled_weight"])
        if not math.isfinite(weight) or weight < 0:
            raise ValueError(f"Invalid compiled weight on {row['edge_id']}")
    return rows


def entropy(probabilities: np.ndarray[Any, np.dtype[np.float64]]) -> float:
    """Return Shannon entropy in natural-log units, ignoring zero mass."""
    positive = probabilities[probabilities > 0]
    return float(-np.sum(positive * np.log(positive)))


def normalized(values: np.ndarray[Any, np.dtype[np.float64]]) -> np.ndarray[Any, Any]:
    """Normalize one non-negative comparison vector."""
    total = float(values.sum())
    if total <= 0:
        raise ValueError("Cannot normalize an empty metric distribution")
    return values / total


def jensen_shannon(
    first: np.ndarray[Any, np.dtype[np.float64]],
    second: np.ndarray[Any, np.dtype[np.float64]],
) -> float:
    """Return Jensen-Shannon divergence in nats for normalized vectors."""
    midpoint = 0.5 * (first + second)

    def kl_divergence(
        distribution: np.ndarray[Any, np.dtype[np.float64]],
    ) -> float:
        mask = distribution > 0
        return float(
            np.sum(distribution[mask] * np.log(distribution[mask] / midpoint[mask]))
        )

    return 0.5 * kl_divergence(first) + 0.5 * kl_divergence(second)


def choice_impacts(
    edges: list[dict[str, str]], potential: dict[str, float]
) -> dict[str, tuple[float, float]]:
    """Calculate weighted win-potential dispersion for each player-choice source."""
    grouped: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for edge in edges:
        if edge["transition_kind"] != "profile_choice":
            continue
        weight = float(edge["compiled_weight"])
        if weight > 0:
            grouped[edge["source_id"]].append(
                (weight, potential[edge["target_id"]])
            )
    result = {}
    for source, values in grouped.items():
        total = sum(weight for weight, _ in values)
        mean = sum(weight * value for weight, value in values) / total
        variance = sum(
            (weight / total) * (value - mean) ** 2 for weight, value in values
        )
        outcome_values = [value for _, value in values]
        result[source] = math.sqrt(max(0.0, variance)), (
            max(outcome_values) - min(outcome_values)
        )
    return result


def compute_profile(
    graph_root: Path,
    profile: dict[str, str],
    node_ids: list[str],
    metadata: dict[str, dict[str, str]],
    combat_ids: set[str],
    expected_edge_ids: list[str] | None,
) -> tuple[ProfileResult, list[str]]:
    """Compute all canonical profile, node and edge metrics."""
    profile_id = profile["profile_id"]
    profile_root = graph_root / profile_id
    matrix = load_matrix(profile_root / "W.csv", node_ids)
    edges = load_compiled_edges(profile_root / "compiled_edges.csv")
    edge_ids = [row["edge_id"] for row in edges]
    if expected_edge_ids is not None and edge_ids != expected_edge_ids:
        raise ValueError(f"Compiled edge order differs for {profile_id}")

    index = {node_id: position for position, node_id in enumerate(node_ids)}
    transient_ids = [node_id for node_id in node_ids if node_id not in ABSORBING_IDS]
    transient_indices = [index[node_id] for node_id in transient_ids]
    absorbing_indices = [index[node_id] for node_id in ABSORBING_IDS]
    transient_position = {
        node_id: position for position, node_id in enumerate(transient_ids)
    }
    q_matrix = matrix[np.ix_(transient_indices, transient_indices)]
    r_matrix = matrix[np.ix_(transient_indices, absorbing_indices)]
    fundamental = np.linalg.inv(np.eye(len(transient_ids)) - q_matrix)
    absorption = fundamental @ r_matrix
    start = transient_position["1"]
    expected_visits = fundamental[start]
    visit_probabilities = np.array(
        [
            clamp_probability(float(expected_visits[i] / fundamental[i, i]))
            for i in range(len(transient_ids))
        ],
        dtype=float,
    )
    death_potentials = np.clip(absorption[:, 0], 0.0, 1.0)
    win_potentials = np.clip(absorption[:, 1], 0.0, 1.0)
    death_probability = clamp_probability(float(death_potentials[start]))
    win_probability = clamp_probability(float(win_potentials[start]))
    if not math.isclose(death_probability + win_probability, 1.0, abs_tol=1e-9):
        raise ValueError(f"Absorption probabilities do not sum to one for {profile_id}")

    expected_visits_given_death = (
        expected_visits * death_potentials / death_probability
    )
    expected_visits_given_win = expected_visits * win_potentials / win_probability
    visit_probability_given_death = np.clip(
        visit_probabilities * death_potentials / death_probability, 0.0, 1.0
    )
    visit_probability_given_win = np.clip(
        visit_probabilities * win_potentials / win_probability, 0.0, 1.0
    )

    local_entropies = np.array(
        [entropy(matrix[index[node_id]]) for node_id in transient_ids], dtype=float
    )
    entropy_contributions = expected_visits * local_entropies
    trajectory_entropy = float(entropy_contributions.sum())
    expected_transitions = float(expected_visits.sum())

    all_death_potential = {"Death": 1.0, "Win": 0.0}
    all_win_potential = {"Death": 0.0, "Win": 1.0}
    for position, node_id in enumerate(transient_ids):
        all_death_potential[node_id] = float(death_potentials[position])
        all_win_potential[node_id] = float(win_potentials[position])
    impacts = choice_impacts(edges, all_win_potential)

    node_rows = []
    for position, node_id in enumerate(transient_ids):
        row_index = index[node_id]
        death_contribution = float(
            expected_visits[position] * matrix[row_index, index["Death"]]
        )
        win_contribution = float(
            expected_visits[position] * matrix[row_index, index["Win"]]
        )
        impact, impact_range = impacts.get(node_id, (0.0, 0.0))
        node_rows.append(
            {
                **profile,
                "node_id": node_id,
                "node_kind": metadata[node_id]["node_kind"],
                "outcome": metadata[node_id]["outcome"],
                "is_combat": boolean(node_id in combat_ids),
                "is_player_choice": boolean(node_id in impacts),
                "expected_visits": formatted(float(expected_visits[position])),
                "visit_probability": formatted(float(visit_probabilities[position])),
                "expected_visits_given_death": formatted(
                    float(expected_visits_given_death[position])
                ),
                "expected_visits_given_win": formatted(
                    float(expected_visits_given_win[position])
                ),
                "visit_probability_given_death": formatted(
                    float(visit_probability_given_death[position])
                ),
                "visit_probability_given_win": formatted(
                    float(visit_probability_given_win[position])
                ),
                "death_potential": formatted(float(death_potentials[position])),
                "win_potential": formatted(float(win_potentials[position])),
                "death_contribution": formatted(death_contribution),
                "win_contribution": formatted(win_contribution),
                "local_entropy_nats": formatted(float(local_entropies[position])),
                "entropy_contribution_nats": formatted(
                    float(entropy_contributions[position])
                ),
                "choice_impact": formatted(impact),
                "choice_win_range": formatted(impact_range),
            }
        )

    edge_rows = []
    edge_flow_values = []
    for edge in edges:
        source_id = edge["source_id"]
        target_id = edge["target_id"]
        weight = float(edge["compiled_weight"])
        if source_id in transient_position:
            source_position = transient_position[source_id]
            flow = float(expected_visits[source_position] * weight)
            death_flow = (
                float(
                    expected_visits[source_position]
                    * weight
                    * all_death_potential[target_id]
                    / death_probability
                )
            )
            win_flow = (
                float(
                    expected_visits[source_position]
                    * weight
                    * all_win_potential[target_id]
                    / win_probability
                )
            )
            is_transient = True
        else:
            flow = death_flow = win_flow = 0.0
            is_transient = False
        edge_flow_values.append(flow)
        edge_rows.append(
            {
                **profile,
                "edge_id": edge["edge_id"],
                "source_id": source_id,
                "target_id": target_id,
                "transition_kind": edge["transition_kind"],
                "compiled_weight": formatted(weight),
                "source_is_transient": boolean(is_transient),
                "expected_flow": formatted(flow),
                "expected_flow_given_death": formatted(death_flow),
                "expected_flow_given_win": formatted(win_flow),
            }
        )

    choice_exposure = sum(
        float(expected_visits[transient_position[node_id]]) for node_id in impacts
    )
    global_agency_total = sum(
        float(expected_visits[transient_position[node_id]]) * impacts[node_id][0]
        for node_id in impacts
    )
    global_agency_mean = (
        global_agency_total / choice_exposure if choice_exposure > 0 else 0.0
    )
    expected_distinct = float(visit_probabilities.sum())
    expected_shared = float(np.square(visit_probabilities).sum())
    replay_overlap = expected_shared / expected_distinct
    profile_row = {
        **profile,
        "death_probability": formatted(death_probability),
        "win_probability": formatted(win_probability),
        "expected_transitions": formatted(expected_transitions),
        "expected_transitions_given_death": formatted(
            float(expected_visits_given_death.sum())
        ),
        "expected_transitions_given_win": formatted(
            float(expected_visits_given_win.sum())
        ),
        "trajectory_entropy_nats": formatted(trajectory_entropy),
        "entropy_per_transition_nats": formatted(
            trajectory_entropy / expected_transitions
        ),
        "expected_distinct_nodes": formatted(expected_distinct),
        "expected_coverage": formatted(expected_distinct / len(transient_ids)),
        "expected_shared_nodes_same_profile": formatted(expected_shared),
        "replay_overlap_ratio": formatted(replay_overlap),
        "replayability": formatted(1 - replay_overlap),
        "choice_exposure": formatted(choice_exposure),
        "global_agency_total": formatted(global_agency_total),
        "global_agency_mean": formatted(global_agency_mean),
    }
    return (
        ProfileResult(
            profile=profile,
            profile_row=profile_row,
            node_rows=node_rows,
            edge_rows=edge_rows,
            node_visit_distribution=normalized(visit_probabilities),
            edge_flow_distribution=normalized(
                np.array(edge_flow_values, dtype=float)
            ),
        ),
        edge_ids,
    )


def node_profile_summaries(
    results: list[ProfileResult],
) -> list[dict[str, str]]:
    """Summarize local visit sensitivity across the complete profile design."""
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for result in results:
        for row in result.node_rows:
            grouped[row["node_id"]].append(row)
    output = []
    first_nodes = {row["node_id"]: row for row in results[0].node_rows}
    for node_id in [row["node_id"] for row in results[0].node_rows]:
        rows = grouped[node_id]
        visits = np.array([float(row["visit_probability"]) for row in rows])
        expected = np.array([float(row["expected_visits"]) for row in rows])
        minimum = min(rows, key=lambda row: float(row["visit_probability"]))
        maximum = max(rows, key=lambda row: float(row["visit_probability"]))
        source = first_nodes[node_id]
        output.append(
            {
                "node_id": node_id,
                "node_kind": source["node_kind"],
                "outcome": source["outcome"],
                "is_combat": source["is_combat"],
                "profile_count": str(len(rows)),
                "mean_visit_probability": formatted(float(visits.mean())),
                "std_visit_probability": formatted(float(visits.std())),
                "min_visit_probability": formatted(float(visits.min())),
                "max_visit_probability": formatted(float(visits.max())),
                "range_visit_probability": formatted(
                    float(visits.max() - visits.min())
                ),
                "min_visit_profile": minimum["profile_id"],
                "max_visit_profile": maximum["profile_id"],
                "mean_expected_visits": formatted(float(expected.mean())),
                "range_expected_visits": formatted(
                    float(expected.max() - expected.min())
                ),
            }
        )
    return output


def profile_pair_rows(results: list[ProfileResult]) -> list[dict[str, str]]:
    """Calculate all unordered pairwise profile divergences."""
    output = []
    for first, second in combinations(results, 2):
        first_profile = first.profile_row
        second_profile = second.profile_row
        output.append(
            {
                "profile_a": first.profile["profile_id"],
                "profile_b": second.profile["profile_id"],
                "node_visit_js_divergence_nats": formatted(
                    jensen_shannon(
                        first.node_visit_distribution,
                        second.node_visit_distribution,
                    )
                ),
                "edge_flow_js_divergence_nats": formatted(
                    jensen_shannon(
                        first.edge_flow_distribution,
                        second.edge_flow_distribution,
                    )
                ),
                "win_probability_gap": formatted(
                    abs(
                        float(first_profile["win_probability"])
                        - float(second_profile["win_probability"])
                    )
                ),
                "trajectory_entropy_gap_nats": formatted(
                    abs(
                        float(first_profile["trajectory_entropy_nats"])
                        - float(second_profile["trajectory_entropy_nats"])
                    )
                ),
            }
        )
    return output


def manifest(
    book_id: str,
    results: list[ProfileResult],
    node_count: int,
    edge_count: int,
) -> dict[str, Any]:
    """Describe schemas, conventions and formulas for downstream scripts."""
    return {
        "schema_version": "1.0",
        "book_id": book_id,
        "method": "Random-Walk Bag-of-Paths on an absorbing Markov chain",
        "start_node": "1",
        "absorbing_nodes": list(ABSORBING_IDS),
        "profile_count": len(results),
        "transient_node_count": node_count,
        "canonical_edge_count": edge_count,
        "entropy_log_base": "e (nats)",
        "definitions": {
            "expected_visits": "N[start,i], with N=(I-Q)^-1",
            "visit_probability": "N[start,i] / N[i,i]",
            "trajectory_entropy_nats": "sum_i expected_visits_i * H(W_i)",
            "expected_coverage": "sum_i visit_probability_i / transient_node_count",
            "replay_overlap_ratio": (
                "sum_i visit_probability_i^2 / sum_i visit_probability_i"
            ),
            "replayability": "1 - replay_overlap_ratio",
            "choice_impact": (
                "compiled-weighted standard deviation of successor win potentials "
                "within profile_choice edges"
            ),
            "global_agency_mean": (
                "expected-visit-weighted choice_impact / choice_exposure"
            ),
            "conditional_expected_visits": (
                "expected_visits_i * outcome_potential_i / P(outcome from start)"
            ),
            "profile_divergence": (
                "Jensen-Shannon divergence between normalized node-visit or edge-flow "
                "vectors"
            ),
        },
        "outputs": {
            "profile_metrics.csv": len(results),
            "node_metrics.csv": len(results) * node_count,
            "edge_metrics.csv": len(results) * edge_count,
            "node_profile_summary.csv": node_count,
            "profile_pair_metrics.csv": len(results) * (len(results) - 1) // 2,
        },
        "output_schemas": {
            "profile_metrics.csv": PROFILE_METRIC_FIELDS,
            "node_metrics.csv": NODE_METRIC_FIELDS,
            "edge_metrics.csv": EDGE_METRIC_FIELDS,
            "node_profile_summary.csv": NODE_PROFILE_SUMMARY_FIELDS,
            "profile_pair_metrics.csv": PROFILE_PAIR_FIELDS,
        },
    }


def main() -> None:
    """Compute and write all canonical phase-4 index tables."""
    parser = argparse.ArgumentParser(
        description="Compute Random-Walk BoP indices for every behavioral profile."
    )
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES_PATH)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    book_id = str(args.book)
    profiles = load_profiles(args.profiles)
    graph_root = Path("data/processed/graph") / book_id
    output_dir = args.output_dir or Path("data/processed/bop") / book_id
    node_ids, metadata, combat_ids = load_node_metadata(book_id)
    transient_count = len(node_ids) - len(ABSORBING_IDS)

    results = []
    expected_edge_ids: list[str] | None = None
    for profile in profiles:
        result, edge_ids = compute_profile(
            graph_root,
            profile,
            node_ids,
            metadata,
            combat_ids,
            expected_edge_ids,
        )
        if expected_edge_ids is None:
            expected_edge_ids = edge_ids
        results.append(result)
    if expected_edge_ids is None:
        raise ValueError("No compiled profiles were processed")

    profile_rows = [result.profile_row for result in results]
    node_rows = [row for result in results for row in result.node_rows]
    edge_rows = [row for result in results for row in result.edge_rows]
    summaries = node_profile_summaries(results)
    pairs = profile_pair_rows(results)
    write_csv(output_dir / "profile_metrics.csv", PROFILE_METRIC_FIELDS, profile_rows)
    write_csv(output_dir / "node_metrics.csv", NODE_METRIC_FIELDS, node_rows)
    write_csv(output_dir / "edge_metrics.csv", EDGE_METRIC_FIELDS, edge_rows)
    write_csv(
        output_dir / "node_profile_summary.csv",
        NODE_PROFILE_SUMMARY_FIELDS,
        summaries,
    )
    write_csv(
        output_dir / "profile_pair_metrics.csv", PROFILE_PAIR_FIELDS, pairs
    )
    manifest_path = output_dir / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            manifest(
                book_id,
                results,
                transient_count,
                len(expected_edge_ids),
            ),
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    neutral = next(
        row for row in profile_rows if row["profile_id"] == "neutral_neutral_neutral"
    )
    print(f"Profiles: {len(profile_rows)}")
    print(f"Node metrics: {len(node_rows)}")
    print(f"Edge metrics: {len(edge_rows)}")
    print(f"Profile pairs: {len(pairs)}")
    print(
        "Neutral: "
        f"Win={float(neutral['win_probability']):.6f}; "
        f"entropy={float(neutral['trajectory_entropy_nats']):.6f} nats; "
        f"coverage={float(neutral['expected_coverage']):.6f}; "
        f"replayability={float(neutral['replayability']):.6f}"
    )
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()
