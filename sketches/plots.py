"""Six static EDA views. Selection and calculation live in data.py."""

import textwrap

import matplotlib

matplotlib.use("Agg")  # Save files without a display server.
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.patches import Patch, PathPatch
import numpy as np
import pandas as pd

from .data import extremes, source_changes
from .geography import load_country_paths
from .settings import ROOT, Settings

UP = "#247F78"
DOWN = "#B8654A"
MISSING = "#DEDEDE"


def set_style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.edgecolor": "#B9B9B9",
        "axes.labelcolor": "#333333",
        "xtick.color": "#555555",
        "ytick.color": "#333333",
        "svg.fonttype": "none",
        "savefig.facecolor": "white",
    })


def finish(fig, title, note, *, plot_top=0.94):
    fig.suptitle(title, x=0.02, y=0.985, ha="left", fontsize=16, fontweight="bold")
    fig.text(
        0.02, 0.015, textwrap.fill(note, width=150),
        ha="left", va="bottom", fontsize=8, color="#555555",
    )
    fig.tight_layout(rect=(0.01, 0.10, 0.99, plot_top))
    return fig


def x_grid(ax):
    ax.set_axisbelow(True)
    ax.grid(axis="x", color="#EAEAEA", linewidth=0.8)
    ax.tick_params(axis="y", length=0)


def selection_note(settings, count):
    return (
        f"{count} countries with endpoint data and ≥ {settings.min_generation_twh:g} TWh "
        f"generation in {settings.end_year}. Up to {settings.top_n} per tail; "
        "cutoff ties use country name. Clean = renewables + nuclear."
    )


def share_map(snapshot, settings):
    fig, ax = plt.subplots(figsize=(14, 8))
    cmap, norm = plt.get_cmap("YlGnBu"), Normalize(0, 100)
    values = snapshot.dropna(subset=["iso_numeric"]).set_index("iso_numeric")["clean_share_pct"]
    for numeric, path in load_country_paths(ROOT / "data/raw/world-atlas-2.0.2-countries-50m.json"):
        if numeric == "010":  # Antarctica is outside the view and has no study data.
            continue
        value = values.get(numeric, np.nan)
        ax.add_patch(PathPatch(
            path, facecolor=MISSING if pd.isna(value) else cmap(norm(value)),
            edgecolor="white", linewidth=0.25,
        ))
    ax.set(xlim=(-180, 180), ylim=(-60, 85), aspect="equal")
    ax.set_axis_off()
    fig.colorbar(
        ScalarMappable(norm=norm, cmap=cmap), ax=ax, orientation="horizontal",
        fraction=0.04, pad=0.04, label="Clean Share of Electricity Generation (%)",
    )
    ax.legend(handles=[Patch(facecolor=MISSING, label="No matched data")], loc="lower left", frameon=False)
    unknown = int(snapshot["clean_share_pct"].isna().sum())
    off_map = snapshot.loc[~snapshot["on_map"], "country"].sort_values().tolist()
    return finish(
        fig, f"Where Is Electricity Cleaner? · {settings.snapshot_year}",
        f"Source: OWID, pinned data. {len(snapshot)} countries and territories; "
        f"{unknown} have no clean-share value. Clean = renewables + nuclear. "
        "Equirectangular map; Antarctica omitted. No generation threshold. "
        f"Not drawable on this map ({len(off_map)}): {', '.join(off_map) or 'none'}. "
        "Use the ranking and exported table for these places.",
    )


def share_ranking(snapshot, settings):
    high, low = extremes(snapshot, "clean_share_pct", settings.top_n)
    height = max(6.5, max(len(high), len(low)) * 0.35 + 2.5)
    fig, axes = plt.subplots(1, 2, figsize=(14, height))
    for ax, rows, title, color in zip(
        axes, (high, low), ("Highest Shares", "Lowest Shares"), (UP, DOWN),
    ):
        if rows.empty:
            ax.text(0.5, 0.5, "No remaining countries", transform=ax.transAxes, ha="center")
        else:
            bars = ax.barh(rows["country"], rows["clean_share_pct"], color=color, height=0.65)
            ax.bar_label(bars, labels=[f"{v:.1f}%" for v in rows["clean_share_pct"]], padding=4, fontsize=9)
            ax.invert_yaxis()
        ax.set(title=title, xlabel="Clean Share (%)", xlim=(0, 116), xticks=[0, 25, 50, 75, 100])
        x_grid(ax)
    return finish(
        fig, f"Which Countries Have the Highest and Lowest Clean Shares? · {settings.snapshot_year}",
        f"Source: OWID. All {len(snapshot)} countries and territories; no generation threshold. "
        f"Up to {settings.top_n} countries per panel. "
        f"{snapshot['clean_share_pct'].isna().sum()} unknown shares are excluded, not treated as zero. "
        "Cutoff ties use country name; the two panels do not repeat countries. Clean includes nuclear.",
    )


