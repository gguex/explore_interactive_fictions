"""Extract presentation-ready summaries from canonical phase-4 BoP tables."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Callable

import numpy as np

DEFAULT_BOOK_ID = "LW01"
DEFAULT_PROFILES_PATH = Path("data/for_graph_model/behavioral_profiles.json")
NEUTRAL_PROFILE_ID = "neutral_neutral_neutral"
PROFILE_FIELDS = ["profile_id", "risk", "morality", "action"]
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
GLOBAL_SUMMARY_FIELDS = [
    "metric",
    "neutral_value",
    "balanced_mean",
    "balanced_std",
    "minimum_value",
    "minimum_profile",
    "maximum_value",
    "maximum_profile",
    "range",
]
AXIS_SUMMARY_FIELDS = [
    "axis",
    "level",
    "metric",
    "profile_count",
    "mean",
    "std",
    "minimum",
    "maximum",
    "delta_vs_axis_neutral",
]
CONTROLLED_RISK_FIELDS = [
    *PROFILE_FIELDS,
    "metric",
    "value",
    "delta_vs_neutral",
]
NODE_PRESENTATION_FIELDS = [
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
]
EDGE_PRESENTATION_FIELDS = [
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
]
NODE_RANKING_FIELDS = ["ranking", "rank", "node_id", "score", "value"]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read one required CSV table."""
    if not path.exists():
        raise FileNotFoundError(f"Missing input; run phase 4.1 first: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header: {path}")
        return list(reader.fieldnames), [dict(row) for row in reader]


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    """Write one deterministic UTF-8 CSV table."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def formatted(value: float) -> str:
    """Serialize one finite float consistently."""
    if not math.isfinite(value):
        raise ValueError(f"Cannot serialize a non-finite value: {value}")
    if abs(value) < 5e-16:
        value = 0.0
    return format(value, ".12g")


def load_profiles(path: Path) -> list[dict[str, str]]:
    """Load the fixed profile design in canonical order."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"{path} must contain a non-empty list")
    profiles = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict) or set(item) != set(PROFILE_FIELDS):
            raise ValueError(f"Invalid profile schema at index {index} in {path}")
        profiles.append({field: str(item[field]) for field in PROFILE_FIELDS})
    profile_ids = [profile["profile_id"] for profile in profiles]
    if len(profile_ids) != len(set(profile_ids)):
        raise ValueError(f"Duplicate profile identifiers in {path}")
    if NEUTRAL_PROFILE_ID not in profile_ids:
        raise ValueError(f"Missing neutral profile in {path}")
    if set(CONTROLLED_RISK_IDS) - set(profile_ids):
        raise ValueError(f"Missing controlled risk profiles in {path}")
    return profiles


def validate_input_schema(
    input_dir: Path, filename: str, header: list[str], manifest: dict[str, Any]
) -> None:
    """Require the exact phase-4.1 schema declared in its manifest."""
    schemas = manifest.get("output_schemas")
    if not isinstance(schemas, dict) or schemas.get(filename) != header:
        raise ValueError(f"Input schema differs from manifest for {filename}")
    if manifest.get("outputs", {}).get(filename) is None:
        raise ValueError(f"Input manifest omits {filename} in {input_dir}")


def group_in_profile_order(
    rows: list[dict[str, str]],
    profile_ids: list[str],
    key: str,
) -> dict[str, list[dict[str, str]]]:
    """Group local rows and preserve configured profile order within each entity."""
    indexed = {(row["profile_id"], row[key]): row for row in rows}
    entity_order = []
    seen: set[str] = set()
    for row in rows:
        entity = row[key]
        if entity not in seen:
            seen.add(entity)
            entity_order.append(entity)
    grouped = {}
    for entity in entity_order:
        try:
            grouped[entity] = [
                indexed[(profile_id, entity)] for profile_id in profile_ids
            ]
        except KeyError as error:
            raise ValueError(
                f"Incomplete profile coverage for {key}={entity}"
            ) from error
    if len(indexed) != len(rows):
        raise ValueError(f"Duplicate profile/entity pairs in {key} table")
    return grouped


