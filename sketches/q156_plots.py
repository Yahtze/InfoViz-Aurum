"""Static sketches for Q1, Q5 and Q6. Selection and calculation live in q156_data.py.

Unlike the Q2-Q4 views, these sketch the planned interactive design: a dashed
"Planned Interaction" box describes what the D3 version will do, and the static
image shows one state of it (a year under the cursor, a selected country, a selected pair).
"""

import textwrap

import matplotlib

matplotlib.use("Agg")  # Save files without a display server.
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FixedLocator, MaxNLocator, NullLocator, StrMethodFormatter
from matplotlib.transforms import offset_copy
import numpy as np

from .sketchesQ2Q3Q4.plots import DOWN, UP
from .q156_data import FOSSIL_SOURCES, OUTCOME_LABELS, mix_table, window

INK = "#333333"
MUTED = "#666666"
GRID = "#EAEAEA"
NOTE_FILL = "#F4F4F4"
# Fossil layers sit at the bottom of the Q1 stacks in grays (dark to light); clean layers use the
# config group colors (as in Q4), so the two families read apart at a glance.
FOSSIL_COLORS = {"Coal": "#77716B", "Gas": "#A29C96", "Oil": "#CBC5BF"}
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
                    bbox={"boxstyle": "round,pad=0.45", "facecolor": MUTED if selected else "white",
                          "edgecolor": MUTED if selected else "#999999", "linewidth": 0.9})


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


def layer_styles(settings):
    """(label, color) for every layer, bottom first: coal, gas, oil, then the clean groups."""
    layers = [(name.title(), FOSSIL_COLORS[name.title()]) for name in FOSSIL_SOURCES]
    return layers + [(group.label, group.color) for group in settings.groups]


def spread(ys, gap, high):
    """Heights for names at ys (ascending): pushed up to be at least gap apart, then down so the
    top one stays below high."""
    spots = []
    for y in ys:
        spots.append(y if not spots else max(y, spots[-1] + gap))
    for i in reversed(range(len(spots))):  # Names near the top would be pushed above the chart.
        spots[i] = min(spots[i], high - gap / 2 if i == len(spots) - 1 else spots[i + 1] - gap)
    return spots


def year_axis(ax, start, end):
    """Year ticks that always include the first and the last year, so no endpoint goes unlabeled."""
    ax.set_xlim(start, end)
    near = (end - start) / 12  # Drop a regular tick this close to an endpoint, so labels do not collide.
    middle = [int(tick) for tick in MaxNLocator(nbins=7, integer=True, steps=[1, 2, 4, 5, 10]).tick_values(start, end)
              if start + near < tick < end - near]
    ax.xaxis.set_major_locator(FixedLocator([int(start), *middle, int(end)]))


def label_layers(ax, year, middles, groups):
    """Name each layer just right of the last year, at the layer's middle, pushed apart so names do not overlap,
    then bracket each group's names (Fossil, Clean). middles holds (y, label, color) in stack order;
    groups holds (group name, labels)."""
    low, high = ax.get_ylim()
    gap = (high - low) * 0.05
    left, right = ax.get_xlim()
    dx = (right - left) * 0.03
    # Layers of zero height share a middle; keep them in stack order, not by name, so no name
    # lands inside the other group's bracket.
    middles = sorted(middles, key=lambda middle: middle[0])
    spots = spread([y for y, _, _ in middles], gap, high)
    renderer = ax.figure.canvas.get_renderer()
    placed, widest = {}, 0
    for (y, label, color), label_y in zip(middles, spots):
        ax.plot([year, year + dx * 0.6], [y, label_y], color=MUTED, linewidth=0.6, clip_on=False)
        ax.plot([year + dx * 0.6, year + dx * 1.3], [label_y, label_y], color=color, linewidth=6, clip_on=False)
        name = ax.text(year + dx * 1.5, label_y, label, va="center", fontsize=8.5, color=INK, clip_on=False)
        placed[label] = label_y
        widest = max(widest, name.get_window_extent(renderer).width * 72 / ax.figure.dpi)
    # Offsets in points from the names' left edge, so a bracket clears the longest name.
    line = offset_copy(ax.transData, fig=ax.figure, x=widest + 5, units="points")
    word = offset_copy(ax.transData, fig=ax.figure, x=widest + 8, units="points")
    for group, labels in groups:
        ys = [placed[label] for label in labels if label in placed]
        if ys:
            bottom, top = min(ys) - gap * 0.4, max(ys) + gap * 0.4
            ax.plot([year + dx * 1.5] * 2, [bottom, top], transform=line, color=MUTED, linewidth=0.9,
                    clip_on=False)
            ax.text(year + dx * 1.5, (bottom + top) / 2, group, transform=word, rotation=90, ha="left",
                    va="center", fontsize=9, fontweight="bold", color=INK, clip_on=False)


