"""Independently validate normalized phase-5.3 pilot annotations."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import runpy
from pathlib import Path
from typing import Any, Callable, cast

DEFAULT_BOOK_ID = "LW01"
DEFAULT_RUN_ID = "LW01_phase5_pilot_v2"
CANONICAL_FIELDS = {
    "schema_version",
    "run_id",
    "task",
    "input_id",
    "model",
    "model_revision",
    "input_sha256",
    "prompt_sha256",
    "input_token_count",
    "generated_token_count",
    "finish_reason",
    "annotation",
}


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


def read_jsonl(path: Path, *, allow_empty: bool = False) -> list[dict[str, Any]]:
    """Read a JSON Lines file."""
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
    if not rows and not allow_empty:
        raise ValueError(f"Unexpected empty file: {path}")
    return rows


def resolve_run_dir(path: Path, run_id: str) -> Path:
    """Resolve the requested cluster output by manifest identity."""
    if (path / "run_manifest.json").is_file():
        return path
    candidates = [
        child
        for child in path.iterdir()
        if child.is_dir() and (child / "run_manifest.json").is_file()
    ]
    matches = [
        child
        for child in candidates
        if read_json(child / "run_manifest.json").get("run_id") == run_id
    ]
    if len(matches) != 1:
        raise ValueError("Could not resolve the requested cluster output directory")
    return matches[0]


def valid_references(story_text: str) -> tuple[set[str], set[str], set[str]]:
    """Extract all evidence identifiers independently."""
    steps = set(re.findall(r"\[STEP (S\d{3})\]", story_text))
    choices = set(re.findall(r"\[CHOSEN ACTION\]\n(S\d{3}-C\d{2})\.", story_text))
    paragraphs = set(re.findall(r"\[PARAGRAPH (\d+)\]", story_text))
    return steps, choices, paragraphs


def validate_references(
    task: str, annotation: dict[str, Any], input_row: dict[str, Any]
) -> None:
    """Require every generated evidence reference to exist in its story."""
    if task == "individual":
        _, choices, paragraphs = valid_references(str(input_row["story_text"]))
        profile = annotation["perceived_profile"]
        for axis in ("risk", "morality", "action"):
            for field in (
                "supporting_choice_refs",
                "counterevidence_choice_refs",
            ):
                if not set(profile[axis][field]) <= choices:
                    raise ValueError(f"Invalid {axis} evidence")
        coherence = annotation["profile_coherence"]
        for field in (
            "supporting_choice_refs",
            "counterevidence_choice_refs",
        ):
            if not set(coherence[field]) <= choices:
                raise ValueError("Invalid coherence evidence")
        if not set(annotation["causal_continuity"]["evidence_paragraph_ids"]) <= (
            paragraphs
        ):
            raise ValueError("Invalid continuity evidence")
        return
    for side in ("a", "b"):
        steps, choices, _ = valid_references(
            str(input_row[f"story_{side}"]["story_text"])
        )
        for reference in annotation[f"evidence_story_{side}"]:
            allowed = choices if "-C" in reference else steps
            if reference not in allowed:
                raise ValueError(f"Invalid pairwise {side} evidence")


def expected_canonical(
    raw: dict[str, Any], run_manifest: dict[str, Any]
) -> dict[str, Any]:
    """Project one immutable raw output into the documented canonical form."""
    return {
        "schema_version": "1.0",
        "run_id": run_manifest["run_id"],
        "task": raw["task"],
        "input_id": raw["input_id"],
        "model": run_manifest["configured_model"],
        "model_revision": run_manifest["resolved_model_revision"],
        "input_sha256": raw["input_sha256"],
        "prompt_sha256": raw["prompt_sha256"],
        "input_token_count": raw["input_token_count"],
        "generated_token_count": raw["generated_token_count"],
        "finish_reason": raw["finish_reason"],
        "annotation": raw["annotation"],
    }


def parse_args() -> argparse.Namespace:
    """Parse independent validator arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--bundle-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args()


