"""Compare human and Qwen phase-5 pilot annotations field by field."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import runpy
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, cast

DEFAULT_BOOK_ID = "LW01"
DEFAULT_RUN_ID = "LW01_phase5_pilot_v2"
CSV_FIELDS = [
    "task",
    "input_id",
    "field",
    "human_value",
    "model_value",
    "status",
    "human_evidence",
    "model_evidence",
    "human_justification",
    "model_justification",
]
ABSTENTION_VALUES = {"unclear", "insufficient", "insufficient_evidence"}
PLAYER_CHOICE_TYPES = {"Player choice", "Player choice: escape from combat"}


def sha256_file(path: Path) -> str:
    """Return one file digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read non-empty JSON objects from one JSON Lines file."""
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number} is not an object")
        rows.append(value)
    if not rows:
        raise ValueError(f"Empty JSON Lines file: {path}")
    return rows


def write_json(path: Path, value: dict[str, Any]) -> None:
    """Write one deterministic JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    """Write the complete field-level comparison table."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def compact_json(value: Any) -> str:
    """Serialize evidence compactly for CSV and Markdown."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def comparison_status(human_value: str, model_value: str) -> str:
    """Classify equality and explicit codebook abstentions."""
    if human_value == model_value:
        return "match"
    if human_value in ABSTENTION_VALUES:
        return "human_abstention"
    if model_value in ABSTENTION_VALUES:
        return "model_abstention"
    return "disagreement"


def individual_context(annotation: dict[str, Any], field: str) -> tuple[str, str]:
    """Return evidence and justification associated with one individual field."""
    if field.startswith("perceived_profile."):
        _, axis, _ = field.split(".")
        axis_row = annotation["perceived_profile"][axis]
        evidence = {
            "supporting": axis_row["supporting_choice_refs"],
            "counterevidence": axis_row["counterevidence_choice_refs"],
        }
        return compact_json(evidence), str(axis_row["justification"])
    if field == "causal_continuity.label":
        row = annotation["causal_continuity"]
        return compact_json(row["evidence_paragraph_ids"]), str(row["justification"])
    row = annotation["profile_coherence"]
    evidence = {
        "supporting": row["supporting_choice_refs"],
        "counterevidence": row["counterevidence_choice_refs"],
    }
    return compact_json(evidence), str(row["justification"])


def pairwise_context(annotation: dict[str, Any], field: str) -> tuple[str, str]:
    """Return shared pairwise evidence and the field's justification."""
    evidence = {
        "story_a": annotation["evidence_story_a"],
        "story_b": annotation["evidence_story_b"],
    }
    justification_field = (
        "narrative_distinctness"
        if field == "narrative_distinctness.label"
        else None
    )
    justification = (
        annotation[justification_field]["justification"]
        if justification_field is not None
        else annotation["profile_shift_justification"]
    )
    return compact_json(evidence), str(justification)


def nested_value(annotation: dict[str, Any], field: str) -> str:
    """Read one dot-separated scalar field."""
    value: Any = annotation
    for part in field.split("."):
        value = value[part]
    if not isinstance(value, str):
        raise ValueError(f"Comparison field is not a string: {field}")
    return value


def comparison_row(
    *,
    task: str,
    identity: str,
    field: str,
    human: dict[str, Any],
    model: dict[str, Any],
) -> dict[str, str]:
    """Build one deterministic field-level comparison record."""
    human_value = nested_value(human, field)
    model_value = nested_value(model, field)
    context = individual_context if task == "individual" else pairwise_context
    human_evidence, human_justification = context(human, field)
    model_evidence, model_justification = context(model, field)
    return {
        "task": task,
        "input_id": identity,
        "field": field,
        "human_value": human_value,
        "model_value": model_value,
        "status": comparison_status(human_value, model_value),
        "human_evidence": human_evidence,
        "model_evidence": model_evidence,
        "human_justification": human_justification,
        "model_justification": model_justification,
    }


def stripped_individual(row: dict[str, Any]) -> dict[str, Any]:
    """Remove the private human calibration envelope."""
    fields = {
        "trajectory_id",
        "perceived_profile",
        "causal_continuity",
        "profile_coherence",
    }
    return {field: row[field] for field in fields}


