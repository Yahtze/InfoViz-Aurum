"""Q5 sketch: change in clean share vs. change in fossil generation, 2010-2024 (108 countries).

Top: the same scatterplot twice, all countries (overview) and the band within +-60 TWh (enlarged), both linear.
Bottom: the selected country's mix over time, the same two charts as Q1, 2010-2024.
The static sketch shows South Korea selected.
"""

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import StrMethodFormatter

from common import (FOSSIL_DOWN, FOSSIL_UP, GRID, MUTED, NOTE_FILL, SHARE_NOT_UP, TEXT, control, draw_mix, footer,
                    interaction_note, read, save, style)

SELECTED = "South Korea"
ZOOM_TWH = 60
LABELED = ["China", "India", "United States"]  # the countries that stretch the overview
OUTCOMES = [
    ("share_up_fossil_down", "Clean share up, fossil down", FOSSIL_DOWN),
    ("share_up_fossil_up", "Clean share up, fossil up", FOSSIL_UP),
    ("share_not_up", "Clean share not up", SHARE_NOT_UP),
]

countries = read("comparison_2010_2024.csv")
selected_mix = read("country_year.csv")
selected_mix = selected_mix[(selected_mix["country"] == SELECTED) & (selected_mix["year"] >= 2010)]
selected = countries[countries["country"] == SELECTED].iloc[0]
in_zoom = countries[countries["d_fossil_twh"].abs() <= ZOOM_TWH]

fig = plt.figure(figsize=(14, 13))
top = fig.add_gridspec(1, 2, left=0.07, right=0.9, top=0.8, bottom=0.5, wspace=0.42)
bottom = fig.add_gridspec(1, 2, left=0.07, right=0.9, top=0.36, bottom=0.07, wspace=0.42)
ax_all, ax_zoom = fig.add_subplot(top[0, 0]), fig.add_subplot(top[0, 1])
ax_share, ax_twh = fig.add_subplot(bottom[0, 0]), fig.add_subplot(bottom[0, 1])

for ax in (ax_all, ax_zoom):
    for outcome, _, look in OUTCOMES:
        rows = countries[countries["outcome"] == outcome]
        ax.scatter(rows["d_clean_share_pp"], rows["d_fossil_twh"], s=40, color=look["color"], marker=look["marker"],
                   edgecolors="white", linewidths=0.6, zorder=3)
    ax.axhline(0, color=MUTED, linewidth=0.8, zorder=2)
    ax.axvline(0, color=MUTED, linewidth=0.8, zorder=2)
    ax.set_xlim(-35, 60)  # the same x scale in both
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    # The selected country: a ring and its name.
    ax.scatter([selected["d_clean_share_pp"]], [selected["d_fossil_twh"]], s=190, facecolors="none",
               edgecolors=TEXT, linewidths=1.8, zorder=4)

xlabel = "Change in clean share, 2010–2024 (percentage points)"
ylabel = "Change in fossil generation, 2010–2024 (TWh)"
style(ax_all, xlabel, ylabel, "All 108 countries")
style(ax_zoom, xlabel, ylabel, f"Enlarged: the {len(in_zoom)} countries within ±{ZOOM_TWH} TWh")

# Overview: mark the enlarged band and name the countries that stretch the axis.
ax_all.set_ylim(-450, 3100)
ax_all.axhspan(-ZOOM_TWH, ZOOM_TWH, facecolor=GRID, edgecolor=MUTED, linestyle="--", linewidth=0.8, zorder=1)
ax_all.annotate(f"±{ZOOM_TWH} TWh band,\nenlarged at right", xy=(50, ZOOM_TWH), xytext=(38, 450),
                fontsize=8.5, color=MUTED, arrowprops={"arrowstyle": "->", "color": MUTED})
for name in LABELED:
    row = countries[countries["country"] == name].iloc[0]
    ax_all.annotate(f"{name} ({row['d_fossil_twh']:+,.0f} TWh)", xy=(row["d_clean_share_pp"], row["d_fossil_twh"]),
                    xytext=(8, 0), textcoords="offset points", va="center", fontsize=8.5)
ax_all.annotate(SELECTED, xy=(selected["d_clean_share_pp"], selected["d_fossil_twh"]), xytext=(30, 45),
                textcoords="offset points", fontsize=8.5, fontweight="bold",
                arrowprops={"arrowstyle": "-", "color": TEXT, "linewidth": 0.8})

# Enlarged view: the three groups by quadrant, the selected country, and the countries that sit on one point.
ax_zoom.set_ylim(-ZOOM_TWH * 1.08, ZOOM_TWH * 1.08)
for x, y, text, align in [(58, 56, "share up, fossil up", "right"), (58, -56, "share up, fossil down", "right"),
                          (-33, 56, "share not up", "left")]:
    ax_zoom.text(x, y, text, ha=align, va="top" if y > 0 else "bottom", fontsize=8.5, color=MUTED, style="italic")
ax_zoom.annotate(f"{SELECTED} (selected)\n{selected['d_clean_share_pp']:+.1f} pp, {selected['d_fossil_twh']:+.1f} TWh",
                 xy=(selected["d_clean_share_pp"], selected["d_fossil_twh"]), xytext=(25, 12),
                 textcoords="offset points", fontsize=8.5, fontweight="bold",
                 arrowprops={"arrowstyle": "-", "color": TEXT, "linewidth": 0.8})
ax_zoom.annotate("Paraguay, Iceland, Bhutan and Nepal\nall sit at (0, 0): pick them from the menu",
                 xy=(0, 0), xytext=(-33, -50), va="top", fontsize=8.5, color=MUTED,
                 arrowprops={"arrowstyle": "->", "color": MUTED})

# The selected country's mix: the Q1 design, 2010-2024.
draw_mix(ax_share, ax_twh, selected_mix, SELECTED)

fig.suptitle("Q5. Which countries raised their clean share while cutting fossil generation,\n"
             "and which raised it but still generated more fossil electricity?",
             x=0.07, y=0.985, ha="left", fontsize=13, fontweight="bold")
interaction_note(fig, 0.07, 0.905,
                 "click a dot (in either scatterplot) or choose a country from the menu;\n"
                 f"the two charts at the bottom show that country's mix, 2010–2024 (the same charts as Q1). "
                 f"Shown: {SELECTED} selected.")
handles = [Line2D([], [], linestyle="none", marker=look["marker"], markersize=8, color=look["color"])
           for _, _, look in OUTCOMES]
labels = [f"{name} ({(countries['outcome'] == outcome).sum()})" for outcome, name, _ in OUTCOMES]
fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.07, 0.86), ncol=3, frameon=False, fontsize=9.5)

fig.text(0.07, 0.415, "Selected country", fontsize=12, fontweight="bold", va="center")
control(fig, 0.2, 0.415, f"Country:  {SELECTED}  ▾")
footer(fig, "Q5")
save(fig, "q5.png")
