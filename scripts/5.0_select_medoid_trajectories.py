"""Phase 5.0: select one empirical conditional medoid per profile and outcome.

For each profile/outcome cell, the script samples complete edge-labelled paths from
the outcome-conditioned Markov chain (Doob h-transform). It then selects an observed
path minimizing the frequency-weighted mean normalized-LCS distance between node
sequences. The finite sample and its unique-path counts are persisted for audit.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import json
import math
import random
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_BOOK_ID = "LW01"
DEFAULT_PROFILES_PATH = Path("data/for_graph_model/behavioral_profiles.json")
DEFAULT_SAMPLE_COUNT = 2000
DEFAULT_SEED = 42
START_NODE = "1"
OUTCOME_IDS = ("Win", "Death")
OUTCOME_SEED_OFFSET = {"Win": 0, "Death": 1}
MAX_TRANSITIONS = 5000
DISTANCE_TOLERANCE = 1e-12
CONTROLLED_PROFILE_IDS = (
    "neutral_neutral_neutral",
    "cautious_neutral_neutral",
    "reckless_neutral_neutral",
    "neutral_selfish_neutral",
    "neutral_noble_neutral",
    "neutral_neutral_physical",
    "neutral_neutral_tactical",
)
PROFILE_FIELDS = ["profile_id", "risk", "morality", "action"]
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
TRAJECTORY_FIELDS = [
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
]


@dataclass(frozen=True)
class Edge:
    """One positive-probability compiled multiedge."""

    edge_id: str
    source_id: str
    target_id: str
    transition_kind: str
    weight: float


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read one required CSV file."""
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header in {path}")
        fields = list(reader.fieldnames)
        return fields, [
            {field: (row.get(field) or "").strip() for field in fields}
            for row in reader
        ]


def read_profiles(path: Path) -> list[dict[str, str]]:
    """Load the seven controlled profiles in their fixed protocol order."""
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"{path} must contain a non-empty JSON list")
    indexed: dict[str, dict[str, str]] = {}
    for position, raw_profile in enumerate(payload):
        if not isinstance(raw_profile, dict) or set(raw_profile) != set(PROFILE_FIELDS):
            raise ValueError(
                f"Profile {position} in {path} must contain exactly {PROFILE_FIELDS}"
            )
        profile = {field: str(raw_profile[field]) for field in PROFILE_FIELDS}
        profile_id = profile["profile_id"]
        if profile_id in indexed:
            raise ValueError(f"Duplicate profile identifier: {profile_id}")
        indexed[profile_id] = profile
    missing = set(CONTROLLED_PROFILE_IDS) - set(indexed)
    if missing:
        raise ValueError(f"Missing controlled profiles: {sorted(missing)}")
    return [indexed[profile_id] for profile_id in CONTROLLED_PROFILE_IDS]


def load_matrix(path: Path) -> tuple[list[str], np.ndarray[Any, Any]]:
    """Load and validate one phase-3 stochastic matrix."""
    fields, rows = read_csv(path)
    if not fields or fields[0] != "node_id":
        raise ValueError(f"Unexpected matrix header in {path}")
    node_ids = fields[1:]
    if [row["node_id"] for row in rows] != node_ids:
        raise ValueError(f"Matrix row and column order differs in {path}")
    if START_NODE not in node_ids or not set(OUTCOME_IDS).issubset(node_ids):
        raise ValueError(f"Missing start or absorbing node in {path}")
    matrix = np.array(
        [[float(row[target_id]) for target_id in node_ids] for row in rows],
        dtype=float,
    )
    if not np.isfinite(matrix).all() or not np.allclose(
        matrix.sum(axis=1), 1.0, rtol=1e-10, atol=1e-10
    ):
        raise ValueError(f"Invalid stochastic matrix in {path}")
    return node_ids, matrix


