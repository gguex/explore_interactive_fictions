"""Build the concise, slide-ready phase-4 BoP presentation package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

MATPLOTLIB_CACHE = Path(tempfile.gettempdir()) / "explore-if-matplotlib"
MATPLOTLIB_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MATPLOTLIB_CACHE))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
matplotlib.rcParams["svg.fonttype"] = "none"
matplotlib.rcParams["svg.hashsalt"] = "explore-interactive-fictions-phase-4"

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.cm import ScalarMappable  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.colors import Normalize  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.transforms import Bbox  # noqa: E402

DEFAULT_BOOK_ID = "LW01"
NEUTRAL_PROFILE_ID = "neutral_neutral_neutral"
SLIDE_SIZE = (40 / 3, 7.5)
SLIDE_DPI = 144
BACKGROUND = "#F7F4EB"
INK = "#243447"
MUTED = "#64717D"
RISK_COLORS = {
    "cautious": "#2878A8",
    "neutral": "#737B84",
    "reckless": "#D66A35",
}
AXIS_COLORS = {
    "risk": "#2878A8",
    "morality": "#5B8C5A",
    "action": "#9467A8",
}
ACTION_MARKERS = {"physical": "o", "neutral": "s", "tactical": "^"}
KEY_NUMBER_FIELDS = ["measure", "neutral", "balanced_mean", "observed_range"]


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read one required UTF-8 CSV input."""
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def save_figure(figure: plt.Figure, output_base: Path) -> list[Path]:
    """Save the same exact slide in editable SVG and 1920x1080 PNG."""
    output_base.parent.mkdir(parents=True, exist_ok=True)
    paths = [output_base.with_suffix(".png"), output_base.with_suffix(".svg")]
    figure.savefig(
        paths[0],
        dpi=SLIDE_DPI,
        facecolor=figure.get_facecolor(),
        metadata={"Software": "explore_interactive_fictions phase 4.3"},
    )
    figure.savefig(
        paths[1],
        facecolor=figure.get_facecolor(),
        metadata={
            "Creator": "explore_interactive_fictions phase 4.3",
            "Date": None,
        },
    )
    plt.close(figure)
    return paths


def apply_slide_style(figure: plt.Figure) -> None:
    """Apply the shared presentation background and typography."""
    figure.patch.set_facecolor(BACKGROUND)
    for axis in figure.axes:
        axis.set_facecolor(BACKGROUND)


def profile_label(row: dict[str, str]) -> str:
    """Return a compact readable label for one three-axis profile."""
    return f"{row['risk']} / {row['morality']} / {row['action']}"


