"""Independently validate phase-5.0 conditional empirical medoids."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_BOOK_ID = "LW01"
DEFAULT_PROFILES_PATH = Path("data/for_graph_model/behavioral_profiles.json")
START_NODE = "1"
OUTCOME_IDS = ("Win", "Death")
CONTROLLED_PROFILE_IDS = (
    "neutral_neutral_neutral",
    "cautious_neutral_neutral",
    "reckless_neutral_neutral",
    "neutral_selfish_neutral",
    "neutral_noble_neutral",
    "neutral_neutral_physical",
    "neutral_neutral_tactical",
)
TRAJECTORY_FIELDS = {
    "trajectory_id",
    "book_id",
    "profile_id",
    "risk",
    "morality",
    "action",
    "outcome",
    "selection_method",
    "distance_metric",
    "sample_count",
    "sampling_seed",
    "unique_sampled_paths",
    "start_node",
    "terminal_node",
    "node_ids",
    "edge_ids",
    "edge_weights",
    "transition_kinds",
    "transition_count",
    "mean_sample_distance",
    "medoid_sample_frequency",
    "medoid_sample_share",
    "medoid_tie_count",
    "tie_break_applied",
    "path_probability",
    "outcome_probability",
    "conditional_path_probability",
    "trajectory_sha256",
}
SAMPLE_FIELDS = {
    "book_id",
    "profile_id",
    "outcome",
    "sampling_seed",
    "edge_ids",
    "node_ids",
    "transition_count",
    "count",
    "sample_share",
    "path_probability",
    "conditional_path_probability",
    "trajectory_sha256",
}
MAX_TRANSITIONS = 5000
ATOL = 5e-11


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read one required CSV file."""
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header in {path}")
        return list(reader.fieldnames), [dict(row) for row in reader]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read non-empty JSON objects from a JSON Lines artifact."""
    if not path.exists():
        raise FileNotFoundError(f"Missing phase-5.0 artifact: {path}")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise ValueError(f"Line {line_number} in {path} is not an object")
        rows.append(raw)
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


def trajectory_digest(
    book_id: str, profile_id: str, outcome: str, edge_ids: list[str]
) -> str:
    """Recompute the stable identity of one edge-labelled path."""
    payload = json.dumps(
        {
            "book_id": book_id,
            "profile_id": profile_id,
            "outcome": outcome,
            "edge_ids": edge_ids,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def close(actual: float, expected: float, label: str) -> None:
    """Require finite scalar agreement within serialization tolerance."""
    if not math.isfinite(actual) or not math.isfinite(expected):
        raise ValueError(f"Non-finite value for {label}: {actual}, {expected}")
    if not math.isclose(actual, expected, rel_tol=ATOL, abs_tol=ATOL):
        raise ValueError(
            f"{label}: got {actual:.15g}, expected {expected:.15g}"
        )


def load_profiles(path: Path) -> dict[str, dict[str, str]]:
    """Load profile metadata for the controlled design."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Profile design in {path} is not a list")
    profiles: dict[str, dict[str, str]] = {}
    for raw in payload:
        if not isinstance(raw, dict):
            raise ValueError(f"Invalid profile entry in {path}")
        profile = {str(key): str(value) for key, value in raw.items()}
        profile_id = profile.get("profile_id", "")
        if not profile_id or profile_id in profiles:
            raise ValueError(f"Missing or duplicate profile identifier in {path}")
        profiles[profile_id] = profile
    if set(CONTROLLED_PROFILE_IDS) - set(profiles):
        raise ValueError("Controlled profile design is incomplete")
    return profiles


def load_matrix(path: Path) -> tuple[list[str], np.ndarray[Any, Any]]:
    """Load and validate one phase-3 transition matrix."""
    fields, rows = read_csv(path)
    if not fields or fields[0] != "node_id":
        raise ValueError(f"Unexpected matrix header in {path}")
    node_ids = fields[1:]
    if [row["node_id"] for row in rows] != node_ids:
        raise ValueError(f"Matrix row and column order differs in {path}")
    matrix = np.array(
        [[float(row[target_id]) for target_id in node_ids] for row in rows],
        dtype=float,
    )
    if not np.isfinite(matrix).all() or not np.allclose(
        matrix.sum(axis=1), 1.0, rtol=ATOL, atol=ATOL
    ):
        raise ValueError(f"Invalid transition matrix in {path}")
    return node_ids, matrix


