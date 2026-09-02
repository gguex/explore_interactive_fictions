"""Phase 5.1: reconstruct blinded full stories from selected medoid paths."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import textwrap
from collections import defaultdict
from pathlib import Path
from typing import Any

DEFAULT_BOOK_ID = "LW01"
OUTCOMES = ("Win", "Death")
PROFILE_AXES = ("risk", "morality", "action")
PLAYER_CHOICE_KINDS = {"profile_choice", "escape"}
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
PAIR_DEFINITIONS = (
    (
        "risk",
        "cautious_neutral_neutral",
        "reckless_neutral_neutral",
    ),
    (
        "morality",
        "neutral_selfish_neutral",
        "neutral_noble_neutral",
    ),
    (
        "action",
        "neutral_neutral_physical",
        "neutral_neutral_tactical",
    ),
)
CALIBRATION_CELLS = {
    ("neutral_neutral_neutral", "Win"),
    ("cautious_neutral_neutral", "Death"),
    ("neutral_noble_neutral", "Win"),
    ("neutral_neutral_tactical", "Death"),
}
HUMAN_PAIR_CALIBRATION_IDS = {"C002", "C003", "C006"}
NODE_FIELDS = [
    "node_id",
    "text_content",
    "absorbing_status",
    "enemies",
    "health_modifier",
    "special_mechanic",
    "image_refs",
    "items_granted",
]
ORIGINAL_EDGE_FIELDS = [
    "source_id",
    "target_id",
    "edge_text",
    "transition_type",
    "realisation_value",
    "semantic_risk",
    "semantic_morality",
    "semantic_action",
    "warnings",
]
COMPILED_EDGE_FIELDS = [
    "edge_id",
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
    "origin",
    "source_ref",
    "note",
    "profile_id",
    "compiled_weight",
]
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


def read_csv(
    path: Path, expected_fields: list[str] | None = None
) -> list[dict[str, str]]:
    """Read one required CSV and optionally enforce its exact schema."""
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header in {path}")
        fields = list(reader.fieldnames)
        if expected_fields is not None and fields != expected_fields:
            raise ValueError(
                f"Unexpected header in {path}: {fields}; expected {expected_fields}"
            )
        return [
            {field: (row.get(field) or "").strip() for field in fields}
            for row in reader
        ]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read non-empty JSON objects from a JSON Lines file."""
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"Line {line_number} in {path} is not an object")
        rows.append(value)
    if not rows:
        raise ValueError(f"Empty JSON Lines input: {path}")
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write deterministic UTF-8 JSON Lines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for row in rows
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def preserve_or_create_template(
    path: Path, rows: list[dict[str, Any]], identity_field: str
) -> str:
    """Create an editable human template once and never overwrite later work."""
    if not path.exists():
        write_jsonl(path, rows)
        return "created"
    existing = read_jsonl(path)
    expected_ids = [str(row[identity_field]) for row in rows]
    existing_ids = [str(row.get(identity_field)) for row in existing]
    if existing_ids != expected_ids:
        raise ValueError(
            f"Existing editable template has unexpected identities: {path}"
        )
    return "preserved"


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    """Write one deterministic CSV table."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def file_sha256(path: Path) -> str:
    """Return a file's SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_sha256(text: str) -> str:
    """Return the SHA-256 digest of one UTF-8 text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def relative_path(path: Path) -> str:
    """Render a repository-relative path when possible."""
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def normalized_text(value: str) -> str:
    """Collapse extraction whitespace without changing punctuation or wording."""
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def load_nodes(path: Path) -> dict[str, str]:
    """Load the 350 source paragraphs and normalized narrative texts."""
    rows = read_csv(path, NODE_FIELDS)
    result: dict[str, str] = {}
    for row in rows:
        node_id = row["node_id"]
        if node_id in result:
            raise ValueError(f"Duplicate paragraph {node_id} in {path}")
        text = normalized_text(row["text_content"])
        if not text:
            raise ValueError(f"Empty narrative text for paragraph {node_id}")
        result[node_id] = text
    return result


def load_original_choices(path: Path) -> dict[str, list[dict[str, str]]]:
    """Index original phase-1 option wording by source paragraph."""
    rows = read_csv(path, ORIGINAL_EDGE_FIELDS)
    result: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        row["edge_text"] = normalized_text(row["edge_text"])
        result[row["source_id"]].append(row)
    return result


def load_compiled_edges(
    path: Path, profile_id: str
) -> dict[str, dict[str, str]]:
    """Load one profile's edge-labelled compiled graph."""
    rows = read_csv(path, COMPILED_EDGE_FIELDS)
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        edge_id = row["edge_id"]
        if edge_id in result:
            raise ValueError(f"Duplicate edge {edge_id} in {path}")
        if row["profile_id"] != profile_id:
            raise ValueError(f"Wrong profile on edge {edge_id}")
        result[edge_id] = row
    return result


