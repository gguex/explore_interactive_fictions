"""Phase 2.2: merge automatic and supervised edges into the final pregraph.

Run this script only after every source in review_queue.csv has been described in
<BOOK_ID>_supervision.csv. The output remains profile-independent and contains no W.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

DEFAULT_BOOK_ID = "LW01"

SUPERVISION_FIELDS = [
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
    "note",
]
AUTO_EDGE_FIELDS = [*SUPERVISION_FIELDS[:-1], "source_ref", "note"]
REVIEW_FIELDS = ["source_id", "review_reason", "text_content", "phase1_edges_json"]
NODE_FIELDS = ["node_id", "node_kind", "outcome", "absorbing", "source_ref"]
FINAL_EDGE_FIELDS = [
    "edge_id",
    *SUPERVISION_FIELDS[:-1],
    "origin",
    "source_ref",
    "note",
]
REPORT_FIELDS = ["metric", "value", "detail"]

TRANSITION_KINDS = {
    "forced",
    "profile_choice",
    "random",
    "kai",
    "state_condition",
    "combat",
    "escape",
    "outcome",
    "manual",
}
WEIGHT_RULES = {"constant", "profile_choice", "formula"}


def read_csv(
    path: Path, expected_fields: list[str] | None = None
) -> list[dict[str, str]]:
    """Read a CSV and optionally enforce its exact header."""
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header: {path}")
        if expected_fields is not None and reader.fieldnames != expected_fields:
            raise ValueError(
                f"Unexpected header in {path}: {reader.fieldnames}; "
                f"expected {expected_fields}"
            )
        return [
            {field: (row.get(field) or "").strip() for field in reader.fieldnames}
            for row in reader
        ]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    """Write a deterministic UTF-8 CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def validate_weight_rule(row: dict[str, str], label: str) -> None:
    """Validate the deterministic annotation rules documented for phase 2."""
    rule = row["weight_rule"]
    value = row["weight_value"]
    expression = row["weight_expression"]

    if rule not in WEIGHT_RULES:
        raise ValueError(f"{label}: unknown weight_rule {rule!r}")

    if rule == "constant":
        if not value or expression:
            raise ValueError(
                f"{label}: constant requires weight_value and no expression"
            )
        try:
            probability = Decimal(value)
        except InvalidOperation as error:
            raise ValueError(f"{label}: invalid constant {value!r}") from error
        if not Decimal("0") <= probability <= Decimal("1"):
            raise ValueError(f"{label}: constant outside [0, 1]: {value}")

    elif rule == "profile_choice":
        if value or expression:
            raise ValueError(f"{label}: profile_choice cannot contain a fixed weight")
        semantic_fields = (
            row["semantic_risk"],
            row["semantic_morality"],
            row["semantic_action"],
        )
        if not all(semantic_fields):
            raise ValueError(
                f"{label}: profile_choice requires all three semantic annotations"
            )

    elif not expression or value:
        raise ValueError(f"{label}: formula requires an expression and no value")


def validate_edge(
    row: dict[str, str], valid_sources: set[str], valid_targets: set[str], label: str
) -> None:
    """Validate one automatic or supervised pregraph edge."""
    if row["source_id"] not in valid_sources:
        raise ValueError(f"{label}: unknown source {row['source_id']!r}")
    if row["target_id"] not in valid_targets:
        raise ValueError(f"{label}: unknown target {row['target_id']!r}")
    if row["transition_kind"] not in TRANSITION_KINDS:
        raise ValueError(f"{label}: unknown transition_kind {row['transition_kind']!r}")
    if bool(row["condition_kind"]) != bool(row["condition_value"]):
        raise ValueError(f"{label}: condition kind and value must be filled together")
    validate_weight_rule(row, label)


def prepare_nodes(
    phase1_nodes: list[dict[str, str]], nodes_filename: str
) -> list[dict[str, str]]:
    """Create narrative, preterminal and shared terminal nodes."""
    nodes = []

    for node in phase1_nodes:
        status = node["absorbing_status"].casefold()
        if status == "death":
            node_kind, outcome = "preterminal", "death"
        elif status == "win":
            node_kind, outcome = "preterminal", "win"
        else:
            node_kind, outcome = "narrative", ""
        nodes.append(
            {
                "node_id": node["node_id"],
                "node_kind": node_kind,
                "outcome": outcome,
                "absorbing": "false",
                "source_ref": f"{nodes_filename}:{node['node_id']}",
            }
        )

    nodes.extend(
        [
            {
                "node_id": "Death",
                "node_kind": "terminal",
                "outcome": "death",
                "absorbing": "true",
                "source_ref": "phase2:shared_outcome",
            },
            {
                "node_id": "Win",
                "node_kind": "terminal",
                "outcome": "win",
                "absorbing": "true",
                "source_ref": "phase2:shared_outcome",
            },
        ]
    )
    return nodes