def stripped_pairwise(row: dict[str, Any]) -> dict[str, Any]:
    """Remove the human envelope and align the canonical A/B identity."""
    fields = {
        "trajectory_a_id",
        "trajectory_b_id",
        "narrative_distinctness",
        "perceived_profile_shift",
        "profile_shift_justification",
        "evidence_story_a",
        "evidence_story_b",
    }
    return {
        "comparison_id": f"{row['comparison_id']}_AB",
        **{field: row[field] for field in fields},
    }


def evidence_rule_violations(
    *,
    source: str,
    task: str,
    identity: str,
    annotation: dict[str, Any],
    stories: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    """Find cited choice references that the codebook excludes as profile evidence."""
    references: list[tuple[str, str, str]] = []
    if task == "individual":
        trajectory_id = str(annotation["trajectory_id"])
        profile = annotation["perceived_profile"]
        for axis in ("risk", "morality", "action"):
            for field in (
                "supporting_choice_refs",
                "counterevidence_choice_refs",
            ):
                references.extend(
                    (trajectory_id, f"perceived_profile.{axis}.{field}", reference)
                    for reference in profile[axis][field]
                )
        coherence = annotation["profile_coherence"]
        for field in (
            "supporting_choice_refs",
            "counterevidence_choice_refs",
        ):
            references.extend(
                (trajectory_id, f"profile_coherence.{field}", reference)
                for reference in coherence[field]
            )
    else:
        for side in ("a", "b"):
            trajectory_id = str(annotation[f"trajectory_{side}_id"])
            references.extend(
                (trajectory_id, f"evidence_story_{side}", reference)
                for reference in annotation[f"evidence_story_{side}"]
                if "-C" in reference
            )
    violations: list[dict[str, str]] = []
    for trajectory_id, location, reference in references:
        story = stories[trajectory_id]
        transition_types = {
            str(step["chosen_action"]["choice_ref"]): str(step["transition_type"])
            for step in story["steps"]
            if step.get("chosen_action")
        }
        transition_type = transition_types.get(reference, "missing")
        if transition_type not in PLAYER_CHOICE_TYPES:
            violations.append(
                {
                    "source": source,
                    "task": task,
                    "input_id": identity,
                    "location": location,
                    "reference": reference,
                    "transition_type": transition_type,
                }
            )
    return violations


def markdown_report(rows: list[dict[str, str]], summary: dict[str, Any]) -> str:
    """Render a compact readable report with evidence for non-matches."""
    lines = [
        "# Phase 5 pilot — Human/Qwen calibration comparison",
        "",
        "> Descriptive prompt calibration only. This is neither accuracy nor an",
        "> out-of-sample validation, and disagreements are not automatically errors.",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "| :--- | ---: |",
    ]
    for status in (
        "match",
        "disagreement",
        "human_abstention",
        "model_abstention",
    ):
        lines.append(f"| `{status}` | {summary['status_counts'].get(status, 0)} |")
    evidence_check = summary["evidence_rule_check"]
    lines.extend(
        [
            "",
            "## Evidence-rule check",
            "",
            f"- Human violations: {evidence_check['human_violation_count']}",
            f"- Qwen violations: {evidence_check['model_violation_count']}",
            "",
        ]
    )
    model_violations = evidence_check["model_violations"]
    if model_violations:
        lines.extend(
            [
                "| ID | Location | Reference | Excluded transition type |",
                "| :--- | :--- | :--- | :--- |",
            ]
        )
        for violation in model_violations:
            lines.append(
                f"| `{violation['input_id']}` | `{violation['location']}` | "
                f"`{violation['reference']}` | "
                f"{violation['transition_type']} |"
            )
    lines.extend(
        [
            "",
            "## All compared fields",
            "",
            "| Task | ID | Field | Human | Qwen | Status |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['task']} | `{row['input_id']}` | `{row['field']}` | "
            f"`{row['human_value']}` | `{row['model_value']}` | "
            f"`{row['status']}` |"
        )
    reviewed = [row for row in rows if row["status"] != "match"]
    lines.extend(["", "## Fields requiring textual review", ""])
    if not reviewed:
        lines.append("None.")
    for row in reviewed:
        lines.extend(
            [
                f"### {row['input_id']} — {row['field']}",
                "",
                f"- Human: `{row['human_value']}` — evidence "
                f"`{row['human_evidence']}`",
                f"- Qwen: `{row['model_value']}` — evidence "
                f"`{row['model_evidence']}`",
                f"- Human justification: {row['human_justification']}",
                f"- Qwen justification: {row['model_justification']}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    """Parse calibration comparison arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--human-dir", type=Path)
    parser.add_argument("--phase5-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args()


def main() -> None:
    """Validate calibration inputs and write descriptive comparison artifacts."""
    args = parse_args()
    book_id = str(args.book)
    run_id = str(args.run_id)
    model_dir = args.model_dir or (
        Path("data/processed/phase5") / book_id / "annotations" / run_id
    )
    human_dir = args.human_dir or Path("data/for_trajectory_annotation") / book_id
    phase5_dir = args.phase5_dir or Path("data/processed/phase5") / book_id
    output_dir = args.output_dir or Path("results/phase5") / book_id / "calibration"

    human_individual_path = human_dir / "human_trajectory_annotations.jsonl"
    human_pairwise_path = human_dir / "human_pairwise_annotations.jsonl"
    model_individual_path = model_dir / "trajectory_annotations.jsonl"
    model_pairwise_path = model_dir / "pairwise_annotations.jsonl"
    human_individual_rows = read_jsonl(human_individual_path)
    human_pairwise_rows = read_jsonl(human_pairwise_path)
    model_individual_rows = read_jsonl(model_individual_path)
    model_pairwise_rows = read_jsonl(model_pairwise_path)
    trajectories_path = phase5_dir / "trajectories.jsonl"
    stories = {
        str(row["trajectory_id"]): row for row in read_jsonl(trajectories_path)
    }

    schema_namespace = runpy.run_path(
        str(Path(__file__).resolve().parents[2] / "cluster_scripts/phase5/schemas.py")
    )
    validate_individual = cast(
        Callable[[Any], list[str]],
        schema_namespace["validate_individual_annotation"],
    )
    validate_pairwise = cast(
        Callable[[Any], list[str]],
        schema_namespace["validate_pairwise_annotation"],
    )
    humans_individual = {
        str(row["trajectory_id"]): stripped_individual(row)
        for row in human_individual_rows
    }
    humans_pairwise = {
        str(row["comparison_id"]): stripped_pairwise(row)
        for row in human_pairwise_rows
    }
    models_individual = {
        str(row["input_id"]): row["annotation"] for row in model_individual_rows
    }
    models_pairwise = {
        str(row["input_id"]).removesuffix("_AB"): row["annotation"]
        for row in model_pairwise_rows
    }
    if set(humans_individual) != set(models_individual):
        raise ValueError("Human and model individual identities differ")
    if set(humans_pairwise) != set(models_pairwise):
        raise ValueError("Human and model pairwise identities differ")
    for identity, annotation in humans_individual.items():
        errors = validate_individual(annotation)
        if errors:
            raise ValueError(f"Invalid human individual {identity}: {errors}")
    for identity, annotation in humans_pairwise.items():
        errors = validate_pairwise(annotation)
        if errors:
            raise ValueError(f"Invalid human pairwise {identity}: {errors}")
    for identity, annotation in models_individual.items():
        errors = validate_individual(annotation)
        if errors:
            raise ValueError(f"Invalid model individual {identity}: {errors}")
    for identity, annotation in models_pairwise.items():
        errors = validate_pairwise(annotation)
        if errors:
            raise ValueError(f"Invalid model pairwise {identity}: {errors}")

    human_violations: list[dict[str, str]] = []
    model_violations: list[dict[str, str]] = []
    for identity, annotation in humans_individual.items():
        human_violations.extend(
            evidence_rule_violations(
                source="human",
                task="individual",
                identity=identity,
                annotation=annotation,
                stories=stories,
            )
        )
    for identity, annotation in humans_pairwise.items():
        human_violations.extend(
            evidence_rule_violations(
                source="human",
                task="pairwise",
                identity=identity,
                annotation=annotation,
                stories=stories,
            )
        )
    for identity, annotation in models_individual.items():
        model_violations.extend(
            evidence_rule_violations(
                source="model",
                task="individual",
                identity=identity,
                annotation=annotation,
                stories=stories,
            )
        )
    for identity, annotation in models_pairwise.items():
        model_violations.extend(
            evidence_rule_violations(
                source="model",
                task="pairwise",
                identity=identity,
                annotation=annotation,
                stories=stories,
            )
        )

    rows: list[dict[str, str]] = []
    individual_fields = [
        "perceived_profile.risk.label",
        "perceived_profile.risk.support",
        "perceived_profile.morality.label",
        "perceived_profile.morality.support",
        "perceived_profile.action.label",
        "perceived_profile.action.support",
        "causal_continuity.label",
        "profile_coherence.label",
    ]
    for identity in sorted(humans_individual):
        for field in individual_fields:
            rows.append(
                comparison_row(
                    task="individual",
                    identity=identity,
                    field=field,
                    human=humans_individual[identity],
                    model=models_individual[identity],
                )
            )
    pairwise_fields = [
        "narrative_distinctness.label",
        "perceived_profile_shift.risk",
        "perceived_profile_shift.morality",
        "perceived_profile_shift.action",
    ]
    for identity in sorted(humans_pairwise):
        for field in pairwise_fields:
            rows.append(
                comparison_row(
                    task="pairwise",
                    identity=identity,
                    field=field,
                    human=humans_pairwise[identity],
                    model=models_pairwise[identity],
                )
            )

    status_counts = Counter(row["status"] for row in rows)
    task_counts: dict[str, Counter[str]] = defaultdict(Counter)
    field_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        task_counts[row["task"]][row["status"]] += 1
        field_counts[row["field"]][row["status"]] += 1
    summary: dict[str, Any] = {
        "schema_version": "1.0",
        "phase": "5-calibration-comparison",
        "book_id": book_id,
        "run_id": run_id,
        "scope": "prompt calibration, not validation",
        "accuracy_computed": False,
        "compared_field_count": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "status_counts_by_task": {
            task: dict(sorted(counts.items()))
            for task, counts in sorted(task_counts.items())
        },
        "status_counts_by_field": {
            field: dict(sorted(counts.items()))
            for field, counts in sorted(field_counts.items())
        },
        "evidence_rule_check": {
            "rule": (
                "Profile evidence may cite only Player choice or Player choice: "
                "escape from combat transitions"
            ),
            "human_violation_count": len(human_violations),
            "model_violation_count": len(model_violations),
            "human_violations": human_violations,
            "model_violations": model_violations,
        },
        "source_hashes": {
            human_individual_path.name: sha256_file(human_individual_path),
            human_pairwise_path.name: sha256_file(human_pairwise_path),
            model_individual_path.name: sha256_file(model_individual_path),
            model_pairwise_path.name: sha256_file(model_pairwise_path),
            trajectories_path.name: sha256_file(trajectories_path),
        },
    }
    csv_path = output_dir / "calibration_diff.csv"
    markdown_path = output_dir / "calibration_diff.md"
    summary_path = output_dir / "calibration_summary.json"
    write_csv(csv_path, rows)
    markdown_path.write_text(markdown_report(rows, summary), encoding="utf-8")
    summary["output_hashes"] = {
        csv_path.name: sha256_file(csv_path),
        markdown_path.name: sha256_file(markdown_path),
    }
    write_json(summary_path, summary)
    print(
        f"OK: compared {len(rows)} fields — "
        f"{status_counts.get('match', 0)} matches, "
        f"{status_counts.get('disagreement', 0)} disagreements, "
        f"{status_counts.get('human_abstention', 0)} human abstentions, "
        f"{status_counts.get('model_abstention', 0)} model abstentions"
    )
    print(f"Readable report: {markdown_path}")


if __name__ == "__main__":
    main()
