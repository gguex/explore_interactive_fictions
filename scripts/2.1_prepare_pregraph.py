"""Phase 2.1: convert phase-1 tables into an automatic pregraph draft.

The script writes automatic transitions, a review queue for unsupported source
paragraphs, and (once only) the empty supervision table. It never builds W.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
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

DISCIPLINE_PATTERN = re.compile(
    r"\b(?:(?:Kai|Magnakai|Grand Master)\s+)?Discipline of\s+"
    r"(?P<name>.+?)"
    r"(?=\s+(?:and|or|on|to|if|when|then|at|in)\b|[,.;:]|$)",
    re.IGNORECASE,
)
ITEM_PATTERN = re.compile(
    r"\b(?:possess|have)\s+(?:a|an)\s+(?P<name>.+?)(?=\s+and\b|[,.;:]|$)",
    re.IGNORECASE,
)
GOLD_PATTERN = re.compile(r"\b(?:have|possess)\s+(?P<count>\d+)\s+Gold Crowns?\b", re.I)
ENDURANCE_AT_LEAST_PATTERN = re.compile(
    r"\b(?P<count>\d+)\s+or\s+more\s+ENDURANCE\s+points?\b", re.I
)


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV while normalizing missing cells to empty strings."""
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header: {path}")
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


def phase1_note(edge: dict[str, str], prefix: str = "") -> str:
    """Keep useful phase-1 warnings without trying to simulate L3 effects."""
    parts = [part for part in (prefix, edge["warnings"]) if part]
    return " | ".join(parts)


def make_edge(
    edge: dict[str, str],
    transition_kind: str,
    weight_rule: str,
    *,
    weight_value: str = "",
    weight_expression: str = "",
    condition_kind: str = "",
    condition_value: str = "",
    note: str = "",
) -> dict[str, str]:
    """Convert one phase-1 edge into the common draft schema."""
    return {
        "source_id": edge["source_id"],
        "target_id": edge["target_id"],
        "transition_kind": transition_kind,
        "weight_rule": weight_rule,
        "weight_value": weight_value,
        "weight_expression": weight_expression,
        "condition_kind": condition_kind,
        "condition_value": condition_value,
        "semantic_risk": edge["semantic_risk"],
        "semantic_morality": edge["semantic_morality"],
        "semantic_action": edge["semantic_action"],
        "source_ref": edge["_source_ref"],
        "note": phase1_note(edge, note),
    }


def random_outcome_count(realisation: str) -> int:
    """Return how many values in a 0--9 random table satisfy a simple rule."""
    normalized = re.sub(r"[–—−]", "-", realisation.lower())

    interval = re.search(r"\b([0-9])\s*-\s*([0-9])\b", normalized)
    if interval:
        start, end = (int(value) for value in interval.groups())
        if start <= end:
            return end - start + 1

    lower = re.search(r"\b([0-9])\s+or\s+lower\b", normalized)
    if lower:
        return int(lower.group(1)) + 1

    higher = re.search(r"\b([0-9])\s+or\s+higher\b", normalized)
    if higher:
        return 10 - int(higher.group(1))

    singleton = re.search(r"\bpick(?:ed)?\s+(?:a\s+)?([0-9])\b", normalized)
    if singleton:
        return 1

    raise ValueError(f"Unsupported random-number rule: {realisation!r}")


def simple_random_probabilities(edges: list[dict[str, str]]) -> list[str]:
    """Parse a complete, one-stage partition of the ten random-table values."""
    if any(
        phrase in edge["warnings"].lower()
        for edge in edges
        for phrase in ("first choice", "last chance", "implicit dead end")
    ):
        raise ValueError("successive or conditional random draws")

    counts = [random_outcome_count(edge["realisation_value"]) for edge in edges]
    if sum(counts) != 10:
        raise ValueError(f"random branches cover {sum(counts)}/10 outcomes")
    return [f"{count / 10:.1f}" for count in counts]


def kai_disciplines(text: str) -> set[str]:
    """Find any named Kai, Magnakai or Grand Master discipline."""
    return {match.group("name").strip() for match in DISCIPLINE_PATTERN.finditer(text)}


