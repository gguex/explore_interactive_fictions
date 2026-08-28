"""Build the two slide-ready phase-5 result figures."""

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
from matplotlib.patches import FancyBboxPatch  # noqa: E402

DEFAULT_BOOK_ID = "LW01"
SLIDE_SIZE = (40 / 3, 7.5)
SLIDE_DPI = 144
BACKGROUND = "#F7F4EB"
INK = "#243447"
MUTED = "#64717D"
LIGHT = "#E5E0D5"
WHITE = "#FFFEFA"
AXIS_COLORS = {
    "risk": "#2878A8",
    "morality": "#5B8C5A",
    "action": "#9467A8",
}
RESULT_COLORS = {
    "recovered": "#397A58",
    "order_sensitive": "#C26B39",
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
    """Apply shared colours and background."""
    figure.patch.set_facecolor(BACKGROUND)
    for axis in figure.axes:
        axis.set_facecolor(BACKGROUND)


def add_card(
    figure: plt.Figure,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    value: str,
    label: str,
    color: str,
    detail: str = "",
) -> None:
    """Draw one rounded result card in figure coordinates."""
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        transform=figure.transFigure,
        boxstyle="round,pad=0.012,rounding_size=0.015",
        facecolor=WHITE,
        edgecolor="#D8D2C7",
        linewidth=1.0,
    )
    figure.patches.append(patch)
    figure.text(
        x + 0.025,
        y + height * 0.60,
        value,
        fontsize=22,
        fontweight="bold",
        color=color,
        va="center",
    )
    figure.text(
        x + 0.025,
        y + height * 0.34,
        label,
        fontsize=9.7,
        fontweight="bold",
        color=INK,
        va="center",
    )
    if detail:
        figure.text(
            x + 0.025,
            y + height * 0.13,
            detail,
            fontsize=7.8,
            color=MUTED,
            va="center",
        )


