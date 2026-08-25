"""Independently validate the phase-4.2 presentation summaries."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_BOOK_ID = "LW01"
DEFAULT_PROFILES_PATH = Path("data/for_graph_model/behavioral_profiles.json")
NEUTRAL_PROFILE_ID = "neutral_neutral_neutral"
ATOL = 5e-9
GLOBAL_METRICS = [
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
AXIS_LEVELS = {
    "risk": ("cautious", "neutral", "reckless"),
    "morality": ("selfish", "neutral", "noble"),
    "action": ("physical", "neutral", "tactical"),
}
CONTROLLED_RISK_IDS = (
    "cautious_neutral_neutral",
    NEUTRAL_PROFILE_ID,
    "reckless_neutral_neutral",
)
EXPECTED_FIELDS = {
    "global_summary.csv": {
        "metric",
        "neutral_value",
        "balanced_mean",
        "balanced_std",
        "minimum_value",
        "minimum_profile",
        "maximum_value",
        "maximum_profile",
        "range",
    },
    "axis_summary.csv": {
        "axis",
        "level",
        "metric",
        "profile_count",
        "mean",
        "std",
        "minimum",
        "maximum",
        "delta_vs_axis_neutral",
    },
    "controlled_risk.csv": {
        "profile_id",
        "risk",
        "morality",
        "action",
        "metric",
        "value",
        "delta_vs_neutral",
    },
    "node_presentation_metrics.csv": {
        "node_id",
        "node_kind",
        "outcome",
        "is_combat",
        "is_player_choice",
        "neutral_expected_visits",
        "neutral_visit_probability",
        "balanced_mean_visit_probability",
        "visit_probability_range",
        "min_visit_profile",
        "max_visit_profile",
        "neutral_death_contribution",
        "balanced_mean_death_contribution",
        "neutral_win_potential",
        "neutral_local_entropy_nats",
        "neutral_entropy_contribution_nats",
        "neutral_choice_impact",
        "neutral_choice_win_range",
        "neutral_visit_probability_given_death",
        "neutral_visit_probability_given_win",
        "neutral_win_minus_death_visit_probability",
    },
    "edge_presentation_metrics.csv": {
        "edge_id",
        "source_id",
        "target_id",
        "transition_kind",
        "neutral_compiled_weight",
        "neutral_expected_flow",
        "balanced_mean_expected_flow",
        "expected_flow_range",
        "neutral_expected_flow_given_death",
        "neutral_expected_flow_given_win",
        "neutral_win_minus_death_expected_flow",
    },
    "node_rankings.csv": {"ranking", "rank", "node_id", "score", "value"},
}


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read one required CSV table."""
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact; run phase 4.2 first: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header: {path}")
        return list(reader.fieldnames), [dict(row) for row in reader]


def close(actual: float, expected: float, label: str) -> None:
    """Require agreement within phase-4 serialization precision."""
    if not math.isfinite(actual) or not math.isfinite(expected):
        raise ValueError(f"Non-finite value for {label}")
    if not math.isclose(actual, expected, rel_tol=ATOL, abs_tol=ATOL):
        raise ValueError(f"{label}: got {actual:.12g}, expected {expected:.12g}")


def values(rows: list[dict[str, str]], field: str) -> np.ndarray[Any, Any]:
    """Extract one numeric column."""
    return np.array([float(row[field]) for row in rows], dtype=float)


def group_rows(
    rows: list[dict[str, str]], profile_ids: list[str], entity_field: str
) -> tuple[list[str], dict[str, list[dict[str, str]]]]:
    """Rebuild local groups in configured profile order."""
    entity_ids = []
    seen: set[str] = set()
    indexed = {}
    for row in rows:
        entity_id = row[entity_field]
        key = (row["profile_id"], entity_id)
        if key in indexed:
            raise ValueError(f"Duplicate local metric pair: {key}")
        indexed[key] = row
        if entity_id not in seen:
            seen.add(entity_id)
            entity_ids.append(entity_id)
    grouped = {}
    for entity_id in entity_ids:
        try:
            grouped[entity_id] = [
                indexed[(profile_id, entity_id)] for profile_id in profile_ids
            ]
        except KeyError as error:
            raise ValueError(f"Incomplete profile coverage for {entity_id}") from error
    return entity_ids, grouped


