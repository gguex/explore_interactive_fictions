"""Independently validate the phase-5.1 reconstructed trajectory corpus."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

DEFAULT_BOOK_ID = "LW01"
OUTCOMES = ("Win", "Death")
TRANSITION_LABELS = {
    "profile_choice": "Player choice",
    "escape": "Player choice: escape from combat",
    "kai": "Kai availability or mechanical route",
    "state_condition": "Inventory or state-dependent route",
    "random": "Random or mechanical resolution",
    "combat": "Combat resolution",
    "forced": "Forced transition",
    "outcome": "Story outcome",
}
PLAYER_CHOICE_KINDS = {"profile_choice", "escape"}
PAIR_DEFINITIONS = (
    ("risk", "cautious_neutral_neutral", "reckless_neutral_neutral"),
    ("morality", "neutral_selfish_neutral", "neutral_noble_neutral"),
    ("action", "neutral_neutral_physical", "neutral_neutral_tactical"),
)
CALIBRATION_CELLS = {
    ("neutral_neutral_neutral", "Win"),
    ("cautious_neutral_neutral", "Death"),
    ("neutral_noble_neutral", "Win"),
    ("neutral_neutral_tactical", "Death"),
}
PUBLIC_STORY_FIELDS = {
    "schema_version",
    "trajectory_id",
    "language",
    "step_count",
    "player_choice_step_count",
    "word_count",
    "character_count",
    "estimated_token_count",
    "story_sha256",
    "steps",
    "story_text",
}
STEP_FIELDS = {
    "step_ref",
    "paragraph_id",
    "narrative_text",
    "available_choices",
    "chosen_action",
    "transition_type",
}
PRIVATE_FIELDS = {
    "trajectory_id",
    "source_trajectory_id",
    "book_id",
    "profile_id",
    "risk",
    "morality",
    "action",
    "outcome",
    "split",
    "node_ids",
    "edge_ids",
    "medoid_trajectory_sha256",
    "story_sha256",
}
PAIR_METRIC_FIELDS = [
    "comparison_id",
    "trajectory_a_id",
    "trajectory_b_id",
    "paragraph_count_a",
    "paragraph_count_b",
    "common_unique_paragraph_count",
    "paragraph_fraction_a",
    "paragraph_fraction_b",
    "paragraph_jaccard_similarity",
    "edge_count_a",
    "edge_count_b",
    "common_unique_edge_count",
    "edge_fraction_a",
    "edge_fraction_b",
    "edge_jaccard_similarity",
    "normalized_node_lcs_similarity",
    "normalized_node_edit_distance",
    "bop_node_visit_js_divergence_nats",
    "bop_edge_flow_js_divergence_nats",
    "bop_win_probability_gap",
    "bop_trajectory_entropy_gap_nats",
]
FORBIDDEN_PUBLIC_KEYS = {
    "profile_id",
    "risk",
    "morality",
    "action",
    "outcome",
    "node_ids",
    "edge_ids",
    "compiled_weight",
    "semantic_risk",
    "semantic_morality",
    "semantic_action",
}
ATOL = 5e-12


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read one required CSV artifact."""
    if not path.exists():
        raise FileNotFoundError(f"Missing input or artifact: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header in {path}")
        return list(reader.fieldnames), [
            {key: (value or "").strip() for key, value in row.items()}
            for row in reader
        ]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read non-empty JSON objects from one JSON Lines artifact."""
    if not path.exists():
        raise FileNotFoundError(f"Missing phase-5.1 artifact: {path}")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"Line {line_number} in {path} is not an object")
        rows.append(value)
    if not rows:
        raise ValueError(f"Empty JSON Lines artifact: {path}")
    return rows


def file_sha256(path: Path) -> str:
    """Return a file's SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_sha256(value: str) -> str:
    """Return the SHA-256 digest of one text."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalized_text(value: str) -> str:
    """Apply the declared phase-5.1 whitespace normalization."""
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def close(actual: float, expected: float, label: str) -> None:
    """Require finite numeric agreement."""
    if not math.isfinite(actual) or not math.isclose(
        actual, expected, rel_tol=ATOL, abs_tol=ATOL
    ):
        raise ValueError(f"{label}: got {actual}, expected {expected}")


def assert_no_private_keys(value: Any, location: str) -> None:
    """Recursively reject private metadata keys from public artifacts."""
    if isinstance(value, dict):
        leaked = FORBIDDEN_PUBLIC_KEYS & set(value)
        if leaked:
            raise ValueError(f"Private keys {sorted(leaked)} leaked in {location}")
        for key, child in value.items():
            assert_no_private_keys(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_no_private_keys(child, f"{location}[{index}]")


def load_nodes(path: Path) -> dict[str, str]:
    """Load normalized source-paragraph text independently."""
    _, rows = read_csv(path)
    result: dict[str, str] = {}
    for row in rows:
        node_id = row["node_id"]
        if node_id in result:
            raise ValueError(f"Duplicate paragraph {node_id}")
        result[node_id] = normalized_text(row["text_content"])
    return result


def load_choices(path: Path) -> dict[str, list[dict[str, str]]]:
    """Load original phase-1 choices in file order."""
    _, rows = read_csv(path)
    result: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        row["edge_text"] = normalized_text(row["edge_text"])
        result[row["source_id"]].append(row)
    return result


def load_compiled_edges(path: Path) -> dict[str, dict[str, str]]:
    """Index compiled edge rows by edge identifier."""
    _, rows = read_csv(path)
    result = {row["edge_id"]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"Duplicate compiled edges in {path}")
    return result


def render_story(steps: list[dict[str, Any]]) -> str:
    """Independently render the downstream story document."""
    blocks: list[str] = []
    for step in steps:
        choices = step["available_choices"]
        available = (
            "\n".join(
                f"{choice['choice_ref']}. {choice['text']}" for choice in choices
            )
            if choices
            else "None."
        )
        chosen = step["chosen_action"]
        prefix = (
            f"{chosen['choice_ref']}. " if chosen["choice_ref"] is not None else ""
        )
        blocks.append(
            "\n".join(
                (
                    f"[STEP {step['step_ref']}]",
                    f"[PARAGRAPH {step['paragraph_id']}]",
                    step["narrative_text"],
                    "",
                    "[AVAILABLE CHOICES]",
                    available,
                    "",
                    "[CHOSEN ACTION]",
                    f"{prefix}{chosen['text']}",
                    "",
                    "[TRANSITION TYPE]",
                    step["transition_type"],
                )
            )
        )
    return "\n\n".join(blocks)


def expected_implicit_action(kind: str, target_id: str) -> str:
    """Return the only two allowed generated transition descriptions."""
    if kind == "combat" and target_id == "Death":
        return "Combat is lost; the trajectory ends here."
    if kind == "outcome":
        return "The narrative ending is reached."
    raise ValueError(f"Unexpected implicit action for {kind}/{target_id}")


def validate_story(
    story: dict[str, Any],
    private: dict[str, Any],
    medoid: dict[str, Any],
    nodes: dict[str, str],
    choices: dict[str, list[dict[str, str]]],
    compiled: dict[str, dict[str, str]],
) -> set[str]:
    """Validate one public story against all source data."""
    public_id = str(private["trajectory_id"])
    if set(story) != PUBLIC_STORY_FIELDS:
        raise ValueError(f"Unexpected public story schema for {public_id}")
    assert_no_private_keys(story, public_id)
    if story["trajectory_id"] != public_id or story["language"] != "en":
        raise ValueError(f"Wrong public identity or language for {public_id}")
    if private["source_trajectory_id"] != medoid["trajectory_id"]:
        raise ValueError(f"Wrong medoid mapping for {public_id}")
    if private["node_ids"] != medoid["node_ids"]:
        raise ValueError(f"Private nodes differ from medoid for {public_id}")
    if private["edge_ids"] != medoid["edge_ids"]:
        raise ValueError(f"Private edges differ from medoid for {public_id}")
    node_ids = [str(node_id) for node_id in medoid["node_ids"]]
    edge_ids = [str(edge_id) for edge_id in medoid["edge_ids"]]
    steps = story["steps"]
    if not isinstance(steps, list) or len(steps) != len(edge_ids):
        raise ValueError(f"Wrong step count for {public_id}")
    valid_choice_refs: set[str] = set()
    choice_step_count = 0
    for position, step in enumerate(steps, 1):
        if not isinstance(step, dict) or set(step) != STEP_FIELDS:
            raise ValueError(f"Unexpected step schema at {public_id}/{position}")
        edge_id = edge_ids[position - 1]
        edge = compiled[edge_id]
        source_id = node_ids[position - 1]
        target_id = node_ids[position]
        if edge["source_id"] != source_id or edge["target_id"] != target_id:
            raise ValueError(f"Discontinuous edge at {public_id}/{position}")
        if step["step_ref"] != f"S{position:03d}":
            raise ValueError(f"Wrong step reference at {public_id}/{position}")
        if step["paragraph_id"] != source_id:
            raise ValueError(f"Wrong paragraph at {public_id}/{position}")
        if step["narrative_text"] != nodes[source_id]:
            raise ValueError(f"Narrative text differs at {public_id}/{position}")
        source_choices = choices.get(source_id, [])
        expected_choices = [
            {
                "choice_ref": f"S{position:03d}-C{index:02d}",
                "text": row["edge_text"],
            }
            for index, row in enumerate(source_choices, 1)
        ]
        if step["available_choices"] != expected_choices:
            raise ValueError(f"Available choices differ at {public_id}/{position}")
        valid_choice_refs.update(choice["choice_ref"] for choice in expected_choices)
        matches = [
            index
            for index, row in enumerate(source_choices)
            if row["target_id"] == target_id
        ]
        if len(matches) > 1:
            raise ValueError(f"Ambiguous original option at {public_id}/{position}")
        chosen = step["chosen_action"]
        expected_chosen: dict[str, Any]
        if matches:
            match = matches[0]
            expected_chosen = {
                "choice_ref": expected_choices[match]["choice_ref"],
                "text": source_choices[match]["edge_text"],
            }
        else:
            expected_chosen = {
                "choice_ref": None,
                "text": expected_implicit_action(
                    edge["transition_kind"], target_id
                ),
            }
        if chosen != expected_chosen:
            raise ValueError(f"Chosen action differs at {public_id}/{position}")
        kind = edge["transition_kind"]
        if step["transition_type"] != TRANSITION_LABELS[kind]:
            raise ValueError(f"Transition label differs at {public_id}/{position}")
        choice_step_count += kind in PLAYER_CHOICE_KINDS
    story_text = render_story(steps)
    if story["story_text"] != story_text:
        raise ValueError(f"Rendered story differs for {public_id}")
    if story["story_sha256"] != text_sha256(story_text):
        raise ValueError(f"Story digest differs for {public_id}")
    if private["story_sha256"] != story["story_sha256"]:
        raise ValueError(f"Private story digest differs for {public_id}")
    if int(story["step_count"]) != len(steps):
        raise ValueError(f"Serialized step count differs for {public_id}")
    if int(story["player_choice_step_count"]) != choice_step_count:
        raise ValueError(f"Player-choice count differs for {public_id}")
    if int(story["word_count"]) != len(story_text.split()):
        raise ValueError(f"Word count differs for {public_id}")
    if int(story["character_count"]) != len(story_text):
        raise ValueError(f"Character count differs for {public_id}")
    if int(story["estimated_token_count"]) != math.ceil(len(story_text) / 4):
        raise ValueError(f"Token estimate differs for {public_id}")
    return valid_choice_refs


def lcs_length(first: list[str], second: list[str]) -> int:
    """Compute a node-sequence LCS length."""
    row = [0] * (len(second) + 1)
    for first_item in first:
        previous = row[:]
        for index, second_item in enumerate(second, 1):
            row[index] = (
                previous[index - 1] + 1
                if first_item == second_item
                else max(previous[index], row[index - 1])
            )
    return row[-1]


def edit_distance(first: list[str], second: list[str]) -> int:
    """Compute node-sequence Levenshtein distance."""
    previous = list(range(len(second) + 1))
    for first_index, first_item in enumerate(first, 1):
        current = [first_index]
        for second_index, second_item in enumerate(second, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[second_index] + 1,
                    previous[second_index - 1]
                    + (first_item != second_item),
                )
            )
        previous = current
    return previous[-1]


def validate_metric_row(
    row: dict[str, str],
    medoid_a: dict[str, Any],
    medoid_b: dict[str, Any],
    bop: dict[str, str],
) -> None:
    """Independently recompute all structural metrics for one pair."""
    label = row["comparison_id"]
    nodes_a = [str(value) for value in medoid_a["node_ids"][:-1]]
    nodes_b = [str(value) for value in medoid_b["node_ids"][:-1]]
    edges_a = [str(value) for value in medoid_a["edge_ids"]]
    edges_b = [str(value) for value in medoid_b["edge_ids"]]
    node_a_set, node_b_set = set(nodes_a), set(nodes_b)
    edge_a_set, edge_b_set = set(edges_a), set(edges_b)
    common_nodes = len(node_a_set & node_b_set)
    common_edges = len(edge_a_set & edge_b_set)
    integer_expected = {
        "paragraph_count_a": len(nodes_a),
        "paragraph_count_b": len(nodes_b),
        "common_unique_paragraph_count": common_nodes,
        "edge_count_a": len(edges_a),
        "edge_count_b": len(edges_b),
        "common_unique_edge_count": common_edges,
    }
    for field, expected in integer_expected.items():
        if int(row[field]) != expected:
            raise ValueError(f"{field} differs for {label}")
    numeric_expected: dict[str, float] = {
        "paragraph_fraction_a": common_nodes / len(node_a_set),
        "paragraph_fraction_b": common_nodes / len(node_b_set),
        "paragraph_jaccard_similarity": common_nodes
        / len(node_a_set | node_b_set),
        "edge_fraction_a": common_edges / len(edge_a_set),
        "edge_fraction_b": common_edges / len(edge_b_set),
        "edge_jaccard_similarity": common_edges / len(edge_a_set | edge_b_set),
        "normalized_node_lcs_similarity": 2
        * lcs_length(nodes_a, nodes_b)
        / (len(nodes_a) + len(nodes_b)),
        "normalized_node_edit_distance": edit_distance(nodes_a, nodes_b)
        / max(len(nodes_a), len(nodes_b)),
        "bop_node_visit_js_divergence_nats": float(
            bop["node_visit_js_divergence_nats"]
        ),
        "bop_edge_flow_js_divergence_nats": float(
            bop["edge_flow_js_divergence_nats"]
        ),
        "bop_win_probability_gap": float(bop["win_probability_gap"]),
        "bop_trajectory_entropy_gap_nats": float(
            bop["trajectory_entropy_gap_nats"]
        ),
    }
    for field, expected_value in numeric_expected.items():
        close(float(row[field]), expected_value, f"{field}/{label}")


def validate_human_templates(
    human_rows: list[dict[str, Any]],
    human_pair_rows: list[dict[str, Any]],
    public_ids: set[str],
    comparison_ids: set[str],
    choice_refs: dict[str, set[str]],
) -> None:
    """Check human-template coverage and any already-filled evidence references."""
    if {str(row.get("trajectory_id")) for row in human_rows} != public_ids:
        raise ValueError("Human trajectory templates do not cover all public stories")
    if {str(row.get("comparison_id")) for row in human_pair_rows} != comparison_ids:
        raise ValueError("Human pair templates do not cover all canonical pairs")
    for row in human_rows:
        public_id = str(row["trajectory_id"])
        if row.get("status") not in {"pending", "complete"}:
            raise ValueError(f"Invalid human status for {public_id}")
        serialized = json.dumps(row, ensure_ascii=False)
        for reference in re.findall(r'"(S\d{3}-C\d{2})"', serialized):
            if reference not in choice_refs[public_id]:
                raise ValueError(f"Unknown human evidence ref {reference}/{public_id}")


def validate_report(report_path: Path, output_paths: list[Path]) -> None:
    """Check phase identity, counts and output hashes in the corpus report."""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("schema_version") != "1.0" or report.get("phase") != "5.1":
        raise ValueError("Unexpected phase-5.1 report version")
    expected_counts = {
        "trajectory_count": 14,
        "calibration_count": 4,
        "validation_count": 10,
        "comparison_count": 6,
        "ordered_pair_count": 12,
    }
    for field, expected in expected_counts.items():
        if report.get(field) != expected:
            raise ValueError(f"Report {field} differs")
    outputs = report.get("outputs")
    if not isinstance(outputs, dict):
        raise ValueError("Report output manifest is missing")
    for path in output_paths:
        matches = [
            value
            for key, value in outputs.items()
            if isinstance(key, str) and key.endswith(path.name)
        ]
        if len(matches) != 1 or not isinstance(matches[0], dict):
            raise ValueError(f"Report does not identify {path.name} exactly once")
        if matches[0].get("sha256") != file_sha256(path):
            raise ValueError(f"Report hash differs for {path.name}")


def main() -> None:
    """Run all independent phase-5.1 corpus checks."""
    parser = argparse.ArgumentParser(
        description="Independently validate the phase-5.1 trajectory corpus."
    )
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument("--phase5-dir", type=Path)
    parser.add_argument("--graph-dir", type=Path)
    parser.add_argument("--annotation-dir", type=Path)
    args = parser.parse_args()

    book_id = str(args.book)
    phase5_dir = args.phase5_dir or Path("data/processed/phase5") / book_id
    graph_dir = args.graph_dir or Path("data/processed/graph") / book_id
    annotation_dir = args.annotation_dir or (
        Path("data/for_trajectory_annotation") / book_id
    )
    nodes_path = (
        Path("data/processed/nodes_edges") / book_id / f"{book_id}_nodes.csv"
    )
    choices_path = (
        Path("data/processed/nodes_edges") / book_id / f"{book_id}_e_edges.csv"
    )
    bop_path = Path("data/processed/bop") / book_id / "profile_pair_metrics.csv"
    medoids_path = phase5_dir / "medoid_trajectories.jsonl"
    trajectories_path = phase5_dir / "trajectories.jsonl"
    private_path = phase5_dir / "trajectory_private_metadata.jsonl"
    pairs_path = phase5_dir / "trajectory_pairs.jsonl"
    pair_private_path = phase5_dir / "pair_private_metadata.jsonl"
    metrics_path = phase5_dir / "pair_structural_metrics.csv"
    report_path = phase5_dir / "trajectory_corpus_report.json"
    human_path = annotation_dir / "human_trajectory_annotations.jsonl"
    human_pairs_path = annotation_dir / "human_pairwise_annotations.jsonl"

    medoids = read_jsonl(medoids_path)
    stories = read_jsonl(trajectories_path)
    private_rows = read_jsonl(private_path)
    ordered_pairs = read_jsonl(pairs_path)
    pair_private_rows = read_jsonl(pair_private_path)
    human_rows = read_jsonl(human_path)
    human_pair_rows = read_jsonl(human_pairs_path)
    metric_fields, metric_rows = read_csv(metrics_path)
    if metric_fields != PAIR_METRIC_FIELDS:
        raise ValueError("Unexpected pair structural metric schema")
    if not (
        len(medoids) == len(stories) == len(private_rows) == len(human_rows) == 14
    ):
        raise ValueError("The four individual artifacts must each contain 14 rows")
    if not (
        len(ordered_pairs) == 12
        and len(pair_private_rows) == len(metric_rows) == len(human_pair_rows) == 6
    ):
        raise ValueError("The pair artifacts have unexpected row counts")

    nodes = load_nodes(nodes_path)
    choices = load_choices(choices_path)
    medoid_by_source = {str(row["trajectory_id"]): row for row in medoids}
    story_by_public = {str(row["trajectory_id"]): row for row in stories}
    private_by_public = {str(row["trajectory_id"]): row for row in private_rows}
    if len(story_by_public) != 14 or set(story_by_public) != set(private_by_public):
        raise ValueError("Public/private trajectory identities differ")
    expected_public_ids = {f"T{position:04d}" for position in range(1, 15)}
    if set(story_by_public) != expected_public_ids:
        raise ValueError("Opaque trajectory identifiers are not canonical")

    choice_refs: dict[str, set[str]] = {}
    medoid_by_cell: dict[tuple[str, str], dict[str, Any]] = {}
    public_by_cell: dict[tuple[str, str], str] = {}
    for public_id in sorted(story_by_public):
        private = private_by_public[public_id]
        if set(private) != PRIVATE_FIELDS:
            raise ValueError(f"Unexpected private schema for {public_id}")
        source_id = str(private["source_trajectory_id"])
        if source_id not in medoid_by_source:
            raise ValueError(f"Unknown medoid mapping for {public_id}")
        medoid = medoid_by_source[source_id]
        profile_id = str(private["profile_id"])
        outcome = str(private["outcome"])
        expected_split = (
            "calibration"
            if (profile_id, outcome) in CALIBRATION_CELLS
            else "validation"
        )
        if private["split"] != expected_split:
            raise ValueError(f"Wrong calibration split for {public_id}")
        compiled = load_compiled_edges(
            graph_dir / profile_id / "compiled_edges.csv"
        )
        choice_refs[public_id] = validate_story(
            story_by_public[public_id],
            private,
            medoid,
            nodes,
            choices,
            compiled,
        )
        cell = (profile_id, outcome)
        medoid_by_cell[cell] = medoid
        public_by_cell[cell] = public_id
        print(
            f"OK: {public_id} — {story_by_public[public_id]['step_count']} steps, "
            f"{story_by_public[public_id]['word_count']} words"
        )

    pair_private_by_id = {
        str(row["comparison_id"]): row for row in pair_private_rows
    }
    metrics_by_id = {row["comparison_id"]: row for row in metric_rows}
    canonical_ids = {f"C{position:03d}" for position in range(1, 7)}
    if set(pair_private_by_id) != canonical_ids or set(metrics_by_id) != canonical_ids:
        raise ValueError("Canonical pair identifiers are incomplete")
    ordered_by_id = {str(row["comparison_id"]): row for row in ordered_pairs}
    if len(ordered_by_id) != 12:
        raise ValueError("Ordered pair identifiers are duplicated")

    _, bop_rows = read_csv(bop_path)
    bop_by_pair = {
        frozenset((row["profile_a"], row["profile_b"])): row for row in bop_rows
    }
    comparison_position = 0
    for axis, profile_a, profile_b in PAIR_DEFINITIONS:
        for outcome in OUTCOMES:
            comparison_position += 1
            comparison_id = f"C{comparison_position:03d}"
            private = pair_private_by_id[comparison_id]
            public_a = public_by_cell[(profile_a, outcome)]
            public_b = public_by_cell[(profile_b, outcome)]
            expected_private = {
                "comparison_id": comparison_id,
                "book_id": book_id,
                "axis": axis,
                "outcome": outcome,
                "profile_a": profile_a,
                "profile_b": profile_b,
                "trajectory_a_id": public_a,
                "trajectory_b_id": public_b,
            }
            if private != expected_private:
                raise ValueError(f"Private pair mapping differs for {comparison_id}")
            ab = ordered_by_id[f"{comparison_id}_AB"]
            ba = ordered_by_id[f"{comparison_id}_BA"]
            assert_no_private_keys(ab, f"{comparison_id}_AB")
            assert_no_private_keys(ba, f"{comparison_id}_BA")
            expected_ab = (
                public_a,
                story_by_public[public_a]["story_text"],
                public_b,
                story_by_public[public_b]["story_text"],
            )
            actual_ab = (
                ab["story_a"]["trajectory_id"],
                ab["story_a"]["story_text"],
                ab["story_b"]["trajectory_id"],
                ab["story_b"]["story_text"],
            )
            actual_ba = (
                ba["story_b"]["trajectory_id"],
                ba["story_b"]["story_text"],
                ba["story_a"]["trajectory_id"],
                ba["story_a"]["story_text"],
            )
            if actual_ab != expected_ab or actual_ba != expected_ab:
                raise ValueError(f"A/B inversion differs for {comparison_id}")
            bop = bop_by_pair[frozenset((profile_a, profile_b))]
            validate_metric_row(
                metrics_by_id[comparison_id],
                medoid_by_cell[(profile_a, outcome)],
                medoid_by_cell[(profile_b, outcome)],
                bop,
            )

    validate_human_templates(
        human_rows,
        human_pair_rows,
        expected_public_ids,
        canonical_ids,
        choice_refs,
    )
    output_paths = [
        trajectories_path,
        private_path,
        pairs_path,
        pair_private_path,
        metrics_path,
    ]
    validate_report(report_path, output_paths)
    print("OK: all 14 stories and 6 bidirectional comparisons validated")


if __name__ == "__main__":
    main()
