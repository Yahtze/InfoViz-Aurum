"""Static sketches for Q1, Q5 and Q6. Selection and calculation live in q156_data.py.

Unlike the Q2-Q4 views, these sketch the planned interactive design: a dashed
"Planned Interaction" box describes what the D3 version will do, and the static
image shows one state of it (a hover, a selected country, a selected pair).
"""

import textwrap

import matplotlib

matplotlib.use("Agg")  # Save files without a display server.
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator, StrMethodFormatter

from .plots import DOWN, UP
from .q156_data import FOSSIL_SOURCES, OUTCOME_LABELS, mix_table, window

INK = "#333333"
MUTED = "#666666"
GRID = "#EAEAEA"
NOTE_FILL = "#F4F4F4"
# Fossil lines are dashed; clean lines are solid and use the config group colors (as in Q4).
FOSSIL_COLORS = {"Coal": "#2B2B2B", "Gas": "#A6761D", "Oil": "#E8636F"}
# Outcome by color and shape, so categories do not rely on color alone.
OUTCOME_STYLE = {
    key: (OUTCOME_LABELS[key], color, marker) for key, color, marker in (
        ("share_up_fossil_down", UP, "o"),
        ("share_up_fossil_up", DOWN, "^"),
        ("share_up_fossil_flat", "#5F5F5F", "D"),
        ("share_not_up", "#A3A3A3", "s"),
    )
}
GROUP_STYLE = {
    True: ("Fossil Generation Fell", UP, "o", ""),
    False: ("Fossil Generation Did Not Fall", DOWN, "^", "///"),
}


def frame(fig, title, note):
    """Title and bottom data note, placed like plots.finish (these layouts are set by hand)."""
    fig.suptitle(title, x=0.02, y=0.985, ha="left", fontsize=16, fontweight="bold")
    fig.text(0.02, 0.012, textwrap.fill(note, width=165), ha="left", va="bottom", fontsize=8, color="#555555")
    return fig


def interaction(fig, x, y, text):
    fig.text(x, y, "Planned Interaction: " + text, fontsize=9.5, va="top", color=INK,
             bbox={"boxstyle": "round,pad=0.5", "facecolor": NOTE_FILL, "edgecolor": "#777777",
                   "linestyle": "--", "linewidth": 0.8})


def control(fig, x, y, text, selected=False):
    """A button or a menu, drawn as a box. The selected one is filled."""
    return fig.text(x, y, text, fontsize=9, va="center", color="white" if selected else INK,
                    bbox={"boxstyle": "round,pad=0.45", "facecolor": INK if selected else "white",
                          "edgecolor": INK if selected else "#999999", "linewidth": 0.9})


