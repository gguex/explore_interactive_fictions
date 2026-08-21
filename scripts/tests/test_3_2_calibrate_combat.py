"""Independent checks for the LW01 combat-calibration report."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import sys
from pathlib import Path
from types import ModuleType

DEFAULT_BOOK_ID = "LW01"


def load_calibrator() -> ModuleType:
    """Load the numbered calibration script without making scripts a package."""
    path = Path("scripts/3.2_calibrate_combat.py")
    spec = importlib.util.spec_from_file_location("combat_calibrator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    """Validate official table examples and aggregation invariants."""
    parser = argparse.ArgumentParser(description="Validate combat calibration.")
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    args = parser.parse_args()
    book_id = str(args.book)

    calibrator = load_calibrator()
    if calibrator.combat_result(-3, 6) != (6, 3):
        raise ValueError("Combat table disagrees with the official -3 example")
    if calibrator.combat_result(0, 6) != (8, 2):
        raise ValueError("Combat table disagrees with the official ratio-0 example")
    if calibrator.combat_result(11, 0)[0] != calibrator.KILL_DAMAGE:
        raise ValueError("Automatic-kill cell is missing")

    report_path = (
        Path("data/processed/graph") / book_id / "combat_calibration.json"
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report["book_id"] != book_id:
        raise ValueError("Calibration report has the wrong book identifier")
    if report["unresolved_simulations"] != 0:
        raise ValueError("Some simulated routes did not reach an absorbing node")

    attrition = report["attrition_aware"]
    fresh = report["fresh_endurance"]
    ordinal = report["by_combat_ordinal"]
    if sum(int(row["attempts"]) for row in ordinal.values()) != attrition["attempts"]:
        raise ValueError("Ordinal attempts do not sum to the pooled attempts")
    if sum(int(row["losses"]) for row in ordinal.values()) != attrition["losses"]:
        raise ValueError("Ordinal losses do not sum to the pooled losses")
    if attrition["loss_probability"] <= fresh["loss_probability"]:
        raise ValueError("Carried Endurance attrition did not increase combat risk")
    if not (
        ordinal["1"]["mean_starting_endurance"]
        > ordinal["2"]["mean_starting_endurance"]
        > ordinal["3"]["mean_starting_endurance"]
    ):
        raise ValueError("Starting Endurance does not decline over early combats")

    expected_win = 1 - float(report["recommended_combat_loss_probability"])
    if not math.isclose(
        float(report["recommended_combat_win_probability"]),
        expected_win,
        abs_tol=1e-12,
    ):
        raise ValueError("Rounded loss and win recommendations are not complementary")

    nodes_path = (
        Path("data/processed/nodes_edges") / book_id / f"{book_id}_nodes.csv"
    )
    with nodes_path.open(encoding="utf-8", newline="") as handle:
        combat_ids = {
            row["node_id"] for row in csv.DictReader(handle) if row["enemies"].strip()
        }
    if set(report["by_paragraph"]) != combat_ids:
        raise ValueError("The report does not cover every combat paragraph")

    print(f"OK: {book_id} combat calibration")
    print(
        f"Attempts={attrition['attempts']}; "
        f"fresh loss={fresh['loss_probability']:.6f}; "
        f"attrition loss={attrition['loss_probability']:.6f}"
    )


if __name__ == "__main__":
    main()