def draw_mix(ax_share, ax_twh, rows, settings, place, cursor_year=None, headroom=1.08):
    """The Q1 design: the sources stacked, share (%) on the left and TWh on the right, fossil at the bottom.
    The fossil boundary falls in one chart and rises in the other when a smaller share of a larger
    total is more electricity. A year with an unknown source is left blank: its layers cannot be
    stacked. headroom sets the TWh axis top as a multiple of the largest total."""
    layers = layer_styles(settings)
    names = [name for name, _ in layers]
    fossil = names[:len(FOSSIL_SOURCES)]
    tables = []
    for ax, unit, label in ((ax_share, "share_pct", "Share of Generation (%)"),
                            (ax_twh, "twh", "Generation (TWh)")):
        table = mix_table(rows, settings, unit)
        values = table[names].where(table[names].notna().all(axis=1))
        years = table["year"]
        # No outlines: white seams between thin layers drew zigzag hairlines.
        ax.stackplot(years, values.T.to_numpy(dtype=float), colors=[color for _, color in layers],
                     linewidth=0, zorder=2)
        fossil_total = values[fossil].sum(axis=1, min_count=len(fossil))
        total = values.sum(axis=1, min_count=len(names))
        ax.plot(years, fossil_total, color=INK, linewidth=1.3, solid_joinstyle="round", zorder=3)
        top = total.max()
        ax.set_ylim(0, 100 if unit == "share_pct" else (top * headroom if top > 0 else 1))
        year_axis(ax, years.iloc[0], years.iloc[-1])
        known = values.dropna()
        title = f"{place}: {label}"
        if unit == "twh":
            ends = [f"{total.iloc[i]:,.0f}" if total.notna().iloc[i] else "unknown" for i in (0, -1)]
            title += f", Total {ends[0]} → {ends[1]}"
        style(ax, "Year", label, title)
        ax.grid(axis="x", visible=False)
        unit_text = (lambda v: f"{v:.1f}%") if unit == "share_pct" else (lambda v: f"{v:,.0f} TWh")
        # The endpoint years only: an endpoint with an unknown source gets no fossil label.
        for row, align, dx in ((table.index[0], "left", 6), (table.index[-1], "right", -6)):
            if fossil_total.notna()[row]:
                ax.annotate(
                    f"Fossil {unit_text(fossil_total[row])}", xy=(years[row], fossil_total[row]),
                    xytext=(dx, -6), textcoords="offset points", ha=align, va="top", fontsize=8.5,
                    fontweight="bold", color=INK, zorder=5,
                    bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "none"})
        if not known.empty:
            last = known.index[-1]
            tops = known[names].cumsum(axis=1).loc[last]
            label_layers(ax, years[last], [(tops[name] - known.loc[last, name] / 2, name, color)
                                           for name, color in layers],
                         (("Fossil", fossil), ("Clean", names[len(fossil):])))
        if cursor_year is not None:
            ax.axvline(cursor_year, color=INK, linestyle="--", linewidth=1, zorder=4)
        tables.append(table)
    ax_twh.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    make_room(ax_share, ax_twh)
    return tables


