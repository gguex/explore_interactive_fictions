"""Build plot-only phase-5 figures for composition in LaTeX slides."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path

MATPLOTLIB_CACHE = Path(tempfile.gettempdir()) / "explore-if-matplotlib"
MATPLOTLIB_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MATPLOTLIB_CACHE))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
matplotlib.rcParams["svg.fonttype"] = "none"
matplotlib.rcParams["svg.hashsalt"] = "explore-interactive-fictions-phase-5"

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

DEFAULT_BOOK_ID = "LW01"
SLIDE_SIZE = (40 / 3, 7.5)
SLIDE_DPI = 144
BACKGROUND = "#FFFFFF"
INK = "#243447"
MUTED = "#64717D"
LIGHT = "#E5E0D5"
AXIS_COLORS = {
    "risk": "#2878A8",
    "morality": "#5B8C5A",
    "action": "#9467A8",
}
ORDER_SENSITIVE = "#C23B22"
CONTRAST_LABELS = {
    "risk": "Cautious (A) vs reckless (B)",
    "morality": "Selfish (A) vs noble (B)",
    "action": "Physical (A) vs tactical (B)",
}
DIRECTION_LABELS = {
    "A_more_cautious": "cautious",
    "A_more_reckless": "reckless",
    "A_more_selfish": "selfish",
    "A_more_noble": "noble",
    "A_more_physical": "physical",
    "A_more_tactical": "tactical",
    "similar": "even",
    "unclear": "unclear",
}
KEY_FIELDS = [
    "slide",
    "metric",
    "subgroup",
    "numerator",
    "denominator",
    "display",
    "interpretation",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read one required UTF-8 CSV table."""
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    """Return one file digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def save_figure(figure: plt.Figure, output_base: Path) -> list[Path]:
    """Save one slide in exact 1920x1080 PNG and editable SVG."""
    output_base.parent.mkdir(parents=True, exist_ok=True)
    paths = [output_base.with_suffix(".png"), output_base.with_suffix(".svg")]
    figure.savefig(
        paths[0],
        dpi=SLIDE_DPI,
        facecolor=figure.get_facecolor(),
        metadata={"Software": "explore_interactive_fictions phase 5.5"},
    )
    figure.savefig(
        paths[1],
        facecolor=figure.get_facecolor(),
        metadata={
            "Creator": "explore_interactive_fictions phase 5.5",
            "Date": None,
        },
    )
    plt.close(figure)
    return paths


def apply_slide_style(figure: plt.Figure) -> None:
    """Apply shared colors and background."""
    figure.patch.set_facecolor(BACKGROUND)
    for axis in figure.axes:
        axis.set_facecolor(BACKGROUND)


def indexed_summary(
    rows: list[dict[str, str]],
) -> dict[tuple[str, str], dict[str, str]]:
    """Index unique long-form phase-5.4 summary rows."""
    indexed = {(row["metric"], row["subgroup"]): row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError("Duplicate phase-5 summary row")
    return indexed


def aggregate_direction(row: dict[str, str], axis: str) -> tuple[str, bool]:
    """Summarize one canonical A/B and B/A directional judgment."""
    forward = row[f"{axis}_shift_ab"]
    reverse = row[f"{axis}_shift_ba_canonical"]
    if forward == reverse:
        return DIRECTION_LABELS[forward], False
    if "unclear" in {forward, reverse}:
        return "unclear", True
    if forward == "similar":
        return DIRECTION_LABELS[reverse], True
    if reverse == "similar":
        return DIRECTION_LABELS[forward], True
    return "even", True


def aggregate_distinctness(row: dict[str, str]) -> tuple[str, bool]:
    """Summarize narrative distinctness across the two story orders."""
    forward = row["narrative_distinctness_ab"]
    reverse = row["narrative_distinctness_ba"]
    if forward == reverse:
        return forward.capitalize(), False
    levels = {"low": 1, "medium": 2, "high": 3}
    labels = {1: "Low", 2: "Medium", 3: "High"}
    mean = (levels[forward] + levels[reverse]) / 2
    if mean.is_integer():
        return labels[int(mean)], True
    lower = labels[int(mean)]
    upper = labels[int(mean) + 1].lower()
    return f"{lower}-{upper}", True


def render_individual_results(
    book_id: str,
    summary: dict[tuple[str, str], dict[str, str]],
    trajectories: list[dict[str, str]],
    output_dir: Path,
) -> list[Path]:
    """Render profile manifestation as one plot-only chart."""
    axes = ("risk", "morality", "action")
    counts = [
        int(summary[("profile_manifestation", axis)]["numerator"]) for axis in axes
    ]
    figure = plt.figure(figsize=SLIDE_SIZE, dpi=SLIDE_DPI)
    apply_slide_style(figure)
    chart = figure.add_axes((0.10, 0.16, 0.82, 0.70))
    y_positions = [2, 1, 0]
    chart.barh(y_positions, [14, 14, 14], color=LIGHT, height=0.56)
    chart.barh(
        y_positions,
        counts,
        color=[AXIS_COLORS[axis] for axis in axes],
        height=0.56,
    )
    for position, count in zip(y_positions, counts, strict=True):
        chart.text(
            count + 0.25,
            position,
            f"{count}/14  ({100 * count / 14:.0f}%)",
            va="center",
            ha="left",
            fontsize=18,
            fontweight="bold",
            color=INK,
        )
    chart.set_xlim(0, 15.7)
    chart.set_yticks(y_positions, [axis.capitalize() for axis in axes])
    chart.set_xticks([0, 2, 4, 6, 8, 10, 12, 14])
    chart.set_xlabel(
        "Exact matches among 14 conditional medoids", fontsize=13, color=MUTED
    )
    chart.set_title(
        "Generated versus perceived profile",
        fontsize=20,
        fontweight="bold",
        color=INK,
        pad=14,
    )
    chart.grid(axis="x", color="#D8D2C7", linewidth=0.7, alpha=0.8)
    chart.spines[["top", "right", "left"]].set_visible(False)
    chart.spines["bottom"].set_color("#B9B3A9")
    chart.tick_params(axis="y", length=0, colors=INK, labelsize=17)
    chart.tick_params(axis="x", colors=MUTED, labelsize=14)
    return save_figure(figure, output_dir / "01_individual_trajectories")


def render_comparison_results(
    book_id: str,
    summary: dict[tuple[str, str], dict[str, str]],
    pairs: list[dict[str, str]],
    output_dir: Path,
) -> list[Path]:
    """Render the six designed pairwise comparisons without result cards."""
    figure = plt.figure(figsize=SLIDE_SIZE, dpi=SLIDE_DPI)
    apply_slide_style(figure)
    table_axis = figure.add_axes((0.025, 0.08, 0.95, 0.84))
    table_axis.axis("off")
    headers = [
        ("Profile contrast", 0.01),
        ("Outcome", 0.27),
        ("Path\ndifference\n(LCS)", 0.36),
        ("A on Risk", 0.48),
        ("A on Morality", 0.62),
        ("A on Action", 0.76),
        ("Narrative\ndistinctness", 0.89),
    ]
    for label, x in headers:
        table_axis.text(
            x,
            0.96,
            label,
            transform=table_axis.transAxes,
            fontsize=13,
            fontweight="bold",
            color=MUTED,
            va="bottom",
            linespacing=1.1,
        )
    for index, row in enumerate(pairs):
        y = 0.82 - index * 0.135
        if index % 2 == 0:
            table_axis.add_patch(
                Rectangle(
                    (0.0, y - 0.052),
                    1.0,
                    0.105,
                    transform=table_axis.transAxes,
                    facecolor="#EEE9DF",
                    edgecolor="none",
                )
            )
        axis_name = row["axis"]
        table_axis.text(
            0.01,
            y,
            CONTRAST_LABELS[axis_name],
            transform=table_axis.transAxes,
            fontsize=13,
            fontweight="bold",
            color=AXIS_COLORS[axis_name],
            va="center",
        )
        table_axis.text(
            0.27,
            y,
            row["outcome"],
            transform=table_axis.transAxes,
            fontsize=14,
            color=INK,
            va="center",
        )
        distance = 1 - float(row["normalized_node_lcs_similarity"])
        table_axis.text(
            0.36,
            y,
            f"{distance:.2f}",
            transform=table_axis.transAxes,
            fontsize=14,
            color=INK,
            va="center",
        )
        for profile_axis, x in zip(
            ("risk", "morality", "action"), (0.48, 0.62, 0.76), strict=True
        ):
            label, order_sensitive = aggregate_direction(row, profile_axis)
            table_axis.text(
                x,
                y,
                label,
                transform=table_axis.transAxes,
                fontsize=12.5,
                color=ORDER_SENSITIVE if order_sensitive else INK,
                fontweight="bold" if profile_axis == axis_name else "normal",
                va="center",
            )
        distinctness, distinctness_order_sensitive = aggregate_distinctness(row)
        table_axis.text(
            0.89,
            y,
            distinctness,
            transform=table_axis.transAxes,
            fontsize=12.5,
            color=ORDER_SENSITIVE if distinctness_order_sensitive else INK,
            va="center",
        )

    return save_figure(figure, output_dir / "02_trajectory_comparisons")


def build_key_rows(
    summary: dict[tuple[str, str], dict[str, str]],
) -> list[dict[str, str]]:
    """Build the compact table of numbers displayed on the two slides."""
    definitions = [
        (
            "individual",
            "profile_manifestation",
            "risk",
            "Exact generated risk level",
        ),
        (
            "individual",
            "profile_manifestation",
            "morality",
            "Exact generated morality level",
        ),
        (
            "individual",
            "profile_manifestation",
            "action",
            "Exact generated action level",
        ),
        (
            "comparison",
            "controlled_contrast_recovery",
            "all",
            "Order-stable recovery of the controlled axis",
        ),
    ]
    rows: list[dict[str, str]] = []
    for slide, metric, subgroup, interpretation in definitions:
        source = summary[(metric, subgroup)]
        numerator = int(source["numerator"])
        denominator = int(source["denominator"])
        rows.append(
            {
                "slide": slide,
                "metric": metric,
                "subgroup": subgroup,
                "numerator": str(numerator),
                "denominator": str(denominator),
                "display": (
                    f"{numerator}/{denominator} ({100 * numerator / denominator:.0f}%)"
                ),
                "interpretation": interpretation,
            }
        )
    return rows


def parse_args() -> argparse.Namespace:
    """Parse presentation-builder arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args()