def build_global_summary(
    profile_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Summarize each global metric over the balanced factorial design."""
    neutral = next(
        row for row in profile_rows if row["profile_id"] == NEUTRAL_PROFILE_ID
    )
    output = []
    for metric in GLOBAL_METRICS:
        data = np.array([float(row[metric]) for row in profile_rows], dtype=float)
        minimum = int(np.argmin(data))
        maximum = int(np.argmax(data))
        output.append(
            {
                "metric": metric,
                "neutral_value": formatted(float(neutral[metric])),
                "balanced_mean": formatted(float(data.mean())),
                "balanced_std": formatted(float(data.std())),
                "minimum_value": formatted(float(data[minimum])),
                "minimum_profile": profile_rows[minimum]["profile_id"],
                "maximum_value": formatted(float(data[maximum])),
                "maximum_profile": profile_rows[maximum]["profile_id"],
                "range": formatted(float(data[maximum] - data[minimum])),
            }
        )
    return output


def build_axis_summary(
    profile_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Calculate marginal summaries after averaging over both other axes."""
    output = []
    for axis, levels in AXIS_LEVELS.items():
        subsets = {
            level: [row for row in profile_rows if row[axis] == level]
            for level in levels
        }
        if any(len(rows) == 0 for rows in subsets.values()):
            raise ValueError(f"Incomplete levels for profile axis {axis}")
        neutral_means = {
            metric: float(
                np.mean([float(row[metric]) for row in subsets["neutral"]])
            )
            for metric in GLOBAL_METRICS
        }
        for level in levels:
            subset = subsets[level]
            for metric in GLOBAL_METRICS:
                data = np.array([float(row[metric]) for row in subset], dtype=float)
                mean = float(data.mean())
                output.append(
                    {
                        "axis": axis,
                        "level": level,
                        "metric": metric,
                        "profile_count": str(len(subset)),
                        "mean": formatted(mean),
                        "std": formatted(float(data.std())),
                        "minimum": formatted(float(data.min())),
                        "maximum": formatted(float(data.max())),
                        "delta_vs_axis_neutral": formatted(
                            mean - neutral_means[metric]
                        ),
                    }
                )
    return output


def build_controlled_risk(
    profile_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Extract the three profiles that vary only along the risk axis."""
    by_profile = {row["profile_id"]: row for row in profile_rows}
    neutral = by_profile[NEUTRAL_PROFILE_ID]
    output = []
    for profile_id in CONTROLLED_RISK_IDS:
        row = by_profile[profile_id]
        for metric in GLOBAL_METRICS:
            value = float(row[metric])
            output.append(
                {
                    **{field: row[field] for field in PROFILE_FIELDS},
                    "metric": metric,
                    "value": formatted(value),
                    "delta_vs_neutral": formatted(value - float(neutral[metric])),
                }
            )
    return output


def build_node_presentation(
    grouped: dict[str, list[dict[str, str]]],
    profile_ids: list[str],
) -> list[dict[str, str]]:
    """Create one graph-ready row per node with neutral and balanced values."""
    neutral_position = profile_ids.index(NEUTRAL_PROFILE_ID)
    output = []
    for node_id, rows in grouped.items():
        neutral = rows[neutral_position]
        visits = np.array([float(row["visit_probability"]) for row in rows])
        mortality = np.array([float(row["death_contribution"]) for row in rows])
        win_visit = float(neutral["visit_probability_given_win"])
        death_visit = float(neutral["visit_probability_given_death"])
        output.append(
            {
                "node_id": node_id,
                "node_kind": neutral["node_kind"],
                "outcome": neutral["outcome"],
                "is_combat": neutral["is_combat"],
                "is_player_choice": neutral["is_player_choice"],
                "neutral_expected_visits": neutral["expected_visits"],
                "neutral_visit_probability": neutral["visit_probability"],
                "balanced_mean_visit_probability": formatted(float(visits.mean())),
                "visit_probability_range": formatted(
                    float(visits.max() - visits.min())
                ),
                "min_visit_profile": rows[int(np.argmin(visits))]["profile_id"],
                "max_visit_profile": rows[int(np.argmax(visits))]["profile_id"],
                "neutral_death_contribution": neutral["death_contribution"],
                "balanced_mean_death_contribution": formatted(
                    float(mortality.mean())
                ),
                "neutral_win_potential": neutral["win_potential"],
                "neutral_local_entropy_nats": neutral["local_entropy_nats"],
                "neutral_entropy_contribution_nats": neutral[
                    "entropy_contribution_nats"
                ],
                "neutral_choice_impact": neutral["choice_impact"],
                "neutral_choice_win_range": neutral["choice_win_range"],
                "neutral_visit_probability_given_death": neutral[
                    "visit_probability_given_death"
                ],
                "neutral_visit_probability_given_win": neutral[
                    "visit_probability_given_win"
                ],
                "neutral_win_minus_death_visit_probability": formatted(
                    win_visit - death_visit
                ),
            }
        )
    return output


def build_edge_presentation(
    grouped: dict[str, list[dict[str, str]]],
    profile_ids: list[str],
) -> list[dict[str, str]]:
    """Create one graph-ready row per edge with neutral and balanced flows."""
    neutral_position = profile_ids.index(NEUTRAL_PROFILE_ID)
    output = []
    for edge_id, rows in grouped.items():
        neutral = rows[neutral_position]
        flows = np.array([float(row["expected_flow"]) for row in rows])
        win_flow = float(neutral["expected_flow_given_win"])
        death_flow = float(neutral["expected_flow_given_death"])
        output.append(
            {
                "edge_id": edge_id,
                "source_id": neutral["source_id"],
                "target_id": neutral["target_id"],
                "transition_kind": neutral["transition_kind"],
                "neutral_compiled_weight": neutral["compiled_weight"],
                "neutral_expected_flow": neutral["expected_flow"],
                "balanced_mean_expected_flow": formatted(float(flows.mean())),
                "expected_flow_range": formatted(float(flows.max() - flows.min())),
                "neutral_expected_flow_given_death": neutral[
                    "expected_flow_given_death"
                ],
                "neutral_expected_flow_given_win": neutral[
                    "expected_flow_given_win"
                ],
                "neutral_win_minus_death_expected_flow": formatted(
                    win_flow - death_flow
                ),
            }
        )
    return output


def node_sort_key(row: dict[str, str]) -> tuple[int, int | str]:
    """Sort numbered paragraphs naturally before any symbolic identifiers."""
    node_id = row["node_id"]
    return (0, int(node_id)) if node_id.isdigit() else (1, node_id)


def build_node_rankings(
    node_rows: list[dict[str, str]], top_n: int
) -> list[dict[str, str]]:
    """Select the local highlights explicitly retained for the presentation."""
    specifications: list[
        tuple[str, str, Callable[[dict[str, str]], bool], bool]
    ] = [
        (
            "neutral_visit_probability",
            "neutral_visit_probability",
            lambda row: True,
            False,
        ),
        (
            "balanced_visit_probability",
            "balanced_mean_visit_probability",
            lambda row: True,
            False,
        ),
        ("profile_sensitivity", "visit_probability_range", lambda row: True, False),
        (
            "neutral_death_contribution",
            "neutral_death_contribution",
            lambda row: True,
            False,
        ),
        (
            "neutral_choice_impact",
            "neutral_choice_impact",
            lambda row: row["is_player_choice"] == "true",
            False,
        ),
        (
            "neutral_outcome_visit_contrast",
            "neutral_win_minus_death_visit_probability",
            lambda row: True,
            True,
        ),
    ]
    output = []
    for ranking, field, predicate, absolute in specifications:
        candidates = [row for row in node_rows if predicate(row)]
        ordered = sorted(
            candidates,
            key=lambda row: (
                -abs(float(row[field])) if absolute else -float(row[field]),
                node_sort_key(row),
            ),
        )[:top_n]
        for rank, row in enumerate(ordered, start=1):
            value = float(row[field])
            output.append(
                {
                    "ranking": ranking,
                    "rank": str(rank),
                    "node_id": row["node_id"],
                    "score": formatted(abs(value) if absolute else value),
                    "value": formatted(value),
                }
            )
    return output


def main() -> None:
    """Write the presentation extraction without recalculating BoP indices."""
    parser = argparse.ArgumentParser(
        description="Summarize canonical BoP indices for analysis and presentation."
    )
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES_PATH)
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--top-n", type=int, default=10)
    args = parser.parse_args()
    if args.top_n <= 0:
        raise ValueError("--top-n must be positive")

    book_id = str(args.book)
    input_dir = args.input_dir or Path("data/processed/bop") / book_id
    output_dir = args.output_dir or input_dir / "presentation"
    profiles = load_profiles(args.profiles)
    profile_ids = [profile["profile_id"] for profile in profiles]
    manifest_path = input_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("book_id") != book_id:
        raise ValueError(f"Input manifest does not describe {book_id}")

    profile_header, profile_rows = read_csv(input_dir / "profile_metrics.csv")
    node_header, node_rows = read_csv(input_dir / "node_metrics.csv")
    edge_header, edge_rows = read_csv(input_dir / "edge_metrics.csv")
    validate_input_schema(
        input_dir, "profile_metrics.csv", profile_header, manifest
    )
    validate_input_schema(input_dir, "node_metrics.csv", node_header, manifest)
    validate_input_schema(input_dir, "edge_metrics.csv", edge_header, manifest)
    if [row["profile_id"] for row in profile_rows] != profile_ids:
        raise ValueError("Profile metrics differ from the configured design")

    grouped_nodes = group_in_profile_order(node_rows, profile_ids, "node_id")
    grouped_edges = group_in_profile_order(edge_rows, profile_ids, "edge_id")
    global_summary = build_global_summary(profile_rows)
    axis_summary = build_axis_summary(profile_rows)
    controlled_risk = build_controlled_risk(profile_rows)
    node_presentation = build_node_presentation(grouped_nodes, profile_ids)
    edge_presentation = build_edge_presentation(grouped_edges, profile_ids)
    node_rankings = build_node_rankings(node_presentation, args.top_n)

    outputs = {
        "global_summary.csv": (GLOBAL_SUMMARY_FIELDS, global_summary),
        "axis_summary.csv": (AXIS_SUMMARY_FIELDS, axis_summary),
        "controlled_risk.csv": (CONTROLLED_RISK_FIELDS, controlled_risk),
        "node_presentation_metrics.csv": (
            NODE_PRESENTATION_FIELDS,
            node_presentation,
        ),
        "edge_presentation_metrics.csv": (
            EDGE_PRESENTATION_FIELDS,
            edge_presentation,
        ),
        "node_rankings.csv": (NODE_RANKING_FIELDS, node_rankings),
    }
    for filename, (fields, rows) in outputs.items():
        write_csv(output_dir / filename, fields, rows)

    global_by_metric = {row["metric"]: row for row in global_summary}
    summary = {
        "schema_version": "1.0",
        "book_id": book_id,
        "source": str(input_dir),
        "profile_count": len(profile_rows),
        "top_n": args.top_n,
        "controlled_risk_profiles": list(CONTROLLED_RISK_IDS),
        "global_metrics": GLOBAL_METRICS,
        "outputs": {filename: len(rows) for filename, (_, rows) in outputs.items()},
        "output_schemas": {
            filename: fields for filename, (fields, _) in outputs.items()
        },
        "headline": {
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
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"Summarized {len(profile_rows)} profiles for {book_id}")
    print(
        f"Global={len(global_summary)}; axes={len(axis_summary)}; "
        f"nodes={len(node_presentation)}; edges={len(edge_presentation)}"
    )
    print(
        "Neutral: "
        f"Win={summary['headline']['neutral_win_probability']:.6f}; "
        f"coverage={summary['headline']['neutral_expected_coverage']:.6f}; "
        f"replayability={summary['headline']['neutral_replayability']:.6f}"
    )
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()