def make_room(ax_left, ax_right, pad=8):
    """Narrow the left chart from its right edge until its names and brackets clear the right chart's
    axis labels: long group labels need more room than the layout's gap."""
    fig = ax_left.figure
    renderer = fig.canvas.get_renderer()
    right_edge = max((text.get_window_extent(renderer).x1 for text in ax_left.texts), default=None)
    if right_edge is None:
        return
    overlap = right_edge + pad - ax_right.get_tightbbox(renderer).x0
    if overlap > 0:
        box = ax_left.get_position()
        ax_left.set_position([box.x0, box.y0, box.width - overlap / fig.bbox.width, box.height])


def world_mix(world, settings):
    """Q1: the world's electricity mix, in shares and in TWh. The layer names and the Fossil and
    Clean brackets at the right of each chart replace a legend."""
    rows = window(world, settings)
    s, e = settings.start_year, settings.end_year
    cursor = 2010 if s < 2010 < e else s
    fig, (ax_share, ax_twh) = plt.subplots(1, 2, figsize=(14, 6.2))
    fig.subplots_adjust(left=0.06, right=0.9, top=0.78, bottom=0.17, wspace=0.52)
    # Room above the TWh stack for the tooltip, so it covers no layer.
    share, twh = draw_mix(ax_share, ax_twh, rows, settings, "World", cursor_year=cursor, headroom=1.3)
    fossil = [name.title() for name in FOSSIL_SOURCES]
    clean = [group.label for group in settings.groups]
    at = {unit: table.loc[table["year"].eq(cursor)].iloc[0] for unit, table in (("share", share), ("twh", twh))}

    def summed(unit, names, form):  # An unknown source makes the sum unknown, not smaller.
        value = at[unit][names].sum(min_count=len(names)) if at[unit][names].notna().all() else None
        return "unknown" if value is None else form.format(value)

    tooltip = "\n".join([
        f"{cursor}",
        f"Fossil {summed('share', fossil, '{:.1f}%')} · {summed('twh', fossil, '{:,.0f} TWh')}",
        f"Clean {summed('share', clean, '{:.1f}%')} · {summed('twh', clean, '{:,.0f} TWh')}",
        f"Total {summed('twh', fossil + clean, '{:,.0f} TWh')}",
    ])
    ax_twh.annotate(tooltip, xy=(cursor, ax_twh.get_ylim()[1]), xytext=(8, -6),
                    textcoords="offset points", va="top", fontsize=8.5,
                    bbox={"boxstyle": "round,pad=0.4", "facecolor": "white", "edgecolor": "#999999",
                          "linewidth": 0.8}, zorder=6)
    interaction(fig, 0.06, 0.915,
                "move the mouse across either chart; a cursor marks the year in both and a tooltip lists every "
                "source's share and TWh.\nClick a source's name at the right to show that source alone as a line "
                f"in both units. Shown: the cursor at {cursor} (tooltip shortened).")
    combined = "".join(  # Groups of several sources, from the config.
        f"; {group.label} = {' + '.join(source.replace('_', ' ') for source in group.sources)}"
        for group in settings.groups if len(group.sources) > 1
    )
    return frame(
        fig, f"Domestic Electricity Generation: World Mix by Source · {s}–{e}",
        f"Source: OWID, pinned data. World row, {s}–{e}. Shares are of domestic generation; "
        f"the {len(settings.groups) + 3} layers add up to total generation and to 100%. Fossil sources are "
        f"the grays at the bottom, and the dark line is their top; clean sources use the Q4 colors. "
        f"Clean = renewables + nuclear{combined}.",
    )


# Q5's country detail: fossil is the line the scatterplot's y is read from, so it is solid and dark;
# clean is dashed, so its green is not read as the scatterplot's "fossil down" color.
FOSSIL_LINE = "#5F5A55"
CLEAN_LINE = "#2F8F5B"
CLEAN_DASH = (0, (5, 2))