def indexed_summary(
    rows: list[dict[str, str]],
) -> dict[tuple[str, str], dict[str, str]]:
    """Index unique long-form phase-5.4 summary rows."""
    indexed = {(row["metric"], row["subgroup"]): row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError("Duplicate phase-5 summary row")
    return indexed


def render_individual_results(
    book_id: str,
    summary: dict[tuple[str, str], dict[str, str]],
    trajectories: list[dict[str, str]],
    output_dir: Path,
) -> list[Path]:
    """Render absolute profile manifestation and individual-story diagnostics."""
    axes = ("risk", "morality", "action")
    counts = [
        int(summary[("profile_manifestation", axis)]["numerator"]) for axis in axes
    ]
    figure = plt.figure(figsize=SLIDE_SIZE, dpi=SLIDE_DPI)
    apply_slide_style(figure)
    chart = figure.add_axes((0.08, 0.22, 0.49, 0.56))
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
            fontsize=12,
            fontweight="bold",
            color=INK,
        )
    chart.set_xlim(0, 15.7)
    chart.set_yticks(y_positions, [axis.capitalize() for axis in axes])
    chart.set_xticks([0, 2, 4, 6, 8, 10, 12, 14])
    chart.set_xlabel(
        "Exact matches among 14 conditional medoids", fontsize=10, color=MUTED
    )
    chart.grid(axis="x", color="#D8D2C7", linewidth=0.7, alpha=0.8)
    chart.spines[["top", "right", "left"]].set_visible(False)
    chart.spines["bottom"].set_color("#B9B3A9")
    chart.tick_params(axis="y", length=0, colors=INK, labelsize=11)
    chart.tick_params(axis="x", colors=MUTED, labelsize=9)

    continuity = sum(row["causal_continuity"] == "continuous" for row in trajectories)
    coherent = sum(row["profile_coherence"] == "coherent" for row in trajectories)
    add_card(
        figure,
        0.63,
        0.58,
        0.29,
        0.16,
        value=f"{continuity}/14",
        label="Causally continuous stories",
        color="#397A58",
        detail="No explicit unsupported dependency was detected.",
    )
    add_card(
        figure,
        0.63,
        0.36,
        0.29,
        0.16,
        value=f"{coherent}/14",
        label="Coherent perceived profiles",
        color="#397A58",
        detail=f"The remaining {14 - coherent} stories were labelled mixed.",
    )
    action_expected = {
        level: [row for row in trajectories if row["expected_action"] == level]
        for level in ("neutral", "physical", "tactical")
    }
    action_matches = {
        level: sum(row["action_status"] == "match" for row in rows)
        for level, rows in action_expected.items()
    }
    figure.text(
        0.63,
        0.285,
        "Why is the action score low?",
        fontsize=11.5,
        fontweight="bold",
        color=INK,
    )
    figure.text(
        0.63,
        0.245,
        "Exact recovery by generated action level",
        fontsize=8.8,
        color=MUTED,
    )
    diagnostic = [
        ("Neutral", "neutral"),
        ("Physical", "physical"),
        ("Tactical", "tactical"),
    ]
    for index, (label, level) in enumerate(diagnostic):
        x = 0.63 + index * 0.105
        total = len(action_expected[level])
        figure.text(x, 0.185, label, fontsize=8.5, color=MUTED, ha="left")
        figure.text(
            x,
            0.145,
            f"{action_matches[level]}/{total}",
            fontsize=15,
            fontweight="bold",
            color=AXIS_COLORS["action"],
            ha="left",
        )

    figure.text(
        0.055,
        0.925,
        f"{book_id} — player profiles leave uneven traces in complete stories",
        fontsize=20.5,
        fontweight="bold",
        color=INK,
    )
    figure.text(
        0.055,
        0.858,
        "Qwen inferred the three axes from 14 blinded conditional medoids, without "
        "profiles, edge labels or BoP indices.",
        fontsize=10.8,
        color=MUTED,
    )
    figure.text(
        0.055,
        0.075,
        "Absolute agreement includes neutral levels. It describes these selected "
        "central trajectories—not model accuracy or all possible playthroughs.",
        fontsize=8.6,
        color=MUTED,
    )
    return save_figure(figure, output_dir / "01_individual_trajectories")


