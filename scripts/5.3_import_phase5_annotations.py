"""Import, validate and normalize raw phase-5 cluster annotations."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import runpy
from pathlib import Path
from typing import Any, Callable, cast

SCHEMA_NAMESPACE = runpy.run_path(
    str(
        Path(__file__).resolve().parents[1]
        / "cluster_scripts"
        / "phase5"
        / "schemas.py"
    )
)
validate_individual_annotation = cast(
    Callable[[Any], list[str]],
    SCHEMA_NAMESPACE["validate_individual_annotation"],
)
validate_pairwise_annotation = cast(
    Callable[[Any], list[str]],
    SCHEMA_NAMESPACE["validate_pairwise_annotation"],
)

DEFAULT_BOOK_ID = "LW01"
DEFAULT_RUN_ID = "LW01_phase5_pilot_v2"
TASK_FILES = {
    "individual": "individual.jsonl",
    "pairwise_ab": "pairwise_ab.jsonl",
    "pairwise_ba": "pairwise_ba.jsonl",
}
WRAPPER_FIELDS = {
    "schema_version",
    "task",
    "input_id",
    "input_sha256",
    "prompt_sha256",
    "input_token_count",
    "generated_token_count",
    "finish_reason",
    "annotation",
    "raw_model_output",
}


def sha256_file(path: Path) -> str:
    """Return one file's SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    """Return one UTF-8 string digest."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_sha256(value: dict[str, Any]) -> str:
    """Hash one object with the serialization used by the cluster runner."""
    serialized = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return sha256_text(serialized)


def read_json(path: Path) -> dict[str, Any]:
    """Read one JSON object."""
    if not path.is_file():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected one JSON object in {path}")
    return value