def main() -> None:
    """Reconstruct and validate all phase-5.3 canonical artifacts."""
    args = parse_args()
    book_id = str(args.book)
    run_id = str(args.run_id)
    transfer_dir = args.run_dir or (
        Path("results/phase5") / book_id / "cluster_runs" / run_id
    )
    run_dir = resolve_run_dir(transfer_dir, run_id)
    bundle_dir = args.bundle_dir or (
        Path("data/for_trajectory_annotation")
        / book_id
        / "server_bundle"
        / run_id
    )
    output_dir = args.output_dir or (
        Path("data/processed/phase5") / book_id / "annotations" / run_id
    )
    run_manifest = read_json(run_dir / "run_manifest.json")
    bundle_manifest = read_json(bundle_dir / "bundle_manifest.json")
    report = read_json(output_dir / "phase5_import_report.json")
    if run_manifest.get("status") != "complete" or report.get("status") != "valid":
        raise ValueError("Run or import is not complete and valid")
    if run_manifest.get("run_id") != run_id or report.get("run_id") != run_id:
        raise ValueError("Run identity differs")
    if run_manifest.get("bundle_manifest_sha256") != sha256_file(
        bundle_dir / "bundle_manifest.json"
    ):
        raise ValueError("Bundle hash differs")
    if bundle_manifest.get("job_counts") != {
        "individual": 4,
        "pairwise_ab": 3,
        "pairwise_ba": 0,
        "total": 7,
    }:
        raise ValueError("Pilot bundle counts differ")

    schema_namespace = runpy.run_path(str(bundle_dir / "schemas.py"))
    individual_validator = cast(
        Callable[[Any], list[str]],
        schema_namespace["validate_individual_annotation"],
    )
    pairwise_validator = cast(
        Callable[[Any], list[str]],
        schema_namespace["validate_pairwise_annotation"],
    )
    task_specs = {
        "individual": (
            "individual.jsonl",
            "trajectory_annotations.jsonl",
            individual_validator,
        ),
        "pairwise_ab": (
            "pairwise_ab.jsonl",
            "pairwise_annotations.jsonl",
            pairwise_validator,
        ),
    }
    for task, (raw_name, canonical_name, validator) in task_specs.items():
        raw_rows = read_jsonl(run_dir / raw_name)
        canonical_rows = read_jsonl(output_dir / canonical_name)
        if canonical_rows != [
            expected_canonical(row, run_manifest) for row in raw_rows
        ]:
            raise ValueError(f"Canonical projection differs for {task}")
        input_rows = read_jsonl(bundle_dir / "inputs" / f"{task}.jsonl")
        identity_field = "trajectory_id" if task == "individual" else "comparison_id"
        inputs = {str(row[identity_field]): row for row in input_rows}
        for row in canonical_rows:
            if set(row) != CANONICAL_FIELDS or "raw_model_output" in row:
                raise ValueError("Canonical fields differ")
            annotation = row["annotation"]
            errors = validator(annotation)
            if errors:
                raise ValueError(f"Schema errors in {row['input_id']}: {errors}")
            validate_references(task, annotation, inputs[str(row["input_id"])])

    if read_jsonl(run_dir / "pairwise_ba.jsonl", allow_empty=True):
        raise ValueError("Pilot unexpectedly contains B/A outputs")
    if read_jsonl(run_dir / "quarantine.jsonl", allow_empty=True):
        raise ValueError("Pilot quarantine is not empty")
    output_hashes = report.get("output_hashes")
    if not isinstance(output_hashes, dict):
        raise ValueError("Import report output hashes are missing")
    for filename in ("trajectory_annotations.jsonl", "pairwise_annotations.jsonl"):
        if output_hashes.get(filename) != sha256_file(output_dir / filename):
            raise ValueError(f"Canonical output hash differs: {filename}")
    print(
        "OK: phase 5.3 independently validated — 4 individual, "
        "3 pairwise, 0 quarantined"
    )


if __name__ == "__main__":
    main()
