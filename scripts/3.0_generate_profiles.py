"""Phase 3.0: generate the single behavioral-profile design.

The profile schema is deliberately limited to the three semantic choice axes. Game
mechanics belong to the separate compilation settings consumed by phase 3.1.
"""

from __future__ import annotations

import argparse
import json
from itertools import product
from pathlib import Path

RISK_LEVELS = ("cautious", "neutral", "reckless")
MORALITY_LEVELS = ("selfish", "neutral", "noble")
ACTION_LEVELS = ("physical", "neutral", "tactical")
DEFAULT_OUTPUT = Path("data/for_graph_model/behavioral_profiles.json")


def generate_profiles() -> list[dict[str, str]]:
    """Return the 27 profiles of the three-by-three-by-three design."""
    profiles = []
    for risk, morality, action in product(
        RISK_LEVELS, MORALITY_LEVELS, ACTION_LEVELS
    ):
        profiles.append(
            {
                "profile_id": f"{risk}_{morality}_{action}",
                "risk": risk,
                "morality": morality,
                "action": action,
            }
        )
    return profiles


def main() -> None:
    """Write the deterministic profile design as JSON."""
    parser = argparse.ArgumentParser(
        description="Generate the 27 behavioral profiles used in phase 3."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output JSON path (default: {DEFAULT_OUTPUT}).",
    )
    args = parser.parse_args()
    output_path = Path(args.output)
    profiles = generate_profiles()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(profiles, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(profiles)} profiles to {output_path}")


if __name__ == "__main__":
    main()