def kai_fallback(text: str) -> bool:
    """Recognize the complementary branch of a single Kai condition."""
    lowered = text.casefold()
    return any(
        phrase in lowered
        for phrase in (
            "if not",
            "if you do not",
            "if you do not possess",
            "if you do not have",
        )
    )


def generic_condition(text: str) -> tuple[str, str] | None:
    """Extract a simple persistent-state condition from phase-1 wording."""
    if condition_fallback(text):
        return None

    endurance = ENDURANCE_AT_LEAST_PATTERN.search(text)
    if endurance:
        return "endurance_at_least", endurance.group("count")

    gold = GOLD_PATTERN.search(text)
    if gold:
        return "gold_crowns_at_least", gold.group("count")

    item = ITEM_PATTERN.search(text)
    if item:
        name = item.group("name").strip()
        if "discipline" not in name.casefold() and "skill" not in name.casefold():
            return "has_item", name
    return None


def condition_fallback(text: str) -> bool:
    """Recognize the alternative used when a persistent condition is false."""
    lowered = text.casefold()
    return any(
        phrase in lowered
        for phrase in (
            "if not",
            "if you do not",
            "if you do not possess",
            "if you do not have",
            "if you now have less than",
        )
    )


def convert_state_condition_source(
    edges: list[dict[str, str]],
) -> tuple[list[dict[str, str]], str]:
    """Convert one simple state condition and its complementary route."""
    conditional = [edge for edge in edges if edge["transition_type"] == "conditional"]
    explicit = [edge for edge in edges if edge["transition_type"] == "explicit_choice"]
    recognized = [
        (edge, condition)
        for edge in conditional
        if (condition := generic_condition(edge["realisation_value"])) is not None
    ]
    fallback = [
        edge
        for edge in conditional
        if condition_fallback(edge["realisation_value"])
    ]

    if len(recognized) != 1:
        return [], "multiple_or_unrecognized_state_conditions"
    if len(fallback) > 1 or (fallback and explicit):
        return [], "state_condition_mixed_with_other_routes"
    if not fallback and not explicit:
        return [], "state_condition_without_fallback"

    positive, (condition_kind, condition_value) = recognized[0]
    if positive in fallback:
        return [], "state_condition_has_no_positive_route"

    availability = (
        f"condition_available({json.dumps(condition_kind)}, "
        f"{json.dumps(condition_value, ensure_ascii=False)})"
    )
    converted = [
        make_edge(
            positive,
            "state_condition",
            "formula",
            weight_expression=availability,
            condition_kind=condition_kind,
            condition_value=condition_value,
            note="Route is taken when the persistent-state condition is available.",
        )
    ]

    if fallback:
        converted.append(
            make_edge(
                fallback[0],
                "state_condition",
                "formula",
                weight_expression=f"1 - {availability}",
                condition_kind=f"{condition_kind}_absent",
                condition_value=condition_value,
                note="Complementary route when the persistent condition is false.",
            )
        )
        return converted, ""

    for edge in explicit:
        expression = f"1 - {availability}"
        if len(explicit) > 1:
            expression += f" * choice_share({edge['source_id']}, {edge['target_id']})"
        converted.append(
            make_edge(
                edge,
                "profile_choice",
                "formula",
                weight_expression=expression,
                note="Choice among routes remaining when the state condition is false.",
            )
        )
    return converted, ""


