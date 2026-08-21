"""Summarize phase-3 absorption results for all behavioral profiles."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_BOOK_ID = "LW01"
DEFAULT_PROFILES_PATH = Path("data/for_graph_model/behavioral_profiles.json")
PROFILE_FIELDS = ["profile_id", "risk", "morality", "action"]
PROFILE_SUMMARY_FIELDS = [
    *PROFILE_FIELDS,
    "death_probability",
    "win_probability",
    "expected_steps_to_absorption",
    "delta_win_vs_neutral",
    "delta_steps_vs_neutral",
]
AXIS_SUMMARY_FIELDS = [
    "axis",
    "level",
    "profile_count",
    "mean_death_probability",
    "mean_win_probability",
    "mean_expected_steps_to_absorption",
    "delta_win_vs_axis_neutral",
    "delta_steps_vs_axis_neutral",
]


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


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    """Write a deterministic UTF-8 summary CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_profiles(path: Path) -> list[dict[str, str]]:
    """Load and enforce the single behavioral-profile schema."""
    payload = read_json(path)
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"{path} must contain a non-empty JSON list")
    result = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict) or set(item) != set(PROFILE_FIELDS):
            raise ValueError(
                f"{path} profile {index} must contain exactly {PROFILE_FIELDS}"
            )
        result.append({field: str(item[field]) for field in PROFILE_FIELDS})
    return result


def profile_metrics(
    graph_root: Path, profile: dict[str, str]
) -> dict[str, str | float]:
    """Calculate absorption probabilities and expected duration for one W."""
    path = graph_root / profile["profile_id"] / "W.csv"
    fields, rows = read_csv(path)
    if not fields or fields[0] != "node_id":
        raise ValueError(f"Unexpected W header in {path}")
    node_ids = fields[1:]
    if [row["node_id"] for row in rows] != node_ids:
        raise ValueError(f"W row identifiers differ from its columns in {path}")
    if {"Death", "Win"} - set(node_ids):
        raise ValueError(f"W lacks Death or Win in {path}")

    matrix = np.array(
        [[float(row[target_id]) for target_id in node_ids] for row in rows],
        dtype=float,
    )
    if matrix.shape != (len(node_ids), len(node_ids)):
        raise ValueError(f"W is not square in {path}")
    if not np.isfinite(matrix).all():
        raise ValueError(f"W contains non-finite values in {path}")

    index = {node_id: position for position, node_id in enumerate(node_ids)}
    transient_ids = [
        node_id for node_id in node_ids if node_id not in {"Death", "Win"}
    ]
    transient_index = [index[node_id] for node_id in transient_ids]
    absorbing_index = [index["Death"], index["Win"]]
    q_matrix = matrix[np.ix_(transient_index, transient_index)]
    r_matrix = matrix[np.ix_(transient_index, absorbing_index)]
    system = np.eye(len(transient_ids)) - q_matrix
    absorption = np.linalg.solve(system, r_matrix)
    expected_steps = np.linalg.solve(system, np.ones(len(transient_ids)))
    start = transient_ids.index("1")
    death_probability, win_probability = absorption[start]

    if not math.isclose(
        float(death_probability + win_probability), 1.0, abs_tol=1e-9
    ):
        raise ValueError(f"Absorption probabilities do not sum to one in {path}")
    return {
        **profile,
        "death_probability": float(death_probability),
        "win_probability": float(win_probability),
        "expected_steps_to_absorption": float(expected_steps[start]),
    }


def formatted(value: float) -> str:
    """Format numeric results consistently without unnecessary zeroes."""
    return format(value, ".12g")


def build_profile_summary(
    metrics: list[dict[str, str | float]],
) -> list[dict[str, str]]:
    """Add deltas from the fully neutral reference profile."""
    neutral = next(
        row for row in metrics if row["profile_id"] == "neutral_neutral_neutral"
    )
    neutral_win = float(neutral["win_probability"])
    neutral_steps = float(neutral["expected_steps_to_absorption"])
    result = []
    for row in metrics:
        win = float(row["win_probability"])
        steps = float(row["expected_steps_to_absorption"])
        result.append(
            {
                **{field: str(row[field]) for field in PROFILE_FIELDS},
                "death_probability": formatted(float(row["death_probability"])),
                "win_probability": formatted(win),
                "expected_steps_to_absorption": formatted(steps),
                "delta_win_vs_neutral": formatted(win - neutral_win),
                "delta_steps_vs_neutral": formatted(steps - neutral_steps),
            }
        )
    return result


