"""Calibrate one book-wide Lone Wolf combat survival probability.

The phase-3 compiler deliberately uses one combat probability for every profile and
paragraph.  This script estimates that scalar from the official Combat Results Table
while retaining combat damage between encounters.  It is a calibration utility, not a
replacement for the generic graph compiler: book-specific modifiers live in a JSON
input, never in ``3.1_compile_w.py``.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_BOOK_ID = "LW01"
KILL_DAMAGE = 10_000

# Rows follow random numbers 1, 2, ..., 9, 0. Columns follow combat-ratio bands
# <=-11, -10/-9, ..., -2/-1, 0, +1/+2, ..., +9/+10, >=+11.
# Each cell is (enemy Endurance loss, Lone Wolf Endurance loss).
COMBAT_RESULTS: tuple[tuple[tuple[int, int], ...], ...] = (
    (
        (0, KILL_DAMAGE), (0, KILL_DAMAGE), (0, 8), (0, 6), (1, 6),
        (2, 5), (3, 5), (4, 5), (5, 4), (6, 4), (7, 4), (8, 3), (9, 3),
    ),
    (
        (0, KILL_DAMAGE), (0, 8), (0, 7), (1, 6), (2, 5), (3, 5),
        (4, 4), (5, 4), (6, 3), (7, 3), (8, 3), (9, 3), (10, 2),
    ),
    (
        (0, 8), (0, 7), (1, 6), (2, 5), (3, 5), (4, 4), (5, 4),
        (6, 3), (7, 3), (8, 3), (9, 2), (10, 2), (11, 2),
    ),
    (
        (0, 8), (1, 7), (2, 6), (3, 5), (4, 4), (5, 4), (6, 3),
        (7, 3), (8, 2), (9, 2), (10, 2), (11, 2), (12, 2),
    ),
    (
        (1, 7), (2, 6), (3, 6), (4, 5), (5, 4), (6, 4), (7, 3),
        (8, 2), (9, 2), (10, 2), (11, 2), (12, 2), (14, 1),
    ),
    (
        (2, 6), (3, 6), (4, 5), (5, 4), (6, 3), (7, 2), (8, 2),
        (9, 2), (10, 2), (11, 1), (12, 1), (14, 1), (16, 1),
    ),
    (
        (3, 5), (4, 5), (5, 4), (6, 3), (7, 2), (8, 2), (9, 1),
        (10, 1), (11, 1), (12, 0), (14, 0), (16, 0), (18, 0),
    ),
    (
        (4, 4), (5, 4), (6, 3), (7, 2), (8, 1), (9, 1), (10, 0),
        (11, 0), (12, 0), (14, 0), (16, 0), (18, 0), (KILL_DAMAGE, 0),
    ),
    (
        (5, 3), (6, 3), (7, 2), (8, 0), (9, 0), (10, 0), (11, 0),
        (12, 0), (14, 0), (16, 0), (18, 0), (KILL_DAMAGE, 0),
        (KILL_DAMAGE, 0),
    ),
    (
        (6, 0), (7, 0), (8, 0), (9, 0), (10, 0), (11, 0), (12, 0),
        (14, 0), (16, 0), (18, 0), (KILL_DAMAGE, 0), (KILL_DAMAGE, 0),
        (KILL_DAMAGE, 0),
    ),
)


@dataclass
class Character:
    """Combat-relevant state for one simulated novice Kai Lord."""

    combat_skill: int
    endurance: int
    maximum_endurance: int
    disciplines: frozenset[str]
    weapons: frozenset[str]
    weaponskill: str | None
    has_healing_potion: bool


def read_json(path: Path) -> Any:
    """Load a required JSON document."""
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    """Load a required CSV document."""
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def ratio_column(ratio: int) -> int:
    """Map an exact Combat Ratio to one of the official table's 13 bands."""
    if ratio <= -11:
        return 0
    if ratio <= -9:
        return 1
    if ratio <= -7:
        return 2
    if ratio <= -5:
        return 3
    if ratio <= -3:
        return 4
    if ratio <= -1:
        return 5
    if ratio == 0:
        return 6
    if ratio <= 2:
        return 7
    if ratio <= 4:
        return 8
    if ratio <= 6:
        return 9
    if ratio <= 8:
        return 10
    if ratio <= 10:
        return 11
    return 12


