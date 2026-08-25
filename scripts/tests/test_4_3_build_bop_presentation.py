"""Validate the slide-ready figures and key-number table built in phase 4.3."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import struct
from pathlib import Path

import numpy as np

DEFAULT_BOOK_ID = "LW01"
EXPECTED_FIGURES = {
    "01_profile_landscape": "player profiles change both survival",
    "02_axis_effects": "risk is the dominant behavioural axis",
    "03_local_index_maps": "three local views of the same narrative graph",
    "04_key_numbers": "five numbers that summarise the reading experience",
}
EXPECTED_TABLE_MEASURES = [
    "Win probability",
    "Expected transitions",
    "Trajectory entropy (nats)",
    "Expected coverage",
    "Replayability",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read one required UTF-8 CSV table."""
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact; run phase 4.3 first: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def png_dimensions(path: Path) -> tuple[int, int]:
    """Read dimensions directly from a PNG IHDR block."""
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Invalid PNG header: {path}")
    return struct.unpack(">II", header[16:24])


def sha256(path: Path) -> str:
    """Return one artifact's SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def format_metric(value: float, kind: str) -> str:
    """Independently reproduce presentation-number formatting."""
    if kind == "percent":
        return f"{100 * value:.1f}%"
    if kind == "count":
        return f"{value:.1f}"
    return f"{value:.2f}"


def validate_key_numbers(
    global_rows: list[dict[str, str]], table_rows: list[dict[str, str]]
) -> None:
    """Check the five selected metrics and every displayed rounded value."""
    if [row["measure"] for row in table_rows] != EXPECTED_TABLE_MEASURES:
        raise ValueError("Key-number measure order or coverage differs")
    by_metric = {row["metric"]: row for row in global_rows}
    definitions = [
        ("win_probability", "percent"),
        ("expected_transitions", "count"),
        ("trajectory_entropy_nats", "number"),
        ("expected_coverage", "percent"),
        ("replayability", "percent"),
    ]
    for produced, (metric, kind) in zip(table_rows, definitions, strict=True):
        source = by_metric[metric]
        expected = {
            "neutral": format_metric(float(source["neutral_value"]), kind),
            "balanced_mean": format_metric(float(source["balanced_mean"]), kind),
            "observed_range": (
                f"{format_metric(float(source['minimum_value']), kind)}–"
                f"{format_metric(float(source['maximum_value']), kind)}"
            ),
        }
        for field, value in expected.items():
            if produced[field] != value:
                raise ValueError(f"Wrong key number for {metric}/{field}")


def main() -> None:
    """Validate figure formats, content markers, numbers and manifest provenance."""
    parser = argparse.ArgumentParser(description="Validate phase-4.3 slide artifacts.")
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    book_id = str(args.book)
    bop_root = args.input_dir or Path("data/processed/bop") / book_id
    presentation_data = bop_root / "presentation"
    output_dir = args.output_dir or Path("results/phase4") / book_id / "presentation"
    profiles = read_csv(bop_root / "profile_metrics.csv")
    global_rows = read_csv(presentation_data / "global_summary.csv")
    rankings = read_csv(presentation_data / "node_rankings.csv")
    table_rows = read_csv(output_dir / "04_key_numbers.csv")
    validate_key_numbers(global_rows, table_rows)

    artifacts = []
    for figure, title_fragment in EXPECTED_FIGURES.items():
        png_path = output_dir / f"{figure}.png"
        svg_path = output_dir / f"{figure}.svg"
        for path in (png_path, svg_path):
            if not path.exists() or path.stat().st_size < 10_000:
                raise ValueError(f"Missing or implausibly small figure: {path}")
            artifacts.append(path)
        width, height = png_dimensions(png_path)
        if (width, height) != (1920, 1080):
            raise ValueError(
                f"Slide PNG is not 1920x1080: {png_path} ({width}x{height})"
            )
        svg = svg_path.read_text(encoding="utf-8")
        if "<svg" not in svg or book_id not in svg or title_fragment not in svg:
            raise ValueError(f"SVG lacks expected English title: {svg_path}")
    table_path = output_dir / "04_key_numbers.csv"
    artifacts.append(table_path)

    manifest_path = output_dir / "presentation_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("book_id") != book_id or manifest.get("language") != "English":
        raise ValueError("Presentation manifest identity or language differs")
    if manifest.get("slide_size_pixels") != [1920, 1080]:
        raise ValueError("Presentation manifest slide size differs")
    if [item["figure"] for item in manifest.get("recommended_order", [])] != [
        "01_profile_landscape",
        "02_axis_effects",
        "03_local_index_maps",
    ]:
        raise ValueError("Recommended presentation order differs")
    if manifest.get("optional_table") != "04_key_numbers":
        raise ValueError("Optional presentation table differs")

    entropy = np.array([float(row["trajectory_entropy_nats"]) for row in profiles])
    win = np.array([float(row["win_probability"]) for row in profiles])
    correlation = float(np.corrcoef(entropy, win)[0, 1])
    if not math.isclose(
        float(manifest["descriptive_win_entropy_correlation"]),
        correlation,
        abs_tol=1e-12,
    ):
        raise ValueError("Manifest landscape correlation differs")
    expected_sensitive = [
        row["node_id"]
        for row in rankings
        if row["ranking"] == "profile_sensitivity"
    ][:3]
    expected_mortality = [
        row["node_id"]
        for row in rankings
        if row["ranking"] == "neutral_death_contribution"
    ][:3]
    if manifest.get("top_profile_sensitive_nodes") != expected_sensitive:
        raise ValueError("Manifest sensitive-node highlights differ")
    if manifest.get("top_neutral_mortality_nodes") != expected_mortality:
        raise ValueError("Manifest mortality-node highlights differ")

    described = manifest.get("artifacts", {})
    if set(described) != {path.name for path in artifacts}:
        raise ValueError("Manifest artifact coverage differs")
    for path in artifacts:
        if described[path.name]["bytes"] != path.stat().st_size:
            raise ValueError(f"Manifest byte count differs for {path.name}")
        if described[path.name]["sha256"] != sha256(path):
            raise ValueError(f"Manifest digest differs for {path.name}")

    print(f"OK: {book_id} phase-4.3 presentation package")
    print(
        f"Figures={len(EXPECTED_FIGURES)} in PNG+SVG; table={len(table_rows)} rows; "
        f"correlation={correlation:.3f}"
    )


if __name__ == "__main__":
    main()
