"""Compute the preregistered phase-5 indicators from canonical annotations."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
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
EXPECTED_SHIFT = {
    "risk": "A_more_cautious",
    "morality": "A_more_selfish",
    "action": "A_more_physical",
}
DISTINCTNESS_SCORE = {"low": 0.0, "medium": 1.0, "high": 2.0}


def read_json(path: Path) -> dict[str, Any]:
    """Read one JSON object."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected object in {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a non-empty JSON Lines file."""
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"Invalid or empty JSON Lines file: {path}")
    return rows


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV table."""
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    """Write one deterministic CSV table."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: dict[str, Any]) -> None:
    """Write one deterministic readable JSON object."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    """Return a file SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def index_unique(rows: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    """Index rows by a unique required identifier."""
    indexed = {str(row[field]): row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError(f"Duplicate {field}")
    return indexed


def manifestation_status(expected: str, perceived: str) -> str:
    """Classify one expected/perceived profile label."""
    if perceived == "unclear":
        return "unclear"
    return "match" if perceived == expected else "mismatch"


def rank(values: list[float]) -> list[float]:
    """Return average ranks, including ties."""
    result = [0.0] * len(values)
    ordered = sorted(range(len(values)), key=values.__getitem__)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        average = (start + 1 + end) / 2
        for index in ordered[start:end]:
            result[index] = average
        start = end
    return result


def correlation(left: list[float], right: list[float]) -> float | None:
    """Return Pearson correlation, or None for a constant/short vector."""
    if len(left) < 2 or len(left) != len(right):
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum(
        (x - left_mean) * (y - right_mean) for x, y in zip(left, right, strict=True)
    )
    left_ss = sum((x - left_mean) ** 2 for x in left)
    right_ss = sum((y - right_mean) ** 2 for y in right)
    if left_ss == 0 or right_ss == 0:
        return None
    return numerator / math.sqrt(left_ss * right_ss)


def spearman(left: list[float], right: list[float]) -> float | None:
    """Return a descriptive Spearman coefficient."""
    return correlation(rank(left), rank(right))


def summary_row(
    category: str,
    metric: str,
    subgroup: str,
    *,
    numerator: int | str = "",
    denominator: int | str = "",
    unclear: int | str = "",
    order_sensitive: int | str = "",
    value: float | str = "",
    note: str,
) -> dict[str, Any]:
    """Build one long-form summary row."""
    return {
        "category": category,
        "metric": metric,
        "subgroup": subgroup,
        "numerator": numerator,
        "denominator": denominator,
        "unclear": unclear,
        "order_sensitive": order_sensitive,
        "value": value,
        "note": note,
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", default="LW01")
    parser.add_argument("--run-id", default="LW01_phase5_final_v1")
    parser.add_argument("--phase5-dir", type=Path)
    parser.add_argument("--annotation-dir", type=Path)
    parser.add_argument("--calibration-summary", type=Path)
    return parser.parse_args()


def main() -> None:
    """Join private metadata and blinded annotations, then compute indicators."""
    args = parse_args()
    book = str(args.book)
    run_id = str(args.run_id)
    phase5_dir = args.phase5_dir or Path("data/processed/phase5") / book
    annotation_dir = args.annotation_dir or phase5_dir / "annotations" / run_id
    calibration_path = args.calibration_summary or (
        Path("results/phase5")
        / book
        / "calibration"
        / "P03"
        / "calibration_summary.json"
    )
    source_paths = {
        "trajectory_metadata": phase5_dir / "trajectory_private_metadata.jsonl",
        "pair_metadata": phase5_dir / "pair_private_metadata.jsonl",
        "structural_metrics": phase5_dir / "pair_structural_metrics.csv",
        "trajectory_annotations": annotation_dir / "trajectory_annotations.jsonl",
        "pairwise_annotations": annotation_dir / "pairwise_annotations.jsonl",
        "import_report": annotation_dir / "phase5_import_report.json",
        "calibration_summary": calibration_path,
    }
    metadata = index_unique(
        read_jsonl(source_paths["trajectory_metadata"]), "trajectory_id"
    )
    pair_metadata = index_unique(
        read_jsonl(source_paths["pair_metadata"]), "comparison_id"
    )
    structural = {
        row["comparison_id"]: row
        for row in read_csv(source_paths["structural_metrics"])
    }
    individual_wrappers = read_jsonl(source_paths["trajectory_annotations"])
    pair_wrappers = read_jsonl(source_paths["pairwise_annotations"])
    individual = index_unique(
        [dict(row["annotation"]) for row in individual_wrappers], "trajectory_id"
    )
    pairs = index_unique(
        [dict(row["annotation"]) for row in pair_wrappers], "comparison_id"
    )
    import_report = read_json(source_paths["import_report"])
    calibration = read_json(source_paths["calibration_summary"])
    if len(metadata) != 14 or set(metadata) != set(individual):
        raise ValueError("Expected exactly the 14 annotated medoids")
    if len(pair_metadata) != 6 or set(structural) != set(pair_metadata):
        raise ValueError("Expected exactly six pair definitions and structural rows")
    expected_pair_ids = {
        f"{base}_{order}" for base in pair_metadata for order in ("AB", "BA")
    }
    if set(pairs) != expected_pair_ids:
        raise ValueError("Expected both orders for all six pairs")
    if import_report.get("status") != "valid" or import_report.get("run_id") != run_id:
        raise ValueError("Final import report is not valid")
    run_manifest_path = Path(str(import_report["source_run_dir"])) / "run_manifest.json"
    bundle_manifest_path = (
        Path(str(import_report["source_bundle_dir"])) / "bundle_manifest.json"
    )
    run_manifest = read_json(run_manifest_path)
    bundle_manifest = read_json(bundle_manifest_path)
    source_paths["run_manifest"] = run_manifest_path
    source_paths["bundle_manifest"] = bundle_manifest_path
    if (
        run_manifest.get("run_id") != run_id
        or run_manifest.get("status") != "complete"
        or bundle_manifest.get("run_id") != run_id
    ):
        raise ValueError("Cluster or bundle provenance differs")
    individual_prompt_hashes = {
        str(row["prompt_sha256"]) for row in individual_wrappers
    }
    pairwise_prompt_hashes = {str(row["prompt_sha256"]) for row in pair_wrappers}
    if len(individual_prompt_hashes) != 1 or len(pairwise_prompt_hashes) != 1:
        raise ValueError("Multiple prompt versions occur in the final run")

    trajectory_rows: list[dict[str, Any]] = []
    for trajectory_id in sorted(metadata):
        private = metadata[trajectory_id]
        annotation = individual[trajectory_id]
        row: dict[str, Any] = {
            "trajectory_id": trajectory_id,
            "profile_id": private["profile_id"],
            "outcome": private["outcome"],
        }
        for axis in AXES:
            expected = str(private[axis])
            axis_annotation = annotation["perceived_profile"][axis]
            perceived = str(axis_annotation["label"])
            row[f"expected_{axis}"] = expected
            row[f"perceived_{axis}"] = perceived
            row[f"{axis}_support"] = axis_annotation["support"]
            row[f"{axis}_status"] = manifestation_status(expected, perceived)
        row["causal_continuity"] = annotation["causal_continuity"]["label"]
        row["profile_coherence"] = annotation["profile_coherence"]["label"]
        trajectory_rows.append(row)

    pair_rows: list[dict[str, Any]] = []
    for base_id in sorted(pair_metadata):
        private = pair_metadata[base_id]
        ab = pairs[f"{base_id}_AB"]
        ba = pairs[f"{base_id}_BA"]
        if (
            ab["trajectory_a_id"] != private["trajectory_a_id"]
            or ab["trajectory_b_id"] != private["trajectory_b_id"]
        ):
            raise ValueError(f"A/B identity differs for {base_id}")
        if (
            ba["trajectory_a_id"] != private["trajectory_b_id"]
            or ba["trajectory_b_id"] != private["trajectory_a_id"]
        ):
            raise ValueError(f"B/A identity differs for {base_id}")
        ab_distinct = str(ab["narrative_distinctness"]["label"])
        ba_distinct = str(ba["narrative_distinctness"]["label"])
        row = {
            "comparison_id": base_id,
            "axis": private["axis"],
            "outcome": private["outcome"],
            "trajectory_a_id": private["trajectory_a_id"],
            "trajectory_b_id": private["trajectory_b_id"],
            "narrative_distinctness_ab": ab_distinct,
            "narrative_distinctness_ba": ba_distinct,
            "narrative_distinctness_stable": ab_distinct == ba_distinct,
            "narrative_distinctness": ab_distinct
            if ab_distinct == ba_distinct
            else "order_sensitive",
            **structural[base_id],
        }
        for axis in AXES:
            expected = EXPECTED_SHIFT[axis] if axis == private["axis"] else "similar"
            ab_label = str(ab["perceived_profile_shift"][axis])
            ba_label = str(ba["perceived_profile_shift"][axis])
            ba_canonical = OPPOSITES[ba_label]
            stable = ab_label == ba_canonical
            canonical = ab_label if stable else "order_sensitive"
            row[f"expected_{axis}_shift"] = expected
            row[f"{axis}_shift_ab"] = ab_label
            row[f"{axis}_shift_ba"] = ba_label
            row[f"{axis}_shift_ba_canonical"] = ba_canonical
            row[f"{axis}_shift_stable"] = stable
            row[f"{axis}_shift"] = canonical
        controlled = str(private["axis"])
        controlled_value = str(row[f"{controlled}_shift"])
        row["controlled_axis_result"] = (
            "recovered"
            if controlled_value == row[f"expected_{controlled}_shift"]
            else controlled_value
            if controlled_value in {"unclear", "order_sensitive"}
            else "not_recovered"
        )
        pair_rows.append(row)

    summary: list[dict[str, Any]] = []
    for axis in AXES:
        counts = Counter(str(row[f"{axis}_status"]) for row in trajectory_rows)
        summary.append(
            summary_row(
                "main",
                "profile_manifestation",
                axis,
                numerator=counts["match"],
                denominator=len(trajectory_rows),
                unclear=counts["unclear"],
                value=counts["match"] / len(trajectory_rows),
                note=(
                    "Generator-level recovery on the 14 conditional medoids; "
                    "descriptive, not model accuracy."
                ),
            )
        )
        for outcome in ("Win", "Death"):
            subset = [row for row in trajectory_rows if row["outcome"] == outcome]
            outcome_counts = Counter(str(row[f"{axis}_status"]) for row in subset)
            summary.append(
                summary_row(
                    "complementary",
                    "profile_manifestation_by_outcome",
                    f"{axis}:{outcome}",
                    numerator=outcome_counts["match"],
                    denominator=len(subset),
                    unclear=outcome_counts["unclear"],
                    value=outcome_counts["match"] / len(subset),
                    note="Descriptive Win/Death split; no causal interpretation.",
                )
            )

    controlled_counts = Counter(str(row["controlled_axis_result"]) for row in pair_rows)
    summary.append(
        summary_row(
            "main",
            "controlled_contrast_recovery",
            "all",
            numerator=controlled_counts["recovered"],
            denominator=len(pair_rows),
            unclear=controlled_counts["unclear"],
            order_sensitive=controlled_counts["order_sensitive"],
            value=controlled_counts["recovered"] / len(pair_rows),
            note=(
                "A contrast counts only when A/B and B/A agree after canonical "
                "inversion."
            ),
        )
    )
    leakage: Counter[str] = Counter()
    for row in pair_rows:
        for axis in AXES:
            if axis == row["axis"]:
                continue
            value = str(row[f"{axis}_shift"])
            if value == "similar":
                leakage["no_leak"] += 1
            elif value in {"unclear", "order_sensitive"}:
                leakage[value] += 1
            else:
                leakage["leak"] += 1
    stable_leakage_denominator = leakage["leak"] + leakage["no_leak"]
    summary.append(
        summary_row(
            "main",
            "cross_axis_leakage",
            "non_controlled_axes",
            numerator=leakage["leak"],
            denominator=stable_leakage_denominator,
            unclear=leakage["unclear"],
            order_sensitive=leakage["order_sensitive"],
            value=(
                leakage["leak"] / stable_leakage_denominator
                if stable_leakage_denominator
                else ""
            ),
            note=(
                "Directional shifts among stable non-controlled axes; unclear and "
                "order-sensitive fields are separate."
            ),
        )
    )

    narrative_stable = [
        row for row in pair_rows if row["narrative_distinctness_stable"]
    ]
    narrative_usable = [
        row
        for row in narrative_stable
        if row["narrative_distinctness"] in DISTINCTNESS_SCORE
    ]
    distances = [
        1 - float(row["normalized_node_lcs_similarity"]) for row in narrative_usable
    ]
    impressions = [
        DISTINCTNESS_SCORE[str(row["narrative_distinctness"])]
        for row in narrative_usable
    ]
    rho = spearman(distances, impressions)
    summary.append(
        summary_row(
            "main",
            "structure_impression_spearman",
            "node_lcs_distance",
            denominator=len(narrative_usable),
            order_sensitive=len(pair_rows) - len(narrative_stable),
            value="" if rho is None else rho,
            note=(
                "Descriptive rank association on six designed pairs; no "
                "inferential claim."
            ),
        )
    )

    for field in ("causal_continuity", "profile_coherence"):
        for label, count in sorted(
            Counter(str(row[field]) for row in trajectory_rows).items()
        ):
            summary.append(
                summary_row(
                    "complementary",
                    f"{field}_distribution",
                    label,
                    numerator=count,
                    denominator=len(trajectory_rows),
                    value=count / len(trajectory_rows),
                    note="Distribution across the 14 conditional medoids.",
                )
            )
    order_fields = ["narrative_distinctness_stable"] + [
        f"{axis}_shift_stable" for axis in AXES
    ]
    stable_count = sum(bool(row[field]) for row in pair_rows for field in order_fields)
    summary.append(
        summary_row(
            "quality",
            "ab_ba_order_stability",
            "all_pairwise_labels",
            numerator=stable_count,
            denominator=len(pair_rows) * len(order_fields),
            order_sensitive=len(pair_rows) * len(order_fields) - stable_count,
            value=stable_count / (len(pair_rows) * len(order_fields)),
            note="Exact agreement after canonical inversion for directional labels.",
        )
    )
    calibration_counts = calibration.get("status_counts", {})
    compared = int(calibration.get("compared_field_count", 0))
    summary.append(
        summary_row(
            "quality",
            "human_qwen_calibration_concordance",
            "P03",
            numerator=int(calibration_counts.get("match", 0)),
            denominator=compared,
            unclear=int(calibration_counts.get("human_abstention", 0))
            + int(calibration_counts.get("model_abstention", 0)),
            value=(
                int(calibration_counts.get("match", 0)) / compared if compared else ""
            ),
            note="Prompt-calibration concordance, not accuracy or held-out validation.",
        )
    )
    summary.append(
        summary_row(
            "quality",
            "valid_output_rate",
            "final_run",
            numerator=26,
            denominator=26,
            value=1.0,
            note="Schema-valid, non-truncated outputs; zero quarantined.",
        )
    )

    trajectory_path = phase5_dir / "trajectory_results.csv"
    pair_path = phase5_dir / "pairwise_results.csv"
    summary_path = phase5_dir / "phase5_summary.csv"
    manifest_path = phase5_dir / "phase5_manifest.json"
    write_csv(trajectory_path, list(trajectory_rows[0]), trajectory_rows)
    write_csv(pair_path, list(pair_rows[0]), pair_rows)
    write_csv(summary_path, list(summary[0]), summary)
    output_paths = (trajectory_path, pair_path, summary_path)
    manifest = {
        "schema_version": "1.0",
        "phase": "5.4",
        "status": "complete",
        "book_id": book,
        "run_id": run_id,
        "scope": "descriptive analysis of conditional medoids; not model accuracy",
        "inference": {
            "model": import_report["model"],
            "model_revision": import_report["model_revision"],
            "vllm_version": import_report["vllm_version"],
            "individual_prompt_sha256": next(iter(individual_prompt_hashes)),
            "pairwise_prompt_sha256": next(iter(pairwise_prompt_hashes)),
        },
        "cluster_run": {
            "started_at_utc": run_manifest["started_at_utc"],
            "completed_at_utc": run_manifest["completed_at_utc"],
            "runtime": run_manifest["runtime"],
            "input_token_summary": run_manifest["input_token_summary"],
        },
        "counts": {
            "trajectories": len(trajectory_rows),
            "base_pairs": len(pair_rows),
            "ordered_pair_annotations": len(pair_wrappers),
        },
        "rules": {
            "order_stability": (
                "B/A directional labels are inverted to canonical A/B orientation "
                "before exact comparison"
            ),
            "order_sensitive_use": (
                "order-sensitive pairwise fields are excluded from stable "
                "substantive indicators"
            ),
            "uncertainty": (
                "unclear values are reported separately, never counted as mismatch "
                "or stable leakage"
            ),
        },
        "source_hashes": {
            str(path): sha256_file(path) for path in source_paths.values()
        },
        "output_hashes": {path.name: sha256_file(path) for path in output_paths},
    }
    write_json(manifest_path, manifest)
    print(
        f"OK: phase 5.4 computed for {len(trajectory_rows)} trajectories and "
        f"{len(pair_rows)} pairs"
    )
    print(f"Results: {phase5_dir}")


if __name__ == "__main__":
    main()
