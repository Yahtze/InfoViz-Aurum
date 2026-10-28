"""Q6 sketch: demand growth and the 2010 mix, countries that reduced fossil generation vs. those that did not.

Left: a scatterplot of demand growth (x) and the 2010 clean share (y), one dot per country.
Right: the 2010 mix of the selected pair as bars, with the pair's numbers below.
Six buttons choose a pair: two countries with similar demand growth but opposite fossil outcomes.
The static sketch shows Ireland - South Korea selected.
"""

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from common import FOSSIL_DOWN, FOSSIL_UP, MUTED, TEXT, control, footer, interaction_note, read, save, style

# The six pairs in the M2 sample (deliverables/m2.md): the closest demand growth, one country from each group.
# Each pair is (reduced fossil generation, did not).
PAIRS = [
    ("United States", "Libya"),
    ("Ireland", "South Korea"),
    ("Belarus", "Argentina"),
    ("Poland", "Cuba"),
    ("Greece", "Bosnia and Herzegovina"),
    ("Kenya", "Algeria"),
]
SELECTED = PAIRS[1]
GROUPS = [(True, "Reduced fossil generation", FOSSIL_DOWN), (False, "Did not reduce", FOSSIL_UP)]
MIX = [("Coal", "coal_share_pct_2010"), ("Gas", "gas_share_pct_2010"), ("Oil", "oil_share_pct_2010"),
       ("Clean", "clean_share_pct_2010")]

countries = read("comparison_2010_2024.csv")
# Countries with no fossil generation in either year had nothing to cut, so they are left out.
no_fossil = (countries["fossil_twh_2010"] == 0) & (countries["fossil_twh_2024"] == 0)
left_out = countries.loc[no_fossil, "country"].tolist()
countries = countries[~no_fossil]
pair = [countries[countries["country"] == name].iloc[0] for name in SELECTED]

fig = plt.figure(figsize=(14, 9))
grid = fig.add_gridspec(2, 2, left=0.07, right=0.97, top=0.72, bottom=0.14, width_ratios=[1.45, 1],
                        height_ratios=[1.2, 1], wspace=0.28, hspace=0.45)
ax_scatter = fig.add_subplot(grid[:, 0])
ax_bars = fig.add_subplot(grid[0, 1])
ax_table = fig.add_subplot(grid[1, 1])

# Scatterplot: every country, then the selected pair with rings, names and a dashed line between them.
for reduced, name, look in GROUPS:
    rows = countries[countries["fossil_reduced"] == reduced]
    ax_scatter.scatter(rows["demand_growth_pct"], rows["clean_share_pct_2010"], s=42, color=look["color"],
                       marker=look["marker"], edgecolors="white", linewidths=0.6, zorder=3,
                       label=f"{name} ({len(rows)})")
ax_scatter.plot([row["demand_growth_pct"] for row in pair], [row["clean_share_pct_2010"] for row in pair],
                color=TEXT, linestyle="--", linewidth=0.9, zorder=2)
for row, offset in zip(pair, [(95, -6), (95, 30)]):
    ax_scatter.scatter([row["demand_growth_pct"]], [row["clean_share_pct_2010"]], s=200, facecolors="none",
                       edgecolors=TEXT, linewidths=1.8, zorder=4)
    ax_scatter.annotate(row["country"], xy=(row["demand_growth_pct"], row["clean_share_pct_2010"]), xytext=offset,
                        textcoords="offset points", va="center", fontsize=9, fontweight="bold",
                        arrowprops={"arrowstyle": "-", "color": TEXT, "linewidth": 0.8, "shrinkB": 9})
ax_scatter.axvline(0, color=MUTED, linewidth=0.8, zorder=1)
ax_scatter.set_ylim(-3, 103)
style(ax_scatter, "Electricity demand growth, 2010–2024 (%)", "Clean share of generation in 2010 (%)",
      f"{len(countries)} countries")