def selected_original_choice(
    source_id: str,
    target_id: str,
    choices: list[dict[str, str]],
) -> int | None:
    """Locate the unique original option corresponding to a selected direct edge."""
    matches = [
        index for index, row in enumerate(choices) if row["target_id"] == target_id
    ]
    if len(matches) > 1:
        raise ValueError(
            f"Ambiguous original choices from {source_id} to {target_id}"
        )
    return matches[0] if matches else None


def implicit_action(edge: dict[str, str]) -> str:
    """Describe a generated mechanical or terminal transition in plain English."""
    kind = edge["transition_kind"]
    target_id = edge["target_id"]
    if kind == "combat" and target_id == "Death":
        return "Combat is lost; the trajectory ends here."
    if kind == "outcome":
        return "The narrative ending is reached."
    raise ValueError(
        f"No original option or implicit wording for edge {edge['edge_id']}"
    )


def render_story(steps: list[dict[str, Any]]) -> str:
    """Render one structured story as the exact English document used downstream."""
    blocks: list[str] = []
    for step in steps:
        choices = step["available_choices"]
        if choices:
            available = "\n".join(
                f"{choice['choice_ref']}. {choice['text']}" for choice in choices
            )
        else:
            available = "None."
        chosen = step["chosen_action"]
        chosen_prefix = (
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
                    f"{chosen_prefix}{chosen['text']}",
                    "",
                    "[TRANSITION TYPE]",
                    step["transition_type"],
                )
            )
        )
    return "\n\n".join(blocks)


def render_human_annex(
    stories: list[dict[str, Any]],
    individual_ids: set[str],
    human_pairs: list[dict[str, Any]],
) -> str:
    """Render only the blinded stories needed for human calibration."""
    story_by_id = {str(story["trajectory_id"]): story for story in stories}
    pair_only_ids = {
        str(row[field])
        for row in human_pairs
        for field in ("trajectory_a_id", "trajectory_b_id")
    } - individual_ids
    selected_ids = sorted(individual_ids | pair_only_ids)
    lines = [
        "# Human calibration trajectories — LW01",
        "",
        "> Read each complete story before annotating it. Do not consult the private",
        "> metadata file: profiles and outcomes must remain hidden during annotation.",
        "",
        "The choice references shown here should be copied into the annotation file,",
        "for example `S012-C02`.",
        "",
        "## Annotation plan",
        "",
        "Individual annotations: "
        + ", ".join(f"`{public_id}`" for public_id in sorted(individual_ids))
        + ".",
        "",
        "Pairwise annotations:",
        "",
    ]
    for row in human_pairs:
        lines.append(
            f"- `{row['comparison_id']}`: story A = `{row['trajectory_a_id']}`; "
            f"story B = `{row['trajectory_b_id']}`."
        )
    lines.extend(
        (
            "",
            "The controlled axis, generating profiles and outcomes are intentionally",
            "not identified here. Stories used only for a pairwise comparison do not",
            "require an individual annotation.",
            "",
            "## Stories",
        )
    )
    for public_id in selected_ids:
        story = story_by_id[public_id]
        role = (
            "individual and possibly pairwise calibration"
            if public_id in individual_ids
            else "pairwise calibration only"
        )
        lines.extend(
            (
                "",
                "---",
                "",
                f"### {public_id}",
                "",
                f"Human task: **{role}**",
                "",
                f"{story['step_count']} steps · {story['word_count']} words",
            )
        )
        for step in story["steps"]:
            lines.extend(
                (
                    "",
                    f"#### {step['step_ref']} — Paragraph {step['paragraph_id']}",
                    "",
                    textwrap.fill(str(step["narrative_text"]), width=100),
                    "",
                    "Available choices:",
                    "",
                )
            )
            available = step["available_choices"]
            if available:
                for choice in available:
                    lines.append(
                        textwrap.fill(
                            str(choice["text"]),
                            width=100,
                            initial_indent=f"- `{choice['choice_ref']}` — ",
                            subsequent_indent="  ",
                        )
                    )
            else:
                lines.append("- None.")
            chosen = step["chosen_action"]
            chosen_ref = (
                f"`{chosen['choice_ref']}` — "
                if chosen["choice_ref"] is not None
                else ""
            )
            lines.extend(
                (
                    "",
                    "Chosen action:",
                    "",
                    textwrap.fill(
                        str(chosen["text"]),
                        width=100,
                        initial_indent=f"> {chosen_ref}",
                        subsequent_indent="> ",
                    ),
                    "",
                    f"Transition type: **{step['transition_type']}**",
                )
            )
    return "\n".join(lines) + "\n"