def main() -> None:
    """Generate the two result slides, key table and audit manifest."""
    args = parse_args()
    book_id = str(args.book)
    input_dir = args.input_dir or Path("data/processed/phase5") / book_id
    output_dir = args.output_dir or Path("results/phase5") / book_id / "presentation"
    source_paths = {
        "summary": input_dir / "phase5_summary.csv",
        "trajectories": input_dir / "trajectory_results.csv",
        "pairs": input_dir / "pairwise_results.csv",
        "analysis_manifest": input_dir / "phase5_manifest.json",
    }
    summary_rows = read_csv(source_paths["summary"])
    trajectories = read_csv(source_paths["trajectories"])
    pairs = read_csv(source_paths["pairs"])
    summary = indexed_summary(summary_rows)
    if len(trajectories) != 14 or len(pairs) != 6:
        raise ValueError("Phase-5.4 result populations are incomplete")

    generated: list[Path] = []
    generated.extend(
        render_individual_results(book_id, summary, trajectories, output_dir)
    )
    generated.extend(render_comparison_results(book_id, summary, pairs, output_dir))
    key_rows = build_key_rows(summary)
    key_path = output_dir / "key_results.csv"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    with key_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=KEY_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(key_rows)
    generated.append(key_path)

    manifest = {
        "schema_version": "1.0",
        "phase": "5.5",
        "status": "complete",
        "book_id": book_id,
        "language": "English",
        "slide_size_pixels": [1920, 1080],
        "deck_plan": [
            {
                "position": "1–2",
                "content": "Procedure and prompt calibration",
                "status": "composed separately in LaTeX",
            },
            {
                "position": "3",
                "figure": "01_individual_trajectories",
                "content": "Plot-only individual-trajectory results",
                "status": "produced",
            },
            {
                "position": "4",
                "figure": "02_trajectory_comparisons",
                "content": "Table-only pairwise trajectory-comparison results",
                "status": "produced",
            },
        ],
        "messages": {
            "01_individual_trajectories": (
                "Absolute profile manifestation is uneven across axes, while all "
                "selected stories remain causally continuous."
            ),
            "02_trajectory_comparisons": (
                "The intended relative profile is recovered in five of six "
                "controlled comparisons; reversal is only a robustness check."
            ),
        },
        "scope": (
            "Descriptive results for 14 conditional medoids and six designed pairs; "
            "not model accuracy or a population estimate"
        ),
        "source_hashes": {str(path): sha256(path) for path in source_paths.values()},
        "artifacts": {
            path.name: {"bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in generated
        },
    }
    manifest_path = output_dir / "presentation_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"OK: built two plot-only phase-5 result figures for {book_id}")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()