def validate_constant_distributions(edges: list[dict[str, str]]) -> None:
    """Check sources whose complete outgoing distribution is already numeric."""
    by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
    for edge in edges:
        by_source[edge["source_id"]].append(edge)

    for source_id, source_edges in by_source.items():
        if all(edge["weight_rule"] == "constant" for edge in source_edges):
            total = sum(
                (Decimal(edge["weight_value"]) for edge in source_edges),
                start=Decimal("0"),
            )
            if total != Decimal("1"):
                raise ValueError(
                    f"Constant outgoing weights for source {source_id} sum to {total}"
                )


def validate_outcomes(nodes: list[dict[str, str]], edges: list[dict[str, str]]) -> None:
    """Ensure every written ending has exactly one edge to its shared outcome."""
    by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
    for edge in edges:
        by_source[edge["source_id"]].append(edge)

    for node in nodes:
        if node["node_kind"] != "preterminal":
            continue
        expected_target = "Death" if node["outcome"] == "death" else "Win"
        outgoing = by_source[node["node_id"]]
        if len(outgoing) != 1 or outgoing[0]["target_id"] != expected_target:
            raise ValueError(
                f"Preterminal {node['node_id']} must point only to {expected_target}"
            )


def numeric_source_key(row: dict[str, str]) -> int:
    """Sort Lone Wolf paragraph identifiers numerically."""
    return int(row["source_id"])


def report_row(metric: str, value: int, detail: str = "") -> dict[str, str]:
    """Build one row of the compact conversion report."""
    return {"metric": metric, "value": str(value), "detail": detail}