def load_edges(
    path: Path,
    profile_id: str,
    node_ids: list[str],
    matrix: np.ndarray[Any, Any],
) -> tuple[list[Edge], dict[str, Edge]]:
    """Load positive multiedges and check that they reconstruct the dense matrix."""
    fields, rows = read_csv(path)
    if fields != COMPILED_EDGE_FIELDS:
        raise ValueError(
            f"Unexpected header in {path}: {fields}; expected {COMPILED_EDGE_FIELDS}"
        )
    index = {node_id: position for position, node_id in enumerate(node_ids)}
    reconstructed = np.zeros_like(matrix)
    for outcome in OUTCOME_IDS:
        reconstructed[index[outcome], index[outcome]] = 1.0
    edges: list[Edge] = []
    seen: set[str] = set()
    for row in rows:
        edge_id = row["edge_id"]
        if edge_id in seen:
            raise ValueError(f"Duplicate edge identifier {edge_id} in {path}")
        seen.add(edge_id)
        if row["profile_id"] != profile_id:
            raise ValueError(f"Edge {edge_id} belongs to the wrong profile")
        source_id = row["source_id"]
        target_id = row["target_id"]
        if source_id not in index or target_id not in index:
            raise ValueError(f"Edge {edge_id} references an unknown node")
        weight = float(row["compiled_weight"])
        if not math.isfinite(weight) or not 0 <= weight <= 1:
            raise ValueError(f"Invalid compiled weight on {edge_id}: {weight}")
        reconstructed[index[source_id], index[target_id]] += weight
        if weight > 0:
            edges.append(
                Edge(
                    edge_id=edge_id,
                    source_id=source_id,
                    target_id=target_id,
                    transition_kind=row["transition_kind"],
                    weight=weight,
                )
            )
    if not np.allclose(reconstructed, matrix, rtol=1e-10, atol=1e-10):
        matrix_path = path.parent / "W.csv"
        raise ValueError(f"Compiled multiedges do not reconstruct {matrix_path}")
    edges.sort(key=lambda edge: edge.edge_id)
    return edges, {edge.edge_id: edge for edge in edges}


def load_phase4_outcomes(
    path: Path, profiles: list[dict[str, str]]
) -> dict[tuple[str, str], float]:
    """Load the phase-4 outcome probabilities used as a cross-check."""
    fields, rows = read_csv(path)
    required = {"profile_id", "death_probability", "win_probability"}
    if not required.issubset(fields):
        raise ValueError(f"Missing outcome-probability fields in {path}")
    indexed = {row["profile_id"]: row for row in rows}
    result: dict[tuple[str, str], float] = {}
    for profile in profiles:
        profile_id = profile["profile_id"]
        if profile_id not in indexed:
            raise ValueError(f"Missing phase-4 metrics for {profile_id}")
        result[(profile_id, "Win")] = float(indexed[profile_id]["win_probability"])
        result[(profile_id, "Death")] = float(
            indexed[profile_id]["death_probability"]
        )
    return result


