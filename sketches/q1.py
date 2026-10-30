"""Q1 sketch: the global electricity mix, 2000-2024, in shares and in TWh.

Two line charts side by side, one line per source.
The static sketch shows the hover state: the mouse is on the coal line at 2010.
"""

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from common import SOURCES, draw_mix, footer, interaction_note, mark_point, read, save, tooltip

HOVER_SOURCE, HOVER_YEAR = "Coal", 2010

world = read("country_year.csv")
world = world[world["country"] == "World"]

fig, (ax_share, ax_twh) = plt.subplots(1, 2, figsize=(14, 6.2))
fig.subplots_adjust(left=0.06, right=0.9, top=0.81, bottom=0.21, wspace=0.42)
share, twh = draw_mix(ax_share, ax_twh, world, "World", highlight=HOVER_SOURCE)

# Hover state: the same source is highlighted in both charts; the tooltip shows both values for that year.
share_value = share.loc[share["year"] == HOVER_YEAR, HOVER_SOURCE].iloc[0]
twh_value = twh.loc[twh["year"] == HOVER_YEAR, HOVER_SOURCE].iloc[0]
mark_point(ax_share, HOVER_YEAR, share_value)
mark_point(ax_twh, HOVER_YEAR, twh_value)
tooltip(ax_share, HOVER_YEAR, share_value, f"{HOVER_SOURCE}, {HOVER_YEAR}\n{share_value:.1f}% of generation\n{twh_value:,.1f} TWh")

fig.suptitle("Q1. How has the global electricity mix changed from 2000 to 2024, in shares and in TWh?",
             x=0.06, y=0.975, ha="left", fontsize=13, fontweight="bold")
interaction_note(fig, 0.06, 0.915,
                 "hover a line to highlight that source in both charts (the other lines fade); "
                 "a tooltip shows its share and TWh for that year. Shown: the mouse on Coal at 2010.")

handles = [Line2D([], [], color=color, linewidth=2) for _, color, _ in SOURCES]
fig.legend(handles, [name for name, _, _ in SOURCES], loc="lower center", ncol=8, frameon=False,
           bbox_to_anchor=(0.5, 0.04), title="Fossil (warm colors): coal, gas, oil · Clean (cool colors): the other five",
           title_fontsize=9, fontsize=9)
footer(fig, "Q1")
save(fig, "q1.png")