def build_story(
    public_id: str,
    trajectory: dict[str, Any],
    nodes: dict[str, str],
    original_choices: dict[str, list[dict[str, str]]],
    compiled_edges: dict[str, dict[str, str]],
) -> dict[str, Any]:
    """Build a blinded structured story from one selected edge-labelled path."""
    node_ids = [str(node_id) for node_id in trajectory["node_ids"]]
    edge_ids = [str(edge_id) for edge_id in trajectory["edge_ids"]]
    if len(node_ids) != len(edge_ids) + 1:
        raise ValueError(f"Path lengths differ for {trajectory['trajectory_id']}")
    if node_ids[-1] not in OUTCOMES:
        raise ValueError(f"Trajectory does not end at an outcome: {node_ids[-1]}")
    steps: list[dict[str, Any]] = []
    current = node_ids[0]
    for position, edge_id in enumerate(edge_ids, 1):
        if current not in nodes:
            raise ValueError(f"Missing narrative text for paragraph {current}")
        edge = compiled_edges.get(edge_id)
        if edge is None:
            raise ValueError(f"Missing selected edge {edge_id}")
        expected_target = node_ids[position]
        if edge["source_id"] != current or edge["target_id"] != expected_target:
            raise ValueError(f"Selected path is discontinuous at edge {edge_id}")
        kind = edge["transition_kind"]
        if kind not in TRANSITION_LABELS:
            raise ValueError(f"Unsupported transition kind {kind} on {edge_id}")
        source_choices = original_choices.get(current, [])
        available_choices = [
            {
                "choice_ref": f"S{position:03d}-C{choice_index:02d}",
                "text": choice["edge_text"],
            }
            for choice_index, choice in enumerate(source_choices, 1)
        ]
        chosen_index = selected_original_choice(
            current, expected_target, source_choices
        )
        if chosen_index is None:
            chosen_ref = None
            chosen_text = implicit_action(edge)
        else:
            chosen_ref = available_choices[chosen_index]["choice_ref"]
            chosen_text = source_choices[chosen_index]["edge_text"]
        steps.append(
            {
                "step_ref": f"S{position:03d}",
                "paragraph_id": current,
                "narrative_text": nodes[current],
                "available_choices": available_choices,
                "chosen_action": {
                    "choice_ref": chosen_ref,
                    "text": chosen_text,
                },
                "transition_type": TRANSITION_LABELS[kind],
            }
        )
        current = expected_target
    story_text = render_story(steps)
    return {
        "schema_version": "1.0",
        "trajectory_id": public_id,
        "language": "en",
        "step_count": len(steps),
        "player_choice_step_count": sum(
            compiled_edges[edge_id]["transition_kind"] in PLAYER_CHOICE_KINDS
            for edge_id in edge_ids
        ),
        "word_count": len(story_text.split()),
        "character_count": len(story_text),
        "estimated_token_count": math.ceil(len(story_text) / 4),
        "story_sha256": text_sha256(story_text),
        "steps": steps,
        "story_text": story_text,
    }


