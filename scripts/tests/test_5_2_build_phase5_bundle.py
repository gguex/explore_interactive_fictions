"""Independently validate a phase-5.2 pilot bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import runpy
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_BOOK_ID = "LW01"
EXPECTED_FILES = {
    "RUN_INSTRUCTIONS.md",
    "bundle_manifest.json",
    "config/inference.json",
    "inputs/individual.jsonl",
    "inputs/pairwise_ab.jsonl",
    "inputs/pairwise_ba.jsonl",
    "prompts/individual.txt",
    "prompts/pairwise.txt",
    "run_phase5.py",
    "schemas.py",
    "schemas/individual.schema.json",
    "schemas/pairwise.schema.json",
}
FORBIDDEN_INPUT_KEYS = {
    "action",
    "annotation",
    "annotation_role",
    "annotator_id",
    "compiled_weight",
    "edge_ids",
    "human_annotation",
    "morality",
    "node_ids",
    "outcome",
    "perceived_profile",
    "profile_coherence",
    "profile_id",
    "risk",
    "semantic_action",
    "semantic_morality",
    "semantic_risk",
    "split",
    "status",
    "weight",
}


def sha256_file(path: Path) -> str:
    """Return one file digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    """Return one UTF-8 string digest."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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
        raise ValueError(f"Unexpected empty JSON Lines file: {path}")
    return rows


def assert_no_forbidden_keys(value: Any, path: str) -> None:
    """Recursively reject hidden data from model inputs."""
    if isinstance(value, dict):
        forbidden = FORBIDDEN_INPUT_KEYS & set(value)
        if forbidden:
            raise ValueError(f"Private keys {sorted(forbidden)} in {path}")
        for key, child in value.items():
            assert_no_forbidden_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_no_forbidden_keys(child, f"{path}[{index}]")


def completed_ids(path: Path, identity_field: str) -> list[str]:
    """Return expected completed calibration identities."""
    rows = read_jsonl(path)
    for row in rows:
        if row.get("status") != "complete":
            raise ValueError(f"Incomplete human source in {path}")
    return sorted(str(row[identity_field]) for row in rows)


def validate_file_table(bundle_dir: Path, manifest: dict[str, Any]) -> None:
    """Validate exact bundle membership, sizes and hashes."""
    actual = {
        str(path.relative_to(bundle_dir))
        for path in bundle_dir.rglob("*")
        if path.is_file()
    }
    if actual != EXPECTED_FILES:
        raise ValueError(
            f"Bundle membership differs: missing={sorted(EXPECTED_FILES - actual)}, "
            f"extra={sorted(actual - EXPECTED_FILES)}"
        )
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError("Manifest file table is missing")
    if set(files) != EXPECTED_FILES - {"bundle_manifest.json"}:
        raise ValueError("Manifest payload membership differs")
    for relative, metadata in files.items():
        if not isinstance(metadata, dict):
            raise ValueError(f"Invalid file metadata: {relative}")
        path = bundle_dir / relative
        if metadata.get("sha256") != sha256_file(path):
            raise ValueError(f"File hash differs: {relative}")
        if metadata.get("bytes") != path.stat().st_size:
            raise ValueError(f"File size differs: {relative}")


def validate_config(bundle_dir: Path) -> dict[str, Any]:
    """Validate the fixed transparent inference configuration."""
    config = read_json(bundle_dir / "config" / "inference.json")
    required = {
        "schema_version",
        "model",
        "model_revision",
        "dtype",
        "tensor_parallel_size",
        "max_model_len",
        "gpu_memory_utilization",
        "max_num_seqs",
        "batch_size",
        "temperature",
        "seed",
        "thinking_enabled",
        "truncate_inputs",
        "sampling",
    }
    if set(config) != required:
        raise ValueError("Inference configuration fields differ")
    expected = {
        "schema_version": "1.0",
        "model": "Qwen/Qwen3.6-27B",
        "dtype": "bfloat16",
        "tensor_parallel_size": 1,
        "max_model_len": 32768,
        "temperature": 0.0,
        "seed": 42,
        "thinking_enabled": False,
        "truncate_inputs": False,
    }
    for field, value in expected.items():
        if config.get(field) != value:
            raise ValueError(f"Unexpected inference setting {field}")
    sampling = config.get("sampling")
    if not isinstance(sampling, dict) or set(sampling) != {
        "individual",
        "pairwise",
    }:
        raise ValueError("Sampling task configuration differs")
    return config


def validate_prompts(bundle_dir: Path) -> None:
    """Require generic prompts with the adopted codebook and no corpus identifiers."""
    individual = (bundle_dir / "prompts" / "individual.txt").read_text(
        encoding="utf-8"
    )
    pairwise = (bundle_dir / "prompts" / "pairwise.txt").read_text(
        encoding="utf-8"
    )
    for name, prompt in (("individual", individual), ("pairwise", pairwise)):
        if re.search(r"\b(?:T[0-9]{4}|C[0-9]{3}|LW[0-9]{2})\b", prompt):
            raise ValueError(f"Corpus identifier leaked into {name} prompt")
        for required in (
            "Player choice",
            "forced",
            "unclear",
            "schema-compliant JSON",
        ):
            if required.lower() not in prompt.lower():
                raise ValueError(f"Missing prompt rule {required!r} in {name}")
    for required in (
        "causal continuity",
        "profile coherence",
        "cautious",
        "noble",
        "tactical",
    ):
        if required.lower() not in individual.lower():
            raise ValueError(f"Missing individual codebook term {required!r}")
    for required in (
        "narrative distinctness",
        "A_more_cautious",
        "A_more_noble",
        "A_more_tactical",
        "similar",
    ):
        if required.lower() not in pairwise.lower():
            raise ValueError(f"Missing pairwise codebook term {required!r}")


def validate_schemas(bundle_dir: Path) -> None:
    """Validate schema exports against dependency-free Python constants."""
    namespace = runpy.run_path(str(bundle_dir / "schemas.py"))
    expected = {
        "individual": namespace.get("INDIVIDUAL_ANNOTATION_SCHEMA"),
        "pairwise": namespace.get("PAIRWISE_ANNOTATION_SCHEMA"),
    }
    for name, python_schema in expected.items():
        exported = read_json(bundle_dir / "schemas" / f"{name}.schema.json")
        if exported != python_schema:
            raise ValueError(f"Exported {name} schema differs")
        if exported.get("additionalProperties") is not False:
            raise ValueError(f"Top-level {name} schema is not closed")
        properties = exported.get("properties")
        if not isinstance(properties, dict):
            raise ValueError(f"Missing {name} schema properties")
        if set(exported.get("required", [])) != set(properties):
            raise ValueError(f"Required {name} fields differ from properties")
        if "uniqueItems" in json.dumps(exported, ensure_ascii=False):
            raise ValueError(
                f"{name} schema uses uniqueItems, unsupported by vLLM 0.28"
            )


def validate_individual_inputs(
    bundle_dir: Path,
    source_stories: dict[str, dict[str, Any]],
    expected_ids: list[str],
) -> list[dict[str, Any]]:
    """Validate the exact four public pilot stories."""
    rows = read_jsonl(bundle_dir / "inputs" / "individual.jsonl")
    if sorted(str(row.get("trajectory_id")) for row in rows) != expected_ids:
        raise ValueError("Pilot individual selection differs")
    expected_fields = {
        "schema_version",
        "task",
        "trajectory_id",
        "story_sha256",
        "story_text",
    }
    for row in rows:
        assert_no_forbidden_keys(row, "individual")
        if set(row) != expected_fields:
            raise ValueError("Individual input fields differ")
        trajectory_id = str(row["trajectory_id"])
        source = source_stories[trajectory_id]
        if row["task"] != "individual" or row["schema_version"] != "1.0":
            raise ValueError(f"Invalid individual envelope: {trajectory_id}")
        if row["story_text"] != source["story_text"]:
            raise ValueError(f"Individual story differs: {trajectory_id}")
        if row["story_sha256"] != source["story_sha256"]:
            raise ValueError(f"Individual story digest differs: {trajectory_id}")
        if sha256_text(str(row["story_text"])) != row["story_sha256"]:
            raise ValueError(f"Individual story hash is invalid: {trajectory_id}")
    return rows


def validate_pairwise_inputs(
    bundle_dir: Path,
    source_pairs: dict[str, dict[str, Any]],
    source_stories: dict[str, dict[str, Any]],
    expected_base_ids: list[str],
) -> list[dict[str, Any]]:
    """Validate the three canonical A/B inputs and empty B/A pilot file."""
    rows = read_jsonl(bundle_dir / "inputs" / "pairwise_ab.jsonl")
    reverse = read_jsonl(
        bundle_dir / "inputs" / "pairwise_ba.jsonl", allow_empty=True
    )
    if reverse:
        raise ValueError("Pilot must not contain B/A jobs")
    expected_ids = [f"{base}_AB" for base in expected_base_ids]
    if sorted(str(row.get("comparison_id")) for row in rows) != expected_ids:
        raise ValueError("Pilot pairwise selection differs")
    expected_fields = {
        "schema_version",
        "task",
        "comparison_id",
        "story_a",
        "story_b",
    }
    story_fields = {"trajectory_id", "story_sha256", "story_text"}
    for row in rows:
        assert_no_forbidden_keys(row, "pairwise_ab")
        if set(row) != expected_fields:
            raise ValueError("Pairwise input fields differ")
        comparison_id = str(row["comparison_id"])
        source = source_pairs[comparison_id]
        if row["task"] != "pairwise_ab" or row["schema_version"] != "1.0":
            raise ValueError(f"Invalid pairwise envelope: {comparison_id}")
        for side in ("story_a", "story_b"):
            story = row[side]
            if not isinstance(story, dict) or set(story) != story_fields:
                raise ValueError(f"Invalid {side}: {comparison_id}")
            trajectory_id = str(story["trajectory_id"])
            if trajectory_id != source[side]["trajectory_id"]:
                raise ValueError(f"Pair identity differs: {comparison_id}/{side}")
            public = source_stories[trajectory_id]
            if story["story_text"] != public["story_text"]:
                raise ValueError(f"Pair story differs: {comparison_id}/{side}")
            if story["story_sha256"] != public["story_sha256"]:
                raise ValueError(f"Pair story digest differs: {comparison_id}/{side}")
    return rows


def validate_runner_without_vllm(bundle_dir: Path) -> None:
    """Exercise the transferred runner's validation-only path."""
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            str(bundle_dir / "run_phase5.py"),
            "--bundle-dir",
            str(bundle_dir),
            "--output-dir",
            str(bundle_dir / "unused-validation-output"),
            "--validate-only",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    if result.returncode != 0:
        raise ValueError(
            "Transferred runner validation failed:\n"
            + result.stdout
            + "\n"
            + result.stderr
        )
    if "all payload hashes and input envelopes validated" not in result.stdout:
        raise ValueError("Transferred runner did not confirm validation")