def combat_result(ratio: int, random_number: int) -> tuple[int, int]:
    """Return enemy and Lone Wolf losses for one combat round."""
    if not 0 <= random_number <= 9:
        raise ValueError(f"Random number outside 0..9: {random_number}")
    row = 9 if random_number == 0 else random_number - 1
    return COMBAT_RESULTS[row][ratio_column(ratio)]


def weighted_choice(
    rng: random.Random, rows: list[dict[str, Any]], weight_key: str
) -> dict[str, Any]:
    """Select one row from non-negative weights, normalizing their sum."""
    total = sum(float(row[weight_key]) for row in rows)
    if total <= 0:
        raise ValueError("Cannot sample from an empty probability mass")
    threshold = rng.random() * total
    cumulative = 0.0
    for row in rows:
        cumulative += float(row[weight_key])
        if threshold < cumulative:
            return row
    return rows[-1]


def create_character(rng: random.Random, config: dict[str, Any]) -> Character:
    """Apply the LW01 creation rolls described by the calibration input."""
    creation = config["character_creation"]
    values = [int(value) for value in creation["random_values"]]
    combat_skill = int(creation["combat_skill_base"]) + rng.choice(values)
    endurance = int(creation["endurance_base"]) + rng.choice(values)

    disciplines = frozenset(
        rng.sample(
            [str(value) for value in creation["disciplines"]],
            k=int(creation["disciplines_chosen"]),
        )
    )
    equipment_roll = str(rng.choice(values))
    equipment = creation["equipment_table"][equipment_roll]
    endurance += int(equipment.get("endurance_bonus", 0))

    weapons = set(str(value) for value in creation["starting_weapons"])
    weapons.update(str(value) for value in equipment.get("weapons", []))
    weaponskill = None
    if "Weaponskill" in disciplines:
        weaponskill_roll = str(rng.choice(values))
        weaponskill = str(creation["weaponskill_table"][weaponskill_roll])

    return Character(
        combat_skill=combat_skill,
        endurance=endurance,
        maximum_endurance=endurance,
        disciplines=disciplines,
        weapons=frozenset(weapons),
        weaponskill=weaponskill,
        has_healing_potion=bool(equipment.get("healing_potion", False)),
    )


def paragraph_modifier(
    character: Character,
    override: dict[str, Any],
    round_number: int,
    has_condition: bool,
) -> int:
    """Resolve declarative paragraph-specific Combat Skill modifiers."""
    modifier = int(override.get("combat_skill_modifier", 0))
    if round_number == 1:
        modifier += int(override.get("first_round_modifier", 0))
    else:
        modifier += int(override.get("later_round_modifier", 0))

    conditional = override.get("unless_discipline")
    if (
        conditional
        and round_number >= int(conditional.get("from_round", 1))
        and str(conditional["name"]) not in character.disciplines
    ):
        modifier += int(conditional["modifier"])
    if not has_condition:
        modifier += int(override.get("absent_condition_modifier", 0))
    return modifier


def effective_combat_skill(
    character: Character,
    override: dict[str, Any],
    rules: dict[str, Any],
    round_number: int,
    has_condition: bool,
) -> int:
    """Compute Lone Wolf's Combat Skill for one round."""
    result = character.combat_skill
    immune = bool(override.get("mindblast_immune", False))
    if "Mindblast" in character.disciplines and not immune:
        result += int(rules["mindblast_bonus"])

    unarmed = bool(override.get("unarmed", False))
    available_weapons = set(character.weapons)
    available_weapons.update(str(value) for value in override.get("weapons", []))
    if (
        not unarmed
        and character.weaponskill is not None
        and character.weaponskill in available_weapons
    ):
        result += int(rules["weaponskill_bonus"])

    return result + paragraph_modifier(
        character, override, round_number, has_condition
    )


def fight(
    rng: random.Random,
    character: Character,
    enemies: list[dict[str, Any]],
    override: dict[str, Any],
    rules: dict[str, Any],
    has_condition_probability: float,
    starting_endurance: int | None = None,
) -> tuple[bool, int]:
    """Fight all enemies in sequence; return survival and remaining Endurance."""
    endurance = (
        character.endurance if starting_endurance is None else starting_endurance
    )
    has_condition = rng.random() < has_condition_probability
    round_number = 0
    for enemy in enemies:
        enemy_endurance = int(enemy["ep"])
        while endurance > 0 and enemy_endurance > 0:
            round_number += 1
            skill = effective_combat_skill(
                character, override, rules, round_number, has_condition
            )
            ratio = skill - int(enemy["cs"])
            enemy_loss, lone_wolf_loss = combat_result(ratio, rng.randrange(10))
            enemy_endurance -= enemy_loss
            endurance -= lone_wolf_loss
        if endurance <= 0:
            return False, 0
    return True, endurance


