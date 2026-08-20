"""Lightweight checks for the files produced by phase 2.1.

This is deliberately separate from the production pipeline. Generic invariants are
checked for every book; known review sources are checked only when an oracle exists.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_BOOK_ID = "LW01"

# Corpus-specific expectations belong here, never in the production scripts.
EXPECTED_REVIEW_SOURCES = {
    "LW01": {
        "21",
        "23",
        "43",
        "112",
        "169",
        "180",
        "191",
        "208",
        "220",
        "227",
        "229",
        "231",
        "334",
        "339",
    }
}
EXPECTED_ENDING_COUNTS = {"LW01": {"death": 16, "win": 1}}
EXPECTED_AUTOMATIC_STATE_CONDITIONS = {
    "LW01": {
        "9": ("has_item", "Vordak Gem"),
        "12": ("gold_crowns_at_least", "10"),
        "173": ("has_item", "Silver Key"),
        "203": ("endurance_at_least", "10"),
    }
}

AUTO_EDGE_FIELDS = [
    "source_id",
    "target_id",
    "transition_kind",
    "weight_rule",
    "weight_value",
    "weight_expression",
    "condition_kind",
    "condition_value",
    "semantic_risk",
    "semantic_morality",
    "semantic_action",
    "source_ref",
    "note",
]
REVIEW_FIELDS = ["source_id", "review_reason", "text_content", "phase1_edges_json"]


def read_csv(
    path: Path, expected_fields: list[str] | None = None
) -> list[dict[str, str]]:
    """Read one required CSV and optionally check its exact header."""
    if not path.exists():
        raise FileNotFoundError(f"Missing file; run phase 2.1 first: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header: {path}")
        if expected_fields is not None and reader.fieldnames != expected_fields:
            raise ValueError(f"Unexpected header in {path}: {reader.fieldnames}")
        return [
            {field: (row.get(field) or "").strip() for field in reader.fieldnames}
            for row in reader
        ]


def add_error(errors: list[str], condition: bool, message: str) -> None:
    """Collect a failed check without stopping the rest of the audit."""
    if not condition:
        errors.append(message)


def check_weight_rule(row: dict[str, str], label: str, errors: list[str]) -> None:
    """Check only the three elementary phase-2.1 weight encodings."""
    rule = row["weight_rule"]
    value = row["weight_value"]
    expression = row["weight_expression"]
    if rule == "constant":
        add_error(errors, bool(value) and not expression, f"{label}: invalid constant")
    elif rule == "profile_choice":
        add_error(
            errors,
            not value and not expression,
            f"{label}: invalid profile_choice",
        )
    elif rule == "formula":
        add_error(errors, bool(expression) and not value, f"{label}: invalid formula")
    else:
        errors.append(f"{label}: unknown weight_rule {rule!r}")


def main() -> None:
    """Audit source coverage, review records, outcome links and weight rules."""
    parser = argparse.ArgumentParser(description="Check the output of phase 2.1.")
    parser.add_argument(
        "--book",
        default=DEFAULT_BOOK_ID,
        help="Lone Wolf book identifier (default: LW01).",
    )
    args = parser.parse_args()
    book_id = str(args.book)

    phase1_dir = Path("data/processed/nodes_edges") / book_id
    edges_path = phase1_dir / f"{book_id}_e_edges.csv"
    nodes_path = phase1_dir / f"{book_id}_nodes.csv"
    pregraph_dir = Path("data/processed/pregraph") / book_id

    phase1_edges = read_csv(edges_path)
    phase1_nodes = read_csv(nodes_path)
    automatic = read_csv(pregraph_dir / "auto_edges.csv", AUTO_EDGE_FIELDS)
    review = read_csv(pregraph_dir / "review_queue.csv", REVIEW_FIELDS)

    errors: list[str] = []
    node_ids = {node["node_id"] for node in phase1_nodes}
    phase1_sources = {edge["source_id"] for edge in phase1_edges}
    review_ids = {row["source_id"] for row in review}
    review_counts = Counter(row["source_id"] for row in review)

    duplicate_review = sorted(
        (source for source, count in review_counts.items() if count != 1), key=int
    )
    add_error(
        errors,
        not duplicate_review,
        f"Review sources must occur once: {duplicate_review}",
    )

    edges_filename = edges_path.name
    automatic_phase1_refs = [
        row["source_ref"]
        for row in automatic
        if row["source_ref"].startswith(f"{edges_filename}:")
    ]
    expected_phase1_refs = {
        f"{edges_filename}:{line_number}"
        for line_number, edge in enumerate(phase1_edges, start=2)
        if edge["source_id"] not in review_ids
    }
    add_error(
        errors,
        set(automatic_phase1_refs) == expected_phase1_refs
        and len(automatic_phase1_refs) == len(expected_phase1_refs),
        "Automatic sources do not trace every non-reviewed phase-1 edge exactly once.",
    )

    automatic_sources = {
        row["source_id"]
        for row in automatic
        if row["source_ref"].startswith(f"{edges_filename}:")
    }
    add_error(
        errors,
        automatic_sources == phase1_sources - review_ids,
        "Phase-1 sources are not partitioned cleanly between automatic and review.",
    )
    add_error(
        errors,
        not automatic_sources & review_ids,
        "Some sources occur in both automatic edges and the review queue.",
    )

    for line_number, row in enumerate(review, start=2):
        label = f"review_queue row {line_number}"
        add_error(errors, bool(row["review_reason"]), f"{label}: missing reason")
        add_error(errors, bool(row["text_content"]), f"{label}: missing text")
        try:
            source_edges = json.loads(row["phase1_edges_json"])
        except json.JSONDecodeError:
            errors.append(f"{label}: invalid phase1_edges_json")
            continue
        add_error(
            errors, isinstance(source_edges, list), f"{label}: edges must be a list"
        )
        if isinstance(source_edges, list):
            add_error(
                errors,
                bool(source_edges)
                and all(
                    edge.get("source_id") == row["source_id"] for edge in source_edges
                ),
                f"{label}: embedded edges do not match the reviewed source",
            )

    valid_targets = node_ids | {"Death", "Win"}
    for line_number, row in enumerate(automatic, start=2):
        label = f"auto_edges row {line_number}"
        add_error(
            errors,
            row["target_id"] in valid_targets,
            f"{label}: unknown target {row['target_id']!r}",
        )
        check_weight_rule(row, label, errors)

    automatic_by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in automatic:
        automatic_by_source[row["source_id"]].append(row)
    for node in phase1_nodes:
        status = node["absorbing_status"].casefold()
        if status not in {"death", "win"}:
            continue
        expected_target = "Death" if status == "death" else "Win"
        outgoing = automatic_by_source[node["node_id"]]
        add_error(
            errors,
            len(outgoing) == 1
            and outgoing[0]["target_id"] == expected_target
            and outgoing[0]["weight_value"] == "1",
            f"Written ending {node['node_id']} is not linked correctly "
            f"to {expected_target}.",
        )

    expected_review = EXPECTED_REVIEW_SOURCES.get(book_id)
    if expected_review is not None:
        add_error(
            errors,
            review_ids == expected_review,
            f"{book_id}: expected review sources {sorted(expected_review, key=int)}, "
            f"found {sorted(review_ids, key=int)}",
        )

    expected_endings = EXPECTED_ENDING_COUNTS.get(book_id)
    if expected_endings is not None:
        ending_counts = Counter(
            node["absorbing_status"].casefold()
            for node in phase1_nodes
            if node["absorbing_status"].casefold() in {"death", "win"}
        )
        add_error(
            errors,
            dict(ending_counts) == expected_endings,
            f"{book_id}: expected written endings {expected_endings}, "
            f"found {dict(ending_counts)}",
        )

    expected_conditions = EXPECTED_AUTOMATIC_STATE_CONDITIONS.get(book_id, {})
    for source_id, (condition_kind, condition_value) in expected_conditions.items():
        outgoing = automatic_by_source[source_id]
        add_error(
            errors,
            len(outgoing) == 2
            and {row["condition_kind"] for row in outgoing}
            == {condition_kind, f"{condition_kind}_absent"}
            and {row["condition_value"] for row in outgoing} == {condition_value}
            and all(row["weight_rule"] == "formula" for row in outgoing),
            f"{book_id}: state condition at source {source_id} was not converted "
            "into complementary symbolic routes.",
        )

    if errors:
        print(f"Phase 2.1 checks failed for {book_id}:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(f"Phase 2.1 checks passed for {book_id}.")
    print(f"- {len(phase1_edges)} phase-1 edges covered")
    print(f"- {len(automatic)} automatic pregraph edges")
    print(f"- {len(review)} source paragraphs queued for supervision")


if __name__ == "__main__":
    main()