ax_scatter.legend(loc="upper right", bbox_to_anchor=(1, 0.86), frameon=False, fontsize=9.5)
ax_scatter.text(0, -0.13, f"Left out: {', '.join(left_out)} (no fossil generation in 2010 or 2024).",
                transform=ax_scatter.transAxes, fontsize=8.5, color=MUTED)

# Bars: the pair's 2010 mix, one bar per country in its group's color (and hatching for "did not reduce").
for i, ((reduced, _, look), row) in enumerate(zip(GROUPS, pair)):
    y = [k + (i - 0.5) * 0.38 for k in range(len(MIX))]
    values = [row[column] for _, column in MIX]
    ax_bars.barh(y, values, height=0.36, color=look["color"], hatch="" if reduced else "///",
                 edgecolor="white", linewidth=0.5)
    for yy, value in zip(y, values):
        ax_bars.text(value + 1.2, yy, f"{value:.1f}%", va="center", fontsize=8.5)
ax_bars.set_yticks(range(len(MIX)), [name for name, _ in MIX])
ax_bars.invert_yaxis()
ax_bars.set_xlim(0, 100)
style(ax_bars, "Share of generation in 2010 (%)", "", f"2010 mix: {SELECTED[0]} vs. {SELECTED[1]}")
ax_bars.grid(axis="x", color="#e4e3df", linewidth=0.8)
ax_bars.grid(axis="y", visible=False)
ax_bars.legend([Patch(facecolor=FOSSIL_DOWN["color"]), Patch(facecolor=FOSSIL_UP["color"], hatch="///")],
               [f"{SELECTED[0]} (reduced)", f"{SELECTED[1]} (did not reduce)"], loc="lower right",
               frameon=False, fontsize=9)

# The pair's numbers: demand growth with generation growth and net imports next to it, and the fossil outcome.
cells = [
    ["Demand growth, 2010–24"] + [f"{row['demand_growth_pct']:+.1f}%" for row in pair],
    ["Generation growth, 2010–24"] + [f"{row['generation_growth_pct']:+.1f}%" for row in pair],
    ["Net imports, % of 2024 demand"] + [f"{row['net_imports_share_of_demand_pct_2024']:.1f}%" for row in pair],
    ["Fossil generation change, 2010–24"] + [f"{row['d_fossil_twh']:+.1f} TWh" for row in pair],
]
ax_table.axis("off")
table = ax_table.table(cellText=cells, colLabels=["", *SELECTED], loc="upper center", cellLoc="right",
                       colWidths=[0.58, 0.21, 0.21])
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1, 1.6)
for (r, c), cell in table.get_celld().items():
    cell.set_edgecolor("#e4e3df")
    if c == 0:
        cell.set_text_props(ha="left")
    if r == 0:
        cell.set_text_props(fontweight="bold")
ax_table.set_title("The selected pair", loc="left", fontsize=11, fontweight="bold")

fig.suptitle("Q6. How do demand growth and the 2010 mix differ between countries\n"
             "that reduced fossil generation and those that did not?",
             x=0.07, y=0.985, ha="left", fontsize=13, fontweight="bold")
interaction_note(fig, 0.07, 0.9,
                 "click a pair button; both countries are highlighted on the scatterplot, and the bars and the table "
                 "show their 2010 mix\nand numbers. Each pair has similar demand growth but opposite fossil outcomes. "
                 f"Shown: {SELECTED[0]} – {SELECTED[1]}.")
# Pair buttons in one row, each placed after the previous one's measured width.
fig.text(0.07, 0.8, "Pairs:", fontsize=9.5, va="center", fontweight="bold")
x = 0.115
renderer = fig.canvas.get_renderer()
for reduced_country, other in PAIRS:
    button = control(fig, x, 0.8, f"{reduced_country} – {other}", selected=(reduced_country, other) == SELECTED)
    x += button.get_window_extent(renderer).width / fig.bbox.width + 0.018
footer(fig, "Q6")
save(fig, "q6.png")