def lcs_length(first: list[str], second: list[str]) -> int:
    """Return the longest-common-subsequence length for two node sequences."""
    previous = [0] * (len(second) + 1)
    for first_item in first:
        current = [0]
        for index, second_item in enumerate(second, 1):
            if first_item == second_item:
                current.append(previous[index - 1] + 1)
            else:
                current.append(max(previous[index], current[-1]))
        previous = current
    return previous[-1]


def edit_distance(first: list[str], second: list[str]) -> int:
    """Return Levenshtein distance between two node sequences."""
    previous = list(range(len(second) + 1))
    for first_index, first_item in enumerate(first, 1):
        current = [first_index]
        for second_index, second_item in enumerate(second, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[second_index] + 1,
                    previous[second_index - 1]
                    + (0 if first_item == second_item else 1),
                )
            )
        previous = current
    return previous[-1]


def rounded(value: float) -> float:
    """Round one finite metric to a stable decimal representation."""
    if not math.isfinite(value):
        raise ValueError(f"Cannot serialize non-finite value: {value}")
    return float(format(value, ".15g"))


def set_similarity(
    first: set[str], second: set[str]
) -> tuple[int, float, float, float]:
    """Return intersection count, directional fractions and Jaccard similarity."""
    common = len(first & second)
    union = len(first | second)
    return (
        common,
        common / len(first),
        common / len(second),
        common / union,
    )


def load_bop_pairs(path: Path) -> dict[frozenset[str], dict[str, str]]:
    """Index phase-4 profile-pair metrics without assuming orientation."""
    rows = read_csv(path)
    result: dict[frozenset[str], dict[str, str]] = {}
    for row in rows:
        key = frozenset((row["profile_a"], row["profile_b"]))
        if key in result:
            raise ValueError(f"Duplicate BoP profile pair {sorted(key)}")
        result[key] = row
    return result


def structural_metrics(
    comparison_id: str,
    public_a: str,
    public_b: str,
    trajectory_a: dict[str, Any],
    trajectory_b: dict[str, Any],
    bop_row: dict[str, str],
) -> dict[str, Any]:
    """Calculate the six predeclared structural comparison measures."""
    nodes_a = [str(node) for node in trajectory_a["node_ids"][:-1]]
    nodes_b = [str(node) for node in trajectory_b["node_ids"][:-1]]
    edges_a = [str(edge) for edge in trajectory_a["edge_ids"]]
    edges_b = [str(edge) for edge in trajectory_b["edge_ids"]]
    common_nodes, node_fraction_a, node_fraction_b, node_jaccard = set_similarity(
        set(nodes_a), set(nodes_b)
    )
    common_edges, edge_fraction_a, edge_fraction_b, edge_jaccard = set_similarity(
        set(edges_a), set(edges_b)
    )
    lcs = lcs_length(nodes_a, nodes_b)
    node_similarity = 2 * lcs / (len(nodes_a) + len(nodes_b))
    node_edit = edit_distance(nodes_a, nodes_b) / max(len(nodes_a), len(nodes_b))
    return {
        "comparison_id": comparison_id,
        "trajectory_a_id": public_a,
        "trajectory_b_id": public_b,
        "paragraph_count_a": len(nodes_a),
        "paragraph_count_b": len(nodes_b),
        "common_unique_paragraph_count": common_nodes,
        "paragraph_fraction_a": rounded(node_fraction_a),
        "paragraph_fraction_b": rounded(node_fraction_b),
        "paragraph_jaccard_similarity": rounded(node_jaccard),
        "edge_count_a": len(edges_a),
        "edge_count_b": len(edges_b),
        "common_unique_edge_count": common_edges,
        "edge_fraction_a": rounded(edge_fraction_a),
        "edge_fraction_b": rounded(edge_fraction_b),
        "edge_jaccard_similarity": rounded(edge_jaccard),
        "normalized_node_lcs_similarity": rounded(node_similarity),
        "normalized_node_edit_distance": rounded(node_edit),
        "bop_node_visit_js_divergence_nats": float(
            bop_row["node_visit_js_divergence_nats"]
        ),
        "bop_edge_flow_js_divergence_nats": float(
            bop_row["edge_flow_js_divergence_nats"]
        ),
        "bop_win_probability_gap": float(bop_row["win_probability_gap"]),
        "bop_trajectory_entropy_gap_nats": float(
            bop_row["trajectory_entropy_gap_nats"]
        ),
    }


