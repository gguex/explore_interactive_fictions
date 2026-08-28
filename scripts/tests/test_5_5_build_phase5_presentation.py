"""Validate the two slide-ready phase-5 result figures."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

FIGURES = {
    "01_individual_trajectories": "player profiles leave uneven traces",
    "02_trajectory_comparisons": "profile contrasts are visible",
}
EXPECTED_KEYS = {
    ("profile_manifestation", "risk"): ("9", "14", "9/14 (64%)"),
    ("profile_manifestation", "morality"): ("6", "14", "6/14 (43%)"),
    ("profile_manifestation", "action"): ("2", "14", "2/14 (14%)"),
    ("controlled_contrast_recovery", "all"): ("5", "6", "5/6 (83%)"),
    ("ab_ba_order_stability", "all_pairwise_labels"): (
        "18",
        "24",
        "18/24 (75%)",
    ),
    ("cross_axis_leakage", "non_controlled_axes"): ("9", "9", "9/9 (100%)"),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read one UTF-8 CSV table."""
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict[str, Any]:
    """Read one JSON object."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected object in {path}")
    return value


def sha256(path: Path) -> str:
    """Return one artifact digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def png_dimensions(path: Path) -> tuple[int, int]:
    """Read dimensions from a PNG IHDR block."""
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Invalid PNG: {path}")
    return struct.unpack(">II", header[16:24])


def parse_args() -> argparse.Namespace:
    """Parse validator arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", default="LW01")
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args()


def main() -> None:
    """Validate slide dimensions, displayed results, plan and provenance."""
    args = parse_args()
    book = str(args.book)
    input_dir = args.input_dir or Path("data/processed/phase5") / book
    output_dir = args.output_dir or Path("results/phase5") / book / "presentation"
    trajectories = read_csv(input_dir / "trajectory_results.csv")
    pairs = read_csv(input_dir / "pairwise_results.csv")
    if len(trajectories) != 14 or len(pairs) != 6:
        raise ValueError("Source result populations differ")

    artifacts: list[Path] = []
    for figure, title_fragment in FIGURES.items():
        png_path = output_dir / f"{figure}.png"
        svg_path = output_dir / f"{figure}.svg"
        for path in (png_path, svg_path):
            if not path.is_file() or path.stat().st_size < 10_000:
                raise ValueError(f"Missing or implausibly small figure: {path}")
            artifacts.append(path)
        if png_dimensions(png_path) != (1920, 1080):
            raise ValueError(f"Wrong PNG dimensions: {png_path}")
        svg = svg_path.read_text(encoding="utf-8")
        if "<svg" not in svg or book not in svg or title_fragment not in svg:
            raise ValueError(f"SVG title or identity differs: {svg_path}")

    key_path = output_dir / "key_results.csv"
    key_rows = read_csv(key_path)
    artifacts.append(key_path)
    indexed = {(row["metric"], row["subgroup"]): row for row in key_rows}
    if set(indexed) != set(EXPECTED_KEYS):
        raise ValueError("Key-result selection differs")
    for key, expected in EXPECTED_KEYS.items():
        row = indexed[key]
        actual = (row["numerator"], row["denominator"], row["display"])
        if actual != expected:
            raise ValueError(f"Displayed key result differs: {key}")

    action_by_level = {
        level: [row for row in trajectories if row["expected_action"] == level]
        for level in ("neutral", "physical", "tactical")
    }
    expected_action_matches = {"neutral": 0, "physical": 0, "tactical": 2}
    for level, expected_matches in expected_action_matches.items():
        matches = sum(row["action_status"] == "match" for row in action_by_level[level])
        if matches != expected_matches:
            raise ValueError(f"Action diagnostic differs: {level}")
    if sum(row["causal_continuity"] == "continuous" for row in trajectories) != 14:
        raise ValueError("Continuity card differs")
    if sum(row["profile_coherence"] == "coherent" for row in trajectories) != 9:
        raise ValueError("Coherence card differs")
    if [row["controlled_axis_result"] for row in pairs].count("recovered") != 5:
        raise ValueError("Pairwise controlled-result table differs")

    manifest = read_json(output_dir / "presentation_manifest.json")
    if (
        manifest.get("status") != "complete"
        or manifest.get("book_id") != book
        or manifest.get("language") != "English"
        or manifest.get("slide_size_pixels") != [1920, 1080]
    ):
        raise ValueError("Presentation manifest identity differs")
    deck_plan = manifest.get("deck_plan")
    if not isinstance(deck_plan, list) or len(deck_plan) != 3:
        raise ValueError("Deck plan differs")
    if deck_plan[0].get("status") != "to be produced later":
        raise ValueError("Procedure/calibration slides are not marked as pending")
    if [row.get("figure") for row in deck_plan[1:]] != list(FIGURES):
        raise ValueError("Produced slide order differs")

    described = manifest.get("artifacts")
    if not isinstance(described, dict) or set(described) != {
        path.name for path in artifacts
    }:
        raise ValueError("Manifest artifact coverage differs")
    for path in artifacts:
        metadata = described[path.name]
        if metadata.get("bytes") != path.stat().st_size or metadata.get(
            "sha256"
        ) != sha256(path):
            raise ValueError(f"Manifest artifact metadata differs: {path.name}")
    print(
        "OK: phase 5.5 presentation package — two English 1920x1080 result "
        "slides and six checked key results"
    )


if __name__ == "__main__":
    main()
