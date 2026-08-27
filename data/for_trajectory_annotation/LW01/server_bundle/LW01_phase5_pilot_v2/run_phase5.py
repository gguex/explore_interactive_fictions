"""Run a self-contained phase-5 annotation bundle with vLLM on the cluster."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from schemas import (
    INDIVIDUAL_ANNOTATION_SCHEMA,
    PAIRWISE_ANNOTATION_SCHEMA,
    validate_individual_annotation,
    validate_pairwise_annotation,
)

TASKS = ("individual", "pairwise_ab", "pairwise_ba")
OUTPUT_FILES = {
    "individual": "individual.jsonl",
    "pairwise_ab": "pairwise_ab.jsonl",
    "pairwise_ba": "pairwise_ba.jsonl",
}


def utc_now() -> str:
    """Return one explicit UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


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


def read_json(path: Path) -> dict[str, Any]:
    """Read one JSON object."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected one JSON object in {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a possibly empty JSON Lines input."""
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
            raise ValueError(f"{path}:{line_number} is not a JSON object")
        rows.append(value)
    return rows


def write_json(path: Path, value: dict[str, Any]) -> None:
    """Atomically write one readable JSON object."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    """Append and flush one deterministic JSON Lines record."""
    line = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def batches(rows: list[dict[str, Any]], size: int) -> Iterator[list[dict[str, Any]]]:
    """Yield fixed-size row batches."""
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def verify_bundle(bundle_dir: Path) -> dict[str, Any]:
    """Verify every payload hash declared by the bundle manifest."""
    manifest_path = bundle_dir / "bundle_manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("schema_version") != "1.0" or manifest.get("phase") != "5.2":
        raise ValueError("Unsupported bundle manifest")
    declared = manifest.get("files")
    if not isinstance(declared, dict) or not declared:
        raise ValueError("Bundle manifest has no file table")
    for relative, metadata in declared.items():
        if not isinstance(relative, str) or not isinstance(metadata, dict):
            raise ValueError("Invalid bundle file-table entry")
        path = bundle_dir / relative
        if not path.is_file():
            raise FileNotFoundError(f"Missing bundle payload: {relative}")
        if sha256_file(path) != metadata.get("sha256"):
            raise ValueError(f"Bundle payload hash differs: {relative}")
        if path.stat().st_size != metadata.get("bytes"):
            raise ValueError(f"Bundle payload size differs: {relative}")
    return manifest


def validate_schema_exports(bundle_dir: Path) -> None:
    """Require exported schemas to match the runner's Python constants."""
    expected = {
        "schemas/individual.schema.json": INDIVIDUAL_ANNOTATION_SCHEMA,
        "schemas/pairwise.schema.json": PAIRWISE_ANNOTATION_SCHEMA,
    }
    for relative, schema in expected.items():
        if read_json(bundle_dir / relative) != schema:
            raise ValueError(f"Exported schema differs from schemas.py: {relative}")