def render_profile_landscape(
    book_id: str, profiles: list[dict[str, str]], output_dir: Path
) -> tuple[list[Path], float]:
    """Show the survival–freedom relation across all configured profiles."""
    entropy = np.array([float(row["trajectory_entropy_nats"]) for row in profiles])
    win = np.array([100 * float(row["win_probability"]) for row in profiles])
    correlation = float(np.corrcoef(entropy, win)[0, 1])
    figure, axis = plt.subplots(figsize=SLIDE_SIZE, dpi=SLIDE_DPI)
    apply_slide_style(figure)
    figure.subplots_adjust(left=0.09, right=0.76, bottom=0.15, top=0.80)

    for risk, color in RISK_COLORS.items():
        for action, marker in ACTION_MARKERS.items():
            subset = [
                row
                for row in profiles
                if row["risk"] == risk and row["action"] == action
            ]
            axis.scatter(
                [float(row["trajectory_entropy_nats"]) for row in subset],
                [100 * float(row["win_probability"]) for row in subset],
                s=82,
                marker=marker,
                c=color,
                edgecolors="white",
                linewidths=0.9,
                alpha=0.92,
                zorder=3,
            )

    coefficients = np.polyfit(entropy, win, 1)
    x_line = np.linspace(float(entropy.min()), float(entropy.max()), 100)
    axis.plot(
        x_line,
        np.polyval(coefficients, x_line),
        color="#93A0AA",
        linestyle="--",
        linewidth=1.5,
        zorder=1,
    )

    neutral = next(
        row for row in profiles if row["profile_id"] == NEUTRAL_PROFILE_ID
    )
    minimum = min(profiles, key=lambda row: float(row["win_probability"]))
    maximum = max(profiles, key=lambda row: float(row["win_probability"]))
    annotations = [
        (neutral, "Neutral profile", (18, 8)),
        (minimum, f"Lowest win\n{profile_label(minimum)}", (18, -6)),
        (maximum, f"Highest win\n{profile_label(maximum)}", (-135, -2)),
    ]
    for row, label, offset in annotations:
        x_value = float(row["trajectory_entropy_nats"])
        y_value = 100 * float(row["win_probability"])
        axis.scatter(
            [x_value],
            [y_value],
            marker="*",
            s=235,
            facecolor="#F5C84C" if row is neutral else RISK_COLORS[row["risk"]],
            edgecolor=INK,
            linewidth=1.1,
            zorder=5,
        )
        axis.annotate(
            label,
            (x_value, y_value),
            xytext=offset,
            textcoords="offset points",
            fontsize=9.5,
            color=INK,
            ha="left",
            va="center",
            arrowprops={"arrowstyle": "-", "color": "#87919A", "lw": 0.8},
        )

    axis.set_xlabel("Trajectory entropy (nats)", fontsize=12, color=INK, labelpad=10)
    axis.set_ylabel("Win probability (%)", fontsize=12, color=INK, labelpad=10)
    axis.grid(True, color="#D9D5CB", linewidth=0.7, alpha=0.8)
    axis.spines[["top", "right"]].set_visible(False)
    axis.spines[["left", "bottom"]].set_color("#AEB5BA")
    axis.tick_params(colors=INK, labelsize=10)
    axis.set_xlim(float(entropy.min()) - 0.35, float(entropy.max()) + 0.35)
    axis.set_ylim(float(win.min()) - 1.5, float(win.max()) + 2.5)

    risk_legend = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="none",
            markerfacecolor=color,
            markeredgecolor="white",
            markersize=8,
            label=level.capitalize(),
        )
        for level, color in RISK_COLORS.items()
    ]
    action_legend = [
        Line2D(
            [0],
            [0],
            marker=marker,
            linestyle="none",
            markerfacecolor="#737B84",
            markeredgecolor="white",
            markersize=8,
            label=level.capitalize(),
        )
        for level, marker in ACTION_MARKERS.items()
    ]
    first_legend = axis.legend(
        handles=risk_legend,
        title="Risk axis (colour)",
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        frameon=False,
        fontsize=9,
        title_fontsize=9.5,
    )
    axis.add_artist(first_legend)
    axis.legend(
        handles=action_legend,
        title="Action axis (shape)",
        loc="upper left",
        bbox_to_anchor=(1.02, 0.62),
        frameon=False,
        fontsize=9,
        title_fontsize=9.5,
    )
    figure.text(
        0.07,
        0.93,
        f"{book_id} — player profiles change both survival and narrative freedom",
        fontsize=21,
        fontweight="bold",
        color=INK,
    )
    figure.text(
        0.07,
        0.865,
        f"Across the 27 configured profiles, win probability and path entropy rise "
        f"together (descriptive r = {correlation:.2f}).",
        fontsize=11.5,
        color=MUTED,
    )
    figure.text(
        0.07,
        0.035,
        "Each point is one profile. The correlation describes the complete factorial "
        "design; it is not a population estimate or a causal effect.",
        fontsize=8.5,
        color=MUTED,
    )
    return save_figure(figure, output_dir / "01_profile_landscape"), correlation