def share_top(peak):
    """The clean-share axis top: a round value above the peak, at most 100%."""
    if not np.isfinite(peak) or peak <= 0:
        return 100.0
    step = 5 if peak < 30 else 10
    return float(min(100, step * np.ceil(peak * 1.1 / step)))


def end_labels(ax, year, ends):
    """Name each line at its last year, right of the chart, pushed apart when two ends are close.
    ends holds (y, text, color). A line whose end is unknown is still named, at the top and without a
    leader, so a dashed line that stops early keeps its name."""
    low, high = ax.get_ylim()
    gap = (high - low) * 0.07
    left, right = ax.get_xlim()
    dx = (right - left) * 0.02
    ends = sorted(((y if np.isfinite(y) else high, text, color, np.isfinite(y)) for y, text, color in ends),
                  key=lambda end: end[0])
    for (y, text, color, known), spot in zip(ends, spread([end[0] for end in ends], gap, high)):
        if known:
            ax.plot([year, year + dx, year + dx * 1.6], [y, spot, spot], color=color, linewidth=0.8,
                    clip_on=False)
        ax.text(year + dx * 1.9, spot, text, va="center", fontsize=9.5, fontweight="bold", color=color,
                clip_on=False)


def outcome_lines(ax_share, ax_twh, rows, settings, place):
    """Q5's country detail: the two values behind the selected dot, over time. Left, the clean share
    (its change is the dot's x); right, fossil and clean generation (the fossil change is the dot's y).
    Lines read the same summary columns as the scatterplot. A missing year breaks a line, and an
    unknown endpoint is shown as unknown, never replaced by another year."""
    s, e = settings.start_year, settings.end_year
    rows = rows.set_index("year").reindex(range(s, e + 1))  # A missing row becomes a gap, not a join.
    years = rows.index.to_numpy()
    series = {column: rows[column].astype(float) for column in ("clean_share_pct", "fossil_twh", "clean_twh")}

    def change(column, value_text, unit):
        start, end = series[column].loc[s], series[column].loc[e]
        values = " → ".join(value_text(v) if np.isfinite(v) else "unknown" for v in (start, end))
        diff = f"{end - start:+,.1f} {unit}" if np.isfinite(start) and np.isfinite(end) else "change unknown"
        return f"{s} → {e}: {values} ({diff})"

    def draw(ax, column, color, style_):
        values = series[column]
        ax.plot(years, values, color=color, linestyle=style_, linewidth=2.2, solid_joinstyle="round",
                dash_capstyle="round", zorder=3, label=column)
        known = values.loc[[s, e]].dropna()
        ax.plot(known.index, known, "o", color=color, markersize=5, zorder=4)

    draw(ax_share, "clean_share_pct", CLEAN_LINE, CLEAN_DASH)
    ax_share.set_ylim(0, share_top(series["clean_share_pct"].max()))
    draw(ax_twh, "fossil_twh", FOSSIL_LINE, "-")
    draw(ax_twh, "clean_twh", CLEAN_LINE, CLEAN_DASH)
    top = np.nanmax([series["fossil_twh"].max(), series["clean_twh"].max(), 0])
    ax_twh.set_ylim(0, top * 1.15 if top > 0 else 1)
    ax_twh.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    twh = lambda v: f"{v:,.1f}"
    for ax, ylabel, title, note in (
        (ax_share, "Clean Share of Generation (%)", f"{place}: Clean Share (%)",
         change("clean_share_pct", lambda v: f"{v:.1f}%", "pp") + "\nIts change is the scatterplot's x"),
        (ax_twh, "Generation (TWh)", f"{place}: Fossil and Clean Generation (TWh)",
         f"Fossil {change('fossil_twh', twh, 'TWh')}, the scatterplot's y\n"
         f"Clean {change('clean_twh', twh, 'TWh')}"),
    ):
        style(ax, "Year", ylabel)
        ax.set_title(title, loc="left", fontsize=11, fontweight="bold", pad=32)
        ax.text(0, 1.015, note, transform=ax.transAxes, fontsize=9, color=MUTED, va="bottom", linespacing=1.4)
        year_axis(ax, s, e)
        ax.grid(axis="x", visible=False)

    def name(label, value, form):
        return f"{label} {form(value)}" if np.isfinite(value) else f"{label} {e}: unknown"

    end_labels(ax_share, e, [(series["clean_share_pct"].loc[e],
                              name("Clean", series["clean_share_pct"].loc[e], lambda v: f"{v:.1f}%"), CLEAN_LINE)])
    digits = 0 if top >= 100 else 1  # The same rounding for both names in a chart.
    end_labels(ax_twh, e, [(series[column].loc[e], name(label, series[column].loc[e], lambda v: f"{v:,.{digits}f}"),
                            color) for column, label, color in (("fossil_twh", "Fossil", FOSSIL_LINE),
                                                                ("clean_twh", "Clean", CLEAN_LINE))])
    make_room(ax_share, ax_twh)


