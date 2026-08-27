"""Build a blinded, self-contained phase-5 inference bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import runpy
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_BOOK_ID = "LW01"
DEFAULT_MODEL = "Qwen/Qwen3.6-27B"
TASKS = ("individual", "pairwise_ab", "pairwise_ba")
FORBIDDEN_INPUT_KEYS = {
    "action",
    "annotation",
    "annotation_role",
    "compiled_weight",
    "edge_ids",
    "human_annotation",
    "morality",
    "node_ids",
    "outcome",
    "profile_id",
    "risk",
    "semantic_action",
    "semantic_morality",
    "semantic_risk",
    "split",
    "weight",
}


def utc_now() -> str:
    """Return one explicit UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def read_jsonl(path: Path, *, allow_empty: bool = False) -> list[dict[str, Any]]:
    """Read JSON objects from one JSON Lines file."""
    if not path.exists():
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
    """Write deterministic JSON Lines, including an intentional empty file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for row in rows
    ]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def write_json(path: Path, value: dict[str, Any]) -> None:
    """Write deterministic readable JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of one file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    """Return the SHA-256 digest of one UTF-8 string."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def relative_path(path: Path) -> str:
    """Render a repository-relative path when possible."""
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path.resolve())


def assert_no_forbidden_keys(value: Any, path: str) -> None:
    """Reject private or derived keys from public task inputs."""
    if isinstance(value, dict):
        forbidden = FORBIDDEN_INPUT_KEYS & set(value)
        if forbidden:
            raise ValueError(f"Private keys {sorted(forbidden)} in {path}")
        for key, child in value.items():
            assert_no_forbidden_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_no_forbidden_keys(child, f"{path}[{index}]")


def completed_human_ids(path: Path, identity_field: str) -> list[str]:
    """Read only opaque identities from completed local calibration records."""
    rows = read_jsonl(path)
    identities: list[str] = []
    for row in rows:
        identity = row.get(identity_field)
        if not isinstance(identity, str) or not identity:
            raise ValueError(f"Missing {identity_field} in {path}")
        if row.get("status") != "complete":
            raise ValueError(f"Human calibration is incomplete: {identity}")
        identities.append(identity)
    if len(set(identities)) != len(identities):
        raise ValueError(f"Duplicate human calibration identity in {path}")
    return identities


def individual_input(story: dict[str, Any]) -> dict[str, Any]:
    """Return the minimal public individual task envelope."""
    story_text = story.get("story_text")
    if not isinstance(story_text, str) or not story_text:
        raise ValueError(f"Empty public story {story.get('trajectory_id')}")
    if sha256_text(story_text) != story.get("story_sha256"):
        raise ValueError(f"Public story hash differs: {story.get('trajectory_id')}")
    return {
        "schema_version": "1.0",
        "task": "individual",
        "trajectory_id": story["trajectory_id"],
        "story_sha256": story["story_sha256"],
        "story_text": story_text,
    }


def pairwise_input(
    pair: dict[str, Any], stories: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Return the minimal public pairwise task envelope."""
    comparison_id = str(pair.get("comparison_id", ""))
    suffix = comparison_id.rsplit("_", 1)[-1]
    if suffix not in {"AB", "BA"}:
        raise ValueError(f"Pair has no canonical order suffix: {comparison_id}")
    result: dict[str, Any] = {
        "schema_version": "1.0",
        "task": f"pairwise_{suffix.lower()}",
        "comparison_id": comparison_id,
    }
    for side in ("a", "b"):
        pair_story = pair.get(f"story_{side}")
        if not isinstance(pair_story, dict):
            raise ValueError(f"Missing story {side} in {comparison_id}")
        trajectory_id = str(pair_story.get("trajectory_id", ""))
        source = stories.get(trajectory_id)
        if source is None:
            raise ValueError(f"Unknown story {trajectory_id} in {comparison_id}")
        if pair_story.get("story_text") != source.get("story_text"):
            raise ValueError(f"Pair story text differs in {comparison_id}/{side}")
        result[f"story_{side}"] = {
            "trajectory_id": trajectory_id,
            "story_sha256": source["story_sha256"],
            "story_text": source["story_text"],
        }
    if result["story_a"]["trajectory_id"] == result["story_b"]["trajectory_id"]:
        raise ValueError(f"Pair repeats one trajectory: {comparison_id}")
    return result


