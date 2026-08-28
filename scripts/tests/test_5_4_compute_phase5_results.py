"""Independently validate the canonical phase-5.4 result tables."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

AXES = ("risk", "morality", "action")
OPPOSITES = {
    "A_more_cautious": "A_more_reckless",
    "A_more_reckless": "A_more_cautious",
    "A_more_selfish": "A_more_noble",
    "A_more_noble": "A_more_selfish",
    "A_more_physical": "A_more_tactical",
    "A_more_tactical": "A_more_physical",
    "similar": "similar",
    "unclear": "unclear",
}


def read_json(path: Path) -> dict[str, Any]:
    """Read one JSON object."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected object in {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read JSON Lines objects."""
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"Invalid JSON Lines file: {path}")
    return rows


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read one CSV table."""
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256_file(path: Path) -> str:
    """Return one file SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    """Parse validator arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", default="LW01")
    parser.add_argument("--run-id", default="LW01_phase5_final_v1")
    parser.add_argument("--phase5-dir", type=Path)
    parser.add_argument("--annotation-dir", type=Path)
    return parser.parse_args()


def main() -> None:
    """Recompute identities and the key preregistered classifications."""
    args = parse_args()
    book = str(args.book)
    run_id = str(args.run_id)
    phase5_dir = args.phase5_dir or Path("data/processed/phase5") / book
    annotation_dir = args.annotation_dir or phase5_dir / "annotations" / run_id
    manifest = read_json(phase5_dir / "phase5_manifest.json")
    if manifest.get("status") != "complete" or manifest.get("run_id") != run_id:
        raise ValueError("Phase-5.4 manifest identity or status differs")
    if manifest.get("scope") != (
        "descriptive analysis of conditional medoids; not model accuracy"
    ):
        raise ValueError("Interpretive scope differs")

    metadata_rows = read_jsonl(phase5_dir / "trajectory_private_metadata.jsonl")
    annotation_rows = read_jsonl(annotation_dir / "trajectory_annotations.jsonl")
    metadata = {str(row["trajectory_id"]): row for row in metadata_rows}
    annotations = {
        str(row["annotation"]["trajectory_id"]): row["annotation"]
        for row in annotation_rows
    }
    trajectory_results = read_csv(phase5_dir / "trajectory_results.csv")
    if len(metadata) != 14 or set(metadata) != set(annotations):
        raise ValueError("Final individual source population differs")
    if [row["trajectory_id"] for row in trajectory_results] != sorted(metadata):
        raise ValueError("Trajectory result identities or order differ")
    for row in trajectory_results:
        trajectory_id = row["trajectory_id"]
        for axis in AXES:
            expected = str(metadata[trajectory_id][axis])
            perceived = str(
                annotations[trajectory_id]["perceived_profile"][axis]["label"]
            )
            status = (
                "unclear"
                if perceived == "unclear"
                else ("match" if perceived == expected else "mismatch")
            )
            if (
                row[f"expected_{axis}"] != expected
                or row[f"perceived_{axis}"] != perceived
                or row[f"{axis}_status"] != status
            ):
                raise ValueError(
                    f"Trajectory classification differs: {trajectory_id}/{axis}"
                )

    pair_metadata_rows = read_jsonl(phase5_dir / "pair_private_metadata.jsonl")
    pair_metadata = {str(row["comparison_id"]): row for row in pair_metadata_rows}
    pair_annotations = {
        str(row["annotation"]["comparison_id"]): row["annotation"]
        for row in read_jsonl(annotation_dir / "pairwise_annotations.jsonl")
    }
    pair_results = read_csv(phase5_dir / "pairwise_results.csv")
    if len(pair_metadata) != 6 or len(pair_annotations) != 12:
        raise ValueError("Final pairwise source population differs")
    if [row["comparison_id"] for row in pair_results] != sorted(pair_metadata):
        raise ValueError("Pairwise result identities or order differ")
    for row in pair_results:
        base_id = row["comparison_id"]
        ab = pair_annotations[f"{base_id}_AB"]
        ba = pair_annotations[f"{base_id}_BA"]
        distinct_stable = (
            ab["narrative_distinctness"]["label"]
            == ba["narrative_distinctness"]["label"]
        )
        if row["narrative_distinctness_stable"] != str(distinct_stable):
            raise ValueError(f"Narrative order stability differs: {base_id}")
        for axis in AXES:
            ab_label = str(ab["perceived_profile_shift"][axis])
            ba_label = str(ba["perceived_profile_shift"][axis])
            stable = ab_label == OPPOSITES[ba_label]
            canonical = ab_label if stable else "order_sensitive"
            if (
                row[f"{axis}_shift_ba_canonical"] != OPPOSITES[ba_label]
                or row[f"{axis}_shift_stable"] != str(stable)
                or row[f"{axis}_shift"] != canonical
            ):
                raise ValueError(f"Pair order classification differs: {base_id}/{axis}")

    summary = read_csv(phase5_dir / "phase5_summary.csv")
    indexed_summary = {(row["metric"], row["subgroup"]): row for row in summary}
    required = {("profile_manifestation", axis) for axis in AXES} | {
        ("controlled_contrast_recovery", "all"),
        ("cross_axis_leakage", "non_controlled_axes"),
        ("structure_impression_spearman", "node_lcs_distance"),
        ("ab_ba_order_stability", "all_pairwise_labels"),
        ("human_qwen_calibration_concordance", "P03"),
        ("valid_output_rate", "final_run"),
    }
    if not required <= set(indexed_summary):
        raise ValueError("Required phase-5 indicators are missing")
    expected_key_counts = {
        ("profile_manifestation", "risk"): ("9", "14"),
        ("profile_manifestation", "morality"): ("6", "14"),
        ("profile_manifestation", "action"): ("2", "14"),
        ("controlled_contrast_recovery", "all"): ("5", "6"),
        ("ab_ba_order_stability", "all_pairwise_labels"): ("18", "24"),
        ("valid_output_rate", "final_run"): ("26", "26"),
    }
    for key, counts in expected_key_counts.items():
        row = indexed_summary[key]
        if (row["numerator"], row["denominator"]) != counts:
            raise ValueError(f"Unexpected key result: {key}")

    output_hashes = manifest.get("output_hashes")
    if not isinstance(output_hashes, dict):
        raise ValueError("Output hashes are missing")
    for filename in (
        "trajectory_results.csv",
        "pairwise_results.csv",
        "phase5_summary.csv",
    ):
        if output_hashes.get(filename) != sha256_file(phase5_dir / filename):
            raise ValueError(f"Output hash differs: {filename}")
    print(
        "OK: phase 5.4 independently validated — 14 trajectories, "
        "6 paired comparisons and all preregistered indicators"
    )


if __name__ == "__main__":
    main()