def outcome_potentials(
    node_ids: list[str], matrix: np.ndarray[Any, Any]
) -> dict[str, dict[str, float]]:
    """Compute every node's probability of absorption in each outcome."""
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
    edges: list[Edge], potentials: dict[str, float]
) -> dict[str, list[tuple[Edge, float]]]:
    """Construct the edge-level Doob chain for one fixed outcome."""
    outgoing: dict[str, list[Edge]] = defaultdict(list)
    for edge in edges:
        outgoing[edge.source_id].append(edge)
    conditioned: dict[str, list[tuple[Edge, float]]] = {}
    for source_id, candidates in outgoing.items():
        source_potential = potentials[source_id]
        if source_potential <= 0:
            continue
        weighted = [
            (edge, edge.weight * potentials[edge.target_id] / source_potential)
            for edge in candidates
            if potentials[edge.target_id] > 0
        ]
        total = math.fsum(probability for _, probability in weighted)
        if not math.isclose(total, 1.0, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError(
                f"Conditioned outgoing mass at {source_id} is {total:.12g}"
            )
        conditioned[source_id] = [
            (edge, probability / total) for edge, probability in weighted
        ]
    return conditioned


def draw_edge(
    candidates: list[tuple[Edge, float]], generator: random.Random
) -> Edge:
    """Draw one edge from a normalized categorical distribution."""
    draw = generator.random()
    cumulative = 0.0
    for edge, probability in candidates:
        cumulative += probability
        if draw < cumulative:
            return edge
    return candidates[-1][0]


def sample_path(
    outcome: str,
    conditioned: dict[str, list[tuple[Edge, float]]],
    generator: random.Random,
) -> tuple[str, ...]:
    """Sample one complete edge-labelled path ending at the fixed outcome."""
    current = START_NODE
    edge_ids: list[str] = []
    for _ in range(MAX_TRANSITIONS):
        if current in OUTCOME_IDS:
            if current != outcome:
                raise ValueError(f"Conditioned chain reached unexpected {current}")
            return tuple(edge_ids)
        candidates = conditioned.get(current)
        if not candidates:
            raise ValueError(f"Conditioned chain has no outgoing edge at {current}")
        edge = draw_edge(candidates, generator)
        edge_ids.append(edge.edge_id)
        current = edge.target_id
    raise ValueError(f"Conditioned sample exceeded {MAX_TRANSITIONS} transitions")


def reconstruct_nodes(
    path: tuple[str, ...], edge_by_id: dict[str, Edge]
) -> list[str]:
    """Reconstruct and validate one path's ordered node sequence."""
    nodes = [START_NODE]
    current = START_NODE
    for edge_id in path:
        edge = edge_by_id[edge_id]
        if edge.source_id != current:
            raise ValueError(f"Discontinuous path at edge {edge_id}")
        current = edge.target_id
        nodes.append(current)
    return nodes


def sequence_masks(sequence: list[str]) -> dict[str, int]:
    """Encode positions by node identifier for bit-parallel LCS."""
    masks: dict[str, int] = {}
    for position, item in enumerate(sequence):
        masks[item] = masks.get(item, 0) | (1 << position)
    return masks


def bitset_lcs_length(first: list[str], second_masks: dict[str, int]) -> int:
    """Calculate the LCS length with bit-parallel dynamic programming."""
    state = 0
    for item in first:
        matches = second_masks.get(item, 0)
        union = state | matches
        shifted = (state << 1) | 1
        state = union & ~(union - shifted)
    return state.bit_count()


def normalized_lcs_distance(
    first: list[str], second: list[str], second_masks: dict[str, int]
) -> float:
    """Return one minus the symmetric normalized node-sequence LCS score."""
    denominator = len(first) + len(second)
    if denominator == 0:
        return 0.0
    return 1.0 - 2 * bitset_lcs_length(first, second_masks) / denominator


def empirical_medoid(
    counts: Counter[tuple[str, ...]], edge_by_id: dict[str, Edge]
) -> tuple[tuple[str, ...], float, int]:
    """Select the sampled path minimizing weighted mean normalized-LCS distance."""
    paths = sorted(counts)
    node_paths = [reconstruct_nodes(path, edge_by_id) for path in paths]
    masks = [sequence_masks(node_path) for node_path in node_paths]
    totals = [0.0] * len(paths)
    sample_count = sum(counts.values())
    for first_index, first_nodes in enumerate(node_paths):
        for second_index in range(first_index + 1, len(paths)):
            distance = normalized_lcs_distance(
                first_nodes, node_paths[second_index], masks[second_index]
            )
            totals[first_index] += counts[paths[second_index]] * distance
            totals[second_index] += counts[paths[first_index]] * distance
    means = [total / sample_count for total in totals]
    minimum = min(means)
    tied = [
        index
        for index, mean in enumerate(means)
        if math.isclose(
            mean,
            minimum,
            rel_tol=DISTANCE_TOLERANCE,
            abs_tol=DISTANCE_TOLERANCE,
        )
    ]
    selected_index = min(tied, key=lambda index: paths[index])
    return paths[selected_index], means[selected_index], len(tied)


def mean_distance_to_sample(
    path: tuple[str, ...],
    counts: Counter[tuple[str, ...]],
    edge_by_id: dict[str, Edge],
) -> float:
    """Measure one path's weighted mean normalized-LCS distance to the sample."""
    nodes = reconstruct_nodes(path, edge_by_id)
    total = 0.0
    for candidate, frequency in counts.items():
        candidate_nodes = reconstruct_nodes(candidate, edge_by_id)
        total += frequency * normalized_lcs_distance(
            nodes, candidate_nodes, sequence_masks(candidate_nodes)
        )
    return total / sum(counts.values())


def require_no_reachable_unit_cycle(edges: list[Edge]) -> None:
    """Reject reachable all-unit cycles, which make the MAP diagnostic ambiguous."""
    outgoing: dict[str, list[Edge]] = defaultdict(list)
    for edge in edges:
        outgoing[edge.source_id].append(edge)
    reached = {START_NODE}
    queue = deque([START_NODE])
    while queue:
        source_id = queue.popleft()
        for edge in outgoing.get(source_id, []):
            if edge.target_id not in reached:
                reached.add(edge.target_id)
                queue.append(edge.target_id)
    unit_outgoing: dict[str, list[str]] = defaultdict(list)
    indegree = {node_id: 0 for node_id in reached}
    for edge in edges:
        if (
            edge.source_id in reached
            and edge.target_id in reached
            and math.isclose(edge.weight, 1.0, abs_tol=DISTANCE_TOLERANCE)
        ):
            unit_outgoing[edge.source_id].append(edge.target_id)
            indegree[edge.target_id] += 1
    roots = [node_id for node_id, degree in indegree.items() if degree == 0]
    heapq.heapify(roots)
    visited = 0
    while roots:
        source_id = heapq.heappop(roots)
        visited += 1
        for target_id in unit_outgoing.get(source_id, []):
            indegree[target_id] -= 1
            if indegree[target_id] == 0:
                heapq.heappush(roots, target_id)
    if visited != len(reached):
        raise ValueError("Reachable unit-probability cycle makes MAP ambiguous")


def map_path(outcome: str, edges: list[Edge]) -> tuple[str, ...]:
    """Compute a canonical maximum-probability path for diagnostics only."""
    require_no_reachable_unit_cycle(edges)
    outgoing: dict[str, list[Edge]] = defaultdict(list)
    for edge in edges:
        outgoing[edge.source_id].append(edge)
    best: dict[str, tuple[float, tuple[str, ...]]] = {START_NODE: (0.0, ())}
    queue: list[tuple[float, tuple[str, ...], str]] = [(0.0, (), START_NODE)]
    while queue:
        cost, path, source_id = heapq.heappop(queue)
        if best.get(source_id) != (cost, path):
            continue
        for edge in outgoing.get(source_id, []):
            candidate = (cost - math.log(edge.weight), (*path, edge.edge_id))
            current = best.get(edge.target_id)
            if current is None or candidate < current:
                best[edge.target_id] = candidate
                heapq.heappush(queue, (*candidate, edge.target_id))
    if outcome not in best:
        raise ValueError(f"Outcome {outcome} is unreachable from {START_NODE}")
    return best[outcome][1]


def path_probability(path: tuple[str, ...], edge_by_id: dict[str, Edge]) -> float:
    """Return the unconditional probability of one edge-labelled path."""
    return math.prod(edge_by_id[edge_id].weight for edge_id in path)


def rounded(value: float) -> float:
    """Round a finite metric to a stable JSON number."""
    if not math.isfinite(value):
        raise ValueError(f"Cannot serialize non-finite value: {value}")
    if abs(value) < 5e-16:
        value = 0.0
    return float(format(value, ".15g"))


def trajectory_digest(
    book_id: str, profile_id: str, outcome: str, edge_ids: list[str]
) -> str:
    """Hash the identity and exact edge-labelled path."""
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


def file_sha256(path: Path) -> str:
    """Return the SHA-256 digest of one file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_path(path: Path) -> str:
    """Render a repository-relative path when possible."""
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write deterministic UTF-8 JSON Lines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for row in rows
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def select_cell(
    book_id: str,
    profile: dict[str, str],
    outcome: str,
    sample_count: int,
    sampling_seed: int,
    edges: list[Edge],
    edge_by_id: dict[str, Edge],
    potentials: dict[str, float],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    """Sample, select and serialize one profile/outcome cell."""
    conditioned = conditioned_adjacency(edges, potentials)
    generator = random.Random(sampling_seed)
    counts: Counter[tuple[str, ...]] = Counter(
        sample_path(outcome, conditioned, generator) for _ in range(sample_count)
    )
    selected_path, mean_distance, medoid_tie_count = empirical_medoid(
        counts, edge_by_id
    )
    selected_nodes = reconstruct_nodes(selected_path, edge_by_id)
    if selected_nodes[-1] != outcome:
        raise ValueError(f"Selected medoid does not end at {outcome}")
    outcome_probability = potentials[START_NODE]
    selected_probability = path_probability(selected_path, edge_by_id)
    profile_id = profile["profile_id"]
    path_edges = [edge_by_id[edge_id] for edge_id in selected_path]
    edge_ids = list(selected_path)
    trajectory = {
        "trajectory_id": f"{book_id}__{profile_id}__{outcome.lower()}__medoid",
        "book_id": book_id,
        "profile_id": profile_id,
        "risk": profile["risk"],
        "morality": profile["morality"],
        "action": profile["action"],
        "outcome": outcome,
        "selection_method": "conditional_empirical_medoid",
        "distance_metric": "one_minus_symmetric_normalized_node_lcs",
        "sample_count": sample_count,
        "sampling_seed": sampling_seed,
        "unique_sampled_paths": len(counts),
        "start_node": START_NODE,
        "terminal_node": outcome,
        "node_ids": selected_nodes,
        "edge_ids": edge_ids,
        "edge_weights": [rounded(edge.weight) for edge in path_edges],
        "transition_kinds": [edge.transition_kind for edge in path_edges],
        "transition_count": len(selected_path),
        "mean_sample_distance": rounded(mean_distance),
        "medoid_sample_frequency": counts[selected_path],
        "medoid_sample_share": rounded(counts[selected_path] / sample_count),
        "medoid_tie_count": medoid_tie_count,
        "tie_break_applied": medoid_tie_count > 1,
        "path_probability": rounded(selected_probability),
        "outcome_probability": rounded(outcome_probability),
        "conditional_path_probability": rounded(
            selected_probability / outcome_probability
        ),
        "trajectory_sha256": trajectory_digest(
            book_id, profile_id, outcome, edge_ids
        ),
    }
    sample_rows: list[dict[str, Any]] = []
    for path in sorted(counts):
        nodes = reconstruct_nodes(path, edge_by_id)
        probability = path_probability(path, edge_by_id)
        sample_rows.append(
            {
                "book_id": book_id,
                "profile_id": profile_id,
                "outcome": outcome,
                "sampling_seed": sampling_seed,
                "edge_ids": list(path),
                "node_ids": nodes,
                "transition_count": len(path),
                "count": counts[path],
                "sample_share": rounded(counts[path] / sample_count),
                "path_probability": rounded(probability),
                "conditional_path_probability": rounded(
                    probability / outcome_probability
                ),
                "trajectory_sha256": trajectory_digest(
                    book_id, profile_id, outcome, list(path)
                ),
            }
        )
    diagnostic_path = map_path(outcome, edges)
    diagnostic_probability = path_probability(diagnostic_path, edge_by_id)
    diagnostic_nodes = reconstruct_nodes(diagnostic_path, edge_by_id)
    diagnostic = {
        "profile_id": profile_id,
        "outcome": outcome,
        "map_transition_count": len(diagnostic_path),
        "map_edge_ids": list(diagnostic_path),
        "map_node_ids": diagnostic_nodes,
        "map_conditional_path_probability": rounded(
            diagnostic_probability / outcome_probability
        ),
        "map_mean_sample_distance": rounded(
            mean_distance_to_sample(diagnostic_path, counts, edge_by_id)
        ),
        "medoid_transition_count": len(selected_path),
        "medoid_mean_sample_distance": rounded(mean_distance),
        "map_equals_medoid": diagnostic_path == selected_path,
    }
    return trajectory, sample_rows, diagnostic


def build_report(
    book_id: str,
    profiles: list[dict[str, str]],
    sample_count: int,
    base_seed: int,
    trajectories: list[dict[str, Any]],
    diagnostics: list[dict[str, Any]],
    input_paths: list[Path],
    trajectories_path: Path,
    samples_path: Path,
) -> dict[str, Any]:
    """Build the auditable selection report."""
    return {
        "schema_version": "2.0",
        "book_id": book_id,
        "phase": "5.0",
        "method": "outcome-conditioned empirical trajectory medoid",
        "conditioning": {
            "method": "edge-level Doob h-transform",
            "formula": "P_o(i->j,e) = w(e) h_o(j) / h_o(i)",
            "potential": "h_o(i) = probability of eventual absorption in outcome o",
        },
        "sampling": {
            "sample_count_per_cell": sample_count,
            "base_seed": base_seed,
            "generator": "Python random.Random (MT19937)",
            "seed_formula": "base_seed + 2 * profile_index + outcome_offset",
            "outcome_offsets": OUTCOME_SEED_OFFSET,
            "max_transitions": MAX_TRANSITIONS,
        },
        "medoid": {
            "candidate_set": "unique observed edge-labelled paths",
            "representation": "ordered node sequence including start and outcome",
            "distance": "1 - 2*LCS(A,B)/(len(A)+len(B))",
            "objective": "frequency-weighted mean distance to all sampled paths",
            "tie_break": "lexicographically smallest complete edge_id sequence",
            "distance_tolerance": DISTANCE_TOLERANCE,
        },
        "start_node": START_NODE,
        "outcomes": list(OUTCOME_IDS),
        "controlled_profile_ids": [profile["profile_id"] for profile in profiles],
        "trajectory_count": len(trajectories),
        "sample_record_count": sum(
            int(row["unique_sampled_paths"]) for row in trajectories
        ),
        "tied_cell_count": sum(bool(row["tie_break_applied"]) for row in trajectories),
        "output_schema": TRAJECTORY_FIELDS,
        "inputs": {
            relative_path(path): file_sha256(path) for path in sorted(input_paths)
        },
        "outputs": {
            relative_path(trajectories_path): {
                "rows": len(trajectories),
                "sha256": file_sha256(trajectories_path),
            },
            relative_path(samples_path): {
                "rows": sum(
                    int(row["unique_sampled_paths"]) for row in trajectories
                ),
                "sha256": file_sha256(samples_path),
            },
        },
        "results": [
            {
                key: row[key]
                for key in (
                    "trajectory_id",
                    "profile_id",
                    "outcome",
                    "transition_count",
                    "sample_count",
                    "sampling_seed",
                    "unique_sampled_paths",
                    "mean_sample_distance",
                    "medoid_sample_frequency",
                    "conditional_path_probability",
                    "trajectory_sha256",
                )
            }
            for row in trajectories
        ],
        "map_diagnostic_only": diagnostics,
        "interpretation_limit": (
            "The selected path is the empirical medoid of a finite conditioned sample. "
            "It is a central observed trajectory under the declared LCS distance, not "
            "the most probable path, a population median, or a summary of all "
            "variation."
        ),
    }


def main() -> None:
    """Select and write the 14 conditional empirical medoids."""
    parser = argparse.ArgumentParser(
        description="Select controlled conditional trajectory medoids for phase 5."
    )
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES_PATH)
    parser.add_argument("--graph-dir", type=Path)
    parser.add_argument("--bop-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLE_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    if args.samples <= 0:
        raise ValueError("--samples must be positive")

    book_id = str(args.book)
    graph_dir = args.graph_dir or Path("data/processed/graph") / book_id
    bop_dir = args.bop_dir or Path("data/processed/bop") / book_id
    output_dir = args.output_dir or Path("data/processed/phase5") / book_id
    metrics_path = bop_dir / "profile_metrics.csv"
    profiles = read_profiles(args.profiles)
    phase4_outcomes = load_phase4_outcomes(metrics_path, profiles)

    trajectories: list[dict[str, Any]] = []
    sample_rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    input_paths = [args.profiles, metrics_path]
    for profile_index, profile in enumerate(profiles):
        profile_id = profile["profile_id"]
        profile_dir = graph_dir / profile_id
        matrix_path = profile_dir / "W.csv"
        edges_path = profile_dir / "compiled_edges.csv"
        node_ids, matrix = load_matrix(matrix_path)
        edges, edge_by_id = load_edges(edges_path, profile_id, node_ids, matrix)
        potentials = outcome_potentials(node_ids, matrix)
        input_paths.extend((matrix_path, edges_path))
        for outcome in OUTCOME_IDS:
            outcome_probability = potentials[outcome][START_NODE]
            expected_probability = phase4_outcomes[(profile_id, outcome)]
            if not math.isclose(
                outcome_probability,
                expected_probability,
                rel_tol=1e-10,
                abs_tol=1e-10,
            ):
                raise ValueError(
                    f"Phase-4 outcome mismatch for {profile_id}/{outcome}"
                )
            sampling_seed = (
                args.seed + 2 * profile_index + OUTCOME_SEED_OFFSET[outcome]
            )
            trajectory, cell_samples, diagnostic = select_cell(
                book_id,
                profile,
                outcome,
                args.samples,
                sampling_seed,
                edges,
                edge_by_id,
                potentials[outcome],
            )
            trajectories.append(trajectory)
            sample_rows.extend(cell_samples)
            diagnostics.append(diagnostic)
            print(
                f"{profile_id}/{outcome}: medoid={trajectory['transition_count']} "
                f"transitions; unique={trajectory['unique_sampled_paths']}; "
                f"mean_distance={trajectory['mean_sample_distance']:.4f}"
            )

    expected_count = len(CONTROLLED_PROFILE_IDS) * len(OUTCOME_IDS)
    if len(trajectories) != expected_count:
        raise ValueError(
            f"Produced {len(trajectories)} trajectories; expected {expected_count}"
        )
    trajectories_path = output_dir / "medoid_trajectories.jsonl"
    samples_path = output_dir / "conditional_path_counts.jsonl"
    report_path = output_dir / "medoid_selection_report.json"
    write_jsonl(trajectories_path, trajectories)
    write_jsonl(samples_path, sample_rows)
    report = build_report(
        book_id,
        profiles,
        args.samples,
        args.seed,
        trajectories,
        diagnostics,
        input_paths,
        trajectories_path,
        samples_path,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Conditional empirical medoids: {len(trajectories)}")
    print(f"Unique sampled-path records: {len(sample_rows)}")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()