def render_axis_effects(
    book_id: str, axis_rows: list[dict[str, str]], output_dir: Path
) -> list[Path]:
    """Render four small multiples of marginal effects versus axis-neutral levels."""
    row_definitions = [
        ("risk", "cautious", "Risk: cautious"),
        ("risk", "reckless", "Risk: reckless"),
        ("morality", "selfish", "Morality: selfish"),
        ("morality", "noble", "Morality: noble"),
        ("action", "physical", "Action: physical"),
        ("action", "tactical", "Action: tactical"),
    ]
    metric_definitions = [
        ("win_probability", "Win probability", 100.0, "pp"),
        ("trajectory_entropy_nats", "Trajectory entropy", 1.0, "nats"),
        ("expected_coverage", "Expected coverage", 100.0, "pp"),
        ("replayability", "Replayability", 100.0, "pp"),
    ]
    indexed = {
        (row["axis"], row["level"], row["metric"]): row for row in axis_rows
    }
    figure, axes = plt.subplots(2, 2, figsize=SLIDE_SIZE, dpi=SLIDE_DPI)
    apply_slide_style(figure)
    figure.subplots_adjust(
        left=0.18, right=0.96, bottom=0.12, top=0.80, hspace=0.44, wspace=0.25
    )
    y_positions = np.arange(len(row_definitions))
    labels = [label for _, _, label in row_definitions]
    for panel, (metric, title, scale, unit) in zip(
        axes.flat, metric_definitions, strict=True
    ):
        effects = np.array(
            [
                scale
                * float(indexed[(axis, level, metric)]["delta_vs_axis_neutral"])
                for axis, level, _ in row_definitions
            ]
        )
        colors = [AXIS_COLORS[axis] for axis, _, _ in row_definitions]
        panel.barh(y_positions, effects, color=colors, height=0.62, alpha=0.92)
        panel.axvline(0, color="#6C747C", linewidth=0.9)
        maximum = max(0.01, float(np.max(np.abs(effects))))
        panel.set_xlim(-maximum * 1.35, maximum * 1.35)
        panel.set_yticks(y_positions, labels if panel in axes[:, 0] else [""] * 6)
        panel.invert_yaxis()
        panel.set_title(title, loc="left", fontsize=12.5, fontweight="bold", color=INK)
        panel.set_xlabel(f"Difference from the neutral level ({unit})", fontsize=8.5)
        panel.grid(axis="x", color="#DDD8CE", linewidth=0.6, alpha=0.8)
        panel.spines[["top", "right", "left"]].set_visible(False)
        panel.spines["bottom"].set_color("#B7B2A9")
        panel.tick_params(axis="y", length=0, labelsize=8.7, colors=INK)
        panel.tick_params(axis="x", labelsize=8, colors=MUTED)
        for position, effect in zip(y_positions, effects, strict=True):
            horizontal = "left" if effect >= 0 else "right"
            offset = maximum * 0.035 if effect >= 0 else -maximum * 0.035
            panel.text(
                effect + offset,
                position,
                f"{effect:+.2f}",
                ha=horizontal,
                va="center",
                fontsize=8.2,
                color=INK,
            )

    legend = [
        Line2D([0], [0], color=color, lw=7, label=axis.capitalize())
        for axis, color in AXIS_COLORS.items()
    ]
    figure.legend(
        handles=legend,
        loc="upper right",
        bbox_to_anchor=(0.96, 0.875),
        frameon=False,
        ncol=3,
        fontsize=9,
    )
    figure.text(
        0.06,
        0.93,
        f"{book_id} — risk is the dominant behavioural axis",
        fontsize=21,
        fontweight="bold",
        color=INK,
    )
    figure.text(
        0.06,
        0.865,
        "Marginal effects average over the nine combinations of the other two axes.",
        fontsize=11.5,
        color=MUTED,
    )
    figure.text(
        0.06,
        0.035,
        "Percentage-point differences are used for probabilities. Each comparison "
        "uses the neutral level of the same axis as its baseline.",
        fontsize=8.5,
        color=MUTED,
    )
    return save_figure(figure, output_dir / "02_axis_effects")


def node_category(row: dict[str, str]) -> str:
    """Map graph metadata to a stable marker category."""
    if row["node_id"] == "1":
        return "start"
    if row["outcome"] == "death":
        return "death"
    if row["outcome"] == "win":
        return "win"
    if row["is_combat"] == "true":
        return "combat"
    return "ordinary"


def aggregate_edge_segments(
    edge_rows: list[dict[str, str]], positions: dict[str, tuple[float, float]]
) -> tuple[list[list[tuple[float, float]]], np.ndarray[Any, Any]]:
    """Aggregate parallel narrative edges and return neutral-flow line segments."""
    flows: dict[tuple[str, str], float] = defaultdict(float)
    for row in edge_rows:
        source = row["source_id"]
        target = row["target_id"]
        if source in positions and target in positions and source != target:
            flows[(source, target)] += float(row["neutral_expected_flow"])
    segments = [
        [positions[source], positions[target]] for source, target in flows
    ]
    values = np.array(list(flows.values()), dtype=float)
    return segments, values