def validate_global(
    profiles: list[dict[str, str]], summary: list[dict[str, str]]
) -> None:
    """Recalculate balanced summaries and observed extrema."""
    if [row["metric"] for row in summary] != GLOBAL_METRICS:
        raise ValueError("Global metric order or coverage differs")
    neutral = next(
        row for row in profiles if row["profile_id"] == NEUTRAL_PROFILE_ID
    )
    for row in summary:
        metric = row["metric"]
        data = values(profiles, metric)
        minimum = int(np.argmin(data))
        maximum = int(np.argmax(data))
        expectations = {
            "neutral_value": float(neutral[metric]),
            "balanced_mean": float(data.mean()),
            "balanced_std": float(data.std()),
            "minimum_value": float(data[minimum]),
            "maximum_value": float(data[maximum]),
            "range": float(data[maximum] - data[minimum]),
        }
        for field, expected in expectations.items():
            close(float(row[field]), expected, f"global/{metric}/{field}")
        if row["minimum_profile"] != profiles[minimum]["profile_id"]:
            raise ValueError(f"Wrong minimum profile for {metric}")
        if row["maximum_profile"] != profiles[maximum]["profile_id"]:
            raise ValueError(f"Wrong maximum profile for {metric}")


def validate_axes(
    profiles: list[dict[str, str]], summary: list[dict[str, str]]
) -> None:
    """Recalculate all 135 marginal axis summaries."""
    expected_keys = [
        (axis, level, metric)
        for axis, levels in AXIS_LEVELS.items()
        for level, metric in product(levels, GLOBAL_METRICS)
    ]
    actual_keys = [(row["axis"], row["level"], row["metric"]) for row in summary]
    if actual_keys != expected_keys:
        raise ValueError("Axis-summary order or coverage differs")
    neutral_means = {}
    for axis in AXIS_LEVELS:
        subset = [row for row in profiles if row[axis] == "neutral"]
        for metric in GLOBAL_METRICS:
            neutral_means[(axis, metric)] = float(values(subset, metric).mean())
    for row in summary:
        axis = row["axis"]
        level = row["level"]
        metric = row["metric"]
        subset = [source for source in profiles if source[axis] == level]
        data = values(subset, metric)
        if int(row["profile_count"]) != len(subset):
            raise ValueError(f"Wrong profile count for {axis}/{level}/{metric}")
        expectations = {
            "mean": float(data.mean()),
            "std": float(data.std()),
            "minimum": float(data.min()),
            "maximum": float(data.max()),
            "delta_vs_axis_neutral": float(data.mean())
            - neutral_means[(axis, metric)],
        }
        for field, expected in expectations.items():
            close(float(row[field]), expected, f"axis/{axis}/{level}/{metric}/{field}")


def validate_controlled_risk(
    profiles: list[dict[str, str]], summary: list[dict[str, str]]
) -> None:
    """Check the three-profile, one-axis controlled comparison."""
    by_profile = {row["profile_id"]: row for row in profiles}
    neutral = by_profile[NEUTRAL_PROFILE_ID]
    expected_keys = list(product(CONTROLLED_RISK_IDS, GLOBAL_METRICS))
    actual_keys = [(row["profile_id"], row["metric"]) for row in summary]
    if actual_keys != expected_keys:
        raise ValueError("Controlled-risk order or coverage differs")
    for row in summary:
        source = by_profile[row["profile_id"]]
        metric = row["metric"]
        value = float(source[metric])
        close(float(row["value"]), value, "controlled value")
        close(
            float(row["delta_vs_neutral"]),
            value - float(neutral[metric]),
            "controlled delta",
        )
        for field in ("risk", "morality", "action"):
            if row[field] != source[field]:
                raise ValueError(f"Controlled profile metadata differs for {field}")


def validate_nodes(
    node_ids: list[str],
    grouped: dict[str, list[dict[str, str]]],
    profile_ids: list[str],
    summary: list[dict[str, str]],
) -> None:
    """Recalculate every graph-ready node aggregation and outcome contrast."""
    if [row["node_id"] for row in summary] != node_ids:
        raise ValueError("Node-presentation order or coverage differs")
    neutral_position = profile_ids.index(NEUTRAL_PROFILE_ID)
    for produced in summary:
        rows = grouped[produced["node_id"]]
        neutral = rows[neutral_position]
        visits = values(rows, "visit_probability")
        mortality = values(rows, "death_contribution")
        exact_fields = {
            "node_kind": "node_kind",
            "outcome": "outcome",
            "is_combat": "is_combat",
            "is_player_choice": "is_player_choice",
            "neutral_expected_visits": "expected_visits",
            "neutral_visit_probability": "visit_probability",
            "neutral_death_contribution": "death_contribution",
            "neutral_win_potential": "win_potential",
            "neutral_local_entropy_nats": "local_entropy_nats",
            "neutral_entropy_contribution_nats": "entropy_contribution_nats",
            "neutral_choice_impact": "choice_impact",
            "neutral_choice_win_range": "choice_win_range",
            "neutral_visit_probability_given_death": (
                "visit_probability_given_death"
            ),
            "neutral_visit_probability_given_win": "visit_probability_given_win",
        }
        for output_field, source_field in exact_fields.items():
            if output_field.startswith(("node_", "outcome", "is_")):
                if produced[output_field] != neutral[source_field]:
                    raise ValueError(
                        f"Node metadata differs at {produced['node_id']}/{output_field}"
                    )
            else:
                close(
                    float(produced[output_field]),
                    float(neutral[source_field]),
                    f"node/{produced['node_id']}/{output_field}",
                )
        numerical = {
            "balanced_mean_visit_probability": float(visits.mean()),
            "visit_probability_range": float(visits.max() - visits.min()),
            "balanced_mean_death_contribution": float(mortality.mean()),
            "neutral_win_minus_death_visit_probability": float(
                neutral["visit_probability_given_win"]
            )
            - float(neutral["visit_probability_given_death"]),
        }
        for field, expected in numerical.items():
            close(
                float(produced[field]),
                expected,
                f"node/{produced['node_id']}/{field}",
            )
        if produced["min_visit_profile"] != rows[int(np.argmin(visits))]["profile_id"]:
            raise ValueError(f"Wrong minimum visit profile at {produced['node_id']}")
        if produced["max_visit_profile"] != rows[int(np.argmax(visits))]["profile_id"]:
            raise ValueError(f"Wrong maximum visit profile at {produced['node_id']}")


