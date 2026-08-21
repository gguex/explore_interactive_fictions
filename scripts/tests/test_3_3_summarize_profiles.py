"""Validate the aggregate summaries produced from all phase-3 profiles."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

DEFAULT_BOOK_ID = "LW01"
DEFAULT_PROFILES_PATH = Path("data/for_graph_model/behavioral_profiles.json")


def read_csv(path: Path) -> list[dict[str, str]]:
    """Load one required CSV summary."""
    if not path.exists():
        raise FileNotFoundError(f"Missing summary; run phase 3.3 first: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def main() -> None:
    """Check profile coverage, complements, deltas, aggregates and extrema."""
    parser = argparse.ArgumentParser(description="Validate phase-3 summaries.")
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES_PATH)
    args = parser.parse_args()

    book_id = str(args.book)
    graph_root = Path("data/processed/graph") / book_id
    configured = json.loads(Path(args.profiles).read_text(encoding="utf-8"))
    configured_ids = [str(row["profile_id"]) for row in configured]
    profiles = read_csv(graph_root / "profile_summary.csv")
    axes = read_csv(graph_root / "axis_summary.csv")
    manifest = json.loads(
        (graph_root / "profile_summary.json").read_text(encoding="utf-8")
    )

    if [row["profile_id"] for row in profiles] != configured_ids:
        raise ValueError("Profile summary differs from the configured design")
    if len(profiles) != 27 or len(axes) != 9:
        raise ValueError("Expected 27 profile rows and 9 axis rows")

    for row in profiles:
        death = float(row["death_probability"])
        win = float(row["win_probability"])
        steps = float(row["expected_steps_to_absorption"])
        if not math.isclose(death + win, 1.0, abs_tol=1e-10):
            raise ValueError(f"Probabilities do not sum to one for {row['profile_id']}")
        if not 0 <= win <= 1 or not math.isfinite(steps) or steps <= 0:
            raise ValueError(f"Invalid summary values for {row['profile_id']}")

    neutral = next(
        row for row in profiles if row["profile_id"] == "neutral_neutral_neutral"
    )
    if not math.isclose(float(neutral["delta_win_vs_neutral"]), 0.0, abs_tol=1e-12):
        raise ValueError("Neutral win delta is not zero")
    if not math.isclose(
        float(neutral["delta_steps_vs_neutral"]), 0.0, abs_tol=1e-12
    ):
        raise ValueError("Neutral duration delta is not zero")

    for axis_row in axes:
        subset = [
            row for row in profiles if row[axis_row["axis"]] == axis_row["level"]
        ]
        if len(subset) != int(axis_row["profile_count"]):
            raise ValueError(
                f"Wrong group size for {axis_row['axis']}/{axis_row['level']}"
            )
        mean_win = sum(float(row["win_probability"]) for row in subset) / len(subset)
        mean_steps = sum(
            float(row["expected_steps_to_absorption"]) for row in subset
        ) / len(subset)
        if not math.isclose(
            mean_win, float(axis_row["mean_win_probability"]), abs_tol=1e-10
        ):
            raise ValueError(f"Wrong mean win value for {axis_row['axis']}")
        if not math.isclose(
            mean_steps,
            float(axis_row["mean_expected_steps_to_absorption"]),
            abs_tol=1e-10,
        ):
            raise ValueError(f"Wrong mean duration for {axis_row['axis']}")

    minimum = min(profiles, key=lambda row: float(row["win_probability"]))
    maximum = max(profiles, key=lambda row: float(row["win_probability"]))
    if manifest["minimum_win_probability"]["profile_id"] != minimum["profile_id"]:
        raise ValueError("Manifest minimum profile is wrong")
    if manifest["maximum_win_probability"]["profile_id"] != maximum["profile_id"]:
        raise ValueError("Manifest maximum profile is wrong")

    print(f"OK: {book_id} profile summaries")
    print(
        f"Profiles={len(profiles)}; axes={len(axes)}; "
        f"Win range={float(manifest['win_probability_range']):.6f}"
    )


if __name__ == "__main__":
    main()