def load_schema_constants(schema_source: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load the dependency-free schema constants from the cluster source."""
    namespace = runpy.run_path(str(schema_source))
    individual = namespace.get("INDIVIDUAL_ANNOTATION_SCHEMA")
    pairwise = namespace.get("PAIRWISE_ANNOTATION_SCHEMA")
    if not isinstance(individual, dict) or not isinstance(pairwise, dict):
        raise ValueError(f"Schema constants are missing in {schema_source}")
    return individual, pairwise


def copy_runtime_assets(source_dir: Path, bundle_dir: Path) -> list[Path]:
    """Copy runner, schemas, prompts and instructions into the bundle."""
    relative_assets = [
        Path("run_phase5.py"),
        Path("schemas.py"),
        Path("RUN_INSTRUCTIONS.md"),
        Path("prompts/individual.txt"),
        Path("prompts/pairwise.txt"),
    ]
    outputs: list[Path] = []
    for relative in relative_assets:
        source = source_dir / relative
        if not source.is_file():
            raise FileNotFoundError(source)
        target = bundle_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        outputs.append(target)
    individual_schema, pairwise_schema = load_schema_constants(
        source_dir / "schemas.py"
    )
    individual_path = bundle_dir / "schemas" / "individual.schema.json"
    pairwise_path = bundle_dir / "schemas" / "pairwise.schema.json"
    write_json(individual_path, individual_schema)
    write_json(pairwise_path, pairwise_schema)
    outputs.extend((individual_path, pairwise_path))
    return outputs


def make_config(model: str, revision: str | None) -> dict[str, Any]:
    """Return the fixed pilot/final inference configuration."""
    return {
        "schema_version": "1.0",
        "model": model,
        "model_revision": revision,
        "dtype": "bfloat16",
        "tensor_parallel_size": 1,
        "max_model_len": 32768,
        "gpu_memory_utilization": 0.9,
        "max_num_seqs": 8,
        "batch_size": 4,
        "temperature": 0.0,
        "seed": 42,
        "thinking_enabled": False,
        "truncate_inputs": False,
        "sampling": {
            "individual": {"max_output_tokens": 1800},
            "pairwise": {"max_output_tokens": 1600},
        },
    }


def estimated_input_tokens(prompt: str, stories: list[str]) -> int:
    """Return the declared conservative character-count planning estimate."""
    payload_characters = len(prompt) + sum(len(story) for story in stories) + 500
    return (payload_characters + 3) // 4


def parse_args() -> argparse.Namespace:
    """Parse the phase-5.2 bundle-builder command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument("--stage", choices=("pilot", "final"), default="pilot")
    parser.add_argument("--run-id")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--phase5-dir", type=Path)
    parser.add_argument("--annotation-dir", type=Path)
    parser.add_argument("--cluster-source-dir", type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--model-revision")
    return parser.parse_args()


def main() -> None:
    """Build one immutable pilot or final cluster bundle."""
    args = parse_args()
    book_id = str(args.book)
    stage = str(args.stage)
    run_id = args.run_id or f"{book_id}_phase5_{stage}_v1"
    phase5_dir = args.phase5_dir or Path("data/processed/phase5") / book_id
    annotation_dir = args.annotation_dir or (
        Path("data/for_trajectory_annotation") / book_id
    )
    cluster_source_dir = args.cluster_source_dir or Path("cluster_scripts/phase5")
    bundle_dir = args.output_dir or annotation_dir / "server_bundle" / run_id
    if bundle_dir.exists() and any(bundle_dir.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty bundle: {bundle_dir}")
    bundle_dir.mkdir(parents=True, exist_ok=True)

    trajectories_path = phase5_dir / "trajectories.jsonl"
    pairs_path = phase5_dir / "trajectory_pairs.jsonl"
    stories_rows = read_jsonl(trajectories_path)
    pair_rows = read_jsonl(pairs_path)
    stories = {str(row["trajectory_id"]): row for row in stories_rows}
    if len(stories) != 14:
        raise ValueError(f"Expected 14 unique public stories, found {len(stories)}")

    if stage == "pilot":
        selected_trajectories = completed_human_ids(
            annotation_dir / "human_trajectory_annotations.jsonl",
            "trajectory_id",
        )
        selected_comparisons = completed_human_ids(
            annotation_dir / "human_pairwise_annotations.jsonl",
            "comparison_id",
        )
        if len(selected_trajectories) != 4 or len(selected_comparisons) != 3:
            raise ValueError("Pilot requires exactly four stories and three pairs")
    else:
        selected_trajectories = sorted(stories)
        selected_comparisons = sorted(
            {
                str(row["comparison_id"]).rsplit("_", 1)[0]
                for row in pair_rows
            }
        )
        if len(selected_comparisons) != 6:
            raise ValueError("Final bundle requires six canonical pairs")

    unknown_trajectories = set(selected_trajectories) - set(stories)
    if unknown_trajectories:
        raise ValueError(f"Unknown pilot stories: {sorted(unknown_trajectories)}")
    individual_rows = [
        individual_input(stories[trajectory_id])
        for trajectory_id in sorted(selected_trajectories)
    ]

    pair_inputs = [pairwise_input(row, stories) for row in pair_rows]
    if stage == "pilot":
        pair_inputs = [
            row
            for row in pair_inputs
            if row["comparison_id"].endswith("_AB")
            and row["comparison_id"].rsplit("_", 1)[0]
            in set(selected_comparisons)
        ]
    else:
        pair_inputs = [
            row
            for row in pair_inputs
            if row["comparison_id"].rsplit("_", 1)[0]
            in set(selected_comparisons)
        ]
    pair_inputs.sort(key=lambda row: str(row["comparison_id"]))
    pairwise_ab_rows = [
        row for row in pair_inputs if row["task"] == "pairwise_ab"
    ]
    pairwise_ba_rows = [
        row for row in pair_inputs if row["task"] == "pairwise_ba"
    ]
    expected_pair_count = 3 if stage == "pilot" else 12
    if len(pair_inputs) != expected_pair_count:
        raise ValueError(
            f"Expected {expected_pair_count} ordered pairs, found {len(pair_inputs)}"
        )

    for task, rows in (
        ("individual", individual_rows),
        ("pairwise_ab", pairwise_ab_rows),
        ("pairwise_ba", pairwise_ba_rows),
    ):
        for index, row in enumerate(rows):
            assert_no_forbidden_keys(row, f"{task}[{index}]")

    payload_paths = copy_runtime_assets(cluster_source_dir, bundle_dir)
    input_paths: list[Path] = []
    for task, rows in (
        ("individual", individual_rows),
        ("pairwise_ab", pairwise_ab_rows),
        ("pairwise_ba", pairwise_ba_rows),
    ):
        path = bundle_dir / "inputs" / f"{task}.jsonl"
        write_jsonl(path, rows)
        input_paths.append(path)
    config_path = bundle_dir / "config" / "inference.json"
    config = make_config(str(args.model), args.model_revision)
    write_json(config_path, config)
    payload_paths.extend((*input_paths, config_path))

    individual_prompt = (
        bundle_dir / "prompts" / "individual.txt"
    ).read_text(encoding="utf-8")
    pairwise_prompt = (bundle_dir / "prompts" / "pairwise.txt").read_text(
        encoding="utf-8"
    )
    estimates = [
        estimated_input_tokens(individual_prompt, [str(row["story_text"])])
        for row in individual_rows
    ]
    estimates.extend(
        estimated_input_tokens(
            pairwise_prompt,
            [str(row["story_a"]["story_text"]), str(row["story_b"]["story_text"])],
        )
        for row in pair_inputs
    )
    maximum_estimated_input_tokens = max(estimates) if estimates else 0
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "phase": "5.2",
        "status": "ready",
        "book_id": book_id,
        "stage": stage,
        "run_id": run_id,
        "created_at_utc": utc_now(),
        "job_counts": {
            "individual": len(individual_rows),
            "pairwise_ab": len(pairwise_ab_rows),
            "pairwise_ba": len(pairwise_ba_rows),
            "total": len(individual_rows) + len(pair_inputs),
        },
        "selection": {
            "trajectory_ids": sorted(selected_trajectories),
            "base_comparison_ids": sorted(selected_comparisons),
            "pilot_pair_order": "AB only" if stage == "pilot" else None,
        },
        "privacy": {
            "opaque_identifiers_only": True,
            "human_annotations_included": False,
            "private_metadata_included": False,
            "bop_metrics_included": False,
            "phase1_semantic_labels_included": False,
        },
        "context_planning": {
            "method": "ceil((prompt characters + story characters + 500) / 4)",
            "maximum_estimated_input_tokens": maximum_estimated_input_tokens,
            "runtime_exact_token_check_required": True,
            "inputs_may_be_truncated": False,
        },
        "source_artifacts": {
            relative_path(trajectories_path): sha256_file(trajectories_path),
            relative_path(pairs_path): sha256_file(pairs_path),
        },
        "files": {
            str(path.relative_to(bundle_dir)): {
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in sorted(payload_paths)
        },
    }
    manifest_path = bundle_dir / "bundle_manifest.json"
    write_json(manifest_path, manifest)
    print(f"Bundle: {bundle_dir}")
    print(
        f"Stage {stage}: {len(individual_rows)} individual, "
        f"{len(pairwise_ab_rows)} A/B, {len(pairwise_ba_rows)} B/A jobs"
    )
    print(
        "Maximum planning estimate: "
        f"{maximum_estimated_input_tokens} input tokens"
    )
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