def read_jsonl(path: Path, *, allow_empty: bool = False) -> list[dict[str, Any]]:
    """Read a JSON Lines file."""
    if not path.is_file():
        raise FileNotFoundError(path)
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
        raise ValueError(f"Empty JSON Lines file: {path}")
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write deterministic normalized JSON Lines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for row in rows
    ]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def write_json(path: Path, value: dict[str, Any]) -> None:
    """Write one deterministic readable JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def relative_path(path: Path) -> str:
    """Render a repository-relative path when possible."""
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path.resolve())


def resolve_run_dir(path: Path, run_id: str) -> Path:
    """Resolve one run by its manifest identity within a transfer wrapper."""
    if (path / "run_manifest.json").is_file():
        return path
    candidates = sorted(
        child
        for child in path.iterdir()
        if child.is_dir() and (child / "run_manifest.json").is_file()
    )
    matches = [
        child
        for child in candidates
        if read_json(child / "run_manifest.json").get("run_id") == run_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one {run_id} output directory below {path}, "
            f"found {len(matches)} among {len(candidates)} candidates"
        )
    return matches[0]


def verify_bundle(bundle_dir: Path) -> dict[str, Any]:
    """Verify the frozen inference payload against its bundle manifest."""
    manifest = read_json(bundle_dir / "bundle_manifest.json")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Bundle manifest has no payload table")
    for relative, metadata in files.items():
        if not isinstance(relative, str) or not isinstance(metadata, dict):
            raise ValueError("Invalid bundle payload metadata")
        path = bundle_dir / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        if sha256_file(path) != metadata.get("sha256"):
            raise ValueError(f"Bundle payload hash differs: {relative}")
        if path.stat().st_size != metadata.get("bytes"):
            raise ValueError(f"Bundle payload size differs: {relative}")
    return manifest


def verify_run_manifest(
    run_dir: Path, bundle_dir: Path, bundle_manifest: dict[str, Any]
) -> dict[str, Any]:
    """Verify run identity, completion, counts and raw-output hashes."""
    manifest = read_json(run_dir / "run_manifest.json")
    if manifest.get("status") != "complete":
        raise ValueError("Cluster run is not complete")
    if manifest.get("run_id") != bundle_manifest.get("run_id"):
        raise ValueError("Run and bundle identifiers differ")
    expected_bundle_hash = sha256_file(bundle_dir / "bundle_manifest.json")
    if manifest.get("bundle_manifest_sha256") != expected_bundle_hash:
        raise ValueError("Run belongs to a different bundle manifest")
    if manifest.get("configured_model") != "Qwen/Qwen3.6-27B":
        raise ValueError("Unexpected model in run manifest")
    if not isinstance(manifest.get("resolved_model_revision"), str):
        raise ValueError("Resolved model revision was not recorded")
    output_files = manifest.get("output_files")
    if not isinstance(output_files, dict):
        raise ValueError("Run manifest has no output file table")
    expected_files = {*TASK_FILES.values(), "quarantine.jsonl"}
    if set(output_files) != expected_files:
        raise ValueError("Run output file table differs")
    for filename, metadata in output_files.items():
        if not isinstance(metadata, dict):
            raise ValueError(f"Invalid output metadata: {filename}")
        path = run_dir / filename
        if sha256_file(path) != metadata.get("sha256"):
            raise ValueError(f"Raw output hash differs: {filename}")
        if path.stat().st_size != metadata.get("bytes"):
            raise ValueError(f"Raw output size differs: {filename}")
    expected_counts = bundle_manifest.get("job_counts")
    results = manifest.get("job_results")
    if not isinstance(expected_counts, dict) or not isinstance(results, dict):
        raise ValueError("Missing job counts")
    for task in TASK_FILES:
        task_result = results.get(task)
        if not isinstance(task_result, dict):
            raise ValueError(f"Missing result counts for {task}")
        if task_result.get("written") != expected_counts.get(task):
            raise ValueError(f"Incomplete valid outputs for {task}")
        if task_result.get("quarantined") != 0:
            raise ValueError(f"Quarantined outputs reported for {task}")
    if read_jsonl(run_dir / "quarantine.jsonl", allow_empty=True):
        raise ValueError("Raw quarantine is not empty")
    return manifest


def valid_references(story_text: str) -> tuple[set[str], set[str], set[str]]:
    """Extract step, chosen-action and paragraph references from public text."""
    steps = set(re.findall(r"\[STEP (S[0-9]{3})\]", story_text))
    choices = set(
        re.findall(r"\[CHOSEN ACTION\]\n(S[0-9]{3}-C[0-9]{2})\.", story_text)
    )
    paragraphs = set(re.findall(r"\[PARAGRAPH ([0-9]+)\]", story_text))
    return steps, choices, paragraphs


def validate_evidence(
    task: str, annotation: dict[str, Any], input_row: dict[str, Any]
) -> list[str]:
    """Validate evidence references against the exact blinded input."""
    errors: list[str] = []
    if task == "individual":
        _, all_choices, paragraphs = valid_references(str(input_row["story_text"]))
        eligible = input_row.get("eligible_profile_choice_refs")
        choices = set(eligible) if isinstance(eligible, list) else all_choices
        profile = annotation.get("perceived_profile", {})
        if isinstance(profile, dict):
            for axis in ("risk", "morality", "action"):
                axis_row = profile.get(axis, {})
                if not isinstance(axis_row, dict):
                    continue
                for field in (
                    "supporting_choice_refs",
                    "counterevidence_choice_refs",
                ):
                    for reference in axis_row.get(field, []):
                        if reference not in choices:
                            errors.append(f"{axis}.{field}: {reference}")
        coherence = annotation.get("profile_coherence", {})
        if isinstance(coherence, dict):
            for field in (
                "supporting_choice_refs",
                "counterevidence_choice_refs",
            ):
                for reference in coherence.get(field, []):
                    if reference not in choices:
                        errors.append(f"profile_coherence.{field}: {reference}")
        continuity = annotation.get("causal_continuity", {})
        if isinstance(continuity, dict):
            for reference in continuity.get("evidence_paragraph_ids", []):
                if reference not in paragraphs:
                    errors.append(f"causal_continuity: {reference}")
        return errors

    for side in ("a", "b"):
        story = input_row[f"story_{side}"]
        steps, all_choices, _ = valid_references(str(story["story_text"]))
        eligible = story.get("eligible_profile_choice_refs")
        choices = set(eligible) if isinstance(eligible, list) else all_choices
        for reference in annotation.get(f"evidence_story_{side}", []):
            allowed = choices if "-C" in str(reference) else steps
            if reference not in allowed:
                errors.append(f"evidence_story_{side}: {reference}")
    return errors


def load_inputs(bundle_dir: Path) -> dict[str, dict[str, dict[str, Any]]]:
    """Load frozen input rows indexed by task and opaque identifier."""
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for task in TASK_FILES:
        rows = read_jsonl(
            bundle_dir / "inputs" / f"{task}.jsonl", allow_empty=True
        )
        field = "trajectory_id" if task == "individual" else "comparison_id"
        indexed = {str(row[field]): row for row in rows}
        if len(indexed) != len(rows):
            raise ValueError(f"Duplicate bundle input for {task}")
        result[task] = indexed
    return result


def validate_wrapper(
    *,
    task: str,
    row: dict[str, Any],
    input_row: dict[str, Any],
    prompt_hash: str,
) -> dict[str, Any]:
    """Validate one raw wrapper and return its annotation object."""
    identity = str(row.get("input_id", ""))
    if set(row) != WRAPPER_FIELDS:
        raise ValueError(f"Unexpected raw wrapper fields: {identity}")
    if row.get("schema_version") != "1.0" or row.get("task") != task:
        raise ValueError(f"Invalid raw wrapper envelope: {identity}")
    if row.get("input_sha256") != canonical_sha256(input_row):
        raise ValueError(f"Input hash differs: {identity}")
    if row.get("prompt_sha256") != prompt_hash:
        raise ValueError(f"Prompt hash differs: {identity}")
    if not isinstance(row.get("input_token_count"), int) or row[
        "input_token_count"
    ] <= 0:
        raise ValueError(f"Invalid input-token count: {identity}")
    if not isinstance(row.get("generated_token_count"), int) or row[
        "generated_token_count"
    ] <= 0:
        raise ValueError(f"Invalid generated-token count: {identity}")
    if row.get("finish_reason") == "length":
        raise ValueError(f"Truncated generation: {identity}")
    annotation = row.get("annotation")
    if not isinstance(annotation, dict):
        raise ValueError(f"Annotation is not an object: {identity}")
    raw_text = row.get("raw_model_output")
    if not isinstance(raw_text, str) or json.loads(raw_text) != annotation:
        raise ValueError(f"Raw and parsed annotations differ: {identity}")
    errors = (
        validate_individual_annotation(annotation)
        if task == "individual"
        else validate_pairwise_annotation(annotation)
    )
    if task == "individual":
        if annotation.get("trajectory_id") != identity:
            errors.append("trajectory_id differs")
    else:
        if annotation.get("comparison_id") != identity:
            errors.append("comparison_id differs")
        for side in ("a", "b"):
            if annotation.get(f"trajectory_{side}_id") != input_row[
                f"story_{side}"
            ]["trajectory_id"]:
                errors.append(f"trajectory_{side}_id differs")
    errors.extend(validate_evidence(task, annotation, input_row))
    if errors:
        raise ValueError(f"Invalid annotation {identity}: {'; '.join(errors)}")
    return annotation


def normalized_row(
    raw: dict[str, Any], annotation: dict[str, Any], run_manifest: dict[str, Any]
) -> dict[str, Any]:
    """Return one canonical annotation with compact provenance."""
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
        "annotation": annotation,
    }


def parse_args() -> argparse.Namespace:
    """Parse phase-5.3 import arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--bundle-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args()


