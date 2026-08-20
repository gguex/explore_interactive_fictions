"""Phase 3.1: compile the profile-independent pregraph into transition matrices.

Profiles contain only the risk, morality and action axes. Kai availability, persistent
conditions, combat and escape use one fixed configuration shared by every profile.
Symbolic expressions are parsed explicitly; this script never evaluates arbitrary code.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

DEFAULT_BOOK_ID = "LW01"
DEFAULT_PROFILES_PATH = Path("data/for_graph_model/behavioral_profiles.json")

PROFILE_FIELDS = {"profile_id", "risk", "morality", "action"}
RISK_LEVELS = {"cautious", "neutral", "reckless"}
MORALITY_LEVELS = {"selfish", "neutral", "noble"}
ACTION_LEVELS = {"physical", "neutral", "tactical"}

PREGRAPH_NODE_FIELDS = [
    "node_id",
    "node_kind",
    "outcome",
    "absorbing",
    "source_ref",
]
PREGRAPH_EDGE_FIELDS = [
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
]
COMPILED_EDGE_FIELDS = [*PREGRAPH_EDGE_FIELDS, "profile_id", "compiled_weight"]

KAI_CALL = r'kai_available\("[^"]+"\)'
CONDITION_CALL = r'condition_available\("[^"]+", "[^"]+"\)'
PLAIN_CHOICE_CALL = re.compile(r"(?<![A-Za-z_])choice_share\(")


@dataclass(frozen=True)
class Profile:
    """The only supported player-profile schema."""

    profile_id: str
    risk: str
    morality: str
    action: str


@dataclass(frozen=True)
class Settings:
    """Experiment-wide mechanical assumptions shared by all profiles."""

    kai_availability: float
    combat_win_probability: float
    escape_probability: float
    has_condition: float
    choice_affinities: dict[str, float]
    special_combat_outcomes: dict[str, dict[str, float]]


def read_csv(path: Path, expected_fields: list[str]) -> list[dict[str, str]]:
    """Read a required CSV and enforce its exact header."""
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected_fields:
            raise ValueError(
                f"Unexpected header in {path}: {reader.fieldnames}; "
                f"expected {expected_fields}"
            )
        return [
            {field: (row.get(field) or "").strip() for field in expected_fields}
            for row in reader
        ]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    """Write a deterministic UTF-8 CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> Any:
    """Read one required JSON document."""
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def probability(value: Any, label: str) -> float:
    """Validate and return a finite probability."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number in [0, 1]")
    result = float(value)
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise ValueError(f"{label} must be a finite number in [0, 1]")
    return result


def positive_number(value: Any, label: str) -> float:
    """Validate and return a finite positive coefficient."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a positive number")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"{label} must be a finite positive number")
    return result


def load_profiles(path: Path) -> list[Profile]:
    """Load profiles and reject every alternate schema."""
    payload = read_json(path)
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"{path} must contain a non-empty JSON list")

    profiles = []
    seen_ids: set[str] = set()
    for index, item in enumerate(payload):
        label = f"{path} profile {index}"
        if not isinstance(item, dict) or set(item) != PROFILE_FIELDS:
            raise ValueError(f"{label} must contain exactly {sorted(PROFILE_FIELDS)}")
        profile = Profile(
            profile_id=str(item["profile_id"]),
            risk=str(item["risk"]),
            morality=str(item["morality"]),
            action=str(item["action"]),
        )
        if not re.fullmatch(r"[A-Za-z0-9_-]+", profile.profile_id):
            raise ValueError(f"{label}: invalid profile_id {profile.profile_id!r}")
        if profile.profile_id in seen_ids:
            raise ValueError(f"{label}: duplicate profile_id {profile.profile_id!r}")
        if profile.risk not in RISK_LEVELS:
            raise ValueError(f"{label}: invalid risk {profile.risk!r}")
        if profile.morality not in MORALITY_LEVELS:
            raise ValueError(f"{label}: invalid morality {profile.morality!r}")
        if profile.action not in ACTION_LEVELS:
            raise ValueError(f"{label}: invalid action {profile.action!r}")
        seen_ids.add(profile.profile_id)
        profiles.append(profile)
    return profiles