def render_local_maps(
    book_id: str,
    node_rows: list[dict[str, str]],
    edge_rows: list[dict[str, str]],
    layout_rows: list[dict[str, str]],
    output_dir: Path,
) -> list[Path]:
    """Render the three most useful local indices on one longitudinal slide."""
    positions = {
        row["node_id"]: (float(row["x"]), float(row["y"])) for row in layout_rows
    }
    if set(positions) != {row["node_id"] for row in node_rows}:
        raise ValueError("Layout and presentation-node sets differ")
    segments, flows = aggregate_edge_segments(edge_rows, positions)
    maximum_flow = float(flows.max()) if len(flows) else 1.0
    definitions = [
        (
            "neutral_visit_probability",
            "A  Neutral visit probability — the common narrative backbone",
            "Blues",
            "Probability",
        ),
        (
            "neutral_death_contribution",
            "B  Mortality contribution — where neutral runs end",
            "Reds",
            "Probability",
        ),
        (
            "visit_probability_range",
            "C  Profile sensitivity — where player types diverge",
            "Purples",
            "Max − min probability",
        ),
    ]
    figure, axes = plt.subplots(3, 1, figsize=SLIDE_SIZE, dpi=SLIDE_DPI)
    apply_slide_style(figure)
    figure.subplots_adjust(left=0.035, right=0.92, bottom=0.08, top=0.83, hspace=0.36)
    markers = {
        "ordinary": ("o", 1.0),
        "combat": ("D", 1.15),
        "death": ("X", 1.35),
        "win": ("*", 1.65),
        "start": ("o", 1.5),
    }
    xs = np.array([positions[row["node_id"]][0] for row in node_rows])
    ys = np.array([positions[row["node_id"]][1] for row in node_rows])
    for axis, (field, title, cmap_name, colorbar_label) in zip(
        axes, definitions, strict=True
    ):
        line_widths = 0.12 + 1.05 * np.sqrt(flows / maximum_flow)
        axis.add_collection(
            LineCollection(
                segments,
                colors="#77828B",
                linewidths=line_widths,
                alpha=0.16,
                zorder=1,
            )
        )
        metric = np.array([float(row[field]) for row in node_rows])
        maximum = max(float(metric.max()), 1e-12)
        normalization = Normalize(vmin=0.0, vmax=maximum)
        color_map = matplotlib.colormaps[cmap_name]
        for category, (marker, multiplier) in markers.items():
            indices = [
                index
                for index, row in enumerate(node_rows)
                if node_category(row) == category
            ]
            if not indices:
                continue
            category_values = metric[indices]
            sizes = multiplier * (8 + 60 * np.sqrt(category_values / maximum))
            axis.scatter(
                xs[indices],
                ys[indices],
                s=sizes,
                c=category_values,
                cmap=color_map,
                norm=normalization,
                marker=marker,
                edgecolors="#38434C",
                linewidths=0.35 if category == "ordinary" else 0.7,
                zorder=3,
            )
        ranked = sorted(
            range(len(node_rows)),
            key=lambda index: (-metric[index], int(node_rows[index]["node_id"])),
        )[:5]
        label_indices = set(ranked)
        label_indices.update(
            index
            for index, row in enumerate(node_rows)
            if row["node_id"] in {"1", "350"}
        )
        for index in sorted(label_indices):
            if node_rows[index]["node_id"] == "1":
                text_offset = (0, -7)
                vertical_alignment = "top"
            else:
                text_offset = (0, 6)
                vertical_alignment = "bottom"
            axis.annotate(
                node_rows[index]["node_id"],
                (xs[index], ys[index]),
                xytext=text_offset,
                textcoords="offset points",
                ha="center",
                va=vertical_alignment,
                fontsize=6.7,
                color=INK,
                fontweight="bold",
                bbox={
                    "boxstyle": "round,pad=0.12",
                    "facecolor": BACKGROUND,
                    "edgecolor": "none",
                    "alpha": 0.82,
                },
                zorder=5,
            )
        colorbar = figure.colorbar(
            ScalarMappable(norm=normalization, cmap=color_map),
            ax=axis,
            fraction=0.012,
            pad=0.012,
            aspect=18,
        )
        colorbar.ax.tick_params(labelsize=7, colors=MUTED)
        colorbar.outline.set_visible(False)  # type: ignore[operator]
        colorbar.set_label(colorbar_label, fontsize=7.5, color=MUTED)
        axis.set_title(title, loc="left", fontsize=11.5, fontweight="bold", color=INK)
        axis.set_xlim(float(xs.min()) - 1.0, float(xs.max()) + 1.0)
        axis.set_ylim(float(ys.min()) - 0.7, float(ys.max()) + 0.7)
        axis.axis("off")

    marker_legend = [
        Line2D(
            [0],
            [0],
            marker=marker,
            linestyle="none",
            markerfacecolor="#A9B7C2",
            markeredgecolor="#38434C",
            markersize=7 * multiplier,
            label=category.capitalize(),
        )
        for category, (marker, multiplier) in markers.items()
    ]
    figure.legend(
        handles=marker_legend,
        loc="upper right",
        bbox_to_anchor=(0.96, 0.91),
        frameon=False,
        ncol=5,
        fontsize=8,
    )
    figure.text(
        0.035,
        0.945,
        f"{book_id} — three local views of the same narrative graph",
        fontsize=20,
        fontweight="bold",
        color=INK,
    )
    figure.text(
        0.035,
        0.885,
        "The Project Aon layout is fixed across panels; only the BoP node metric "
        "changes.",
        fontsize=10.8,
        color=MUTED,
    )
    figure.text(
        0.035,
        0.025,
        "Node size and colour encode the panel metric. Faint edges are scaled by "
        "neutral expected flow. Labels identify each panel’s five largest values plus "
        "§1 and §350.",
        fontsize=8.2,
        color=MUTED,
    )
    return save_figure(figure, output_dir / "03_local_index_maps")