def style(ax, xlabel, ylabel, title=""):
    ax.set_title(title, loc="left", fontsize=11, fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_axisbelow(True)
    ax.grid(color=GRID, linewidth=0.8)
    ax.spines["left"].set_visible(True)


def label_extremes(ax, rows, x, y, text):
    """Label a few points beside them; a label that would sit on an earlier one moves down."""
    left, right = ax.get_xlim()
    low, high = ax.get_ylim()
    placed = []
    for _, row in rows.sort_values(y, ascending=False).iterrows():
        on_right = row[x] < left + (right - left) * 0.7
        shift = -11 * sum(
            abs(px - row[x]) < (right - left) * 0.3 and abs(py - row[y]) < (high - low) * 0.06 for px, py in placed
        )
        placed.append((row[x], row[y]))
        ax.annotate(text(row), xy=(row[x], row[y]), xytext=(7 if on_right else -7, shift),
                    textcoords="offset points", ha="left" if on_right else "right", va="center",
                    fontsize=8.5, color=INK,
                    arrowprops={"arrowstyle": "-", "color": MUTED, "linewidth": 0.6} if shift else None)


def line_styles(settings):
    """(label, color, linestyle) for every line, fossil first."""
    lines = [(name.title(), FOSSIL_COLORS[name.title()], "--") for name in FOSSIL_SOURCES]
    return lines + [(group.label, group.color, "-") for group in settings.groups]


def label_ends(ax, table, lines):
    """Name each line just right of its last point, pushed apart so names do not overlap."""
    low, high = ax.get_ylim()
    gap = (high - low) * 0.05
    x = table["year"].iloc[-1]
    dx = (x - table["year"].iloc[0]) * 0.03
    ends = sorted(
        (table[label].iloc[-1], label, color) for label, color, _ in lines if table[label].notna().iloc[-1]
    )
    previous = None
    for y, label, color in ends:
        label_y = y if previous is None else max(y, previous + gap)
        previous = label_y
        ax.plot([x, x + dx * 0.6], [y, label_y], color=MUTED, linewidth=0.6, clip_on=False)
        ax.plot([x + dx * 0.6, x + dx * 1.3], [label_y, label_y], color=color, linewidth=2.5, clip_on=False)
        ax.text(x + dx * 1.5, label_y, label.title(), va="center", fontsize=8.5, color=INK, clip_on=False)


def draw_mix(ax_share, ax_twh, rows, settings, place, highlight=None):
    """The Q1 design: one line per source, share (%) on the left and TWh on the right.
    Q5 reuses it for the selected country. highlight is the hovered source; the others fade."""
    lines = line_styles(settings)
    tables = []
    for ax, unit, label in ((ax_share, "share_pct", "Share of Generation (%)"),
                            (ax_twh, "twh", "Generation (TWh)")):
        table = mix_table(rows, settings, unit)
        for name, color, linestyle in lines:
            faded = highlight is not None and name != highlight
            ax.plot(table["year"], table[name], color=color, linestyle=linestyle,
                    alpha=0.35 if faded else 1, linewidth=3 if name == highlight else 2)
        top = table.drop(columns="year").max().max()
        ax.set_ylim(0, top * 1.08 if top > 0 else 1)
        ax.set_xlim(table["year"].iloc[0], table["year"].iloc[-1])
        ax.xaxis.set_major_locator(MaxNLocator(nbins=7, integer=True, steps=[1, 2, 4, 5, 10]))
        style(ax, "Year", label, f"{place}: {label}")
        label_ends(ax, table, lines)
        tables.append(table)
    ax_twh.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    return tables


def mix_legend(fig, settings, y):
    handles = [Line2D([], [], color=color, linestyle=linestyle, linewidth=2) for _, color, linestyle in line_styles(settings)]
    labels = [label.title() for label, _, _ in line_styles(settings)]
    fig.legend(handles, labels, loc="lower center", ncol=len(handles), frameon=False, bbox_to_anchor=(0.5, y),
               title="Fossil: Dashed · Clean: Solid (Colors as in Q4)", title_fontsize=9, fontsize=9)


def world_mix(world, settings):
    """Q1: the world's electricity mix, in shares and in TWh."""
    rows = window(world, settings)
    s, e = settings.start_year, settings.end_year
    hover_source, hover_year = "Coal", 2010 if s < 2010 < e else s
    fig, (ax_share, ax_twh) = plt.subplots(1, 2, figsize=(14, 6.8))
    fig.subplots_adjust(left=0.06, right=0.9, top=0.8, bottom=0.25, wspace=0.42)
    share, twh = draw_mix(ax_share, ax_twh, rows, settings, "World", highlight=hover_source)
    share_value = share.loc[share["year"].eq(hover_year), hover_source].iloc[0]
    twh_value = twh.loc[twh["year"].eq(hover_year), hover_source].iloc[0]
    for ax, value in ((ax_share, share_value), (ax_twh, twh_value)):
        ax.plot([hover_year], [value], "o", markersize=8, markerfacecolor="white",
                markeredgecolor=INK, markeredgewidth=1.6, zorder=5)
    ax_share.annotate(
        f"{hover_source}, {hover_year}\n{share_value:.1f}% of Generation\n{twh_value:,.1f} TWh",
        xy=(hover_year, share_value), xytext=(12, -40), textcoords="offset points", va="top", fontsize=8.5,
        bbox={"boxstyle": "round,pad=0.4", "facecolor": "white", "edgecolor": "#999999", "linewidth": 0.8},
        zorder=6,
    )
    interaction(fig, 0.06, 0.915,
                "hover a line to highlight that source in both charts (the other lines fade); a tooltip shows "
                f"its share and TWh for that year.\nShown: the mouse on {hover_source} at {hover_year}.")
    mix_legend(fig, settings, 0.06)
    return frame(
        fig, f"Domestic Electricity Generation: World Mix by Source · {s}–{e}",
        f"Source: OWID, pinned data. World row, {s}–{e}. Shares are of domestic generation; "
        "the eight lines add up to total generation and to 100%. Clean = renewables + nuclear; "
        "Other Clean = bioenergy + other renewables excluding bioenergy.",
    )


def fossil_outcome_scatter(table, countries, settings, example):
    """Q5: change in clean share vs. change in fossil generation, overview and enlarged band,
    with the selected country's mix below."""
    s, e, zoom = settings.start_year, settings.end_year, settings.q5_zoom_twh
    in_zoom = table.loc[table["d_fossil_twh"].abs().le(zoom)]
    present = [key for key in OUTCOME_STYLE if table["outcome"].eq(key).any()]

    fig = plt.figure(figsize=(14, 13))
    top = fig.add_gridspec(1, 2, left=0.07, right=0.9, top=0.83, bottom=0.55, wspace=0.42)
    bottom = fig.add_gridspec(1, 2, left=0.07, right=0.9, top=0.41, bottom=0.11, wspace=0.42)
    ax_all, ax_zoom = fig.add_subplot(top[0, 0]), fig.add_subplot(top[0, 1])
    ax_share, ax_twh = fig.add_subplot(bottom[0, 0]), fig.add_subplot(bottom[0, 1])

    x = table["d_clean_share_pp"]
    span = (x.min() - 5, x.max() + 5)
    xlabel = "Change in Clean Share (Percentage Points)"
    ylabel = "Change in Fossil Generation (TWh)"
    for ax, shown_rows in ((ax_all, table), (ax_zoom, in_zoom)):
        for key in present:
            label, color, marker = OUTCOME_STYLE[key]
            rows = shown_rows.loc[shown_rows["outcome"].eq(key)]
            ax.scatter(rows["d_clean_share_pp"], rows["d_fossil_twh"], s=40, color=color, marker=marker,
                       edgecolors="white", linewidths=0.6, zorder=3)
        ax.axhline(0, color="#777777", linewidth=0.8, zorder=2)
        ax.axvline(0, color="#777777", linewidth=0.8, zorder=2)
        ax.set_xlim(*span)  # The same x scale in both.
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
        if example is not None:
            ax.scatter([example["d_clean_share_pp"]], [example["d_fossil_twh"]], s=190, facecolors="none",
                       edgecolors=INK, linewidths=1.8, zorder=4)
    style(ax_all, xlabel, ylabel, f"All {len(table)} Countries")
    style(ax_zoom, xlabel, ylabel, f"Enlarged: {len(in_zoom)} Countries Within ±{zoom:g} TWh")

    y = table["d_fossil_twh"]
    pad = (y.max() - y.min()) * 0.06
    ax_all.set_ylim(min(y.min(), -zoom) - pad, max(y.max(), zoom) + pad)
    ax_all.axhspan(-zoom, zoom, facecolor="#F0F0F0", edgecolor="#999999", linestyle="--", linewidth=0.8, zorder=1)
    ax_all.annotate(f"±{zoom:g} TWh Band,\nEnlarged at Right", xy=(span[1] - 8, zoom), xytext=(0.62, 0.35),
                    textcoords="axes fraction", fontsize=8.5, color=MUTED,
                    arrowprops={"arrowstyle": "->", "color": MUTED})
    label_extremes(ax_all, table.loc[y.abs().nlargest(3).index], "d_clean_share_pp", "d_fossil_twh",
                   lambda row: f"{row['country']} ({row['d_fossil_twh']:+,.0f} TWh)")

    ax_zoom.set_ylim(-zoom * 1.08, zoom * 1.08)
    for xx, yy, text, align in ((span[1] - 2, zoom, "Share Up, Fossil Up", "right"),
                                (span[1] - 2, -zoom, "Share Up, Fossil Down", "right"),
                                (span[0] + 2, zoom, "Share Not Up", "left")):
        ax_zoom.text(xx, yy, text, ha=align, va="top" if yy > 0 else "bottom", fontsize=8.5,
                     color=MUTED, style="italic")
    stacked = table.loc[x.abs().lt(0.05) & y.abs().lt(0.05), "country"].sort_values().tolist()
    if stacked:
        ax_zoom.annotate(f"{len(stacked)} countries sit at (0, 0) (pick them from the menu):\n" + textwrap.fill(", ".join(stacked), 48),
                         xy=(0, 0), xytext=(0.03, 0.12), textcoords="axes fraction", fontsize=8.5, color=MUTED,
                         arrowprops={"arrowstyle": "->", "color": MUTED})

    if example is None:
        for ax in (ax_share, ax_twh):
            ax.axis("off")
        ax_share.text(0, 0.5, "No country fits the example rule for these settings.", fontsize=10, color=MUTED)
        shown = "no country selected"
    else:
        name = example["country"]
        ax_all.annotate(name, xy=(example["d_clean_share_pp"], example["d_fossil_twh"]), xytext=(-45, 55),
                        textcoords="offset points", ha="right", fontsize=8.5, fontweight="bold", color=INK,
                        arrowprops={"arrowstyle": "-", "color": INK, "linewidth": 0.8})
        if abs(example["d_fossil_twh"]) <= zoom:
            ax_zoom.annotate(
                f"{name} (Selected)\n{example['d_clean_share_pp']:+.1f} pp, {example['d_fossil_twh']:+.1f} TWh",
                xy=(example["d_clean_share_pp"], example["d_fossil_twh"]), xytext=(25, 12),
                textcoords="offset points", fontsize=8.5, fontweight="bold", color=INK,
                arrowprops={"arrowstyle": "-", "color": INK, "linewidth": 0.8},
            )
        draw_mix(ax_share, ax_twh, window(countries.loc[countries["country"].eq(name)], settings), settings, name)
        shown = f"{name} selected"

    handles = [Line2D([], [], linestyle="none", marker=OUTCOME_STYLE[key][2], markersize=8,
                      color=OUTCOME_STYLE[key][1]) for key in present]
    labels = [f"{OUTCOME_STYLE[key][0]} ({int(table['outcome'].eq(key).sum())})" for key in present]
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.07, 0.895), ncol=len(present),
               frameon=False, fontsize=9.5)
    interaction(fig, 0.07, 0.94,
                "click a dot (in either scatterplot) or choose a country from the menu; the two charts at the "
                f"bottom show\nthat country's mix, {s}–{e} (the same charts as Q1). Shown: {shown}.")
    fig.text(0.07, 0.465, "Selected Country", fontsize=12, fontweight="bold", va="center", color=INK)
    control(fig, 0.2, 0.465, f"Country:  {example['country'] if example is not None else 'Choose'}  ▾")
    no_start = int(table["fossil_twh_start"].eq(0).sum())
    if settings.q5_example:
        rule = f"Example: {settings.q5_example}, set in the config (q5.example)."
    else:
        rule = f"Example rule: the largest {e} generator among \"share up, fossil up\" countries in the band."
    return frame(
        fig, f"Domestic Electricity Generation: Clean-Share Change vs. Fossil Change · {s}–{e}",
        f"Source: OWID. {len(table)} countries with endpoint data and ≥ {settings.min_generation_twh:g} TWh "
        f"generation in {e}. Both scatterplots use the same linear x scale. Percent change in fossil generation "
        f"is not used: small bases give extreme percentages, and {no_start} countries had no fossil generation "
        f"in {s}. {rule} Clean = renewables + nuclear. Not causal.",
    )