def render_comparison_results(
    book_id: str,
    summary: dict[tuple[str, str], dict[str, str]],
    pairs: list[dict[str, str]],
    output_dir: Path,
) -> list[Path]:
    """Render pairwise recovery, order stability and all six designed comparisons."""
    controlled = summary[("controlled_contrast_recovery", "all")]
    stability = summary[("ab_ba_order_stability", "all_pairwise_labels")]
    leakage = summary[("cross_axis_leakage", "non_controlled_axes")]
    figure = plt.figure(figsize=SLIDE_SIZE, dpi=SLIDE_DPI)
    apply_slide_style(figure)
    add_card(
        figure,
        0.055,
        0.67,
        0.265,
        0.14,
        value=f"{controlled['numerator']}/{controlled['denominator']}",
        label="Controlled contrasts recovered",
        color="#397A58",
        detail="Only order-stable controlled-axis labels count.",
    )
    add_card(
        figure,
        0.365,
        0.67,
        0.265,
        0.14,
        value=f"{stability['numerator']}/{stability['denominator']}",
        label="Labels stable under A/B reversal",
        color="#397A58",
        detail="Narrative distinctness plus three profile shifts.",
    )
    add_card(
        figure,
        0.675,
        0.67,
        0.265,
        0.14,
        value=f"{leakage['numerator']}/{leakage['denominator']}",
        label="Stable off-axis labels shifted",
        color="#C26B39",
        detail=f"{leakage['order_sensitive']} more were order-sensitive.",
    )

    table_axis = figure.add_axes((0.055, 0.16, 0.89, 0.43))
    table_axis.axis("off")
    headers = [
        ("Pair", 0.01),
        ("Controlled design", 0.11),
        ("Structural distance", 0.34),
        ("Narrative A/B → B/A", 0.55),
        ("Controlled contrast", 0.79),
    ]
    for label, x in headers:
        table_axis.text(
            x,
            1.03,
            label,
            transform=table_axis.transAxes,
            fontsize=9.2,
            fontweight="bold",
            color=MUTED,
            va="bottom",
        )
    for index, row in enumerate(pairs):
        y = 0.91 - index * 0.155
        if index % 2 == 0:
            table_axis.add_patch(
                FancyBboxPatch(
                    (0.0, y - 0.055),
                    1.0,
                    0.12,
                    transform=table_axis.transAxes,
                    boxstyle="round,pad=0.006,rounding_size=0.006",
                    facecolor="#EEE9DF",
                    edgecolor="none",
                )
            )
        axis_name = row["axis"]
        table_axis.text(
            0.01,
            y,
            row["comparison_id"],
            transform=table_axis.transAxes,
            fontsize=10,
            fontweight="bold",
            color=INK,
            va="center",
        )
        table_axis.text(
            0.11,
            y,
            f"{axis_name.capitalize()} · {row['outcome']}",
            transform=table_axis.transAxes,
            fontsize=9.5,
            fontweight="bold",
            color=AXIS_COLORS[axis_name],
            va="center",
        )
        distance = 1 - float(row["normalized_node_lcs_similarity"])
        table_axis.text(
            0.34,
            y,
            f"{distance:.2f}",
            transform=table_axis.transAxes,
            fontsize=10,
            color=INK,
            va="center",
        )
        distinct_ab = row["narrative_distinctness_ab"].capitalize()
        distinct_ba = row["narrative_distinctness_ba"].capitalize()
        distinct_color = (
            INK if row["narrative_distinctness_stable"] == "True" else "#C26B39"
        )
        table_axis.text(
            0.55,
            y,
            f"{distinct_ab} → {distinct_ba}",
            transform=table_axis.transAxes,
            fontsize=10,
            color=distinct_color,
            fontweight="bold",
            va="center",
        )
        result = row["controlled_axis_result"]
        display = "Recovered" if result == "recovered" else "Order-sensitive"
        table_axis.text(
            0.79,
            y,
            display,
            transform=table_axis.transAxes,
            fontsize=10,
            color=RESULT_COLORS[result],
            fontweight="bold",
            va="center",
        )

    figure.text(
        0.055,
        0.925,
        f"{book_id} — profile contrasts are visible, but axes co-vary",
        fontsize=20.5,
        fontweight="bold",
        color=INK,
    )
    figure.text(
        0.055,
        0.858,
        "Six extreme-profile pairs were judged in both orders; B/A directions were "
        "inverted before exact stability checks.",
        fontsize=10.8,
        color=MUTED,
    )
    figure.text(
        0.055,
        0.075,
        "Structural distance = 1 − normalized paragraph-sequence LCS. Off-axis shifts "
        "show that the generated axes are not narratively orthogonal.",
        fontsize=8.6,
        color=MUTED,
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
        (
            "comparison",
            "ab_ba_order_stability",
            "all_pairwise_labels",
            "Exact A/B–B/A agreement after inversion",
        ),
        (
            "comparison",
            "cross_axis_leakage",
            "non_controlled_axes",
            "Directional shifts among stable off-axis labels",
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
                "status": "to be produced later",
            },
            {
                "position": "3",
                "figure": "01_individual_trajectories",
                "content": "Individual-trajectory results",
                "status": "produced",
            },
            {
                "position": "4",
                "figure": "02_trajectory_comparisons",
                "content": "Pairwise trajectory-comparison results",
                "status": "produced",
            },
        ],
        "messages": {
            "01_individual_trajectories": (
                "Absolute profile manifestation is uneven across axes, while all "
                "selected stories remain causally continuous."
            ),
            "02_trajectory_comparisons": (
                "Relative contrasts are usually recovered, but profile axes co-vary "
                "and some judgments remain order-sensitive."
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
    print(f"OK: built two phase-5 result slides for {book_id}")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()