def format_metric(value: float, kind: str) -> str:
    """Format a key number for direct use on a slide."""
    if kind == "percent":
        return f"{100 * value:.1f}%"
    if kind == "count":
        return f"{value:.1f}"
    return f"{value:.2f}"


def build_key_number_rows(
    global_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Select five complementary global measures for the compact table."""
    indexed = {row["metric"]: row for row in global_rows}
    definitions = [
        ("win_probability", "Win probability", "percent"),
        ("expected_transitions", "Expected transitions", "count"),
        ("trajectory_entropy_nats", "Trajectory entropy (nats)", "number"),
        ("expected_coverage", "Expected coverage", "percent"),
        ("replayability", "Replayability", "percent"),
    ]
    output = []
    for metric, label, kind in definitions:
        row = indexed[metric]
        minimum = float(row["minimum_value"])
        maximum = float(row["maximum_value"])
        output.append(
            {
                "measure": label,
                "neutral": format_metric(float(row["neutral_value"]), kind),
                "balanced_mean": format_metric(float(row["balanced_mean"]), kind),
                "observed_range": (
                    f"{format_metric(minimum, kind)}–{format_metric(maximum, kind)}"
                ),
            }
        )
    return output


def render_key_numbers(
    book_id: str, rows: list[dict[str, str]], output_dir: Path
) -> tuple[list[Path], Path]:
    """Render and export the compact five-number presentation table."""
    csv_path = output_dir / "04_key_numbers.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=KEY_NUMBER_FIELDS, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)

    figure, axis = plt.subplots(figsize=SLIDE_SIZE, dpi=SLIDE_DPI)
    apply_slide_style(figure)
    axis.axis("off")
    figure.text(
        0.06,
        0.91,
        f"{book_id} — five numbers that summarise the reading experience",
        fontsize=21,
        fontweight="bold",
        color=INK,
    )
    figure.text(
        0.06,
        0.845,
        "Neutral is a defined behavioural profile; the balanced mean weights all 27 "
        "configured profiles equally.",
        fontsize=11.2,
        color=MUTED,
    )
    cell_text = [
        [row["measure"], row["neutral"], row["balanced_mean"], row["observed_range"]]
        for row in rows
    ]
    table = axis.table(
        cellText=cell_text,
        colLabels=["Measure", "Neutral profile", "Balanced mean", "Observed range"],
        cellLoc="center",
        colLoc="center",
        bbox=Bbox.from_bounds(0.055, 0.20, 0.89, 0.55),
        colWidths=[0.37, 0.20, 0.20, 0.23],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    for (row_index, column_index), cell in table.get_celld().items():
        cell.set_edgecolor(BACKGROUND)
        cell.set_linewidth(3)
        if row_index == 0:
            cell.set_facecolor("#284B63")
            cell.get_text().set_color("white")
            cell.get_text().set_fontweight("bold")
        else:
            cell.set_facecolor("#E7E2D7" if row_index % 2 else "#F0ECE3")
            cell.get_text().set_color(INK)
            if column_index == 0:
                cell.get_text().set_horizontalalignment("left")
                cell.get_text().set_fontweight("bold")
    figure.text(
        0.06,
        0.09,
        "Ranges are descriptive minima and maxima over the complete factorial design, "
        "not confidence intervals.",
        fontsize=9,
        color=MUTED,
    )
    return save_figure(figure, output_dir / "04_key_numbers"), csv_path


def sha256(path: Path) -> str:
    """Return the SHA-256 digest of one generated artifact."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    """Generate the complete concise phase-4 presentation package."""
    parser = argparse.ArgumentParser(
        description="Build slide-ready figures and a table from phase-4.2 summaries."
    )
    parser.add_argument("--book", default=DEFAULT_BOOK_ID)
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--layout", type=Path)
    args = parser.parse_args()

    book_id = str(args.book)
    bop_root = args.input_dir or Path("data/processed/bop") / book_id
    presentation_root = bop_root / "presentation"
    output_dir = args.output_dir or Path("results/phase4") / book_id / "presentation"
    layout_path = args.layout or (
        Path("data/processed/graph") / book_id / "project_aon_layout.csv"
    )
    profile_rows = read_csv(bop_root / "profile_metrics.csv")
    global_rows = read_csv(presentation_root / "global_summary.csv")
    axis_rows = read_csv(presentation_root / "axis_summary.csv")
    node_rows = read_csv(presentation_root / "node_presentation_metrics.csv")
    edge_rows = read_csv(presentation_root / "edge_presentation_metrics.csv")
    ranking_rows = read_csv(presentation_root / "node_rankings.csv")
    layout_rows = read_csv(layout_path)
    if len(profile_rows) != 27 or len(node_rows) != len(layout_rows):
        raise ValueError("Phase-4.2 inputs or layout are incomplete")

    generated: list[Path] = []
    paths, correlation = render_profile_landscape(book_id, profile_rows, output_dir)
    generated.extend(paths)
    generated.extend(render_axis_effects(book_id, axis_rows, output_dir))
    generated.extend(
        render_local_maps(book_id, node_rows, edge_rows, layout_rows, output_dir)
    )
    key_rows = build_key_number_rows(global_rows)
    paths, table_csv = render_key_numbers(book_id, key_rows, output_dir)
    generated.extend(paths)
    generated.append(table_csv)

    top_sensitive = [
        row["node_id"]
        for row in ranking_rows
        if row["ranking"] == "profile_sensitivity"
    ][:3]
    top_mortality = [
        row["node_id"]
        for row in ranking_rows
        if row["ranking"] == "neutral_death_contribution"
    ][:3]
    manifest = {
        "schema_version": "1.0",
        "book_id": book_id,
        "slide_size_pixels": [1920, 1080],
        "language": "English",
        "source_tables": {
            "bop": str(bop_root),
            "presentation": str(presentation_root),
            "layout": str(layout_path),
        },
        "recommended_order": [
            {
                "figure": "01_profile_landscape",
                "message": "Profiles change both survival and narrative freedom.",
            },
            {
                "figure": "02_axis_effects",
                "message": "Risk is the dominant behavioural axis.",
            },
            {
                "figure": "03_local_index_maps",
                "message": "Importance, danger and profile sensitivity occur in "
                "different parts of the graph.",
            },
        ],
        "optional_table": "04_key_numbers",
        "descriptive_win_entropy_correlation": correlation,
        "top_profile_sensitive_nodes": top_sensitive,
        "top_neutral_mortality_nodes": top_mortality,
        "artifacts": {
            path.name: {"bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in generated
        },
    }
    manifest_path = output_dir / "presentation_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"Built {len(generated)} presentation artifacts for {book_id}")
    print(
        f"Landscape correlation={correlation:.3f}; "
        f"top sensitivity={','.join(top_sensitive)}; "
        f"top mortality={','.join(top_mortality)}"
    )
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()