def main() -> None:
    """Validate one complete cluster return and write canonical artifacts."""
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

    bundle_manifest = verify_bundle(bundle_dir)
    if bundle_manifest.get("book_id") != book_id:
        raise ValueError("Bundle belongs to another book")
    if bundle_manifest.get("run_id") != run_id:
        raise ValueError("Requested and bundled run identifiers differ")
    run_manifest = verify_run_manifest(run_dir, bundle_dir, bundle_manifest)
    inputs = load_inputs(bundle_dir)

    normalized: dict[str, list[dict[str, Any]]] = {
        task: [] for task in TASK_FILES
    }
    for task, filename in TASK_FILES.items():
        prompt_filename = "individual.txt" if task == "individual" else "pairwise.txt"
        prompt_hash = sha256_file(bundle_dir / "prompts" / prompt_filename)
        raw_rows = read_jsonl(run_dir / filename, allow_empty=True)
        seen: set[str] = set()
        for raw in raw_rows:
            identity = str(raw.get("input_id", ""))
            if identity in seen:
                raise ValueError(f"Duplicate raw output identity: {identity}")
            seen.add(identity)
            input_row = inputs[task].get(identity)
            if input_row is None:
                raise ValueError(f"Unknown raw output identity: {identity}")
            annotation = validate_wrapper(
                task=task,
                row=raw,
                input_row=input_row,
                prompt_hash=prompt_hash,
            )
            normalized[task].append(
                normalized_row(raw, annotation, run_manifest)
            )
        if seen != set(inputs[task]):
            raise ValueError(f"Missing or unexpected outputs for {task}")

    individual_path = output_dir / "trajectory_annotations.jsonl"
    pairwise_path = output_dir / "pairwise_annotations.jsonl"
    write_jsonl(individual_path, normalized["individual"])
    pairwise_rows = normalized["pairwise_ab"] + normalized["pairwise_ba"]
    write_jsonl(pairwise_path, pairwise_rows)
    report_path = output_dir / "phase5_import_report.json"
    report = {
        "schema_version": "1.0",
        "phase": "5.3",
        "status": "valid",
        "book_id": book_id,
        "run_id": run_id,
        "stage": run_manifest["stage"],
        "model": run_manifest["configured_model"],
        "model_revision": run_manifest["resolved_model_revision"],
        "vllm_version": run_manifest["vllm_version"],
        "source_run_dir": relative_path(run_dir),
        "source_bundle_dir": relative_path(bundle_dir),
        "counts": {
            "individual": len(normalized["individual"]),
            "pairwise_ab": len(normalized["pairwise_ab"]),
            "pairwise_ba": len(normalized["pairwise_ba"]),
            "quarantined": 0,
        },
        "source_hashes": {
            "bundle_manifest.json": sha256_file(
                bundle_dir / "bundle_manifest.json"
            ),
            "run_manifest.json": sha256_file(run_dir / "run_manifest.json"),
            **{
                filename: sha256_file(run_dir / filename)
                for filename in (*TASK_FILES.values(), "quarantine.jsonl")
            },
        },
        "output_hashes": {
            individual_path.name: sha256_file(individual_path),
            pairwise_path.name: sha256_file(pairwise_path),
        },
        "raw_outputs_modified": False,
    }
    write_json(report_path, report)
    print(
        f"OK: imported {len(normalized['individual'])} individual and "
        f"{len(pairwise_rows)} pairwise annotations from {run_id}"
    )
    print(f"Canonical output: {output_dir}")


if __name__ == "__main__":
    main()