def validate_edges(
    edge_ids: list[str],
    grouped: dict[str, list[dict[str, str]]],
    profile_ids: list[str],
    summary: list[dict[str, str]],
) -> None:
    """Recalculate every graph-ready edge aggregation and outcome contrast."""
    if [row["edge_id"] for row in summary] != edge_ids:
        raise ValueError("Edge-presentation order or coverage differs")
    neutral_position = profile_ids.index(NEUTRAL_PROFILE_ID)
    for produced in summary:
        rows = grouped[produced["edge_id"]]
        neutral = rows[neutral_position]
        flows = values(rows, "expected_flow")
        for field in ("source_id", "target_id", "transition_kind"):
            if produced[field] != neutral[field]:
                raise ValueError(f"Edge metadata differs at {produced['edge_id']}")
        exact_numeric = {
            "neutral_compiled_weight": "compiled_weight",
            "neutral_expected_flow": "expected_flow",
            "neutral_expected_flow_given_death": "expected_flow_given_death",
            "neutral_expected_flow_given_win": "expected_flow_given_win",
        }
        for output_field, source_field in exact_numeric.items():
            close(
                float(produced[output_field]),
                float(neutral[source_field]),
                f"edge/{produced['edge_id']}/{output_field}",
            )
        expectations = {
            "balanced_mean_expected_flow": float(flows.mean()),
            "expected_flow_range": float(flows.max() - flows.min()),
            "neutral_win_minus_death_expected_flow": float(
                neutral["expected_flow_given_win"]
            )
            - float(neutral["expected_flow_given_death"]),
        }
        for field, expected in expectations.items():
            close(
                float(produced[field]),
                expected,
                f"edge/{produced['edge_id']}/{field}",
            )


def node_key(node_id: str) -> tuple[int, int | str]:
    """Return the expected natural paragraph ordering key."""
    return (0, int(node_id)) if node_id.isdigit() else (1, node_id)


def validate_rankings(
    nodes: list[dict[str, str]], rankings: list[dict[str, str]], top_n: int
) -> None:
    """Rebuild the six deterministic top-node lists."""
    specifications = [
        ("neutral_visit_probability", "neutral_visit_probability", False, False),
        (
            "balanced_visit_probability",
            "balanced_mean_visit_probability",
            False,
            False,
        ),
        ("profile_sensitivity", "visit_probability_range", False, False),
        (
            "neutral_death_contribution",
            "neutral_death_contribution",
            False,
            False,
        ),
        ("neutral_choice_impact", "neutral_choice_impact", True, False),
        (
            "neutral_outcome_visit_contrast",
            "neutral_win_minus_death_visit_probability",
            False,
            True,
        ),
    ]
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rankings:
        grouped[row["ranking"]].append(row)
    if list(grouped) != [item[0] for item in specifications]:
        raise ValueError("Node-ranking categories or order differ")
    for ranking, field, choices_only, absolute in specifications:
        candidates = [
            row
            for row in nodes
            if not choices_only or row["is_player_choice"] == "true"
        ]
        expected = sorted(
            candidates,
            key=lambda row: (
                -abs(float(row[field])) if absolute else -float(row[field]),
                node_key(row["node_id"]),
            ),
        )[:top_n]
        actual = grouped[ranking]
        if len(actual) != min(top_n, len(candidates)):
            raise ValueError(f"Wrong ranking length for {ranking}")
        paired = zip(actual, expected, strict=True)
        for rank, (produced, source) in enumerate(paired, 1):
            value = float(source[field])
            wrong_rank = int(produced["rank"]) != rank
            wrong_node = produced["node_id"] != source["node_id"]
            if wrong_rank or wrong_node:
                raise ValueError(f"Wrong order in ranking {ranking}")
            close(float(produced["value"]), value, f"ranking/{ranking}/value")
            close(
                float(produced["score"]),
                abs(value) if absolute else value,
                f"ranking/{ranking}/score",
            )