def main() -> None:
    """Validate the hand-off and write the final profile-independent pregraph."""
    parser = argparse.ArgumentParser(
        description="Finalize the profile-independent pregraph for one book."
    )
    parser.add_argument(
        "--book",
        default=DEFAULT_BOOK_ID,
        help="Lone Wolf book identifier (default: LW01).",
    )
    args = parser.parse_args()
    book_id = str(args.book)

    phase1_dir = Path("data/processed/nodes_edges") / book_id
    edges_path = phase1_dir / f"{book_id}_edges.csv"
    nodes_path = phase1_dir / f"{book_id}_nodes.csv"
    pregraph_dir = Path("data/processed/pregraph") / book_id
    auto_edges_path = pregraph_dir / "auto_edges.csv"
    review_queue_path = pregraph_dir / "review_queue.csv"
    supervision_path = Path("data/for_graph_model") / f"{book_id}_supervision.csv"
    pregraph_nodes_path = pregraph_dir / "pregraph_nodes.csv"
    pregraph_edges_path = pregraph_dir / "pregraph_edges.csv"
    report_path = pregraph_dir / "conversion_report.csv"

    phase1_edges = read_csv(edges_path)
    phase1_nodes = read_csv(nodes_path)
    automatic = read_csv(auto_edges_path, AUTO_EDGE_FIELDS)
    review_queue = read_csv(review_queue_path, REVIEW_FIELDS)
    supervision = read_csv(supervision_path, SUPERVISION_FIELDS)

    phase1_node_ids = {node["node_id"] for node in phase1_nodes}
    phase1_source_ids = {edge["source_id"] for edge in phase1_edges}
    valid_targets = phase1_node_ids | {"Death", "Win"}
    review_ids = {row["source_id"] for row in review_queue}
    supervised_ids = {row["source_id"] for row in supervision}

    missing_annotations = review_ids - supervised_ids
    unexpected_annotations = supervised_ids - review_ids
    if missing_annotations:
        missing = ", ".join(sorted(missing_annotations, key=int))
        raise ValueError(f"Supervision is incomplete; missing sources: {missing}")
    if unexpected_annotations:
        unexpected = ", ".join(sorted(unexpected_annotations, key=int))
        raise ValueError(f"Annotations exist outside the review queue: {unexpected}")

    automatic_sources = {row["source_id"] for row in automatic}
    overlap = automatic_sources & review_ids
    if overlap:
        sources = ", ".join(sorted(overlap, key=int))
        raise ValueError(f"Reviewed sources also appear in automatic edges: {sources}")

    expected_automatic_sources = phase1_source_ids - review_ids
    missing_automatic_sources = expected_automatic_sources - automatic_sources
    if missing_automatic_sources:
        missing = ", ".join(sorted(missing_automatic_sources, key=int))
        raise ValueError(f"Phase-1 sources were not converted: {missing}")

    expected_phase1_refs = {
        f"{edges_path.name}:{line_number}"
        for line_number, edge in enumerate(phase1_edges, start=2)
        if edge["source_id"] not in review_ids
    }
    actual_phase1_ref_list = [
        row["source_ref"]
        for row in automatic
        if row["source_ref"].startswith(f"{edges_path.name}:")
    ]
    actual_phase1_refs = set(actual_phase1_ref_list)
    if actual_phase1_refs != expected_phase1_refs or len(actual_phase1_ref_list) != len(
        actual_phase1_refs
    ):
        raise ValueError(
            "Automatic edges do not trace every expected phase-1 edge once"
        )

    combined: list[dict[str, str]] = []
    for index, row in enumerate(automatic):
        validate_edge(
            row, phase1_node_ids, valid_targets, f"auto_edges row {index + 2}"
        )
        combined.append({**row, "origin": "auto", "_order": str(index)})

    for index, row in enumerate(supervision):
        label = f"supervision row {index + 2}"
        validate_edge(row, phase1_node_ids, valid_targets, label)
        if not row["note"]:
            raise ValueError(f"{label}: a concise justification is required")
        combined.append(
            {
                **row,
                "origin": "supervised",
                "source_ref": f"{supervision_path.name}:{index + 2}",
                "_order": str(index),
            }
        )

    combined.sort(key=numeric_source_key)
    for index, row in enumerate(combined, start=1):
        row["edge_id"] = f"e{index:04d}"

    pregraph_nodes = prepare_nodes(phase1_nodes, nodes_path.name)
    validate_constant_distributions(combined)
    validate_outcomes(pregraph_nodes, combined)

    outgoing_sources = {edge["source_id"] for edge in combined}
    nonterminal_ids = {
        node["node_id"] for node in pregraph_nodes if node["node_kind"] != "terminal"
    }
    missing_outgoing = nonterminal_ids - outgoing_sources
    if missing_outgoing:
        missing = ", ".join(sorted(missing_outgoing, key=int))
        raise ValueError(f"Non-terminal nodes without outgoing edges: {missing}")

    reviewed_phase1_edges = sum(
        edge["source_id"] in review_ids for edge in phase1_edges
    )
    classified_phase1_edges = len(actual_phase1_refs) + reviewed_phase1_edges
    if classified_phase1_edges != len(phase1_edges):
        raise ValueError(
            f"Only {classified_phase1_edges}/{len(phase1_edges)} phase-1 edges "
            "were classified or replaced"
        )

    report = [
        report_row("phase1_nodes", len(phase1_nodes)),
        report_row("phase1_edges", len(phase1_edges)),
        report_row("automatic_phase1_edges", len(actual_phase1_refs)),
        report_row("replaced_phase1_edges", reviewed_phase1_edges),
        report_row("supervised_sources", len(review_ids)),
        report_row("automatic_pregraph_edges", len(automatic)),
        report_row("supervised_pregraph_edges", len(supervision)),
        report_row("pregraph_nodes", len(pregraph_nodes)),
        report_row("pregraph_edges", len(combined)),
        report_row(
            "unclassified_phase1_edges",
            len(phase1_edges) - classified_phase1_edges,
            "Must be zero.",
        ),
    ]

    write_csv(pregraph_nodes_path, NODE_FIELDS, pregraph_nodes)
    write_csv(pregraph_edges_path, FINAL_EDGE_FIELDS, combined)
    write_csv(report_path, REPORT_FIELDS, report)

    print(f"{len(pregraph_nodes)} nodes written to {pregraph_nodes_path}")
    print(f"{len(combined)} edges written to {pregraph_edges_path}")
    print(f"Conversion report written to {report_path}")


if __name__ == "__main__":
    main()