def is_escape_edge(edge: dict[str, Any]) -> bool:
    """Identify the generic escape role in a compiled phase-3 edge."""
    return (
        edge.get("condition_kind") == "combat_outcome"
        and edge.get("condition_value") == "escape"
    )


def summarize_rate(losses: int, attempts: int) -> dict[str, float | int]:
    """Return a binomial estimate and its normal 95% interval."""
    if attempts == 0:
        return {"attempts": 0, "losses": 0, "loss_probability": 0.0}
    rate = losses / attempts
    half_width = 1.96 * math.sqrt(rate * (1 - rate) / attempts)
    return {
        "attempts": attempts,
        "losses": losses,
        "loss_probability": rate,
        "ci95_low": max(0.0, rate - half_width),
        "ci95_high": min(1.0, rate + half_width),
    }


def calibrate(book_id: str, config: dict[str, Any]) -> dict[str, Any]:
    """Run the reproducible route and combat simulation."""
    base = Path("data/processed")
    nodes_path = base / "nodes_edges" / book_id / f"{book_id}_nodes.csv"
    profile_id = str(config["profile_id"])
    edges_path = base / "graph" / book_id / profile_id / "compiled_edges.csv"
    settings_path = (
        Path("data/for_graph_model") / f"{book_id}_compilation_settings.json"
    )

    nodes = {row["node_id"]: row for row in read_csv(nodes_path)}
    enemies = {
        node_id: json.loads(row["enemies"])
        for node_id, row in nodes.items()
        if row.get("enemies", "").strip()
    }
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_csv(edges_path):
        edge: dict[str, Any] = dict(row)
        edge["compiled_weight"] = float(row["compiled_weight"])
        outgoing[row["source_id"]].append(edge)

    settings = read_json(settings_path)
    has_condition_probability = float(settings["has_condition"])
    rules = config["combat_rules"]
    overrides = config["combat_overrides"]
    rng = random.Random(int(config["seed"]))

    attempts = losses = fresh_losses = escaped = unresolved = 0
    by_ordinal: dict[int, dict[str, float]] = defaultdict(
        lambda: {"attempts": 0.0, "losses": 0.0, "starting_endurance": 0.0}
    )
    by_paragraph: dict[str, dict[str, float]] = defaultdict(
        lambda: {"attempts": 0.0, "losses": 0.0, "starting_endurance": 0.0}
    )

    for _ in range(int(config["simulations"])):
        character = create_character(rng, config)
        node_id = "1"
        completed_combats = 0
        for _step in range(int(config["max_steps"])):
            if node_id in {"Death", "Win"}:
                break

            if node_id not in enemies:
                if (
                    "Healing" in character.disciplines
                    and character.endurance < character.maximum_endurance
                ):
                    character.endurance += 1
                selected = weighted_choice(rng, outgoing[node_id], "compiled_weight")
                node_id = str(selected["target_id"])
                continue

            edges = outgoing[node_id]
            escape_edges = [edge for edge in edges if is_escape_edge(edge)]
            escape_mass = sum(float(edge["compiled_weight"]) for edge in escape_edges)
            if escape_edges and rng.random() < escape_mass:
                escaped += 1
                selected = weighted_choice(rng, escape_edges, "compiled_weight")
                node_id = str(selected["target_id"])
                continue

            combat_edges = [
                edge
                for edge in edges
                if edge["target_id"] != "Death" and not is_escape_edge(edge)
            ]
            if not combat_edges:
                raise ValueError(f"Combat paragraph {node_id} has no continuation")

            override = dict(overrides.get(node_id, {}))
            ordinal = completed_combats + 1
            attempts += 1
            by_ordinal[ordinal]["attempts"] += 1
            by_ordinal[ordinal]["starting_endurance"] += character.endurance
            by_paragraph[node_id]["attempts"] += 1
            by_paragraph[node_id]["starting_endurance"] += character.endurance

            fresh_character = Character(
                combat_skill=character.combat_skill,
                endurance=character.maximum_endurance,
                maximum_endurance=character.maximum_endurance,
                disciplines=character.disciplines,
                weapons=character.weapons,
                weaponskill=character.weaponskill,
                has_healing_potion=False,
            )
            fresh_survived, _ = fight(
                rng,
                fresh_character,
                enemies[node_id],
                override,
                rules,
                has_condition_probability,
            )
            if not fresh_survived:
                fresh_losses += 1

            survived, remaining = fight(
                rng,
                character,
                enemies[node_id],
                override,
                rules,
                has_condition_probability,
            )
            if not survived:
                losses += 1
                by_ordinal[ordinal]["losses"] += 1
                by_paragraph[node_id]["losses"] += 1
                node_id = "Death"
                continue

            character.endurance = remaining
            completed_combats += 1
            missing = character.maximum_endurance - character.endurance
            threshold = int(rules["healing_potion_use_threshold"])
            if character.has_healing_potion and missing >= threshold:
                character.endurance = min(
                    character.maximum_endurance,
                    character.endurance + int(rules["healing_potion_points"]),
                )
                character.has_healing_potion = False
            selected = weighted_choice(rng, combat_edges, "compiled_weight")
            node_id = str(selected["target_id"])
        else:
            unresolved += 1

    pooled = summarize_rate(losses, attempts)
    fresh = summarize_rate(fresh_losses, attempts)

    ordinal_report: dict[str, dict[str, float | int]] = {}
    for ordinal, values in sorted(by_ordinal.items()):
        ordinal_attempts = int(values["attempts"])
        rate = summarize_rate(int(values["losses"]), ordinal_attempts)
        rate["mean_starting_endurance"] = (
            values["starting_endurance"] / ordinal_attempts
        )
        ordinal_report[str(ordinal)] = rate

    paragraph_report: dict[str, dict[str, float | int]] = {}
    for node_id, values in sorted(by_paragraph.items(), key=lambda item: int(item[0])):
        paragraph_attempts = int(values["attempts"])
        rate = summarize_rate(int(values["losses"]), paragraph_attempts)
        rate["mean_starting_endurance"] = (
            values["starting_endurance"] / paragraph_attempts
        )
        paragraph_report[node_id] = rate

    loss_probability = float(pooled["loss_probability"])
    return {
        "book_id": book_id,
        "method": "pooled encounter hazard with carried combat Endurance",
        "profile_id_for_route_exposure": profile_id,
        "seed": int(config["seed"]),
        "simulations": int(config["simulations"]),
        "unresolved_simulations": unresolved,
        "escaped_encounters_not_counted_as_fights": escaped,
        "fresh_endurance": fresh,
        "attrition_aware": pooled,
        "recommended_combat_loss_probability": round(loss_probability, 3),
        "recommended_combat_win_probability": round(1 - loss_probability, 3),
        "by_combat_ordinal": ordinal_report,
        "by_paragraph": paragraph_report,
    }


def main() -> None:
    """Parse arguments, run calibration and write its audit report."""
    parser = argparse.ArgumentParser(
        description="Calibrate one fixed Lone Wolf combat probability."
    )
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument(
        "--config",
        type=Path,
        help="Defaults to data/for_graph_model/<book>_combat_calibration.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Defaults to data/processed/graph/<book>/combat_calibration.json.",
    )
    args = parser.parse_args()

    book_id = str(args.book)
    config_path = args.config or (
        Path("data/for_graph_model") / f"{book_id}_combat_calibration.json"
    )
    output_path = args.output or (
        Path("data/processed/graph") / book_id / "combat_calibration.json"
    )
    report = calibrate(book_id, read_json(config_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    attrition = report["attrition_aware"]
    fresh = report["fresh_endurance"]
    print(f"Combat attempts: {attrition['attempts']}")
    print(f"Fresh-Endurance loss probability: {fresh['loss_probability']:.6f}")
    print(f"Attrition-aware loss probability: {attrition['loss_probability']:.6f}")
    print(
        "Recommended fixed combat_win_probability: "
        f"{report['recommended_combat_win_probability']:.3f}"
    )
    print(f"Report: {output_path}")


if __name__ == "__main__":
    main()