def load_settings(path: Path) -> Settings:
    """Load and validate the experiment-wide settings."""
    payload = read_json(path)
    required = {
        "kai_availability",
        "combat_win_probability",
        "escape_probability",
        "has_condition",
        "choice_affinities",
        "special_combat_outcomes",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError(f"{path} must contain exactly {sorted(required)}")

    raw_affinities = payload["choice_affinities"]
    affinity_keys = {"matching", "neutral", "opposed"}
    if not isinstance(raw_affinities, dict) or set(raw_affinities) != affinity_keys:
        raise ValueError(f"choice_affinities must contain exactly {affinity_keys}")
    affinities = {
        key: positive_number(raw_affinities[key], f"choice_affinities.{key}")
        for key in sorted(affinity_keys)
    }

    raw_special = payload["special_combat_outcomes"]
    if not isinstance(raw_special, dict):
        raise ValueError("special_combat_outcomes must be an object")
    special: dict[str, dict[str, float]] = {}
    for source_id, raw_distribution in raw_special.items():
        label = f"special_combat_outcomes.{source_id}"
        if not isinstance(raw_distribution, dict) or not raw_distribution:
            raise ValueError(f"{label} must be a non-empty object")
        distribution = {
            str(outcome): probability(value, f"{label}.{outcome}")
            for outcome, value in raw_distribution.items()
        }
        if not math.isclose(sum(distribution.values()), 1.0, abs_tol=1e-12):
            raise ValueError(f"{label} must sum to 1")
        special[str(source_id)] = distribution

    return Settings(
        kai_availability=probability(
            payload["kai_availability"], "kai_availability"
        ),
        combat_win_probability=probability(
            payload["combat_win_probability"], "combat_win_probability"
        ),
        escape_probability=probability(
            payload["escape_probability"], "escape_probability"
        ),
        has_condition=probability(payload["has_condition"], "has_condition"),
        choice_affinities=affinities,
        special_combat_outcomes=special,
    )


def axis_affinity(profile_value: str, edge_value: str, settings: Settings) -> float:
    """Return the fixed coefficient for one semantic axis."""
    if profile_value == "neutral" or edge_value == "neutral":
        return settings.choice_affinities["neutral"]
    if profile_value == edge_value:
        return settings.choice_affinities["matching"]
    return settings.choice_affinities["opposed"]


def edge_affinity(row: dict[str, str], profile: Profile, settings: Settings) -> float:
    """Combine the three independent axis affinities multiplicatively."""
    annotations = (
        (profile.risk, row["semantic_risk"], RISK_LEVELS),
        (profile.morality, row["semantic_morality"], MORALITY_LEVELS),
        (profile.action, row["semantic_action"], ACTION_LEVELS),
    )
    result = 1.0
    for profile_value, edge_value, valid_values in annotations:
        if edge_value not in valid_values:
            raise ValueError(
                f"Edge {row['edge_id']} has invalid semantic annotation "
                f"{edge_value!r}"
            )
        result *= axis_affinity(profile_value, edge_value, settings)
    return result


def availability(expression: str, settings: Settings) -> float:
    """Resolve an availability argument used by available_choice_share."""
    if expression == "1":
        return 1.0
    if re.fullmatch(KAI_CALL, expression):
        return settings.kai_availability
    if re.fullmatch(CONDITION_CALL, expression):
        return settings.has_condition
    raise ValueError(f"Unsupported availability expression: {expression!r}")


def require_call_matches_edge(
    row: dict[str, str], source_id: str, target_id: str, function_name: str
) -> None:
    """Ensure a symbolic share refers to the edge that carries it."""
    if source_id != row["source_id"] or target_id != row["target_id"]:
        raise ValueError(
            f"Edge {row['edge_id']}: {function_name} refers to "
            f"{source_id}->{target_id}"
        )


def normalized_share(
    row: dict[str, str],
    source_edges: list[dict[str, str]],
    profile: Profile,
    settings: Settings,
    candidate: Callable[[dict[str, str]], bool],
    availability_of: Callable[[dict[str, str]], float] | None = None,
) -> float:
    """Normalize one affinity over the relevant local choice group."""
    candidates = [edge for edge in source_edges if candidate(edge)]
    if row not in candidates:
        raise ValueError(f"Edge {row['edge_id']} is absent from its choice group")

    def weighted_affinity(edge: dict[str, str]) -> float:
        available = 1.0 if availability_of is None else availability_of(edge)
        return available * edge_affinity(edge, profile, settings)

    denominator = sum(weighted_affinity(edge) for edge in candidates)
    if denominator <= 0:
        raise ValueError(f"Edge {row['edge_id']}: empty available choice group")
    return weighted_affinity(row) / denominator


def available_argument(row: dict[str, str]) -> str:
    """Extract the third argument of available_choice_share."""
    match = re.fullmatch(
        r"available_choice_share\((\d+), (\d+), (.+)\)",
        row["weight_expression"],
    )
    if match is None:
        raise ValueError(f"Edge {row['edge_id']}: malformed available_choice_share")
    require_call_matches_edge(row, match[1], match[2], "available_choice_share")
    return match[3]


def choice_share(
    row: dict[str, str],
    source_edges: list[dict[str, str]],
    profile: Profile,
    settings: Settings,
) -> float:
    """Normalize an ordinary choice group."""
    return normalized_share(
        row,
        source_edges,
        profile,
        settings,
        lambda edge: bool(PLAIN_CHOICE_CALL.search(edge["weight_expression"])),
    )


def postcombat_choice_share(
    row: dict[str, str],
    source_edges: list[dict[str, str]],
    profile: Profile,
    settings: Settings,
) -> float:
    """Normalize choices available after a combat victory."""
    return normalized_share(
        row,
        source_edges,
        profile,
        settings,
        lambda edge: "postcombat_choice_share(" in edge["weight_expression"],
    )


def available_choice_share(
    row: dict[str, str],
    source_edges: list[dict[str, str]],
    profile: Profile,
    settings: Settings,
) -> float:
    """Normalize choices after multiplying each by its availability."""
    return normalized_share(
        row,
        source_edges,
        profile,
        settings,
        lambda edge: edge["weight_expression"].startswith(
            "available_choice_share("
        ),
        lambda edge: availability(available_argument(edge), settings),
    )


def combat_outcome(source_id: str, outcome: str, settings: Settings) -> float:
    """Resolve a standard or book-specific categorical combat outcome."""
    special = settings.special_combat_outcomes.get(source_id)
    if special is not None:
        if outcome not in special:
            raise ValueError(
                f"Missing special combat outcome {outcome!r} for source {source_id}"
            )
        return special[outcome]

    if outcome == "escape":
        return settings.escape_probability
    if outcome == "win":
        return (1 - settings.escape_probability) * settings.combat_win_probability
    if outcome == "death":
        return (1 - settings.escape_probability) * (
            1 - settings.combat_win_probability
        )
    raise ValueError(
        f"Combat source {source_id} uses non-standard outcome {outcome!r} "
        "without a fixed special distribution"
    )


def compile_formula(
    row: dict[str, str],
    source_edges: list[dict[str, str]],
    profile: Profile,
    settings: Settings,
) -> float:
    """Compile one of the explicitly supported symbolic expression forms."""
    expression = row["weight_expression"]

    if re.fullmatch(KAI_CALL, expression):
        return settings.kai_availability
    if re.fullmatch(rf"1 - {KAI_CALL}", expression):
        return 1 - settings.kai_availability
    if re.fullmatch(CONDITION_CALL, expression):
        return settings.has_condition
    if re.fullmatch(rf"1 - {CONDITION_CALL}", expression):
        return 1 - settings.has_condition

    match = re.fullmatch(
        rf"\(1 - {KAI_CALL}\) \* choice_share\((\d+), (\d+)\)", expression
    )
    if match is not None:
        require_call_matches_edge(row, match[1], match[2], "choice_share")
        return (1 - settings.kai_availability) * choice_share(
            row, source_edges, profile, settings
        )

    match = re.fullmatch(r"choice_share\((\d+), (\d+)\)", expression)
    if match is not None:
        require_call_matches_edge(row, match[1], match[2], "choice_share")
        return choice_share(row, source_edges, profile, settings)

    if expression.startswith("available_choice_share("):
        available_argument(row)
        return available_choice_share(row, source_edges, profile, settings)

    match = re.fullmatch(r"combat_win\((\d+)\)", expression)
    if match is not None:
        if match[1] != row["source_id"]:
            raise ValueError(f"Edge {row['edge_id']}: combat_win source mismatch")
        return settings.combat_win_probability

    match = re.fullmatch(r"1 - combat_win\((\d+)\)", expression)
    if match is not None:
        if match[1] != row["source_id"]:
            raise ValueError(f"Edge {row['edge_id']}: combat_win source mismatch")
        return 1 - settings.combat_win_probability

    match = re.fullmatch(r"combat_win\((\d+)\) \* ([0-9.]+)", expression)
    if match is not None:
        if match[1] != row["source_id"]:
            raise ValueError(f"Edge {row['edge_id']}: combat_win source mismatch")
        return settings.combat_win_probability * probability(
            float(match[2]), f"Edge {row['edge_id']} combat multiplier"
        )

    match = re.fullmatch(
        r"combat_win\((\d+)\) \* postcombat_choice_share\((\d+), (\d+)\)",
        expression,
    )
    if match is not None:
        if match[1] != row["source_id"]:
            raise ValueError(f"Edge {row['edge_id']}: combat_win source mismatch")
        require_call_matches_edge(
            row, match[2], match[3], "postcombat_choice_share"
        )
        return settings.combat_win_probability * postcombat_choice_share(
            row, source_edges, profile, settings
        )

    match = re.fullmatch(r'combat_outcome\((\d+), "([^"]+)"\)', expression)
    if match is not None:
        if match[1] != row["source_id"]:
            raise ValueError(f"Edge {row['edge_id']}: combat_outcome source mismatch")
        return combat_outcome(match[1], match[2], settings)

    raise ValueError(
        f"Edge {row['edge_id']}: unsupported weight expression {expression!r}"
    )


def compile_profile(
    nodes: list[dict[str, str]],
    edges: list[dict[str, str]],
    profile: Profile,
    settings: Settings,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Compile edge probabilities and the corresponding dense transition matrix."""
    by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
    for edge in edges:
        by_source[edge["source_id"]].append(edge)

    compiled_edges: list[dict[str, str]] = []
    for edge in edges:
        rule = edge["weight_rule"]
        if rule == "constant":
            weight = probability(float(edge["weight_value"]), edge["edge_id"])
        elif rule == "profile_choice":
            weight = normalized_share(
                edge,
                by_source[edge["source_id"]],
                profile,
                settings,
                lambda candidate: candidate["weight_rule"] == "profile_choice",
            )
        elif rule == "formula":
            weight = compile_formula(
                edge, by_source[edge["source_id"]], profile, settings
            )
        else:
            raise ValueError(f"Edge {edge['edge_id']}: unknown weight_rule {rule!r}")
        if not math.isfinite(weight) or not -1e-12 <= weight <= 1 + 1e-12:
            raise ValueError(
                f"Edge {edge['edge_id']}: invalid compiled weight {weight}"
            )
        compiled_edges.append(
            {
                **edge,
                "profile_id": profile.profile_id,
                "compiled_weight": format(max(0.0, min(1.0, weight)), ".15g"),
            }
        )

    for node in nodes:
        if node["absorbing"] == "true":
            continue
        total = sum(
            float(edge["compiled_weight"])
            for edge in compiled_edges
            if edge["source_id"] == node["node_id"]
        )
        if not math.isclose(total, 1.0, abs_tol=1e-12):
            raise ValueError(
                f"Profile {profile.profile_id}: outgoing weights for "
                f"{node['node_id']} sum to {total}"
            )

    node_ids = [node["node_id"] for node in nodes]
    node_set = set(node_ids)
    matrix: dict[str, dict[str, float]] = {
        source_id: defaultdict(float) for source_id in node_ids
    }
    for edge in compiled_edges:
        if edge["source_id"] not in node_set or edge["target_id"] not in node_set:
            raise ValueError(f"Edge {edge['edge_id']} refers to an unknown node")
        matrix[edge["source_id"]][edge["target_id"]] += float(
            edge["compiled_weight"]
        )
    for node in nodes:
        if node["absorbing"] == "true":
            matrix[node["node_id"]][node["node_id"]] = 1.0

    matrix_rows = []
    for source_id in node_ids:
        matrix_rows.append(
            {
                "node_id": source_id,
                **{
                    target_id: format(matrix[source_id][target_id], ".15g")
                    for target_id in node_ids
                },
            }
        )
    return compiled_edges, matrix_rows


def main() -> None:
    """Compile one or every configured behavioral profile."""
    parser = argparse.ArgumentParser(
        description="Compile the phase-2 pregraph into one W per player profile."
    )
    parser.add_argument(
        "--book", default=DEFAULT_BOOK_ID, help="Book identifier (default: LW01)."
    )
    parser.add_argument(
        "--profiles",
        type=Path,
        default=DEFAULT_PROFILES_PATH,
        help=f"Profile JSON (default: {DEFAULT_PROFILES_PATH}).",
    )
    parser.add_argument(
        "--settings",
        type=Path,
        help="Fixed settings JSON (default: <BOOK_ID>_compilation_settings.json).",
    )
    parser.add_argument(
        "--profile",
        action="append",
        dest="profile_ids",
        help="Compile only this profile_id; may be repeated.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        help="Output root (default: data/processed/graph/<BOOK_ID>).",
    )
    args = parser.parse_args()

    book_id = str(args.book)
    pregraph_dir = Path("data/processed/pregraph") / book_id
    settings_path = args.settings or (
        Path("data/for_graph_model") / f"{book_id}_compilation_settings.json"
    )
    output_root = args.output_root or (Path("data/processed/graph") / book_id)

    nodes = read_csv(pregraph_dir / "pregraph_nodes.csv", PREGRAPH_NODE_FIELDS)
    edges = read_csv(pregraph_dir / "pregraph_edges.csv", PREGRAPH_EDGE_FIELDS)
    profiles = load_profiles(Path(args.profiles))
    settings = load_settings(Path(settings_path))

    if args.profile_ids:
        requested = set(args.profile_ids)
        known = {profile.profile_id for profile in profiles}
        missing = requested - known
        if missing:
            raise ValueError(f"Unknown requested profiles: {sorted(missing)}")
        profiles = [profile for profile in profiles if profile.profile_id in requested]

    for profile in profiles:
        compiled_edges, matrix_rows = compile_profile(nodes, edges, profile, settings)
        profile_dir = output_root / profile.profile_id
        write_csv(
            profile_dir / "compiled_edges.csv",
            COMPILED_EDGE_FIELDS,
            compiled_edges,
        )
        write_csv(
            profile_dir / "W.csv",
            ["node_id", *(node["node_id"] for node in nodes)],
            matrix_rows,
        )
        print(
            f"Compiled {book_id}/{profile.profile_id}: "
            f"{len(nodes)} nodes, {len(compiled_edges)} edges"
        )


if __name__ == "__main__":
    main()