def parse_args() -> argparse.Namespace:
    """Parse validator arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument("--bundle-dir", type=Path)
    parser.add_argument("--phase5-dir", type=Path)
    parser.add_argument("--annotation-dir", type=Path)
    return parser.parse_args()


def main() -> None:
    """Validate the complete phase-5.2 pilot bundle independently."""
    args = parse_args()
    book_id = str(args.book)
    phase5_dir = args.phase5_dir or Path("data/processed/phase5") / book_id
    annotation_dir = args.annotation_dir or (
        Path("data/for_trajectory_annotation") / book_id
    )
    bundle_dir = args.bundle_dir or (
        annotation_dir / "server_bundle" / f"{book_id}_phase5_pilot_v2"
    )
    manifest = read_json(bundle_dir / "bundle_manifest.json")
    if manifest.get("schema_version") != "1.0" or manifest.get("phase") != "5.2":
        raise ValueError("Unexpected bundle manifest schema")
    if manifest.get("book_id") != book_id or manifest.get("stage") != "pilot":
        raise ValueError("Bundle is not the requested pilot")
    validate_file_table(bundle_dir, manifest)
    config = validate_config(bundle_dir)
    validate_prompts(bundle_dir)
    validate_schemas(bundle_dir)

    story_rows = read_jsonl(phase5_dir / "trajectories.jsonl")
    pair_rows = read_jsonl(phase5_dir / "trajectory_pairs.jsonl")
    source_stories = {str(row["trajectory_id"]): row for row in story_rows}
    source_pairs = {str(row["comparison_id"]): row for row in pair_rows}
    expected_trajectories = completed_ids(
        annotation_dir / "human_trajectory_annotations.jsonl", "trajectory_id"
    )
    expected_pairs = completed_ids(
        annotation_dir / "human_pairwise_annotations.jsonl", "comparison_id"
    )
    individual_rows = validate_individual_inputs(
        bundle_dir, source_stories, expected_trajectories
    )
    pairwise_rows = validate_pairwise_inputs(
        bundle_dir, source_pairs, source_stories, expected_pairs
    )
    expected_counts = {
        "individual": 4,
        "pairwise_ab": 3,
        "pairwise_ba": 0,
        "total": 7,
    }
    if manifest.get("job_counts") != expected_counts:
        raise ValueError("Pilot job counts differ")
    selection = manifest.get("selection")
    if not isinstance(selection, dict):
        raise ValueError("Pilot selection manifest is missing")
    if selection.get("trajectory_ids") != expected_trajectories:
        raise ValueError("Manifest trajectory selection differs")
    if selection.get("base_comparison_ids") != expected_pairs:
        raise ValueError("Manifest comparison selection differs")
    privacy = manifest.get("privacy")
    if not isinstance(privacy, dict) or not all(
        privacy.get(field) is expected
        for field, expected in {
            "opaque_identifiers_only": True,
            "human_annotations_included": False,
            "private_metadata_included": False,
            "bop_metrics_included": False,
            "phase1_semantic_labels_included": False,
        }.items()
    ):
        raise ValueError("Privacy assertions differ")
    serialized_manifest = json.dumps(manifest, ensure_ascii=False).lower()
    if "human_trajectory_annotations" in serialized_manifest or (
        "human_pairwise_annotations" in serialized_manifest
    ):
        raise ValueError("Human annotation source leaked into the manifest")
    planning = manifest.get("context_planning")
    if not isinstance(planning, dict) or planning.get(
        "inputs_may_be_truncated"
    ) is not False:
        raise ValueError("No-truncation assertion is missing")
    maximum_estimate = planning.get("maximum_estimated_input_tokens")
    if not isinstance(maximum_estimate, int) or maximum_estimate + max(
        int(config["sampling"][task]["max_output_tokens"])
        for task in ("individual", "pairwise")
    ) > int(config["max_model_len"]):
        raise ValueError("Planning estimate exceeds the configured context window")

    validate_runner_without_vllm(bundle_dir)
    print(
        f"OK: pilot {manifest['run_id']} — {len(individual_rows)} individual and "
        f"{len(pairwise_rows)} canonical A/B jobs; bundle is blinded and autonomous"
    )


if __name__ == "__main__":
    main()