def load_edges(
    path: Path,
    profile_id: str,
    node_ids: list[str],
    matrix: np.ndarray[Any, Any],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Load multiedges and independently check their dense aggregation."""
    _, rows = read_csv(path)
    index = {node_id: position for position, node_id in enumerate(node_ids)}
    reconstructed = np.zeros_like(matrix)
    for outcome in OUTCOME_IDS:
        reconstructed[index[outcome], index[outcome]] = 1.0
    edges: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        edge_id = str(row["edge_id"])
        if edge_id in seen:
            raise ValueError(f"Duplicate edge identifier {edge_id}")
        seen.add(edge_id)
        if row["profile_id"] != profile_id:
            raise ValueError(f"Wrong profile metadata on {edge_id}")
        weight = float(row["compiled_weight"])
        if not math.isfinite(weight) or not 0 <= weight <= 1:
            raise ValueError(f"Invalid weight on {edge_id}")
        source_id = str(row["source_id"])
        target_id = str(row["target_id"])
        reconstructed[index[source_id], index[target_id]] += weight
        if weight > 0:
            edges.append(
                {
                    "edge_id": edge_id,
                    "source_id": source_id,
                    "target_id": target_id,
                    "transition_kind": str(row["transition_kind"]),
                    "weight": weight,
                }
            )
    if not np.allclose(reconstructed, matrix, rtol=ATOL, atol=ATOL):
        raise ValueError(f"Compiled edges do not reconstruct {path.parent / 'W.csv'}")
    edges.sort(key=lambda edge: str(edge["edge_id"]))
    return edges, {str(edge["edge_id"]): edge for edge in edges}


def outcome_potentials(
    node_ids: list[str], matrix: np.ndarray[Any, Any]
) -> dict[str, dict[str, float]]:
    """Recompute all Win and Death absorption probabilities."""
    index = {node_id: position for position, node_id in enumerate(node_ids)}
    transient_ids = [node_id for node_id in node_ids if node_id not in OUTCOME_IDS]
    transient_positions = [index[node_id] for node_id in transient_ids]
    absorbing_positions = [index[outcome] for outcome in OUTCOME_IDS]
    q_matrix = matrix[np.ix_(transient_positions, transient_positions)]
    r_matrix = matrix[np.ix_(transient_positions, absorbing_positions)]
    absorption = np.linalg.solve(np.eye(len(q_matrix)) - q_matrix, r_matrix)
    result: dict[str, dict[str, float]] = {outcome: {} for outcome in OUTCOME_IDS}
    for outcome_position, outcome in enumerate(OUTCOME_IDS):
        for row_position, node_id in enumerate(transient_ids):
            result[outcome][node_id] = float(absorption[row_position, outcome_position])
        for terminal in OUTCOME_IDS:
            result[outcome][terminal] = 1.0 if terminal == outcome else 0.0
    return result


def conditioned_adjacency(
    edges: list[dict[str, Any]], potentials: dict[str, float]
) -> dict[str, list[tuple[dict[str, Any], float]]]:
    """Independently construct an edge-level Doob chain."""
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        outgoing[str(edge["source_id"])].append(edge)
    result: dict[str, list[tuple[dict[str, Any], float]]] = {}
    for source_id, candidates in outgoing.items():
        source_potential = potentials[source_id]
        if source_potential <= 0:
            continue
        weighted = [
            (
                edge,
                float(edge["weight"])
                * potentials[str(edge["target_id"])]
                / source_potential,
            )
            for edge in candidates
            if potentials[str(edge["target_id"])] > 0
        ]
        total = math.fsum(probability for _, probability in weighted)
        if not math.isclose(total, 1.0, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError(f"Invalid conditioned mass at {source_id}: {total}")
        result[source_id] = [
            (edge, probability / total) for edge, probability in weighted
        ]
    return result


def regenerated_counts(
    outcome: str,
    sample_count: int,
    sampling_seed: int,
    conditioned: dict[str, list[tuple[dict[str, Any], float]]],
) -> Counter[tuple[str, ...]]:
    """Regenerate the declared conditioned sample from its seed."""
    generator = random.Random(sampling_seed)
    counts: Counter[tuple[str, ...]] = Counter()
    for _ in range(sample_count):
        current = START_NODE
        path: list[str] = []
        for _ in range(MAX_TRANSITIONS):
            if current in OUTCOME_IDS:
                if current != outcome:
                    raise ValueError(f"Sampler reached unexpected outcome {current}")
                counts[tuple(path)] += 1
                break
            candidates = conditioned.get(current)
            if not candidates:
                raise ValueError(f"No conditioned edge at {current}")
            draw = generator.random()
            cumulative = 0.0
            selected = candidates[-1][0]
            for edge, probability in candidates:
                cumulative += probability
                if draw < cumulative:
                    selected = edge
                    break
            path.append(str(selected["edge_id"]))
            current = str(selected["target_id"])
        else:
            raise ValueError("A regenerated path exceeded the transition limit")
    return counts


def reconstruct_nodes(
    path: tuple[str, ...], edge_by_id: dict[str, dict[str, Any]]
) -> list[str]:
    """Reconstruct and validate the nodes of one edge-labelled path."""
    nodes = [START_NODE]
    current = START_NODE
    for edge_id in path:
        if edge_id not in edge_by_id:
            raise ValueError(f"Unknown positive-probability edge {edge_id}")
        edge = edge_by_id[edge_id]
        if edge["source_id"] != current:
            raise ValueError(f"Discontinuous path at {edge_id}")
        current = str(edge["target_id"])
        nodes.append(current)
    return nodes


def node_masks(sequence: list[str]) -> dict[str, int]:
    """Build bit masks for an independent LCS calculation."""
    result: dict[str, int] = {}
    for index, node_id in enumerate(sequence):
        result[node_id] = result.get(node_id, 0) | (1 << index)
    return result


def lcs_length(first: list[str], second_masks: dict[str, int]) -> int:
    """Compute the LCS length by a bit-vector recurrence."""
    row = 0
    for node_id in first:
        matches = second_masks.get(node_id, 0)
        merged = row | matches
        row = merged & ~(merged - ((row << 1) | 1))
    return row.bit_count()


def distance(first: list[str], second: list[str]) -> float:
    """Compute the declared symmetric normalized-LCS distance."""
    return 1.0 - 2 * lcs_length(first, node_masks(second)) / (
        len(first) + len(second)
    )


def medoid_summary(
    counts: Counter[tuple[str, ...]], edge_by_id: dict[str, dict[str, Any]]
) -> tuple[tuple[str, ...], float, int]:
    """Recompute the weighted sample medoid and canonical tie-break."""
    paths = sorted(counts)
    nodes = [reconstruct_nodes(path, edge_by_id) for path in paths]
    totals = [0.0] * len(paths)
    for first_index in range(len(paths)):
        for second_index in range(first_index + 1, len(paths)):
            pair_distance = distance(nodes[first_index], nodes[second_index])
            totals[first_index] += counts[paths[second_index]] * pair_distance
            totals[second_index] += counts[paths[first_index]] * pair_distance
    means = [total / sum(counts.values()) for total in totals]
    minimum = min(means)
    tied = [
        index
        for index, mean in enumerate(means)
        if math.isclose(mean, minimum, rel_tol=1e-12, abs_tol=1e-12)
    ]
    selected = min(tied, key=lambda index: paths[index])
    return paths[selected], means[selected], len(tied)


def path_probability(
    path: tuple[str, ...], edge_by_id: dict[str, dict[str, Any]]
) -> float:
    """Recompute the unconditional probability of a sampled path."""
    return math.prod(float(edge_by_id[edge_id]["weight"]) for edge_id in path)


def validate_cell(
    book_id: str,
    profile_id: str,
    outcome: str,
    trajectory: dict[str, Any],
    sample_rows: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    edge_by_id: dict[str, dict[str, Any]],
    potentials: dict[str, float],
) -> None:
    """Validate one trajectory, persisted sample and deterministic regeneration."""
    label = f"{profile_id}/{outcome}"
    if set(trajectory) != TRAJECTORY_FIELDS:
        raise ValueError(f"Unexpected trajectory schema for {label}")
    if trajectory["selection_method"] != "conditional_empirical_medoid":
        raise ValueError(f"Unexpected selection method for {label}")
    if trajectory["distance_metric"] != "one_minus_symmetric_normalized_node_lcs":
        raise ValueError(f"Unexpected distance metric for {label}")
    sample_count = int(trajectory["sample_count"])
    sampling_seed = int(trajectory["sampling_seed"])
    persisted: Counter[tuple[str, ...]] = Counter()
    for row in sample_rows:
        if set(row) != SAMPLE_FIELDS:
            raise ValueError(f"Unexpected sample schema for {label}")
        if int(row["sampling_seed"]) != sampling_seed:
            raise ValueError(f"Mixed sampling seeds for {label}")
        path = tuple(str(edge_id) for edge_id in row["edge_ids"])
        if path in persisted:
            raise ValueError(f"Duplicate unique-path record for {label}")
        count = int(row["count"])
        if count <= 0:
            raise ValueError(f"Non-positive path count for {label}")
        persisted[path] = count
        nodes = reconstruct_nodes(path, edge_by_id)
        if nodes[-1] != outcome or row["node_ids"] != nodes:
            raise ValueError(f"Wrong nodes or outcome in sample for {label}")
        if int(row["transition_count"]) != len(path):
            raise ValueError(f"Wrong sample length for {label}")
        probability = path_probability(path, edge_by_id)
        close(float(row["sample_share"]), count / sample_count, f"share {label}")
        close(float(row["path_probability"]), probability, f"P(path) {label}")
        close(
            float(row["conditional_path_probability"]),
            probability / potentials[START_NODE],
            f"P(path|outcome) {label}",
        )
        expected_digest = trajectory_digest(book_id, profile_id, outcome, list(path))
        if row["trajectory_sha256"] != expected_digest:
            raise ValueError(f"Wrong sample digest for {label}")
    if sum(persisted.values()) != sample_count:
        raise ValueError(f"Persisted sample size differs for {label}")
    if len(persisted) != int(trajectory["unique_sampled_paths"]):
        raise ValueError(f"Unique sample count differs for {label}")

    conditioned = conditioned_adjacency(edges, potentials)
    regenerated = regenerated_counts(
        outcome, sample_count, sampling_seed, conditioned
    )
    if regenerated != persisted:
        raise ValueError(f"Seeded conditioned sample is not reproducible for {label}")

    medoid_path, mean_distance, tie_count = medoid_summary(persisted, edge_by_id)
    if list(medoid_path) != trajectory["edge_ids"]:
        raise ValueError(f"Selected path is not the empirical medoid for {label}")
    selected_nodes = reconstruct_nodes(medoid_path, edge_by_id)
    if trajectory["node_ids"] != selected_nodes:
        raise ValueError(f"Selected node sequence differs for {label}")
    if trajectory["terminal_node"] != outcome or trajectory["start_node"] != START_NODE:
        raise ValueError(f"Wrong trajectory endpoints for {label}")
    if int(trajectory["transition_count"]) != len(medoid_path):
        raise ValueError(f"Wrong medoid length for {label}")
    if int(trajectory["medoid_sample_frequency"]) != persisted[medoid_path]:
        raise ValueError(f"Wrong medoid frequency for {label}")
    if int(trajectory["medoid_tie_count"]) != tie_count:
        raise ValueError(f"Wrong medoid tie count for {label}")
    if bool(trajectory["tie_break_applied"]) != (tie_count > 1):
        raise ValueError(f"Wrong tie flag for {label}")
    close(
        float(trajectory["mean_sample_distance"]),
        mean_distance,
        f"medoid objective {label}",
    )
    close(
        float(trajectory["medoid_sample_share"]),
        persisted[medoid_path] / sample_count,
        f"medoid share {label}",
    )
    probability = path_probability(medoid_path, edge_by_id)
    close(float(trajectory["path_probability"]), probability, f"P(medoid) {label}")
    close(
        float(trajectory["outcome_probability"]),
        potentials[START_NODE],
        f"P(outcome) {label}",
    )
    close(
        float(trajectory["conditional_path_probability"]),
        probability / potentials[START_NODE],
        f"P(medoid|outcome) {label}",
    )
    expected_digest = trajectory_digest(
        book_id, profile_id, outcome, list(medoid_path)
    )
    if trajectory["trajectory_sha256"] != expected_digest:
        raise ValueError(f"Wrong medoid digest for {label}")
    expected_weights = [float(edge_by_id[edge_id]["weight"]) for edge_id in medoid_path]
    expected_kinds = [
        str(edge_by_id[edge_id]["transition_kind"]) for edge_id in medoid_path
    ]
    if not np.allclose(
        trajectory["edge_weights"], expected_weights, rtol=ATOL, atol=ATOL
    ):
        raise ValueError(f"Wrong edge weights for {label}")
    if trajectory["transition_kinds"] != expected_kinds:
        raise ValueError(f"Wrong transition kinds for {label}")


def validate_report(
    report_path: Path,
    trajectories_path: Path,
    samples_path: Path,
    trajectories: list[dict[str, Any]],
    sample_rows: list[dict[str, Any]],
) -> None:
    """Validate the manifest metadata and output hashes."""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("schema_version") != "2.0" or report.get("phase") != "5.0":
        raise ValueError("Unexpected phase-5.0 report version")
    if report.get("trajectory_count") != len(trajectories):
        raise ValueError("Report trajectory count differs")
    if report.get("sample_record_count") != len(sample_rows):
        raise ValueError("Report sample-record count differs")
    outputs = report.get("outputs")
    if not isinstance(outputs, dict):
        raise ValueError("Report outputs are missing")
    matched = 0
    for path, expected_rows in (
        (trajectories_path, len(trajectories)),
        (samples_path, len(sample_rows)),
    ):
        records = [
            value
            for key, value in outputs.items()
            if isinstance(key, str) and key.endswith(path.name)
        ]
        if len(records) != 1 or not isinstance(records[0], dict):
            raise ValueError(f"Report does not identify {path.name} exactly once")
        if records[0].get("rows") != expected_rows:
            raise ValueError(f"Report row count differs for {path.name}")
        if records[0].get("sha256") != file_sha256(path):
            raise ValueError(f"Report hash differs for {path.name}")
        matched += 1
    if matched != 2:
        raise ValueError("Not all phase-5.0 outputs were checked")


def main() -> None:
    """Run all independent phase-5.0 checks."""
    parser = argparse.ArgumentParser(
        description="Independently validate phase-5 conditional medoids."
    )
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES_PATH)
    parser.add_argument("--graph-dir", type=Path)
    parser.add_argument("--input-dir", type=Path)
    args = parser.parse_args()

    book_id = str(args.book)
    graph_dir = args.graph_dir or Path("data/processed/graph") / book_id
    input_dir = args.input_dir or Path("data/processed/phase5") / book_id
    trajectories_path = input_dir / "medoid_trajectories.jsonl"
    samples_path = input_dir / "conditional_path_counts.jsonl"
    report_path = input_dir / "medoid_selection_report.json"
    trajectories = read_jsonl(trajectories_path)
    sample_rows = read_jsonl(samples_path)
    profiles = load_profiles(args.profiles)

    indexed_trajectories: dict[tuple[str, str], dict[str, Any]] = {}
    for row in trajectories:
        cell = (str(row.get("profile_id")), str(row.get("outcome")))
        if cell in indexed_trajectories:
            raise ValueError(f"Duplicate trajectory cell: {cell}")
        indexed_trajectories[cell] = row
    expected_cells = {
        (profile_id, outcome)
        for profile_id in CONTROLLED_PROFILE_IDS
        for outcome in OUTCOME_IDS
    }
    if set(indexed_trajectories) != expected_cells:
        raise ValueError("The 14 controlled profile/outcome cells are incomplete")

    grouped_samples: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in sample_rows:
        grouped_samples[(str(row.get("profile_id")), str(row.get("outcome")))].append(
            row
        )
    if set(grouped_samples) != expected_cells:
        raise ValueError("Sample records do not cover the 14 controlled cells")

    for profile_id in CONTROLLED_PROFILE_IDS:
        matrix_path = graph_dir / profile_id / "W.csv"
        edges_path = graph_dir / profile_id / "compiled_edges.csv"
        node_ids, matrix = load_matrix(matrix_path)
        edges, edge_by_id = load_edges(edges_path, profile_id, node_ids, matrix)
        potentials = outcome_potentials(node_ids, matrix)
        profile = profiles[profile_id]
        for outcome in OUTCOME_IDS:
            trajectory = indexed_trajectories[(profile_id, outcome)]
            if trajectory.get("book_id") != book_id:
                raise ValueError(f"Wrong book identifier for {profile_id}/{outcome}")
            for field in ("risk", "morality", "action"):
                if trajectory.get(field) != profile[field]:
                    raise ValueError(f"Wrong hidden profile metadata for {profile_id}")
            validate_cell(
                book_id,
                profile_id,
                outcome,
                trajectory,
                grouped_samples[(profile_id, outcome)],
                edges,
                edge_by_id,
                potentials[outcome],
            )
            print(
                f"OK: {profile_id}/{outcome} — "
                f"{trajectory['unique_sampled_paths']} unique paths"
            )

    validate_report(
        report_path,
        trajectories_path,
        samples_path,
        trajectories,
        sample_rows,
    )
    print(f"OK: all {len(trajectories)} {book_id} empirical medoids validated")


if __name__ == "__main__":
    main()