def fossil_outcome_scatter(table, countries, settings, example):
    """Q5: change in clean share vs. change in fossil generation, overview and enlarged band,
    with the selected country's mix below."""
    s, e, zoom = settings.start_year, settings.end_year, settings.q5_zoom_twh
    in_zoom = table.loc[table["d_fossil_twh"].abs().le(zoom)]
    present = [key for key in OUTCOME_STYLE if table["outcome"].eq(key).any()]

    fig = plt.figure(figsize=(14, 13))
    # The enlarged band holds most countries, so it gets the wider chart.
    top = fig.add_gridspec(1, 2, left=0.07, right=0.9, top=0.83, bottom=0.55, wspace=0.3, width_ratios=[1, 1.5])
    bottom = fig.add_gridspec(1, 2, left=0.07, right=0.9, top=0.395, bottom=0.11, wspace=0.42)
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
    # The three largest changes, plus the largest fall if it is not among them.
    extremes = y.abs().nlargest(3).index.union([y.idxmin()])
    label_extremes(ax_all, table.loc[extremes], "d_clean_share_pp", "d_fossil_twh",
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
        else:  # Point from the band's edge toward the selected country, so the selection still shows here.
            above = example["d_fossil_twh"] > 0
            # The text runs toward the middle and sits inside the quadrant names, which take the
            # outer 21 points at the top and bottom.
            right_half = example["d_clean_share_pp"] > sum(span) / 2
            ax_zoom.annotate(
                f"{name} ({example['d_fossil_twh']:+,.0f} TWh) is {'above' if above else 'below'} the band",
                xy=(example["d_clean_share_pp"], (1 if above else -1) * zoom * 1.08),
                xytext=(-4 if right_half else 4, -28 if above else 28), textcoords="offset points",
                ha="right" if right_half else "left", va="top" if above else "bottom", fontsize=8.5,
                fontweight="bold", color=INK, zorder=5, arrowprops={"arrowstyle": "->", "color": INK, "linewidth": 0.8},
                bbox={"boxstyle": "round,pad=0.2", "facecolor": "white", "edgecolor": "none", "alpha": 0.85},
            )
        outcome_lines(ax_share, ax_twh, window(countries.loc[countries["country"].eq(name)], settings), settings,
                      name)
        shown = f"{name} selected"

    handles = [Line2D([], [], linestyle="none", marker=OUTCOME_STYLE[key][2], markersize=8,
                      color=OUTCOME_STYLE[key][1]) for key in present]
    labels = [f"{OUTCOME_STYLE[key][0]} ({int(table['outcome'].eq(key).sum())})" for key in present]
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.07, 0.895), ncol=len(present),
               frameon=False, fontsize=9.5)
    interaction(fig, 0.07, 0.94,
                "click a dot (in either scatterplot) or pick a country from a searchable list grouped by outcome; "
                "the two charts at the bottom trace\nthat country's clean share and its fossil and clean generation "
                f"(the dot's x and y), with each source in a tooltip. Shown: {shown}.")
    fig.text(0.07, 0.47, "Selected Country", fontsize=12, fontweight="bold", va="center", color=INK)
    control(fig, 0.2, 0.47, f"Country:  {example['country'] if example is not None else 'Choose'}  ▾")
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
        f"in {s}. {rule} Changes are computed before rounding. Clean = renewables + nuclear. Not causal.",
    )