def individual_annotation_template(public_id: str) -> dict[str, Any]:
    """Return one empty human-annotation record using the canonical grid."""
    axis_template: dict[str, Any] = {
        "label": None,
        "support": None,
        "justification": "",
        "supporting_choice_refs": [],
        "counterevidence_choice_refs": [],
    }
    return {
        "trajectory_id": public_id,
        "annotation_role": "prompt_calibration",
        "annotator_id": "",
        "status": "pending",
        "perceived_profile": {
            axis: dict(axis_template) for axis in PROFILE_AXES
        },
        "causal_continuity": {
            "label": None,
            "justification": "",
            "evidence_paragraph_ids": [],
        },
        "profile_coherence": {
            "label": None,
            "justification": "",
            "supporting_choice_refs": [],
            "counterevidence_choice_refs": [],
        },
    }


def pair_annotation_template(
    comparison_id: str, public_a: str, public_b: str
) -> dict[str, Any]:
    """Return one empty human pairwise-annotation record."""
    return {
        "comparison_id": comparison_id,
        "trajectory_a_id": public_a,
        "trajectory_b_id": public_b,
        "annotator_id": "",
        "status": "pending",
        "narrative_distinctness": {"label": None, "justification": ""},
        "perceived_profile_shift": {axis: None for axis in PROFILE_AXES},
        "profile_shift_justification": "",
        "evidence_story_a": [],
        "evidence_story_b": [],
    }