def change_bars(comparison, settings):
    high, low = extremes(comparison, "d_clean_share_pp", settings.top_n, changes=True)
    height = max(6.5, max(len(high), len(low)) * 0.35 + 2.5)
    fig, axes = plt.subplots(1, 2, figsize=(14, height))
    span = max(comparison["d_clean_share_pp"].abs().max() * 1.25, 1)
    for ax, rows, title, color in zip(
        axes, (high, low), ("Largest Increases", "Largest Decreases"), (UP, DOWN),
    ):
        if rows.empty:
            ax.text(0.5, 0.5, "No countries in this direction", transform=ax.transAxes, ha="center")
        else:
            bars = ax.barh(rows["country"], rows["d_clean_share_pp"], color=color, height=0.65)
            ax.bar_label(
                bars, labels=[f"{v:+.1f}" for v in rows["d_clean_share_pp"]], padding=4, fontsize=9,
            )
            ax.invert_yaxis()
        ax.axvline(0, color="#777777", linewidth=0.8)
        ax.set(title=title, xlabel="Change in Clean Share (Percentage Points)", xlim=(-span, span))
        x_grid(ax)
    return finish(
        fig, f"Who Gained or Lost the Most Clean Share? · {settings.start_year}–{settings.end_year}",
        "Source: OWID. " + selection_note(settings, len(comparison))
        + " Only positive gains and negative losses appear.",
    )


def endpoint_comparison(comparison, settings):
    high, low = extremes(comparison, "d_clean_share_pp", settings.top_n, changes=True)
    height = max(6.5, max(len(high), len(low)) * 0.35 + 2.5)
    fig, axes = plt.subplots(1, 2, figsize=(14, height))
    for ax, rows, title, color in zip(
        axes, (high, low), ("Largest Increases", "Largest Decreases"), (UP, DOWN),
    ):
        y = np.arange(len(rows))
        if rows.empty:
            ax.text(0.5, 0.5, "No countries in this direction", transform=ax.transAxes, ha="center")
        else:
            ax.hlines(y, rows["clean_share_pct_start"], rows["clean_share_pct_end"], color=color, linewidth=2)
            ax.scatter(
                rows["clean_share_pct_start"], y, marker="o", s=42,
                facecolors="white", edgecolors=color, zorder=3, label=str(settings.start_year),
            )
            ax.scatter(
                rows["clean_share_pct_end"], y, marker="D", s=36,
                color=color, zorder=4, label=str(settings.end_year),
            )
            ax.set_yticks(y, rows["country"])
            ax.invert_yaxis()
            ax.legend(loc="best", frameon=False, fontsize=8)
        ax.set(title=title, xlabel="Clean Share (%)", xlim=(-3, 103), xticks=[0, 25, 50, 75, 100])
        x_grid(ax)
    return finish(
        fig, f"Where Did Those Countries Start and Finish? · {settings.start_year}–{settings.end_year}",
        "Source: OWID. " + selection_note(settings, len(comparison))
        + " Open circle = start; filled diamond = end. Lines connect endpoints, not annual trends.",
    )


def source_breakdown(comparison, settings, unit):
    selected, _ = extremes(comparison, "d_clean_share_pp", settings.top_n, changes=True)
    table = source_changes(selected, settings, unit)
    fig, ax = plt.subplots(figsize=(13, max(6.5, len(table) * 0.4 + 2.5)))
    if table.empty:
        ax.text(0.5, 0.5, "No countries increased their clean share", transform=ax.transAxes, ha="center")
    else:
        positive, negative = np.zeros(len(table)), np.zeros(len(table))
        y = np.arange(len(table))
        for group in settings.groups:
            values = table[group.label].to_numpy()
            left = np.where(values >= 0, positive, negative)
            ax.barh(y, values, left=left, color=group.color, height=0.65, label=group.label)
            positive += np.maximum(values, 0)
            negative += np.minimum(values, 0)
        ax.scatter(table["total"], y, color="#222222", marker="D", s=26, zorder=5, label="Net clean change")
        ax.set_yticks(y, table["country"])
        ax.invert_yaxis()
        ax.legend(loc="lower left", bbox_to_anchor=(0, 1.02), ncol=min(4, len(settings.groups) + 1), frameon=False, fontsize=9)
        # Zero-width segments at an extreme create sticky bar edges. Set explicit
        # padding so regrouping cannot clip the net marker at that extreme.
        lower = min(float(negative.min()), float(table["total"].min()), 0)
        upper = max(float(positive.max()), float(table["total"].max()), 0)
        padding = max(upper - lower, 1) * 0.12
        ax.set_xlim(lower - padding, upper + padding)
    ax.axvline(0, color="#777777", linewidth=0.8)
    ax.set_xlabel(
        "Change in Share of Total Electricity Generation (Percentage Points)"
        if unit == "pp" else "Change in Electricity Generation (TWh)",
    )
    x_grid(ax)
    perspective = "Which Sources Changed the Mix?" if unit == "pp" else "Which Sources Changed Actual Output?"
    note = (
        "Source: OWID. " + selection_note(settings, len(comparison))
        + " Both source views use the largest clean-share gainers, ranked by percentage-point gain. "
        "Negative segments show declining sources; diamonds show the net sum. "
        + (
            "Share changes are an accounting breakdown, not proof of cause."
            if unit == "pp" else
            "TWh changes need not follow share changes; growing demand can raise output even as a share falls."
        )
    )
    return finish(
        fig, f"{perspective} · {settings.start_year}–{settings.end_year}",
        note,
        plot_top=0.86 if len(settings.groups) > 3 else 0.90,
    )