# Demand growth (%) at which the Q6 ratio axis is labeled.
DEMAND_TICKS = (-50, -20, 0, 50, 100, 300, 900, 1900, 3900, 9900)
# The Q6 start-year mix panels: coal, gas, oil, and clean, each on the same 0-100% scale.
MIX_PANELS = (("Coal", "coal_share_pct_start"), ("Gas", "gas_share_pct_start"), ("Oil", "oil_share_pct_start"),
             ("Clean", "clean_share_pct_start"))
GROUP_ROW = {True: 1, False: 0}  # Fell on top.


def growth_text(pct):
    return "0%" if round(pct) == 0 else f"{pct:+,.0f}%".replace("-", "−")


def jitter(countries):
    """A fixed vertical offset per country, the same in every Q6 panel, so a country can be traced.
    It only spreads the dots within their group's row; the x value is exact."""
    rng = np.random.default_rng(6313)
    names = sorted(countries)
    return dict(zip(names, rng.uniform(-0.17, 0.17, len(names))))


def missing(value):
    return value is None or not np.isfinite(value)


def draw_groups(ax, table, values, offsets, chosen, unit):
    """One row per group: a box (quartiles and median, whiskers 1.5 × IQR) with every country as a dot.
    values is a Series aligned with table; unknown values are left out. Returns each group's median."""
    medians = {}
    for reduced, (label, color, marker, _) in GROUP_STYLE.items():
        y = GROUP_ROW[reduced]
        mask = table["fossil_reduced"].eq(reduced) & values.notna()
        x = values[mask]
        if x.empty:
            ax.text(0.5, y, "No countries", transform=ax.get_yaxis_transform(), ha="center", va="center",
                    fontsize=9, color=MUTED)
            continue
        ax.boxplot([x.to_numpy()], positions=[y], orientation="horizontal", widths=0.5, showfliers=False,
                   patch_artist=True, manage_ticks=False, zorder=2,
                   boxprops={"facecolor": to_rgba(color, 0.12), "edgecolor": color},
                   medianprops={"color": color, "linewidth": 2.2}, whiskerprops={"color": color},
                   capprops={"color": color})
        ys = y + table.loc[mask, "country"].map(offsets)
        ax.scatter(x, ys, s=26, color=color, marker=marker, edgecolors="white", linewidths=0.5, zorder=3)
        medians[reduced] = x.median()
        ax.annotate(f"Median {unit(medians[reduced])}", xy=(medians[reduced], y + 0.25), xytext=(0, 3),
                    textcoords="offset points", ha="center", va="bottom", fontsize=8.5, fontweight="bold",
                    color=color, zorder=5)
    for name in chosen:
        row = table.loc[table["country"].eq(name)]
        if row.empty or missing(values[row.index[0]]):
            continue
        reduced = bool(row["fossil_reduced"].iloc[0])
        ax.scatter([values[row.index[0]]], [GROUP_ROW[reduced] + offsets[name]], s=170, facecolors="none",
                   edgecolors=INK, linewidths=1.6, zorder=4)
    ax.set_ylim(-0.6, 1.7)
    counts = {reduced: int(table["fossil_reduced"].eq(reduced).sum()) for reduced in GROUP_STYLE}
    ax.set_yticks([GROUP_ROW[True], GROUP_ROW[False]],
                  [f"Fell ({counts[True]})", f"Did Not Fall ({counts[False]})"])
    ax.grid(axis="y", visible=False)
    return medians