def main() -> None:
    """Build phase-5 stories, ordered pairs, private mappings and human templates."""
    parser = argparse.ArgumentParser(
        description="Build the blinded phase-5 trajectory corpus."
    )
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument("--phase5-dir", type=Path)
    parser.add_argument("--graph-dir", type=Path)
    parser.add_argument("--nodes", type=Path)
    parser.add_argument("--original-edges", type=Path)
    parser.add_argument("--bop-pairs", type=Path)
    parser.add_argument("--annotation-dir", type=Path)
    args = parser.parse_args()

    book_id = str(args.book)
    phase5_dir = args.phase5_dir or Path("data/processed/phase5") / book_id
    graph_dir = args.graph_dir or Path("data/processed/graph") / book_id
    nodes_path = args.nodes or (
        Path("data/processed/nodes_edges") / book_id / f"{book_id}_nodes.csv"
    )
    original_edges_path = args.original_edges or (
        Path("data/processed/nodes_edges") / book_id / f"{book_id}_edges.csv"
    )
    bop_pairs_path = args.bop_pairs or (
        Path("data/processed/bop") / book_id / "profile_pair_metrics.csv"
    )
    annotation_dir = args.annotation_dir or (
        Path("data/for_trajectory_annotation") / book_id
    )
    medoids_path = phase5_dir / "medoid_trajectories.jsonl"

    medoids = read_jsonl(medoids_path)
    if len(medoids) != 14:
        raise ValueError(f"Expected 14 medoids, found {len(medoids)}")
    nodes = load_nodes(nodes_path)
    original_choices = load_original_choices(original_edges_path)
    bop_pairs = load_bop_pairs(bop_pairs_path)

    stories: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []
    human_rows: list[dict[str, Any]] = []
    medoid_by_cell: dict[tuple[str, str], dict[str, Any]] = {}
    public_by_cell: dict[tuple[str, str], str] = {}
    story_by_public_id: dict[str, dict[str, Any]] = {}
    input_paths = [medoids_path, nodes_path, original_edges_path, bop_pairs_path]
    for position, medoid in enumerate(medoids, 1):
        profile_id = str(medoid["profile_id"])
        outcome = str(medoid["outcome"])
        cell = (profile_id, outcome)
        if cell in medoid_by_cell:
            raise ValueError(f"Duplicate medoid cell {cell}")
        public_id = f"T{position:04d}"
        compiled_path = graph_dir / profile_id / "compiled_edges.csv"
        compiled_edges = load_compiled_edges(compiled_path, profile_id)
        if compiled_path not in input_paths:
            input_paths.append(compiled_path)
        story = build_story(
            public_id, medoid, nodes, original_choices, compiled_edges
        )
        annotation_role = (
            "human_calibration" if cell in CALIBRATION_CELLS else "model_analysis"
        )
        private_rows.append(
            {
                "trajectory_id": public_id,
                "source_trajectory_id": medoid["trajectory_id"],
                "book_id": book_id,
                "profile_id": profile_id,
                "risk": medoid["risk"],
                "morality": medoid["morality"],
                "action": medoid["action"],
                "outcome": outcome,
                "annotation_role": annotation_role,
                "node_ids": medoid["node_ids"],
                "edge_ids": medoid["edge_ids"],
                "medoid_trajectory_sha256": medoid["trajectory_sha256"],
                "story_sha256": story["story_sha256"],
            }
        )
        stories.append(story)
        if cell in CALIBRATION_CELLS:
            human_rows.append(individual_annotation_template(public_id))
        medoid_by_cell[cell] = medoid
        public_by_cell[cell] = public_id
        story_by_public_id[public_id] = story

    pair_rows: list[dict[str, Any]] = []
    pair_private_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    human_pair_rows: list[dict[str, Any]] = []
    comparison_position = 0
    for axis, profile_a, profile_b in PAIR_DEFINITIONS:
        bop_key = frozenset((profile_a, profile_b))
        if bop_key not in bop_pairs:
            raise ValueError(f"Missing BoP pair metrics for {profile_a}/{profile_b}")
        for outcome in OUTCOMES:
            comparison_position += 1
            comparison_id = f"C{comparison_position:03d}"
            cell_a = (profile_a, outcome)
            cell_b = (profile_b, outcome)
            if cell_a not in medoid_by_cell or cell_b not in medoid_by_cell:
                raise ValueError(f"Missing medoid for comparison {comparison_id}")
            public_a = public_by_cell[cell_a]
            public_b = public_by_cell[cell_b]
            for order, first_id, second_id in (
                ("AB", public_a, public_b),
                ("BA", public_b, public_a),
            ):
                pair_rows.append(
                    {
                        "schema_version": "1.0",
                        "comparison_id": f"{comparison_id}_{order}",
                        "story_a": {
                            "trajectory_id": first_id,
                            "story_text": story_by_public_id[first_id]["story_text"],
                        },
                        "story_b": {
                            "trajectory_id": second_id,
                            "story_text": story_by_public_id[second_id]["story_text"],
                        },
                    }
                )
            pair_private_rows.append(
                {
                    "comparison_id": comparison_id,
                    "book_id": book_id,
                    "axis": axis,
                    "outcome": outcome,
                    "profile_a": profile_a,
                    "profile_b": profile_b,
                    "trajectory_a_id": public_a,
                    "trajectory_b_id": public_b,
                }
            )
            metric_rows.append(
                structural_metrics(
                    comparison_id,
                    public_a,
                    public_b,
                    medoid_by_cell[cell_a],
                    medoid_by_cell[cell_b],
                    bop_pairs[bop_key],
                )
            )
            if comparison_id in HUMAN_PAIR_CALIBRATION_IDS:
                human_pair_rows.append(
                    pair_annotation_template(comparison_id, public_a, public_b)
                )

    trajectories_path = phase5_dir / "trajectories.jsonl"
    private_path = phase5_dir / "trajectory_private_metadata.jsonl"
    pairs_path = phase5_dir / "trajectory_pairs.jsonl"
    pair_private_path = phase5_dir / "pair_private_metadata.jsonl"
    metrics_path = phase5_dir / "pair_structural_metrics.csv"
    human_path = annotation_dir / "human_trajectory_annotations.jsonl"
    human_pairs_path = annotation_dir / "human_pairwise_annotations.jsonl"
    annex_path = annotation_dir / "TRAJECTORIES_FOR_ANNOTATION.md"
    report_path = phase5_dir / "trajectory_corpus_report.json"
    write_jsonl(trajectories_path, stories)
    write_jsonl(private_path, private_rows)
    write_jsonl(pairs_path, pair_rows)
    write_jsonl(pair_private_path, pair_private_rows)
    write_csv(metrics_path, metric_rows, PAIR_METRIC_FIELDS)
    human_status = preserve_or_create_template(
        human_path, human_rows, "trajectory_id"
    )
    human_pair_status = preserve_or_create_template(
        human_pairs_path, human_pair_rows, "comparison_id"
    )
    annex_path.parent.mkdir(parents=True, exist_ok=True)
    annex_path.write_text(
        render_human_annex(
            stories,
            {str(row["trajectory_id"]) for row in human_rows},
            human_pair_rows,
        ),
        encoding="utf-8",
    )

    outputs = [
        trajectories_path,
        private_path,
        pairs_path,
        pair_private_path,
        metrics_path,
        annex_path,
    ]
    report = {
        "schema_version": "1.1",
        "book_id": book_id,
        "phase": "5.1",
        "status": "complete",
        "trajectory_count": len(stories),
        "human_calibration_trajectory_count": sum(
            row["annotation_role"] == "human_calibration" for row in private_rows
        ),
        "model_only_trajectory_count": sum(
            row["annotation_role"] == "model_analysis" for row in private_rows
        ),
        "comparison_count": len(pair_private_rows),
        "ordered_pair_count": len(pair_rows),
        "human_calibration_pair_count": len(human_pair_rows),
        "transition_labels": TRANSITION_LABELS,
        "player_choice_kinds": sorted(PLAYER_CHOICE_KINDS),
        "human_calibration_rule": (
            "neutral/Win plus one controlled pole per axis, alternating outcomes: "
            "cautious/Death, noble/Win, tactical/Death"
        ),
        "human_pair_calibration_rule": (
            "one blinded pair per axis, reusing a human-calibrated trajectory: "
            "C002, C003 and C006"
        ),
        "length_summary": {
            "minimum_steps": min(int(story["step_count"]) for story in stories),
            "maximum_steps": max(int(story["step_count"]) for story in stories),
            "minimum_words": min(int(story["word_count"]) for story in stories),
            "maximum_words": max(int(story["word_count"]) for story in stories),
            "maximum_estimated_tokens": max(
                int(story["estimated_token_count"]) for story in stories
            ),
            "token_estimate_warning": (
                "Character-count/4 is only a planning estimate; 5.2 must use the exact "
                "Qwen tokenizer after adding the prompt."
            ),
        },
        "inputs": {
            relative_path(path): file_sha256(path) for path in sorted(input_paths)
        },
        "outputs": {
            relative_path(path): {"sha256": file_sha256(path)} for path in outputs
        },
        "editable_human_templates": {
            relative_path(human_path): {
                "rows": len(human_rows),
                "status": human_status,
                "sha256_at_report_time": file_sha256(human_path),
            },
            relative_path(human_pairs_path): {
                "rows": len(human_pair_rows),
                "status": human_pair_status,
                "sha256_at_report_time": file_sha256(human_pairs_path),
            },
        },
    }
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"Blinded complete stories: {len(stories)}")
    print(
        "Human calibration/model-only stories: "
        f"{report['human_calibration_trajectory_count']}/"
        f"{report['model_only_trajectory_count']}"
    )
    print(f"Ordered pair documents: {len(pair_rows)} ({len(pair_private_rows)} pairs)")
    print(
        "Story lengths: "
        f"{report['length_summary']['minimum_steps']}–"
        f"{report['length_summary']['maximum_steps']} steps; "
        f"up to {report['length_summary']['maximum_words']} words"
    )
    print(f"Output: {phase5_dir}")
    print(f"Human templates: {annotation_dir}")


if __name__ == "__main__":
    main()
