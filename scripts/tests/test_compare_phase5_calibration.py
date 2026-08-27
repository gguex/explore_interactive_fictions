"""Independently validate the phase-5 human/Qwen calibration comparison."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_BOOK_ID = "LW01"
DEFAULT_RUN_ID = "LW01_phase5_pilot_v2"
ABSTENTIONS = {"unclear", "insufficient", "insufficient_evidence"}
PLAYER_CHOICE_TYPES = {"Player choice", "Player choice: escape from combat"}
INDIVIDUAL_FIELDS = [
    "perceived_profile.risk.label",
    "perceived_profile.risk.support",
    "perceived_profile.morality.label",
    "perceived_profile.morality.support",
    "perceived_profile.action.label",
    "perceived_profile.action.support",
    "causal_continuity.label",
    "profile_coherence.label",
]
PAIRWISE_FIELDS = [
    "narrative_distinctness.label",
    "perceived_profile_shift.risk",
    "perceived_profile_shift.morality",
    "perceived_profile_shift.action",
]


def sha256_file(path: Path) -> str:
    """Return one file digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    """Read one JSON object."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected object in {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read non-empty JSON Lines objects."""
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"Invalid JSON Lines file: {path}")
    return rows


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read the field-level comparison table."""
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("Calibration CSV has no header")
        return list(reader.fieldnames), list(reader)


def nested(annotation: dict[str, Any], field: str) -> str:
    """Read one dot-separated scalar value."""
    value: Any = annotation
    for part in field.split("."):
        value = value[part]
    if not isinstance(value, str):
        raise ValueError(f"Non-string calibration field: {field}")
    return value


def expected_status(human: str, model: str) -> str:
    """Reapply the documented abstention priority."""
    if human == model:
        return "match"
    if human in ABSTENTIONS:
        return "human_abstention"
    if model in ABSTENTIONS:
        return "model_abstention"
    return "disagreement"


def human_individual(row: dict[str, Any]) -> dict[str, Any]:
    """Project the editable human envelope to annotation fields."""
    return {
        key: row[key]
        for key in (
            "trajectory_id",
            "perceived_profile",
            "causal_continuity",
            "profile_coherence",
        )
    }


def human_pairwise(row: dict[str, Any]) -> dict[str, Any]:
    """Project one human pair and align its canonical A/B identity."""
    return {
        "comparison_id": f"{row['comparison_id']}_AB",
        **{
            key: row[key]
            for key in (
                "trajectory_a_id",
                "trajectory_b_id",
                "narrative_distinctness",
                "perceived_profile_shift",
                "profile_shift_justification",
                "evidence_story_a",
                "evidence_story_b",
            )
        },
    }


def evidence_violations(
    task: str,
    identity: str,
    annotation: dict[str, Any],
    stories: dict[str, dict[str, Any]],
    source: str,
) -> list[dict[str, str]]:
    """Recalculate excluded transition citations independently."""
    references: list[tuple[str, str, str]] = []
    if task == "individual":
        trajectory_id = str(annotation["trajectory_id"])
        for axis in ("risk", "morality", "action"):
            axis_row = annotation["perceived_profile"][axis]
            for field in (
                "supporting_choice_refs",
                "counterevidence_choice_refs",
            ):
                references.extend(
                    (trajectory_id, f"perceived_profile.{axis}.{field}", ref)
                    for ref in axis_row[field]
                )
        coherence = annotation["profile_coherence"]
        for field in (
            "supporting_choice_refs",
            "counterevidence_choice_refs",
        ):
            references.extend(
                (trajectory_id, f"profile_coherence.{field}", ref)
                for ref in coherence[field]
            )
    else:
        for side in ("a", "b"):
            trajectory_id = str(annotation[f"trajectory_{side}_id"])
            references.extend(
                (trajectory_id, f"evidence_story_{side}", ref)
                for ref in annotation[f"evidence_story_{side}"]
                if "-C" in ref
            )
    result: list[dict[str, str]] = []
    for trajectory_id, location, reference in references:
        transitions = {
            str(step["chosen_action"]["choice_ref"]): str(step["transition_type"])
            for step in stories[trajectory_id]["steps"]
            if step.get("chosen_action")
        }
        transition = transitions.get(reference, "missing")
        if transition not in PLAYER_CHOICE_TYPES:
            result.append(
                {
                    "source": source,
                    "task": task,
                    "input_id": identity,
                    "location": location,
                    "reference": reference,
                    "transition_type": transition,
                }
            )
    return result


def parse_args() -> argparse.Namespace:
    """Parse independent comparison-validator arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--human-dir", type=Path)
    parser.add_argument("--phase5-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args()


def main() -> None:
    """Validate every comparison value, status, hash and evidence warning."""
    args = parse_args()
    book_id = str(args.book)
    run_id = str(args.run_id)
    phase5_dir = args.phase5_dir or Path("data/processed/phase5") / book_id
    model_dir = args.model_dir or phase5_dir / "annotations" / run_id
    human_dir = args.human_dir or Path("data/for_trajectory_annotation") / book_id
    calibration_root = Path("results/phase5") / book_id / "calibration"
    output_dir = args.output_dir or calibration_root
    csv_path = output_dir / "calibration_diff.csv"
    markdown_path = output_dir / "calibration_diff.md"
    summary_path = output_dir / "calibration_summary.json"
    iteration_csv_path = calibration_root / "prompt_iteration_log.csv"
    iteration_markdown_path = calibration_root / "prompt_iteration_log.md"
    actual_files = {path.name for path in output_dir.iterdir() if path.is_file()}
    expected_files = {
        csv_path.name,
        markdown_path.name,
        summary_path.name,
    }
    if output_dir.resolve() == calibration_root.resolve():
        expected_files.update(
            {iteration_csv_path.name, iteration_markdown_path.name}
        )
    if actual_files != expected_files:
        raise ValueError("Calibration output membership differs")

    iteration_header, iteration_rows = read_csv(iteration_csv_path)
    if len(iteration_header) != len(set(iteration_header)):
        raise ValueError("Prompt-iteration CSV has duplicate columns")
    if [row.get("trial_id") for row in iteration_rows] != ["P01", "P02", "P03"]:
        raise ValueError("Prompt-iteration registry differs")
    if iteration_rows[0].get("status") != "completed":
        raise ValueError("P01 must be recorded as completed")
    if iteration_rows[1].get("status") != "completed":
        raise ValueError("P02 must be recorded as completed")
    if iteration_rows[2].get("status") != "completed":
        raise ValueError("P03 must be recorded as completed")
    if "prompt calibration, not model accuracy" not in (
        iteration_markdown_path.read_text(encoding="utf-8")
    ):
        raise ValueError("Prompt-iteration report omits its interpretation guard")

    human_individual_path = human_dir / "human_trajectory_annotations.jsonl"
    human_pairwise_path = human_dir / "human_pairwise_annotations.jsonl"
    model_individual_path = model_dir / "trajectory_annotations.jsonl"
    model_pairwise_path = model_dir / "pairwise_annotations.jsonl"
    humans_i = {
        str(row["trajectory_id"]): human_individual(row)
        for row in read_jsonl(human_individual_path)
    }
    humans_p = {
        str(row["comparison_id"]): human_pairwise(row)
        for row in read_jsonl(human_pairwise_path)
    }
    models_i = {
        str(row["input_id"]): row["annotation"]
        for row in read_jsonl(model_individual_path)
    }
    models_p = {
        str(row["input_id"]).removesuffix("_AB"): row["annotation"]
        for row in read_jsonl(model_pairwise_path)
    }
    header, rows = read_csv(csv_path)
    if len(header) != len(set(header)) or len(rows) != 44:
        raise ValueError("Calibration CSV dimensions differ")
    indexed = {(row["task"], row["input_id"], row["field"]): row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError("Duplicate calibration comparison rows")
    for task, humans, models, fields in (
        ("individual", humans_i, models_i, INDIVIDUAL_FIELDS),
        ("pairwise", humans_p, models_p, PAIRWISE_FIELDS),
    ):
        if set(humans) != set(models):
            raise ValueError(f"Calibration identities differ for {task}")
        for identity in humans:
            for field in fields:
                row = indexed[(task, identity, field)]
                human_value = nested(humans[identity], field)
                model_value = nested(models[identity], field)
                values_differ = (
                    row["human_value"] != human_value
                    or row["model_value"] != model_value
                )
                if values_differ:
                    raise ValueError("Compared value differs from source annotation")
                if row["status"] != expected_status(human_value, model_value):
                    raise ValueError("Comparison status differs")

    summary = read_json(summary_path)
    counts = Counter(row["status"] for row in rows)
    if summary.get("status_counts") != dict(sorted(counts.items())):
        raise ValueError("Summary status counts differ")
    if summary.get("compared_field_count") != 44:
        raise ValueError("Summary comparison count differs")
    if summary.get("accuracy_computed") is not False or summary.get("scope") != (
        "prompt calibration, not validation"
    ):
        raise ValueError("Calibration interpretation guard differs")
    expected_source_hashes = {
        human_individual_path.name: sha256_file(human_individual_path),
        human_pairwise_path.name: sha256_file(human_pairwise_path),
        model_individual_path.name: sha256_file(model_individual_path),
        model_pairwise_path.name: sha256_file(model_pairwise_path),
        "trajectories.jsonl": sha256_file(phase5_dir / "trajectories.jsonl"),
    }
    if summary.get("source_hashes") != expected_source_hashes:
        raise ValueError("Calibration source hashes differ")
    if summary.get("output_hashes") != {
        csv_path.name: sha256_file(csv_path),
        markdown_path.name: sha256_file(markdown_path),
    }:
        raise ValueError("Calibration output hashes differ")

    stories = {
        str(row["trajectory_id"]): row
        for row in read_jsonl(phase5_dir / "trajectories.jsonl")
    }
    human_violations: list[dict[str, str]] = []
    model_violations: list[dict[str, str]] = []
    for task, humans, models in (
        ("individual", humans_i, models_i),
        ("pairwise", humans_p, models_p),
    ):
        for identity, annotation in humans.items():
            human_violations.extend(
                evidence_violations(task, identity, annotation, stories, "human")
            )
        for identity, annotation in models.items():
            model_violations.extend(
                evidence_violations(task, identity, annotation, stories, "model")
            )
    evidence_check = summary.get("evidence_rule_check")
    if not isinstance(evidence_check, dict):
        raise ValueError("Evidence-rule summary is missing")
    if evidence_check.get("human_violations") != human_violations:
        raise ValueError("Human evidence violations differ")
    if evidence_check.get("model_violations") != model_violations:
        raise ValueError("Model evidence violations differ")
    if human_violations:
        raise ValueError("Human calibration cites inadmissible profile evidence")
    markdown = markdown_path.read_text(encoding="utf-8")
    evidence_line = f"Qwen violations: {len(model_violations)}"
    if "neither accuracy nor" not in markdown or evidence_line not in markdown:
        raise ValueError("Readable report omits interpretation or evidence warnings")
    print(
        "OK: calibration comparison independently validated — "
        f"{counts.get('match', 0)} matches, "
        f"{counts.get('disagreement', 0)} disagreements, "
        f"{counts.get('human_abstention', 0)} human abstentions, "
        f"{len(model_violations)} Qwen evidence-rule violations"
    )


if __name__ == "__main__":
    main()