def demand_pairs(table, left_out, pairs, summary, settings):
    """Q6: demand growth and the start-year mix, countries whose fossil generation fell vs. did not."""
    s, e, zoom = settings.start_year, settings.end_year, settings.q6_zoom_pct
    selected = pairs.iloc[settings.q6_selected_pair - 1] if len(pairs) >= settings.q6_selected_pair else None
    names = [] if selected is None else [selected["country_reduced"], selected["country_other"]]
    chosen = [table.loc[table["country"].eq(name)].iloc[0] for name in names]
    in_zoom = table.loc[table["demand_growth_pct"].le(zoom)]

    fig = plt.figure(figsize=(14, 13.5))
    # Lay out the pair buttons first. Each extra row makes the figure 0.4 in taller, so the
    # legend and the charts below the buttons keep their size.
    renderer = fig.canvas.get_renderer()
    button_rows, bx = [[]], 0.115
    for row in pairs.itertuples(index=False):
        text = f"{row.country_reduced} – {row.country_other}"
        probe = control(fig, 0, 0, text)
        width = probe.get_window_extent(renderer).width / fig.bbox.width
        probe.remove()
        if bx + width > 0.97 and button_rows[-1]:
            button_rows.append([])
            bx = 0.115
        button_rows[-1].append((bx, text, row.pair == settings.q6_selected_pair))
        bx += width + 0.015
    height = 13.5 + 0.4 * (len(button_rows) - 1)
    fig.set_size_inches(14, height)

    def below(y):  # The same distance from the bottom as in the 13.5 in layout.
        return y * 13.5 / height

    def above(y):  # The same distance from the top.
        return 1 - (1 - y) * 13.5 / height

    top = fig.add_gridspec(1, 2, left=0.07, right=0.97, top=below(0.79), bottom=below(0.5), wspace=0.22)
    bottom = fig.add_gridspec(1, 2, left=0.07, right=0.97, top=below(0.4), bottom=below(0.08),
                              width_ratios=[1, 1.1], wspace=0.3)
    ax_all, ax_zoom = fig.add_subplot(top[0, 0]), fig.add_subplot(top[0, 1])
    ax_bars, ax_table = fig.add_subplot(bottom[0, 0]), fig.add_subplot(bottom[0, 1])

    medians = summary.set_index("fossil_reduced")["median_demand_growth_pct"]
    xlabel = f"Electricity Demand Growth, {s}–{e} (%)"
    ylabel = f"Clean Share of Generation in {s} (%)"
    for ax, rows in ((ax_all, table), (ax_zoom, in_zoom)):
        for reduced, (label, color, marker, _) in GROUP_STYLE.items():
            group = rows.loc[rows["fossil_reduced"].eq(reduced)]
            ax.scatter(group["demand_growth_pct"], group["clean_share_pct_start"], s=40, color=color,
                       marker=marker, edgecolors="white", linewidths=0.6, zorder=3)
            ax.axvline(medians[reduced], color=color, linestyle="--", linewidth=1.2, zorder=2)
        ax.axvline(0, color="#777777", linewidth=0.8, zorder=1)
        ax.set_ylim(-3, 103)
        ax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
        if chosen:
            ax.plot([row["demand_growth_pct"] for row in chosen], [row["clean_share_pct_start"] for row in chosen],
                    color=INK, linestyle=":", linewidth=1, zorder=2)
            ax.scatter([row["demand_growth_pct"] for row in chosen], [row["clean_share_pct_start"] for row in chosen],
                       s=190, facecolors="none", edgecolors=INK, linewidths=1.8, zorder=4)
    style(ax_all, xlabel, ylabel, f"All {len(table)} Countries")
    style(ax_zoom, xlabel, ylabel, f"Enlarged: {len(in_zoom)} Countries With Growth ≤ {zoom:,.0f}%")
    x = table["demand_growth_pct"]
    spread = max(x.max() - x.min(), 50)  # A few close values still get a readable range.
    ax_all.set_xlim(x.min() - spread * 0.03, x.max() + spread * 0.12)
    ax_all.axvspan(x.min(), zoom, facecolor="#F0F0F0", edgecolor="#999999", linestyle="--", linewidth=0.8, zorder=0)
    ax_all.annotate(f"≤ {zoom:,.0f}% Band,\nEnlarged at Right", xy=(zoom, 78), xytext=(18, 0),
                    textcoords="offset points", va="center", fontsize=8.5, color=MUTED,
                    arrowprops={"arrowstyle": "->", "color": MUTED})
    label_extremes(ax_all, table.nlargest(3, "demand_growth_pct"), "demand_growth_pct", "clean_share_pct_start",
                   lambda row: f"{row['country']} ({row['demand_growth_pct']:+,.0f}%)")
    ax_zoom.set_xlim(min(x.min(), 0) - 10, zoom + 10)

    mix = [("Coal", "coal_share_pct_start"), ("Gas", "gas_share_pct_start"), ("Oil", "oil_share_pct_start"),
           ("Clean", "clean_share_pct_start")]
    if chosen:
        for i, (reduced, row) in enumerate(zip((True, False), chosen)):
            _, color, _, hatch = GROUP_STYLE[reduced]
            positions = [k + (i - 0.5) * 0.38 for k in range(len(mix))]
            values = [row[column] for _, column in mix]
            ax_bars.barh(positions, values, height=0.36, color=color, hatch=hatch, edgecolor="white", linewidth=0.5)
            for position, value in zip(positions, values):
                ax_bars.text(value + 1.2, position, f"{value:.1f}%", va="center", fontsize=8.5, color=INK)
        ax_bars.legend([Patch(facecolor=GROUP_STYLE[True][1]), Patch(facecolor=GROUP_STYLE[False][1], hatch="///")],
                       [f"{names[0]} (Fell)", f"{names[1]} (Did Not Fall)"], loc="lower right", frameon=False,
                       fontsize=9)
    ax_bars.set_yticks(range(len(mix)), [name for name, _ in mix])
    ax_bars.invert_yaxis()
    ax_bars.set_xlim(0, 110)
    style(ax_bars, f"Share of Generation in {s} (%)", "",
          f"{s} Mix: {names[0]} vs. {names[1]}" if chosen else f"{s} Mix")
    ax_bars.grid(axis="y", visible=False)

    ax_table.axis("off")
    ax_table.set_title("The Selected Pair", loc="left", fontsize=11, fontweight="bold")
    if chosen:
        cells = [
            [f"Demand Growth, {s}–{e}"] + [f"{row['demand_growth_pct']:+,.1f}%" for row in chosen],
            [f"Generation Growth, {s}–{e}"] + [f"{row['generation_growth_pct']:+,.1f}%" for row in chosen],
            [f"Net Imports, % of {e} Demand"] + [f"{row['net_imports_share_of_demand_pct_end']:.1f}%" for row in chosen],
            [f"Fossil Generation Change, {s}–{e}"] + [f"{row['d_fossil_twh']:+,.1f} TWh" for row in chosen],
        ]
        grid = ax_table.table(cellText=cells, colLabels=["", *names], loc="upper center", cellLoc="right",
                              colWidths=[0.5, 0.25, 0.25])
        grid.auto_set_font_size(False)
        grid.set_fontsize(9)
        grid.scale(1, 1.7)
        for (r, c), cell in grid.get_celld().items():
            cell.set_edgecolor(GRID)
            if c == 0:
                cell.set_text_props(ha="left")
            if r == 0:
                cell.set_text_props(fontweight="bold")

    handles = [Line2D([], [], linestyle="none", marker=marker, markersize=8, color=color)
               for _, color, marker, _ in GROUP_STYLE.values()]
    labels = [f"{label} ({int(table['fossil_reduced'].eq(reduced).sum())})"
              for reduced, (label, _, _, _) in GROUP_STYLE.items()]
    for reduced, (label, color, _, _) in GROUP_STYLE.items():
        handles.append(Line2D([], [], color=color, linestyle="--", linewidth=1.2))
        labels.append(f"Median: {medians[reduced]:,.1f}%")
    if chosen:
        handles.append(Line2D([], [], linestyle="none", marker="o", markersize=12, markerfacecolor="none",
                              markeredgecolor=INK, markeredgewidth=1.8))
        labels.append(f"Selected Pair: {' and '.join(names)}")
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.07, below(0.86)), ncol=len(handles),
               frameon=False, fontsize=9.5, columnspacing=1.4, handletextpad=0.4)
    interaction(fig, 0.07, above(0.94),
                "click a pair button; both countries are ringed in the scatterplots, and the bars and the table "
                f"show their {s} mix and numbers.\nEach pair has similar demand growth but opposite fossil outcomes. "
                f"Shown: pair {settings.q6_selected_pair}, {' – '.join(names) if names else 'none'}.")
    fig.text(0.07, above(0.885), "Pairs:", fontsize=9.5, va="center", fontweight="bold", color=INK)
    for i, buttons in enumerate(button_rows):
        for bx, text, selected in buttons:
            control(fig, bx, above(0.885) - i * 0.4 / height, text, selected=selected)

    reduced, other = (summary.set_index("fossil_reduced").loc[flag] for flag in (True, False))
    return frame(
        fig, f"Electricity Demand Growth and Fossil Generation Outcomes · {s}–{e}",
        f"Source: OWID. {len(table)} compared countries; left out: {', '.join(left_out) or 'none'} "
        f"(zero fossil generation in both {s} and {e}). Demand = generation + net imports. The group comparison answers "
        f"Q6: median demand growth {reduced['median_demand_growth_pct']:,.1f}% where fossil generation fell "
        f"({int(reduced['countries'])} countries) vs. {other['median_demand_growth_pct']:,.1f}% where it did not "
        f"({int(other['countries'])}). The pairs (closest demand growth across groups, each country once) "
        "illustrate exceptions; they are not a sample. Not causal.",
    )
