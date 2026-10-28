"""Shared settings and drawing helpers for the M2 sketches (Matplotlib).

Run each sketch from the repository root, for example:

    python sketches/q1.py

Each script writes a PNG next to itself (sketches/q1.png).
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import StrMethodFormatter

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUT = Path(__file__).resolve().parent
DATA_NOTE = "Data: Our World in Data, owid_energy (30 Sep 2026 version)"

TEXT = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e4e3df"
NOTE_FILL = "#f3f2ee"

# One line per source. Bioenergy and other renewables share one line:
# other renewables alone are about 0.3% of world generation.
# Fossil sources are warm colors, clean sources are cool colors; the same colors in Q1 and Q5.
# (name, color, columns that are added together)
SOURCES = [
    ("Coal", "#8b3a12", ["coal"]),
    ("Gas", "#eda100", ["gas"]),
    ("Oil", "#e34948", ["oil"]),
    ("Nuclear", "#4a3aa7", ["nuclear"]),
    ("Hydro", "#2a78d6", ["hydro"]),
    ("Wind", "#1baf7a", ["wind"]),
    ("Solar", "#56b4e9", ["solar"]),
    ("Bioenergy & other renewables", "#008300", ["bioenergy", "other_renewables_excluding_bioenergy"]),
]

# Fossil outcome, the same in Q5 and Q6. Color and shape, so groups don't rely on color alone.
FOSSIL_DOWN = {"color": "#2a78d6", "marker": "o"}
FOSSIL_UP = {"color": "#eb6834", "marker": "^"}
SHARE_NOT_UP = {"color": "#8f8e88", "marker": "s"}

plt.rcParams.update({"font.size": 10, "text.color": TEXT, "axes.labelcolor": TEXT,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.edgecolor": MUTED})


def read(name):
    return pd.read_csv(PROCESSED / name)


def style(ax, xlabel, ylabel, title=None):
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title, loc="left", fontsize=11, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def mix_table(rows, unit):
    """One column per line in SOURCES. unit is "share_pct" or "twh"."""
    rows = rows.sort_values("year").reset_index(drop=True)
    table = pd.DataFrame({"year": rows["year"]})
    for name, _, columns in SOURCES:
        table[name] = sum(rows[f"{c}_{unit}"] for c in columns)
    return table


def label_ends(ax, table):
    """Write each line's name just right of its last point, pushing labels apart so they don't overlap."""
    low, high = ax.get_ylim()
    gap = (high - low) * 0.045
    x = table["year"].iloc[-1]
    dx = (x - table["year"].iloc[0]) * 0.03
    ends = sorted(((table[name].iloc[-1], name, color) for name, color, _ in SOURCES))
    previous = None
    for y, name, color in ends:
        text = name.replace(" & ", " &\n")  # the long name takes two lines
        lines = text.count("\n") + 1
        if previous is None:
            label_y = y
        else:
            label_y = max(y, previous[0] + gap * (previous[1] + lines) / 2)
        previous = (label_y, lines)
        # A thin gray leader from the line's end, then a short dash in the line's color, then the name.
        ax.plot([x, x + dx * 0.6], [y, label_y], color=MUTED, linewidth=0.6, clip_on=False)
        ax.plot([x + dx * 0.6, x + dx * 1.3], [label_y, label_y], color=color, linewidth=2.5, clip_on=False)
        ax.text(x + dx * 1.5, label_y, text, va="center", fontsize=8.5, linespacing=0.9, clip_on=False)


def draw_mix(ax_share, ax_twh, rows, place, highlight=None):
    """The Q1 design: one line per source, share of generation (%) on the left, generation (TWh) on the right.
    Q5 reuses it for the selected country. highlight is the source under the mouse (the others fade)."""
    panels = [(ax_share, "share_pct", "Share of generation (%)", f"{place}: share of generation (%)"),
              (ax_twh, "twh", "Generation (TWh)", f"{place}: generation (TWh)")]
    tables = []
    for ax, unit, ylabel, title in panels:
        table = mix_table(rows, unit)
        for name, color, _ in SOURCES:
            faded = highlight is not None and name != highlight
            ax.plot(table["year"], table[name], color=color, alpha=0.4 if faded else 1,
                    linewidth=3.2 if name == highlight else 2)
        top = table.drop(columns="year").max().max()
        ax.set_ylim(0, top * 1.08)
        ax.set_xlim(table["year"].iloc[0], table["year"].iloc[-1])
        style(ax, "Year", ylabel, title)
        label_ends(ax, table)
        tables.append(table)
    ax_twh.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    return tables


def mark_point(ax, x, y):
    ax.plot([x], [y], "o", markersize=7, markerfacecolor="white", markeredgecolor=TEXT, markeredgewidth=1.6, zorder=5)


def tooltip(ax, x, y, text, offset=(10, -10)):
    """A tooltip box next to the mouse position, as in the Week 7 lab (10 px from the pointer)."""
    ax.annotate(text, xy=(x, y), xytext=offset, textcoords="offset points", va="top", fontsize=8.5,
                bbox={"boxstyle": "round,pad=0.4", "facecolor": "white", "edgecolor": MUTED, "linewidth": 0.8},
                zorder=6)


def interaction_note(fig, x, y, text):
    """A dashed box that explains an interaction. It is not part of the chart."""
    fig.text(x, y, "Interaction: " + text, fontsize=9.5, va="top",
             bbox={"boxstyle": "round,pad=0.5", "facecolor": NOTE_FILL, "edgecolor": MUTED,
                   "linestyle": "--", "linewidth": 0.8})


def control(fig, x, y, text, selected=False):
    """A button or a dropdown menu, drawn as a box. The selected one is filled."""
    return fig.text(x, y, text, fontsize=9, va="center", color="white" if selected else TEXT,
             bbox={"boxstyle": "round,pad=0.45", "facecolor": TEXT if selected else "white",
                   "edgecolor": TEXT if selected else MUTED, "linewidth": 0.9})


def footer(fig, questions):
    fig.text(0.01, 0.008, f"Sketch for {questions} by Yusuke Katsuki · {DATA_NOTE}", fontsize=8, color=MUTED)


def save(fig, name):
    fig.savefig(OUT / name, dpi=150, facecolor="white")
    print("wrote", OUT / name)