def convert_kai_source(
    edges: list[dict[str, str]],
) -> tuple[list[dict[str, str]], str]:
    """Convert the standard one-discipline pattern or return a review reason."""
    conditional = [edge for edge in edges if edge["transition_type"] == "conditional"]
    explicit = [edge for edge in edges if edge["transition_type"] == "explicit_choice"]
    disciplines = set().union(
        *(kai_disciplines(edge["realisation_value"]) for edge in conditional)
    )

    if not disciplines:
        return [], "state_or_resource_condition"
    if len(disciplines) > 1:
        return [], "multiple_kai_disciplines"

    discipline = next(iter(disciplines))
    positive = [
        edge
        for edge in conditional
        if discipline in kai_disciplines(edge["realisation_value"])
    ]
    fallback = [edge for edge in conditional if edge not in positive]

    if len(positive) != 1:
        return [], "multiple_conditions_for_one_kai_discipline"
    if fallback and (
        len(fallback) != 1 or not kai_fallback(fallback[0]["realisation_value"])
    ):
        return [], "kai_condition_mixed_with_another_condition"
    if fallback and explicit:
        return [], "kai_fallback_mixed_with_player_choices"
    if not fallback and not explicit:
        return [], "kai_condition_without_fallback"

    quoted_discipline = json.dumps(discipline, ensure_ascii=False)
    availability = f"kai_available({quoted_discipline})"
    converted = [
        make_edge(
            positive[0],
            "kai",
            "formula",
            weight_expression=availability,
            condition_kind="kai_discipline",
            condition_value=discipline,
            note="Kai route is taken whenever the discipline is available.",
        )
    ]

    if fallback:
        converted.append(
            make_edge(
                fallback[0],
                "kai",
                "formula",
                weight_expression=f"1 - {availability}",
                condition_kind="kai_discipline_absent",
                condition_value=discipline,
            )
        )
        return converted, ""

    for edge in explicit:
        if len(explicit) == 1:
            expression = f"1 - {availability}"
        else:
            expression = (
                f"(1 - {availability}) * "
                f"choice_share({edge['source_id']}, {edge['target_id']})"
            )
        converted.append(
            make_edge(
                edge,
                "profile_choice",
                "formula",
                weight_expression=expression,
                note="Choice among routes remaining when the Kai route is unavailable.",
            )
        )
    return converted, ""


def combat_review_reason(edges: list[dict[str, str]]) -> str:
    """Give the annotator a concise reason for a non-standard combat."""
    conditions = " ".join(edge["realisation_value"] for edge in edges).casefold()
    if "round" in conditions:
        return "combat_outcome_depends_on_duration"
    if "endurance" in conditions:
        return "combat_outcome_depends_on_endurance_loss"
    if any(edge["transition_type"] == "explicit_choice" for edge in edges):
        return "combat_with_escape_or_postcombat_choice"
    return "combat_with_multiple_conditional_outcomes"


def convert_source(
    edges: list[dict[str, str]], node: dict[str, str]
) -> tuple[list[dict[str, str]], str]:
    """Convert one complete source paragraph, or route it to supervision."""
    source_id = edges[0]["source_id"]
    types = {edge["transition_type"] for edge in edges}
    has_combat = bool(node["enemies"])

    if has_combat:
        victory = f"combat_win({source_id})"
        if len(edges) == 1 and types == {"forced"}:
            converted = [
                make_edge(
                    edges[0],
                    "combat",
                    "formula",
                    weight_expression=victory,
                    note="Transition after combat victory.",
                )
            ]
        elif types == {"stochastic"}:
            try:
                probabilities = simple_random_probabilities(edges)
            except ValueError as error:
                return [], f"combat_with_unsupported_random_rule: {error}"
            converted = [
                make_edge(
                    edge,
                    "combat",
                    "formula",
                    weight_expression=f"{victory} * {probability}",
                    note="Combat victory followed by a random-number result.",
                )
                for edge, probability in zip(edges, probabilities, strict=True)
            ]
        else:
            return [], combat_review_reason(edges)

        converted.append(
            {
                "source_id": source_id,
                "target_id": "Death",
                "transition_kind": "combat",
                "weight_rule": "formula",
                "weight_value": "",
                "weight_expression": f"1 - {victory}",
                "condition_kind": "",
                "condition_value": "",
                "semantic_risk": "",
                "semantic_morality": "",
                "semantic_action": "",
                "source_ref": f"generated:combat_death:{source_id}",
                "note": "Implicit death when the combat is lost.",
            }
        )
        return converted, ""

    if len(edges) == 1 and types == {"forced"}:
        return [make_edge(edges[0], "forced", "constant", weight_value="1")], ""

    if types == {"explicit_choice"}:
        return [
            make_edge(edge, "profile_choice", "profile_choice") for edge in edges
        ], ""

    if types == {"stochastic"}:
        try:
            probabilities = simple_random_probabilities(edges)
        except ValueError as error:
            return [], f"unsupported_random_rule: {error}"
        return [
            make_edge(edge, "random", "constant", weight_value=probability)
            for edge, probability in zip(edges, probabilities, strict=True)
        ], ""

    if "conditional" in types:
        if any(
            kai_disciplines(edge["realisation_value"])
            for edge in edges
            if edge["transition_type"] == "conditional"
        ):
            return convert_kai_source(edges)
        return convert_state_condition_source(edges)

    return [], f"unsupported_transition_combination: {sorted(types)}"