def demand_pairs(table, left_out, pairs, settings):
    """Q6: demand growth and the start-year mix, countries whose fossil generation fell vs. did not.
    Each panel compares the two groups directly (boxes and dots); the pairs are examples."""
    s, e = settings.start_year, settings.end_year
    selected = pairs.iloc[settings.q6_selected_pair - 1] if len(pairs) >= settings.q6_selected_pair else None
    names = [] if selected is None else [selected["country_reduced"], selected["country_other"]]
    offsets = jitter(table["country"])

    fig = plt.figure(figsize=(14, 15))
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
    height = 15 + 0.4 * (len(button_rows) - 1)
    fig.set_size_inches(14, height)

    def below(y):  # The same distance from the bottom as in the 15 in layout.
        return y * 15 / height

    def above(y):  # The same distance from the top.
        return 1 - (1 - y) * 15 / height

    top = fig.add_gridspec(1, 1, left=0.13, right=0.97, top=below(0.79), bottom=below(0.6))
    bottom = fig.add_gridspec(2, 2, left=0.13, right=0.97, top=below(0.5), bottom=below(0.105),
                              hspace=0.6, wspace=0.3)
    ax_demand = fig.add_subplot(top[0, 0])
    mix_axes = [fig.add_subplot(bottom[i // 2, i % 2]) for i in range(len(MIX_PANELS))]

    # Demand growth spans from a small fall to many times the start, so the axis is the ratio
    # demand_end / demand_start on a log scale (1× = no change), labeled as percent change.
    growth = table["demand_growth_pct"]
    ratio = (1 + growth / 100).where(growth > -100)  # Demand that fell to zero has no place on a log scale.
    no_data, to_zero = int(growth.isna().sum()), int(growth.le(-100).sum())
    demand_medians = draw_groups(ax_demand, table, ratio, offsets, names,
                                 lambda r: f"{100 * (r - 1):+,.1f}%".replace("-", "−"))
    ax_demand.set_xscale("log")
    known = ratio.dropna()
    low, high = (min(known.min(), 1), max(known.max(), 1)) if not known.empty else (0.5, 2)
    ax_demand.set_xlim(low / 1.25, high * 1.6)
    ticks = [1 + pct / 100 for pct in DEMAND_TICKS if low / 1.25 <= 1 + pct / 100 <= high * 1.6]
    ax_demand.xaxis.set_major_locator(FixedLocator(ticks))
    ax_demand.xaxis.set_minor_locator(NullLocator())
    ax_demand.set_xticklabels([growth_text(100 * (tick - 1)) for tick in ticks])
    ax_demand.axvline(1, color="#777777", linewidth=0.8, zorder=1)
    style(ax_demand, f"Electricity Demand Growth, {s}–{e} (Log Scale of Demand {e} ÷ Demand {s})", "",
          f"Demand Growth, {s}–{e}")
    ax_demand.grid(axis="y", visible=False)
    for _, row in table.assign(ratio=ratio).dropna(subset=["ratio"]).nlargest(2, "ratio").iterrows():
        ax_demand.annotate(f"{row['country']} ({growth_text(row['demand_growth_pct'])})",
                           xy=(row["ratio"], GROUP_ROW[bool(row["fossil_reduced"])] + offsets[row["country"]]),
                           xytext=(-8, -12), textcoords="offset points", ha="right", va="center", fontsize=8.5,
                           color=INK, arrowprops={"arrowstyle": "-", "color": MUTED, "linewidth": 0.6})
    for name in names:
        row = table.loc[table["country"].eq(name)].iloc[0]
        if missing(ratio[row.name]):
            continue
        ax_demand.annotate(name, xy=(ratio[row.name], GROUP_ROW[bool(row["fossil_reduced"])] + offsets[name]),
                           xytext=(-14, 0), textcoords="offset points", ha="right", va="center", fontsize=8.5,
                           fontweight="bold", color=INK)

    mix_medians = {}
    for ax, (name, column) in zip(mix_axes, MIX_PANELS):
        mix_medians[name] = draw_groups(ax, table, table[column], offsets, names, lambda v: f"{v:.1f}%")
        ax.set_xlim(-3, 103)
        unknown = int(table[column].isna().sum())
        style(ax, f"Share of Generation in {s} (%)", "",
              f"{name} Share in {s}" + (f" ({unknown} unknown)" if unknown else ""))
        ax.grid(axis="y", visible=False)
    fig.text(0.02, below(0.535), f"Starting Mix: Each Source's Share of Generation in {s}", fontsize=12,
             fontweight="bold", va="center", color=INK)

    handles = [Line2D([], [], linestyle="none", marker=marker, markersize=8, color=color)
               for _, color, marker, _ in GROUP_STYLE.values()]
    labels = [f"{label} ({int(table['fossil_reduced'].eq(reduced).sum())})"
              for reduced, (label, _, _, _) in GROUP_STYLE.items()]
    handles.append(Patch(facecolor="white", edgecolor=MUTED))
    labels.append("Box: Middle Half; Thick Line: Median")
    if names:
        handles.append(Line2D([], [], linestyle="none", marker="o", markersize=12, markerfacecolor="none",
                              markeredgecolor=INK, markeredgewidth=1.6))
        labels.append(f"Selected Pair: {' and '.join(names)}")
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.07, below(0.86)), ncol=len(handles),
               frameon=False, fontsize=9.5, columnspacing=1.4, handletextpad=0.4)
    interaction(fig, 0.07, above(0.94),
                "hover a dot to highlight that country in all five charts. A pair button rings two countries "
                f"with similar demand growth but\nopposite fossil outcomes. Shown: pair {settings.q6_selected_pair}, "
                f"{' – '.join(names) if names else 'none'}.")
    fig.text(0.07, above(0.885), "Pairs:", fontsize=9.5, va="center", fontweight="bold", color=INK)
    for i, buttons in enumerate(button_rows):
        for bx, text, chosen in buttons:
            control(fig, bx, above(0.885) - i * 0.4 / height, text, selected=chosen)

    # The note's medians are the drawn ones, so they match the chart.
    answer = ""
    if all(flag in demand_medians for flag in (True, False)):
        answer = (f" Median demand growth: {100 * (demand_medians[True] - 1):+,.1f}% where fossil generation fell "
                  f"vs. {100 * (demand_medians[False] - 1):+,.1f}% where it did not"
                  f"{' (countries in the demand chart)' if no_data or to_zero else ''}.")
    if all(flag in mix_medians["Clean"] for flag in (True, False)):
        answer += (f" Median clean share in {s}: {mix_medians['Clean'][True]:.1f}% vs. "
                   f"{mix_medians['Clean'][False]:.1f}%.")
    skipped = "".join(
        f" Not in the demand chart: {count} {'country' if count == 1 else 'countries'} {reason}."
        for count, reason in ((no_data, "without demand data"), (to_zero, "whose demand fell to zero"))
        if count
    )
    return frame(
        fig, f"Electricity Demand Growth, Starting Mix, and Fossil Generation Outcomes · {s}–{e}",
        f"Source: OWID. {len(table)} compared countries; left out: {', '.join(left_out) or 'none'} "
        f"(zero fossil generation in both {s} and {e}). Demand = generation + net imports. Whiskers reach the "
        f"farthest country within 1.5 × IQR of the box (IQR = the box's length; for demand, measured on the ratio "
        f"itself, not on the log scale); dots are spread up and down only to reduce overlap.{skipped}{answer} The pairs "
        "(closest demand growth across groups, each country once) illustrate exceptions; they are not a sample. "
        "Not causal.",
    )