def build_axis_summary(
    metrics: list[dict[str, str | float]],
) -> list[dict[str, str]]:
    """Average results over the other two axes for each axis level."""
    levels = {
        "risk": ("cautious", "neutral", "reckless"),
        "morality": ("selfish", "neutral", "noble"),
        "action": ("physical", "neutral", "tactical"),
    }
    grouped: dict[tuple[str, str], list[dict[str, str | float]]] = defaultdict(list)
    for row in metrics:
        for axis in levels:
            grouped[(axis, str(row[axis]))].append(row)

    means: dict[tuple[str, str], tuple[float, float, float]] = {}
    for key, rows in grouped.items():
        count = len(rows)
        means[key] = (
            sum(float(row["death_probability"]) for row in rows) / count,
            sum(float(row["win_probability"]) for row in rows) / count,
            sum(float(row["expected_steps_to_absorption"]) for row in rows) / count,
        )

    result = []
    for axis, ordered_levels in levels.items():
        _, neutral_win, neutral_steps = means[(axis, "neutral")]
        for level in ordered_levels:
            death, win, steps = means[(axis, level)]
            result.append(
                {
                    "axis": axis,
                    "level": level,
                    "profile_count": str(len(grouped[(axis, level)])),
                    "mean_death_probability": formatted(death),
                    "mean_win_probability": formatted(win),
                    "mean_expected_steps_to_absorption": formatted(steps),
                    "delta_win_vs_axis_neutral": formatted(win - neutral_win),
                    "delta_steps_vs_axis_neutral": formatted(steps - neutral_steps),
                }
            )
    return result


def main() -> None:
    """Generate profile-level, axis-level and compact JSON summaries."""
    parser = argparse.ArgumentParser(description="Summarize all phase-3 profiles.")
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES_PATH)
    parser.add_argument(
        "--graph-root",
        type=Path,
        help="Defaults to data/processed/graph/<book>.",
    )
    args = parser.parse_args()

    book_id = str(args.book)
    graph_root = args.graph_root or Path("data/processed/graph") / book_id
    profiles = load_profiles(Path(args.profiles))
    metrics = [profile_metrics(graph_root, profile) for profile in profiles]
    profile_summary = build_profile_summary(metrics)
    axis_summary = build_axis_summary(metrics)

    write_csv(
        graph_root / "profile_summary.csv", PROFILE_SUMMARY_FIELDS, profile_summary
    )
    write_csv(graph_root / "axis_summary.csv", AXIS_SUMMARY_FIELDS, axis_summary)

    neutral = next(
        row for row in metrics if row["profile_id"] == "neutral_neutral_neutral"
    )
    minimum = min(metrics, key=lambda row: float(row["win_probability"]))
    maximum = max(metrics, key=lambda row: float(row["win_probability"]))
    manifest = {
        "book_id": book_id,
        "profile_count": len(metrics),
        "neutral": {
            "profile_id": neutral["profile_id"],
            "win_probability": neutral["win_probability"],
            "death_probability": neutral["death_probability"],
            "expected_steps_to_absorption": neutral["expected_steps_to_absorption"],
        },
        "minimum_win_probability": {
            "profile_id": minimum["profile_id"],
            "value": minimum["win_probability"],
        },
        "maximum_win_probability": {
            "profile_id": maximum["profile_id"],
            "value": maximum["win_probability"],
        },
        "win_probability_range": float(maximum["win_probability"])
        - float(minimum["win_probability"]),
    }
    (graph_root / "profile_summary.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Summarized {len(metrics)} profiles for {book_id}")
    print(
        f"Neutral: Win={float(neutral['win_probability']):.6f}, "
        f"steps={float(neutral['expected_steps_to_absorption']):.3f}"
    )
    print(
        "Win range: "
        f"{minimum['profile_id']}={float(minimum['win_probability']):.6f} to "
        f"{maximum['profile_id']}={float(maximum['win_probability']):.6f}"
    )
    print(f"Outputs: {graph_root / 'profile_summary.csv'}")
    print(f"         {graph_root / 'axis_summary.csv'}")
    print(f"         {graph_root / 'profile_summary.json'}")


if __name__ == "__main__":
    main()