def outcome_edges(
    nodes: list[dict[str, str]], nodes_filename: str
) -> list[dict[str, str]]:
    """Link written endings to the two shared outcome nodes."""
    converted = []
    for node in nodes:
        status = node["absorbing_status"].casefold()
        if status not in {"death", "win"}:
            continue
        target = "Death" if status == "death" else "Win"
        converted.append(
            {
                "source_id": node["node_id"],
                "target_id": target,
                "transition_kind": "outcome",
                "weight_rule": "constant",
                "weight_value": "1",
                "weight_expression": "",
                "condition_kind": "",
                "condition_value": "",
                "semantic_risk": "",
                "semantic_morality": "",
                "semantic_action": "",
                "source_ref": f"{nodes_filename}:{node['node_id']}",
                "note": "Written narrative ending linked to its shared outcome.",
            }
        )
    return converted


def create_supervision_table(supervision_path: Path) -> bool:
    """Create the annotation template once; never overwrite an existing table."""
    supervision_path.parent.mkdir(parents=True, exist_ok=True)
    if supervision_path.exists():
        with supervision_path.open(encoding="utf-8", newline="") as handle:
            existing_header = next(csv.reader(handle), None)
        if existing_header != SUPERVISION_FIELDS:
            raise ValueError(
                f"Unexpected header in existing supervision file: {supervision_path}"
            )
        return False

    write_csv(supervision_path, SUPERVISION_FIELDS, [])
    return True


def numeric_source_key(row: dict[str, str]) -> int:
    """Sort Lone Wolf paragraph identifiers numerically."""
    return int(row["source_id"])


def main() -> None:
    """Prepare automatic edges and the structured annotation hand-off."""
    parser = argparse.ArgumentParser(
        description="Prepare the profile-independent pregraph draft for one book."
    )
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
    auto_edges_path = pregraph_dir / "auto_edges.csv"
    review_queue_path = pregraph_dir / "review_queue.csv"
    supervision_path = Path("data/for_graph_model") / f"{book_id}_supervision.csv"

    edges = read_csv(edges_path)
    nodes = read_csv(nodes_path)
    nodes_by_id = {node["node_id"]: node for node in nodes}

    edges_by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
    for line_number, edge in enumerate(edges, start=2):
        edge["_source_ref"] = f"{edges_path.name}:{line_number}"
        edges_by_source[edge["source_id"]].append(edge)

    automatic: list[dict[str, str]] = []
    review: list[dict[str, str]] = []
    phase1_fields = [field for field in edges[0] if not field.startswith("_")]

    for source_id in sorted(edges_by_source, key=int):
        source_edges = edges_by_source[source_id]
        converted, reason = convert_source(source_edges, nodes_by_id[source_id])
        if reason:
            review.append(
                {
                    "source_id": source_id,
                    "review_reason": reason,
                    "text_content": nodes_by_id[source_id]["text_content"],
                    "phase1_edges_json": json.dumps(
                        [
                            {field: edge[field] for field in phase1_fields}
                            for edge in source_edges
                        ],
                        ensure_ascii=False,
                    ),
                }
            )
        else:
            automatic.extend(converted)

    automatic.extend(outcome_edges(nodes, nodes_path.name))
    automatic.sort(key=numeric_source_key)

    write_csv(auto_edges_path, AUTO_EDGE_FIELDS, automatic)
    write_csv(review_queue_path, REVIEW_FIELDS, review)
    supervision_created = create_supervision_table(supervision_path)

    print(f"{len(automatic)} automatic pregraph edges written to {auto_edges_path}")
    print(f"{len(review)} source paragraphs written to {review_queue_path}")
    action = "created" if supervision_created else "preserved"
    print(f"Supervision table {action}: {supervision_path}")


if __name__ == "__main__":
    main()