def main() -> None:
    """Validate every phase-4.2 aggregation against canonical phase-4.1 rows."""
    parser = argparse.ArgumentParser(description="Validate phase-4.2 BoP summaries.")
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES_PATH)
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--summary-dir", type=Path)
    args = parser.parse_args()

    book_id = str(args.book)
    input_dir = args.input_dir or Path("data/processed/bop") / book_id
    summary_dir = args.summary_dir or input_dir / "presentation"
    configured = json.loads(args.profiles.read_text(encoding="utf-8"))
    if not isinstance(configured, list):
        raise ValueError("Profile design must be a list")
    profile_ids = [str(row["profile_id"]) for row in configured]
    _, profiles = read_csv(input_dir / "profile_metrics.csv")
    _, nodes = read_csv(input_dir / "node_metrics.csv")
    _, edges = read_csv(input_dir / "edge_metrics.csv")
    if [row["profile_id"] for row in profiles] != profile_ids:
        raise ValueError("Canonical profiles differ from configured design")
    node_ids, grouped_nodes = group_rows(nodes, profile_ids, "node_id")
    edge_ids, grouped_edges = group_rows(edges, profile_ids, "edge_id")

    loaded = {
        filename: read_csv(summary_dir / filename) for filename in EXPECTED_FIELDS
    }
    for filename, expected_fields in EXPECTED_FIELDS.items():
        if set(loaded[filename][0]) != expected_fields:
            raise ValueError(f"Unexpected summary schema: {filename}")
    global_summary = loaded["global_summary.csv"][1]
    axis_summary = loaded["axis_summary.csv"][1]
    controlled = loaded["controlled_risk.csv"][1]
    node_summary = loaded["node_presentation_metrics.csv"][1]
    edge_summary = loaded["edge_presentation_metrics.csv"][1]
    rankings = loaded["node_rankings.csv"][1]

    validate_global(profiles, global_summary)
    validate_axes(profiles, axis_summary)
    validate_controlled_risk(profiles, controlled)
    validate_nodes(node_ids, grouped_nodes, profile_ids, node_summary)
    validate_edges(edge_ids, grouped_edges, profile_ids, edge_summary)

    manifest_path = summary_dir / "summary.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    top_n = int(manifest["top_n"])
    validate_rankings(node_summary, rankings, top_n)
    expected_counts = {
        filename: len(rows) for filename, (_, rows) in loaded.items()
    }
    if manifest.get("book_id") != book_id:
        raise ValueError("Summary manifest book differs")
    if manifest.get("profile_count") != len(profiles):
        raise ValueError("Summary manifest profile count differs")
    if manifest.get("global_metrics") != GLOBAL_METRICS:
        raise ValueError("Summary manifest global metrics differ")
    if manifest.get("controlled_risk_profiles") != list(CONTROLLED_RISK_IDS):
        raise ValueError("Summary manifest controlled profiles differ")
    if manifest.get("outputs") != expected_counts:
        raise ValueError("Summary manifest output counts differ")
    for filename, (header, _) in loaded.items():
        if manifest.get("output_schemas", {}).get(filename) != header:
            raise ValueError(f"Summary manifest schema differs for {filename}")

    global_by_metric = {row["metric"]: row for row in global_summary}
    headline_expectations = {
        "neutral_win_probability": float(
            global_by_metric["win_probability"]["neutral_value"]
        ),
        "balanced_mean_win_probability": float(
            global_by_metric["win_probability"]["balanced_mean"]
        ),
        "neutral_trajectory_entropy_nats": float(
            global_by_metric["trajectory_entropy_nats"]["neutral_value"]
        ),
        "neutral_expected_coverage": float(
            global_by_metric["expected_coverage"]["neutral_value"]
        ),
        "neutral_replayability": float(
            global_by_metric["replayability"]["neutral_value"]
        ),
    }
    for field, expected in headline_expectations.items():
        close(float(manifest["headline"][field]), expected, f"headline/{field}")

    print(f"OK: {book_id} phase-4.2 presentation summaries")
    print(
        f"Global={len(global_summary)}; axes={len(axis_summary)}; "
        f"nodes={len(node_summary)}; edges={len(edge_summary)}; "
        f"rankings={len(rankings)}"
    )


if __name__ == "__main__":
    main()
