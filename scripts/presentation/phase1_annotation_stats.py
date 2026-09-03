#!/usr/bin/env python3
"""Build reproducible phase-1 annotation statistics for the presentation."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any

SEMANTIC_FIELDS = (
    "semantic_risk",
    "semantic_morality",
    "semantic_action",
)
TEXT_FIELDS = ("realisation_value", "warnings")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize phase-1 calibration and full-book annotations."
    )
    parser.add_argument("--book", default="LW01", help="Book identifier.")
    parser.add_argument("--gold", type=Path, help="Human calibration CSV.")
    parser.add_argument(
        "--calibration-output", type=Path, help="Final LLM calibration CSV."
    )
    parser.add_argument("--full-edges", type=Path, help="Full annotation CSV.")
    parser.add_argument("--nodes", type=Path, help="Complete nodes CSV.")
    parser.add_argument("--output", type=Path, help="Output JSON path.")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def normalize(value: str | None) -> str:
    return (value or "").strip()


def edge_key(row: dict[str, str]) -> tuple[str, str, str]:
    """Use edge text to distinguish parallel edges with the same endpoints."""
    return (
        normalize(row.get("source_id")),
        normalize(row.get("target_id")),
        normalize(row.get("edge_text")),
    )


def unique_edges(
    rows: list[dict[str, str]], path: Path
) -> dict[tuple[str, str, str], dict[str, str]]:
    indexed: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in rows:
        key = edge_key(row)
        if key in indexed:
            msg = f"Duplicate transition record in {path}: {key}"
            raise ValueError(msg)
        indexed[key] = row
    return indexed


def percentage(count: int, total: int) -> float:
    return round(100 * count / total, 1) if total else 0.0


def agreement_summary(
    field: str,
    keys: list[tuple[str, str, str]],
    gold: dict[tuple[str, str, str], dict[str, str]],
    model: dict[tuple[str, str, str], dict[str, str]],
) -> dict[str, Any]:
    disagreements = [
        {
            "source_id": key[0],
            "target_id": key[1],
            "gold": normalize(gold[key].get(field)),
            "model": normalize(model[key].get(field)),
        }
        for key in keys
        if normalize(gold[key].get(field)) != normalize(model[key].get(field))
    ]
    total = len(keys)
    agreement_count = total - len(disagreements)
    return {
        "evaluated": total,
        "agreements": agreement_count,
        "disagreements": len(disagreements),
        "agreement_percent": percentage(agreement_count, total),
        "details": disagreements,
    }


def calibration_summary(
    gold_rows: list[dict[str, str]],
    model_rows: list[dict[str, str]],
    gold_path: Path,
    model_path: Path,
) -> dict[str, Any]:
    gold = unique_edges(gold_rows, gold_path)
    model = unique_edges(model_rows, model_path)
    gold_keys = set(gold)
    model_keys = set(model)
    common_keys = sorted(gold_keys & model_keys)

    transition_type = agreement_summary(
        "transition_type", common_keys, gold, model
    )
    semantic_keys = [
        key
        for key in common_keys
        if normalize(gold[key].get("transition_type")) == "explicit_choice"
        and normalize(model[key].get("transition_type")) == "explicit_choice"
    ]
    semantic = {
        field: agreement_summary(field, semantic_keys, gold, model)
        for field in SEMANTIC_FIELDS
    }
    unscored_text = {
        field: agreement_summary(field, common_keys, gold, model)
        for field in TEXT_FIELDS
    }
    scored_disagreements = transition_type["disagreements"] + sum(
        summary["disagreements"] for summary in semantic.values()
    )

    return {
        "paragraphs": len(
            {normalize(row.get("source_id")) for row in gold_rows}
        ),
        "reference_transitions": len(gold_rows),
        "model_transitions": len(model_rows),
        "matched_transition_records": len(common_keys),
        "missing_transition_records": len(gold_keys - model_keys),
        "extra_transition_records": len(model_keys - gold_keys),
        "field_agreement": {
            "transition_type": transition_type,
            **semantic,
        },
        "scored_disagreements_total": scored_disagreements,
        "unscored_text_fields": unscored_text,
        "scope_note": (
            "Only topology, transition_type, and the three semantic axes are "
            "scored. Free-text realisation_value and warnings are reported "
            "separately because literal equality is not a reliable quality score."
        ),
    }


def distribution(values: list[str]) -> dict[str, dict[str, float | int]]:
    counts = Counter(values)
    total = len(values)
    return {
        label: {"count": count, "percent": percentage(count, total)}
        for label, count in sorted(counts.items())
    }


def full_annotation_summary(
    rows: list[dict[str, str]], node_rows: list[dict[str, str]]
) -> dict[str, Any]:
    node_ids = {normalize(row.get("node_id")) for row in node_rows}
    unknown_sources = {
        normalize(row.get("source_id")) for row in rows
    } - node_ids
    if unknown_sources:
        msg = f"Transitions have unknown source paragraphs: {sorted(unknown_sources)}"
        raise ValueError(msg)

    outgoing_counts = Counter(normalize(row.get("source_id")) for row in rows)
    degrees = [outgoing_counts.get(node_id, 0) for node_id in node_ids]
    nonterminal_degrees = [degree for degree in degrees if degree > 0]
    explicit_choices = [
        row
        for row in rows
        if normalize(row.get("transition_type")) == "explicit_choice"
    ]
    semantic_axes = {
        field: distribution([normalize(row.get(field)) for row in explicit_choices])
        for field in SEMANTIC_FIELDS
    }
    warning_count = sum(bool(normalize(row.get("warnings"))) for row in rows)
    transition_types = tuple(
        sorted({normalize(row.get("transition_type")) for row in rows})
    )
    return {
        "paragraph_structure": {
            "paragraphs": len(node_rows),
            "paragraph_statuses": distribution(
                [normalize(row.get("absorbing_status")) for row in node_rows]
            ),
            "paragraphs_with_outgoing_transitions": len(nonterminal_degrees),
            "terminal_paragraphs": degrees.count(0),
            "single_transition_paragraphs": degrees.count(1),
            "branching_paragraphs": sum(degree >= 2 for degree in degrees),
            "outgoing_transition_count": distribution(
                [str(degree) for degree in degrees]
            ),
            "mean_transitions_per_nonterminal_paragraph": round(
                sum(nonterminal_degrees) / len(nonterminal_degrees), 2
            ),
            "median_transitions_per_nonterminal_paragraph": median(
                nonterminal_degrees
            ),
            "maximum_transitions_from_one_paragraph": max(degrees),
            "paragraphs_with_enemies": sum(
                normalize(row.get("enemies")) not in {"", "[]"}
                for row in node_rows
            ),
        },
        "edge_annotations": {
            "transitions": len(rows),
            "transition_types": distribution(
                [normalize(row.get("transition_type")) for row in rows]
            ),
            "paragraphs_containing_each_type": {
                transition_type: sum(
                    any(
                        normalize(row.get("transition_type")) == transition_type
                        for row in rows
                        if normalize(row.get("source_id")) == source_id
                    )
                    for source_id in outgoing_counts
                )
                for transition_type in transition_types
            },
            "explicit_choices": len(explicit_choices),
            "semantic_axes_among_explicit_choices": semantic_axes,
            "warnings": {
                "count": warning_count,
                "percent": percentage(warning_count, len(rows)),
            },
            "paragraph_type_note": (
                "Paragraph counts by transition type are not mutually exclusive."
            ),
        },
    }


def main() -> None:
    args = parse_args()
    book_id = str(args.book)
    gold_path = args.gold or Path(
        f"data/for_edge_extraction/{book_id}_calibration_edges_gold.csv"
    )
    model_path = args.calibration_output or Path(
        f"results/curnagl_results/csv/{book_id}_calibration_edges_final.csv"
    )
    full_path = args.full_edges or Path(
        f"data/processed/nodes_edges/{book_id}/{book_id}_edges.csv"
    )
    nodes_path = args.nodes or Path(
        f"data/processed/nodes_edges/{book_id}/{book_id}_nodes.csv"
    )
    output_path = args.output or Path(
        f"results/presentation/{book_id}_phase1_annotation_stats.json"
    )

    result = {
        "book_id": book_id,
        "calibration": calibration_summary(
            read_csv(gold_path), read_csv(model_path), gold_path, model_path
        ),
        "full_annotation": full_annotation_summary(
            read_csv(full_path), read_csv(nodes_path)
        ),
        "inputs": {
            "gold": str(gold_path),
            "calibration_output": str(model_path),
            "full_edges": str(full_path),
            "nodes": str(nodes_path),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nWritten to {output_path}")


if __name__ == "__main__":
    main()