def validate_input_rows(
    bundle_dir: Path, manifest: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    """Load task inputs and enforce identities, counts and story hashes."""
    result: dict[str, list[dict[str, Any]]] = {}
    counts = manifest.get("job_counts")
    if not isinstance(counts, dict):
        raise ValueError("Bundle manifest has no job counts")
    for task in TASKS:
        rows = read_jsonl(bundle_dir / "inputs" / f"{task}.jsonl")
        if len(rows) != counts.get(task):
            raise ValueError(f"Job count differs for {task}")
        identities: set[str] = set()
        for row in rows:
            if task == "individual":
                identity = str(row.get("trajectory_id", ""))
                story_text = row.get("story_text")
                story_hash = row.get("story_sha256")
                if set(row) != {
                    "schema_version",
                    "task",
                    "trajectory_id",
                    "story_sha256",
                    "story_text",
                }:
                    raise ValueError(f"Unexpected individual input schema: {identity}")
                if row.get("task") != task or row.get("schema_version") != "1.0":
                    raise ValueError(f"Invalid individual envelope: {identity}")
                if not re.fullmatch(r"T[0-9]{4}", identity):
                    raise ValueError(f"Invalid trajectory identifier: {identity}")
                if not isinstance(story_text, str) or not story_text:
                    raise ValueError(f"Empty story: {identity}")
                if sha256_text(story_text) != story_hash:
                    raise ValueError(f"Story hash differs: {identity}")
            else:
                identity = str(row.get("comparison_id", ""))
                if set(row) != {
                    "schema_version",
                    "task",
                    "comparison_id",
                    "story_a",
                    "story_b",
                }:
                    raise ValueError(f"Unexpected pairwise input schema: {identity}")
                if row.get("task") != task or row.get("schema_version") != "1.0":
                    raise ValueError(f"Invalid pairwise envelope: {identity}")
                expected_suffix = "AB" if task == "pairwise_ab" else "BA"
                if not re.fullmatch(rf"C[0-9]{{3}}_{expected_suffix}", identity):
                    raise ValueError(f"Invalid comparison identifier: {identity}")
                story_ids: set[str] = set()
                for side in ("story_a", "story_b"):
                    story = row.get(side)
                    if not isinstance(story, dict) or set(story) != {
                        "trajectory_id",
                        "story_sha256",
                        "story_text",
                    }:
                        raise ValueError(f"Invalid {side} envelope: {identity}")
                    trajectory_id = story.get("trajectory_id")
                    story_text = story.get("story_text")
                    if not isinstance(trajectory_id, str) or not re.fullmatch(
                        r"T[0-9]{4}", trajectory_id
                    ):
                        raise ValueError(f"Invalid {side} identity: {identity}")
                    if trajectory_id in story_ids:
                        raise ValueError(f"Pair repeats one story: {identity}")
                    story_ids.add(trajectory_id)
                    if not isinstance(story_text, str) or not story_text:
                        raise ValueError(f"Empty {side}: {identity}")
                    if sha256_text(story_text) != story.get("story_sha256"):
                        raise ValueError(f"Story hash differs in {identity}/{side}")
            if identity in identities:
                raise ValueError(f"Duplicate task identity: {identity}")
            identities.add(identity)
        result[task] = rows
    if sum(len(rows) for rows in result.values()) != counts.get("total"):
        raise ValueError("Total job count differs")
    return result


def format_messages(tokenizer: Any, system_prompt: str, user_text: str) -> str:
    """Apply the Qwen chat template with thinking explicitly disabled."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]
    try:
        rendered = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
    except TypeError as exc:
        raise RuntimeError(
            "The installed tokenizer does not accept enable_thinking=False; "
            "upgrade transformers instead of running with an unknown thinking mode."
        ) from exc
    if not isinstance(rendered, str):
        raise TypeError("Tokenizer returned a non-text chat prompt")
    return rendered


def row_identity(task: str, row: dict[str, Any]) -> str:
    """Return the opaque identity for one task input."""
    field = "trajectory_id" if task == "individual" else "comparison_id"
    return str(row[field])


def user_payload(task: str, row: dict[str, Any]) -> str:
    """Render only the public input fields shown to the model."""
    if task == "individual":
        value = {
            "trajectory_id": row["trajectory_id"],
            "complete_story": row["story_text"],
        }
    else:
        value = {
            "comparison_id": row["comparison_id"],
            "trajectory_a_id": row["story_a"]["trajectory_id"],
            "story_a": row["story_a"]["story_text"],
            "trajectory_b_id": row["story_b"]["trajectory_id"],
            "story_b": row["story_b"]["story_text"],
        }
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def valid_story_references(story_text: str) -> tuple[set[str], set[str], set[str]]:
    """Return step, chosen-choice and paragraph references present in one story."""
    steps = set(re.findall(r"\[STEP (S[0-9]{3})\]", story_text))
    choices = set(
        re.findall(r"\[CHOSEN ACTION\]\n(S[0-9]{3}-C[0-9]{2})\.", story_text)
    )
    paragraphs = set(re.findall(r"\[PARAGRAPH ([0-9]+)\]", story_text))
    return steps, choices, paragraphs


def validate_annotation_against_input(
    task: str, annotation: dict[str, Any], row: dict[str, Any]
) -> list[str]:
    """Check generated identities and evidence against the exact public input."""
    if task == "individual":
        errors = validate_individual_annotation(annotation)
        if annotation.get("trajectory_id") != row["trajectory_id"]:
            errors.append("trajectory_id differs from the input")
        _, choices, paragraphs = valid_story_references(row["story_text"])
        profile = annotation.get("perceived_profile")
        if isinstance(profile, dict):
            for axis in ("risk", "morality", "action"):
                value = profile.get(axis)
                if not isinstance(value, dict):
                    continue
                for field in (
                    "supporting_choice_refs",
                    "counterevidence_choice_refs",
                ):
                    refs = value.get(field)
                    if isinstance(refs, list):
                        for reference in refs:
                            if reference not in choices:
                                errors.append(
                                    f"{axis}.{field} cites a non-chosen action: "
                                    f"{reference}"
                                )
        coherence = annotation.get("profile_coherence")
        if isinstance(coherence, dict):
            for field in (
                "supporting_choice_refs",
                "counterevidence_choice_refs",
            ):
                refs = coherence.get(field)
                if isinstance(refs, list):
                    for reference in refs:
                        if reference not in choices:
                            errors.append(
                                f"profile_coherence cites a non-chosen action: "
                                f"{reference}"
                            )
        continuity = annotation.get("causal_continuity")
        if isinstance(continuity, dict):
            refs = continuity.get("evidence_paragraph_ids")
            if isinstance(refs, list):
                for reference in refs:
                    if reference not in paragraphs:
                        errors.append(f"unknown paragraph evidence: {reference}")
        return errors

    errors = validate_pairwise_annotation(annotation)
    if annotation.get("comparison_id") != row["comparison_id"]:
        errors.append("comparison_id differs from the input")
    for side in ("a", "b"):
        story = row[f"story_{side}"]
        if annotation.get(f"trajectory_{side}_id") != story["trajectory_id"]:
            errors.append(f"trajectory_{side}_id differs from the input")
        steps, choices, _ = valid_story_references(story["story_text"])
        refs = annotation.get(f"evidence_story_{side}")
        if isinstance(refs, list):
            for reference in refs:
                valid = choices if "-C" in str(reference) else steps
                if reference not in valid:
                    errors.append(f"unknown story {side.upper()} evidence: {reference}")
    return errors


def existing_output_ids(
    path: Path, task: str, input_rows: list[dict[str, Any]]
) -> set[str]:
    """Load and validate already completed identities for resume mode."""
    if not path.exists():
        return set()
    inputs = {row_identity(task, row): row for row in input_rows}
    identities: set[str] = set()
    for line_number, row in enumerate(read_jsonl(path), 1):
        identity = row.get("input_id")
        if row.get("task") != task or not isinstance(identity, str):
            raise ValueError(f"Invalid resumed output {path}:{line_number}")
        if identity in identities:
            raise ValueError(f"Duplicate resumed output identity: {identity}")
        if identity not in inputs:
            raise ValueError(f"Resumed output is absent from inputs: {identity}")
        annotation = row.get("annotation")
        if not isinstance(annotation, dict):
            raise ValueError(f"Invalid resumed annotation object: {identity}")
        errors = validate_annotation_against_input(
            task, annotation, inputs[identity]
        )
        if errors:
            raise ValueError(
                f"Invalid resumed annotation {identity}: {'; '.join(errors)}"
            )
        identities.add(identity)
    return identities


def hardware_summary() -> dict[str, Any]:
    """Return auditable runtime and accelerator information when available."""
    result: dict[str, Any] = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": sys.version,
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
    }
    try:
        import torch

        result["torch_version"] = torch.__version__
        result["cuda_version"] = torch.version.cuda
        result["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            result["gpu_count"] = torch.cuda.device_count()
            result["gpus"] = [
                torch.cuda.get_device_name(index)
                for index in range(torch.cuda.device_count())
            ]
    except Exception as exc:  # pragma: no cover - cluster diagnostic
        result["torch_diagnostic_error"] = f"{type(exc).__name__}: {exc}"
    return result


def load_vllm() -> tuple[Any, Any, Any]:
    """Import vLLM only when inference is actually requested."""
    from vllm import LLM, SamplingParams
    from vllm.sampling_params import StructuredOutputsParams

    return LLM, SamplingParams, StructuredOutputsParams


def output_wrapper(
    task: str,
    row: dict[str, Any],
    annotation: dict[str, Any],
    raw_text: str,
    prompt_hash: str,
    input_tokens: int,
    generated_tokens: int,
    finish_reason: str | None,
) -> dict[str, Any]:
    """Build one immutable raw-output envelope."""
    return {
        "schema_version": "1.0",
        "task": task,
        "input_id": row_identity(task, row),
        "input_sha256": sha256_text(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        ),
        "prompt_sha256": prompt_hash,
        "input_token_count": input_tokens,
        "generated_token_count": generated_tokens,
        "finish_reason": finish_reason,
        "annotation": annotation,
        "raw_model_output": raw_text,
    }


def run_task(
    *,
    task: str,
    rows: list[dict[str, Any]],
    bundle_dir: Path,
    output_dir: Path,
    llm: Any,
    tokenizer: Any,
    sampling_params_type: Any,
    structured_outputs_type: Any,
    config: dict[str, Any],
    resume: bool,
) -> tuple[int, int, list[int]]:
    """Run one task family, streaming valid and quarantined outputs."""
    prompt_name = "individual.txt" if task == "individual" else "pairwise.txt"
    prompt_text = (bundle_dir / "prompts" / prompt_name).read_text(encoding="utf-8")
    prompt_hash = sha256_text(prompt_text)
    schema = (
        INDIVIDUAL_ANNOTATION_SCHEMA
        if task == "individual"
        else PAIRWISE_ANNOTATION_SCHEMA
    )
    sampling_key = "individual" if task == "individual" else "pairwise"
    task_config = config["sampling"][sampling_key]
    sampling_params = sampling_params_type(
        temperature=float(config["temperature"]),
        seed=int(config["seed"]),
        max_tokens=int(task_config["max_output_tokens"]),
        structured_outputs=structured_outputs_type(
            json=json.dumps(schema, ensure_ascii=False)
        ),
    )
    output_path = output_dir / OUTPUT_FILES[task]
    completed = existing_output_ids(output_path, task, rows) if resume else set()
    pending = [row for row in rows if row_identity(task, row) not in completed]
    successes = 0
    quarantined = 0
    token_counts: list[int] = []
    for batch_number, batch in enumerate(
        batches(pending, int(config["batch_size"])), 1
    ):
        eligible_rows: list[dict[str, Any]] = []
        prompts: list[str] = []
        input_lengths: list[int] = []
        for row in batch:
            rendered = format_messages(
                tokenizer, prompt_text, user_payload(task, row)
            )
            token_count = len(
                tokenizer.encode(rendered, add_special_tokens=False)
            )
            token_counts.append(token_count)
            if token_count + int(task_config["max_output_tokens"]) > int(
                config["max_model_len"]
            ):
                append_jsonl(
                    output_dir / "quarantine.jsonl",
                    {
                        "schema_version": "1.0",
                        "task": task,
                        "input_id": row_identity(task, row),
                        "reason": "context_window_exceeded",
                        "input_token_count": token_count,
                        "max_output_tokens": task_config["max_output_tokens"],
                        "max_model_len": config["max_model_len"],
                    },
                )
                quarantined += 1
                continue
            eligible_rows.append(row)
            prompts.append(rendered)
            input_lengths.append(token_count)
        if not eligible_rows:
            continue
        print(
            f"[{task} batch {batch_number}] generating {len(eligible_rows)} jobs",
            flush=True,
        )
        outputs = llm.generate(prompts, sampling_params, use_tqdm=False)
        if len(outputs) != len(eligible_rows):
            raise RuntimeError(f"vLLM output count differs for {task}")
        for row, output, input_tokens in zip(
            eligible_rows, outputs, input_lengths, strict=True
        ):
            identity = row_identity(task, row)
            completion = output.outputs[0]
            raw_text = completion.text
            finish_reason = getattr(completion, "finish_reason", None)
            try:
                annotation = json.loads(raw_text)
                if not isinstance(annotation, dict):
                    raise ValueError("model output is not one JSON object")
                errors = validate_annotation_against_input(task, annotation, row)
                if finish_reason == "length":
                    errors.append("generation ended at the output-token limit")
                if errors:
                    raise ValueError("; ".join(errors))
            except Exception as exc:
                append_jsonl(
                    output_dir / "quarantine.jsonl",
                    {
                        "schema_version": "1.0",
                        "task": task,
                        "input_id": identity,
                        "reason": "invalid_model_output",
                        "error": f"{type(exc).__name__}: {exc}",
                        "raw_model_output": raw_text,
                        "finish_reason": finish_reason,
                    },
                )
                quarantined += 1
                continue
            append_jsonl(
                output_path,
                output_wrapper(
                    task,
                    row,
                    annotation,
                    raw_text,
                    prompt_hash,
                    input_tokens,
                    len(getattr(completion, "token_ids", [])),
                    finish_reason,
                ),
            )
            successes += 1
    return successes, quarantined, token_counts


def parse_args() -> argparse.Namespace:
    """Parse the standalone cluster command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate bundle integrity without importing vLLM or loading the model.",
    )
    return parser.parse_args()


def main() -> None:
    """Validate the bundle, run all requested jobs and record the environment."""
    args = parse_args()
    bundle_dir = args.bundle_dir.resolve()
    output_dir = args.output_dir.resolve()
    manifest = verify_bundle(bundle_dir)
    validate_schema_exports(bundle_dir)
    task_rows = validate_input_rows(bundle_dir, manifest)
    config = read_json(bundle_dir / "config" / "inference.json")
    if args.validate_only:
        print(
            f"OK: {manifest['run_id']} — {manifest['job_counts']['total']} jobs, "
            "all payload hashes and input envelopes validated"
        )
        return

    if output_dir.exists() and any(output_dir.iterdir()) and not args.resume:
        raise FileExistsError(
            f"Output directory is not empty; use --resume: {output_dir}"
        )
    if (
        args.resume
        and output_dir.exists()
        and any(output_dir.iterdir())
        and not (output_dir / "run_manifest.json").is_file()
    ):
        raise FileNotFoundError("Cannot resume without run_manifest.json")
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename in (*OUTPUT_FILES.values(), "quarantine.jsonl"):
        (output_dir / filename).touch(exist_ok=True)
    manifest_path = output_dir / "run_manifest.json"
    bundle_manifest_hash = sha256_file(bundle_dir / "bundle_manifest.json")
    if args.resume and manifest_path.exists():
        previous = read_json(manifest_path)
        if previous.get("bundle_manifest_sha256") != bundle_manifest_hash:
            raise ValueError("Resume output belongs to another bundle")

    started_at = utc_now()
    run_manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "phase": "5.2-cluster-run",
        "status": "running",
        "run_id": manifest["run_id"],
        "stage": manifest["stage"],
        "bundle_manifest_sha256": bundle_manifest_hash,
        "started_at_utc": started_at,
        "configured_model": config["model"],
        "configured_revision": config.get("model_revision"),
        "runtime": hardware_summary(),
    }
    write_json(manifest_path, run_manifest)

    llm_type, sampling_params_type, structured_outputs_type = load_vllm()
    model_kwargs: dict[str, Any] = {
        "model": config["model"],
        "tensor_parallel_size": int(config["tensor_parallel_size"]),
        "dtype": config["dtype"],
        "max_model_len": int(config["max_model_len"]),
        "gpu_memory_utilization": float(config["gpu_memory_utilization"]),
        "max_num_seqs": int(config["max_num_seqs"]),
    }
    if config.get("model_revision"):
        model_kwargs["revision"] = config["model_revision"]
    print(f"Loading {config['model']} with vLLM", flush=True)
    llm = llm_type(**model_kwargs)
    tokenizer = llm.get_tokenizer()

    counts: dict[str, dict[str, int]] = {}
    all_input_tokens: list[int] = []
    for task in TASKS:
        success, quarantine, token_counts = run_task(
            task=task,
            rows=task_rows[task],
            bundle_dir=bundle_dir,
            output_dir=output_dir,
            llm=llm,
            tokenizer=tokenizer,
            sampling_params_type=sampling_params_type,
            structured_outputs_type=structured_outputs_type,
            config=config,
            resume=args.resume,
        )
        counts[task] = {"written": success, "quarantined": quarantine}
        all_input_tokens.extend(token_counts)

    model_config = getattr(getattr(llm, "llm_engine", None), "model_config", None)
    hf_config = getattr(model_config, "hf_config", None)
    resolved_revision = getattr(hf_config, "_commit_hash", None)
    run_manifest.update(
        {
            "status": "complete",
            "completed_at_utc": utc_now(),
            "vllm_version": importlib.metadata.version("vllm"),
            "resolved_model_revision": resolved_revision,
            "job_results": counts,
            "input_token_summary": {
                "minimum": min(all_input_tokens) if all_input_tokens else 0,
                "maximum": max(all_input_tokens) if all_input_tokens else 0,
                "measured_jobs": len(all_input_tokens),
            },
            "output_files": {
                path.name: {
                    "sha256": sha256_file(path),
                    "bytes": path.stat().st_size,
                }
                for path in sorted(output_dir.glob("*.jsonl"))
            },
        }
    )
    write_json(manifest_path, run_manifest)
    print(
        f"Complete: {sum(row['written'] for row in counts.values())} valid outputs, "
        f"{sum(row['quarantined'] for row in counts.values())} quarantined",
        flush=True,
    )


if __name__ == "__main__":
    main()
