"""Tests for Q1, Q5 and Q6: the world mix, fossil outcomes, and demand-growth pairs."""

from dataclasses import replace
import math
from pathlib import Path
import re
import tempfile
import unittest
import warnings

import numpy as np
import pandas as pd

from prep.report_q156 import (
    REPORT_NAME, START_MIX, TABLE_DIR, baseline_settings, build_report, cutoff_section, facts, hypothesis_check,
    hypothesis_text, majority_text, markdown_table, q1_section, q5_section, q6_section, q156_results, q156_samples,
    start_mix_summary, start_mix_text,
)
from sketches.sketchesQ2Q3Q4.data import load_country_year
from sketches.q156_data import (
    OUTCOME_LABELS, OUTCOMES, fossil_outcomes, group_summary, growth_pct, load_world, matched_pairs,
    mix_table, q5_example, q6_countries, window,
)
from sketches.settings import ROOT, load_settings


class MixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = load_settings()
        cls.world = window(load_world(), cls.settings)

    def test_world_lines_add_up_in_both_units(self):
        share = mix_table(self.world, self.settings, "share_pct")
        twh = mix_table(self.world, self.settings, "twh")
        labels = ["Coal", "Gas", "Oil", *(group.label for group in self.settings.groups)]
        self.assertEqual(share.columns.tolist(), ["year", *labels])
        self.assertEqual(share["year"].tolist(), list(range(2000, 2025)))
        np.testing.assert_allclose(share[labels].sum(axis=1), 100, atol=0.01, rtol=0)
        np.testing.assert_allclose(twh[labels].sum(axis=1), self.world["generation_twh"], atol=0.01, rtol=0)

    def test_every_compared_country_adds_up(self):
        countries = load_country_year()
        compared = set(fossil_outcomes(countries, self.settings)["iso3"])
        for iso3, rows in countries.loc[countries["iso3"].isin(compared)].groupby("iso3"):
            with self.subTest(iso3=iso3):
                for unit in ("share_pct", "twh"):
                    mix_table(rows, self.settings, unit)  # Raises if a complete year does not add up.

    def test_unknown_source_stays_unknown(self):
        rows = self.world.copy()
        rows.loc[rows.index[0], "coal_twh"] = np.nan
        table = mix_table(rows, self.settings, "twh")
        self.assertTrue(math.isnan(table["Coal"].iloc[0]))

    def test_inconsistent_sources_fail(self):
        rows = self.world.copy()
        rows.loc[rows.index[0], "coal_twh"] += 5
        with self.assertRaisesRegex(ValueError, "add up to generation"):
            mix_table(rows, self.settings, "twh")
        with self.assertRaisesRegex(ValueError, "twh or share_pct"):
            mix_table(rows, self.settings, "pp")

    def test_missing_endpoint_year_is_clear(self):
        with self.assertRaisesRegex(ValueError, "Year 1999 is unavailable for World"):
            window(load_world(), replace(self.settings, start_year=1999))


class OutcomeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = load_settings()
        cls.countries = load_country_year()
        cls.table = fossil_outcomes(cls.countries, cls.settings)

    def test_baseline_counts(self):
        self.assertEqual(len(self.table), 108)
        self.assertEqual(self.table["outcome"].value_counts().to_dict(), {
            "share_up_fossil_up": 44, "share_up_fossil_down": 35, "share_not_up": 29,
        })
        self.assertEqual(set(OUTCOMES), set(OUTCOME_LABELS))

    def test_matches_pinned_comparison(self):
        expected = pd.read_csv(ROOT / "data/processed/comparison_2000_2024.csv")
        expected = expected.set_index("iso3").loc[self.table["iso3"]]
        self.assertEqual(self.table["outcome"].tolist(), expected["outcome"].tolist())
        np.testing.assert_allclose(self.table["d_fossil_twh"], expected["d_fossil_twh"], atol=0.001, rtol=0)
        np.testing.assert_allclose(
            self.table["demand_growth_pct"], expected["demand_growth_pct"], atol=0.001, rtol=0,
        )

    def test_unchanged_fossil_is_its_own_outcome(self):
        table = fossil_outcomes(self.countries, replace(self.settings, start_year=2004))
        flat = table.loc[table["outcome"].eq("share_up_fossil_flat")]
        self.assertEqual(len(flat), 1)
        self.assertTrue(flat["d_fossil_twh"].eq(0).all())
        self.assertTrue(flat["d_clean_share_pp"].gt(0).all())

    def test_growth_is_blank_for_nonpositive_start(self):
        result = growth_pct(pd.Series([10.0, 10.0, 10.0]), pd.Series([5.0, 0.0, -1.0]))
        self.assertEqual(result.iloc[0], 100)
        self.assertTrue(result.iloc[1:].isna().all())
        self.assertEqual(int(self.table["fossil_twh_start"].eq(0).sum()), 4)

    def test_example_rule(self):
        self.assertEqual(q5_example(self.table, self.settings)["country"], "South Africa")
        later = replace(self.settings, start_year=2010)
        self.assertEqual(q5_example(fossil_outcomes(self.countries, later), later)["country"], "Brazil")
        tiny = replace(self.settings, q5_zoom_twh=0.001)
        self.assertIsNone(q5_example(self.table, tiny))

    def test_configured_example_must_be_compared(self):
        chosen = replace(self.settings, q5_example="Germany")
        self.assertEqual(q5_example(self.table, chosen)["country"], "Germany")
        with self.assertRaisesRegex(ValueError, "not a compared country"):
            q5_example(self.table, replace(self.settings, q5_example="Atlantis"))


class DemandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = load_settings()
        cls.table, cls.left_out = q6_countries(fossil_outcomes(load_country_year(), cls.settings))
        cls.pairs = matched_pairs(cls.table, cls.settings.q6_pairs)

    def test_countries_without_fossil_generation_are_left_out(self):
        self.assertEqual(self.left_out, ["Bhutan", "Democratic Republic of Congo", "Iceland", "Paraguay"])
        self.assertEqual(len(self.table), 104)
        self.assertEqual(self.table["fossil_reduced"].value_counts().to_dict(), {False: 69, True: 35})

    def test_group_summary(self):
        summary = group_summary(self.table).set_index("fossil_reduced")
        self.assertEqual(summary.loc[True, "countries"], 35)
        self.assertAlmostEqual(summary.loc[True, "median_demand_growth_pct"], 10.4, places=1)
        self.assertAlmostEqual(summary.loc[False, "median_demand_growth_pct"], 165.3, places=1)

    def test_pairs_cross_groups_once_with_growing_gaps(self):
        self.assertEqual(self.pairs["pair"].tolist(), [1, 2, 3, 4, 5, 6])
        names = self.pairs["country_reduced"].tolist() + self.pairs["country_other"].tolist()
        self.assertEqual(len(names), len(set(names)))
        groups = self.table.set_index("country")["fossil_reduced"]
        self.assertTrue(groups.loc[self.pairs["country_reduced"]].all())
        self.assertFalse(groups.loc[self.pairs["country_other"]].any())
        self.assertTrue(self.pairs["gap_pp"].is_monotonic_increasing)
        np.testing.assert_allclose(
            self.pairs["gap_pp"],
            (self.pairs["demand_growth_pct_reduced"] - self.pairs["demand_growth_pct_other"]).abs(),
        )
        self.assertEqual(self.pairs.iloc[0][["country_reduced", "country_other"]].tolist(),
                         ["Netherlands", "South Africa"])

    def test_more_pairs_than_possible(self):
        pairs = matched_pairs(self.table, 1000)
        self.assertEqual(len(pairs), 35)  # One per country whose fossil generation fell.


class SettingsTests(unittest.TestCase):
    def test_defaults_and_config(self):
        settings = load_settings()
        self.assertEqual((settings.q5_zoom_twh, settings.q5_example), (60, None))
        self.assertEqual((settings.q6_pairs, settings.q6_selected_pair), (6, 1))

    def test_rejects_invalid_q5_q6_settings(self):
        settings = load_settings()
        for change in (
            {"q5_zoom_twh": 0}, {"q5_zoom_twh": -1}, {"q5_zoom_twh": math.nan}, {"q5_zoom_twh": True},
            {"q6_pairs": 0}, {"q6_pairs": 2.0},
            {"q6_selected_pair": 7}, {"q5_example": " "}, {"q5_example": 3},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(settings, **change)

    def test_rejects_labels_that_clash_with_mix_columns(self):
        settings = load_settings()
        for label in ("year", "Coal", "Gas", "Oil"):
            groups = (replace(settings.groups[0], label=label), *settings.groups[1:])
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, "reserved"):
                replace(settings, groups=groups)


class PlotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = load_settings()
        cls.countries = load_country_year()
        cls.table = fossil_outcomes(cls.countries, cls.settings)

    def render(self, settings=None, example=True):
        from sketches.q156_plots import demand_pairs, fossil_outcome_scatter, world_mix

        settings = settings or self.settings
        table = fossil_outcomes(self.countries, settings)
        q6, left_out = q6_countries(table)
        return (
            world_mix(load_world(), settings),
            fossil_outcome_scatter(table, self.countries, settings,
                                   q5_example(table, settings) if example else None),
            demand_pairs(q6, left_out, matched_pairs(q6, settings.q6_pairs), settings),
        )

    def test_titles_notes_and_interaction_boxes(self):
        import matplotlib.pyplot as plt
        from sketches.sketchesQ2Q3Q4.plots import set_style

        set_style()
        titles = (
            "Domestic Electricity Generation: World Mix by Source · 2000–2024",
            "Domestic Electricity Generation: Clean-Share Change vs. Fossil Change · 2000–2024",
            "Electricity Demand Growth, Starting Mix, and Fossil Generation Outcomes · 2000–2024",
        )
        for fig, title in zip(self.render(), titles):
            with self.subTest(title=title):
                try:
                    texts = [text.get_text() for text in fig.texts]
                    self.assertEqual(texts.count(title), 1)
                    heading = fig.texts[texts.index(title)]
                    self.assertGreater(heading.get_position()[1], 0.95)
                    self.assertNotRegex(title, r"\bQ[1-6]\b")
                    self.assertEqual(sum(text.startswith("Source: OWID") for text in texts), 1)
                    self.assertEqual(sum(text.startswith("Planned Interaction:") for text in texts), 1)
                    fig.canvas.draw()
                    bounds = heading.get_window_extent(fig.canvas.get_renderer())
                    self.assertGreaterEqual(bounds.x0, 0)
                    self.assertLessEqual(bounds.x1, fig.bbox.width)
                finally:
                    plt.close(fig)
        self.assertIn("Demand", titles[2])
        self.assertNotIn("Domestic Electricity Generation", titles[2])

    def test_other_windows_and_no_example_render_without_warnings(self):
        import matplotlib.pyplot as plt

        for settings, example in (
            (replace(self.settings, start_year=2004), True),
            (replace(self.settings, start_year=2010, q6_selected_pair=6), True),
            (replace(self.settings, q5_zoom_twh=0.001), True),
            (self.settings, False),
        ):
            with self.subTest(start=settings.start_year, example=example), warnings.catch_warnings():
                warnings.simplefilter("error")
                for fig in self.render(settings, example):
                    try:
                        fig.canvas.draw()
                    finally:
                        plt.close(fig)

    def test_q1_note_follows_the_configured_groups(self):
        import matplotlib.pyplot as plt
        from sketches.q156_plots import world_mix
        from sketches.settings import SourceGroup

        split = self.settings.groups[:4] + (
            SourceGroup("Bioenergy", ("bioenergy",), "#5A9A78"),
            SourceGroup("Other Renewables", ("other_renewables_excluding_bioenergy",), "#9C9C5A"),
        )
        for settings, expected, absent in (
            (self.settings, "the 8 layers add up", "the 9 layers"),
            (replace(self.settings, groups=split), "the 9 layers add up", "Other Clean"),
        ):
            with self.subTest(groups=len(settings.groups)):
                fig = world_mix(load_world(), settings)
                try:
                    note = " ".join(next(text.get_text() for text in fig.texts
                                         if text.get_text().startswith("Source: OWID")).split())
                    self.assertIn(expected, note)
                    self.assertNotIn(absent, note)
                finally:
                    plt.close(fig)

    def test_q5_note_names_a_configured_example(self):
        import matplotlib.pyplot as plt

        for settings, expected, absent in (
            (self.settings, "Example rule:", "set in the config"),
            (replace(self.settings, q5_example="Germany"), "Example: Germany, set in the config (q5.example).",
             "Example rule:"),
        ):
            with self.subTest(example=settings.q5_example):
                fig = self.render(settings)[1]
                try:
                    note = " ".join(next(text.get_text() for text in fig.texts
                                         if text.get_text().startswith("Source: OWID")).split())
                    self.assertIn(expected, note)
                    self.assertNotIn(absent, note)
                finally:
                    plt.close(fig)

    def test_q6_demand_axis_with_one_country(self):
        import matplotlib.pyplot as plt

        # Only the United States is left, with negative demand growth; the other group is empty.
        settings = replace(self.settings, end_year=2001, min_generation_twh=3000.0)
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            fig = self.render(settings)[2]
        try:
            ax = fig.axes[0]
            ratios = [x for collection in ax.collections for x in collection.get_offsets()[:, 0]]
            self.assertEqual(len(ratios), 1)
            self.assertLess(ratios[0], 1)  # Demand fell: below 1× on the ratio axis.
            left, right = ax.get_xlim()
            self.assertLess(left, ratios[0])
            self.assertLess(ratios[0], right)
            self.assertLess(left, 1)
            self.assertLess(1, right)  # The no-change line stays on the chart.
            self.assertIn("No countries", [text.get_text() for text in ax.texts])
        finally:
            plt.close(fig)

    def test_q1_fossil_line_is_the_top_of_the_fossil_layers(self):
        import matplotlib.pyplot as plt
        from sketches.q156_plots import world_mix

        fig = world_mix(load_world(), self.settings)
        try:
            world = window(load_world(), self.settings)
            for ax, unit in zip(fig.axes[:2], ("share_pct", "twh")):
                table = mix_table(world, self.settings, unit)
                line = next(line for line in ax.get_lines() if len(line.get_xdata()) == len(table))
                expected = table[["Coal", "Gas", "Oil"]].sum(axis=1).to_numpy()
                np.testing.assert_allclose(line.get_ydata(), expected)
                # The stack's top is total generation (or 100%).
                top = ax.collections[-1].get_paths()[0].vertices[:, 1].max()
                self.assertAlmostEqual(top, table.drop(columns="year").sum(axis=1).max(), places=6)
        finally:
            plt.close(fig)

    def test_q1_unknown_values_are_not_summed_as_zero(self):
        import matplotlib.pyplot as plt
        from sketches.q156_plots import world_mix

        world = load_world()
        for year, column in ((2010, "coal_twh"), (2024, "coal_twh")):
            with self.subTest(year=year):
                broken = world.copy()
                broken.loc[broken["year"].eq(year), [column, "coal_share_pct"]] = np.nan
                fig = world_mix(broken, self.settings)
                try:
                    texts = [text.get_text() for ax in fig.axes for text in ax.texts]
                    titles = [ax.get_title(loc="left") for ax in fig.axes]
                    if year == 2010:  # The cursor year: the tooltip says unknown instead of a smaller sum.
                        tooltip = next(text for text in texts if text.startswith("2010"))
                        self.assertIn("Fossil unknown · unknown", tooltip)
                        self.assertIn("Total unknown", tooltip)
                        self.assertIn("Clean 32.5%", tooltip)
                    else:  # The end year: no total or fossil label from another year.
                        self.assertIn("World: Generation (TWh), Total 15,279 → unknown", titles)
                        self.assertFalse(any(text.startswith("Fossil 18,") or text.startswith("Fossil 59")
                                             for text in texts))
                finally:
                    plt.close(fig)

    def test_q6_note_medians_match_the_drawn_dots(self):
        import matplotlib.pyplot as plt
        from sketches.q156_plots import demand_pairs

        q6, left_out = q6_countries(self.table)
        q6 = q6.copy()
        fell = q6.index[q6["fossil_reduced"]]
        q6.loc[fell[0], "demand_growth_pct"] = -100.0  # Demand fell to zero.
        q6.loc[fell[1], "demand_growth_pct"] = np.nan
        fig = demand_pairs(q6, left_out, matched_pairs(q6, 6), self.settings)
        try:
            note = " ".join(next(text.get_text() for text in fig.texts
                                 if text.get_text().startswith("Source: OWID")).split())
            drawn = q6.loc[q6["fossil_reduced"] & q6["demand_growth_pct"].gt(-100), "demand_growth_pct"]
            self.assertIn(f"Median demand growth: {drawn.median():+,.1f}% where fossil generation fell", note)
            self.assertIn("(countries in the demand chart)", note)
            self.assertIn("1 country without demand data", note)
            self.assertIn("1 country whose demand fell to zero", note)
        finally:
            plt.close(fig)

    def test_q6_panels_show_every_country_and_the_group_medians(self):
        import matplotlib.pyplot as plt
        from sketches.q156_plots import MIX_PANELS

        q6, _ = q6_countries(self.table)
        fig = self.render()[2]
        try:
            demand, *mix = fig.axes
            self.assertEqual(demand.get_xscale(), "log")
            self.assertEqual([ax.get_title(loc="left") for ax in mix],
                             [f"{name} Share in {self.settings.start_year}" for name, _ in MIX_PANELS])
            for ax, values in [(demand, 1 + q6["demand_growth_pct"] / 100)] + [
                    (ax, q6[column]) for ax, (_, column) in zip(mix, MIX_PANELS)]:
                dots = [c for c in ax.collections if len(c.get_offsets()) > 2]  # Not the pair rings.
                self.assertEqual(sum(len(c.get_offsets()) for c in dots), int(values.notna().sum()))
                for reduced, collection in zip((True, False), dots):
                    expected = values[q6["fossil_reduced"].eq(reduced)].median()
                    self.assertAlmostEqual(np.median(np.ma.getdata(collection.get_offsets())[:, 0]), expected)
        finally:
            plt.close(fig)

    def test_q6_pair_buttons_do_not_cover_the_legend_or_charts(self):
        import matplotlib.pyplot as plt

        for pairs in (6, 12, 35):
            with self.subTest(pairs=pairs):
                fig = self.render(replace(self.settings, q6_pairs=pairs))[2]
                try:
                    fig.canvas.draw()
                    renderer = fig.canvas.get_renderer()
                    buttons = [text.get_bbox_patch().get_window_extent(renderer) for text in fig.texts
                               if text.get_bbox_patch() is not None and " – " in text.get_text()
                               and not text.get_text().startswith("Planned Interaction:")]
                    self.assertEqual(len(buttons), pairs)
                    legend = fig.legends[0].get_window_extent(renderer)
                    charts = max(ax.get_tightbbox(renderer).y1 for ax in fig.axes[:2])
                    self.assertGreater(legend.y0, charts)
                    for i, button in enumerate(buttons):
                        self.assertFalse(button.overlaps(legend))
                        self.assertGreater(button.y0, legend.y1)
                        self.assertLess(button.x1, fig.bbox.width)
                        self.assertFalse(any(button.overlaps(other) for other in buttons[i + 1:]))
                finally:
                    plt.close(fig)

    def test_label_layers_keeps_zero_layers_in_stack_order(self):
        import matplotlib.pyplot as plt
        from sketches.q156_plots import label_layers

        # As in Paraguay with Nuclear listed first: four zero-height layers share a middle, and
        # sorting them by name would put Nuclear among the fossil names.
        fig, ax = plt.subplots()
        try:
            ax.set_xlim(2000, 2024)
            ax.set_ylim(0, 100)
            stack = ["Coal", "Gas", "Oil", "Nuclear", "Hydro"]
            label_layers(ax, 2024, [(0, name, "#999999") for name in stack[:4]] + [(50, "Hydro", "#3AA7A3")],
                         (("Fossil", stack[:3]), ("Clean", stack[3:])))
            spots = {text.get_text(): text.get_position()[1] for text in ax.texts}
            self.assertEqual(sorted(stack, key=spots.get), stack)
        finally:
            plt.close(fig)

    def test_mix_charts_set_fossil_apart_from_clean(self):
        import matplotlib.pyplot as plt
        from matplotlib.colors import to_rgba
        from sketches.q156_plots import FOSSIL_COLORS, world_mix
        from sketches.settings import SourceGroup

        long_names = self.settings.groups[:4] + (
            SourceGroup("Bioenergy", ("bioenergy",), "#5A9A78"),
            SourceGroup("Other Renewables", ("other_renewables_excluding_bioenergy",), "#9C9C5A"),
        )
        fossil = ["Coal", "Gas", "Oil"]
        for case, settings in (("default", self.settings), ("long names", replace(self.settings, groups=long_names))):
            clean = [group.label for group in settings.groups]
            q1 = world_mix(load_world(), settings)
            try:
                charts = q1.axes[:2]
                q1.canvas.draw()
                renderer = q1.canvas.get_renderer()
                for ax in charts:
                    with self.subTest(case=case, chart=ax.get_title(loc="left")):
                        # Fossil layers are grays from dark to light, clean layers keep the config
                        # colors, and no outline zigzags between them.
                        layers = ax.collections[:len(fossil) + len(clean)]
                        colors = [tuple(layer.get_facecolor()[0]) for layer in layers]
                        expected = [FOSSIL_COLORS[name] for name in fossil] + [g.color for g in settings.groups]
                        self.assertEqual(colors, [to_rgba(color) for color in expected])
                        lightness = [sum(color[:3]) for color in colors[:len(fossil)]]
                        self.assertEqual(lightness, sorted(set(lightness)))
                        self.assertTrue(all(np.all(layer.get_linewidths() == 0) for layer in layers))
                        # Names stay in stack order by group, and each bracket word sits right of
                        # every name, within its own group's names.
                        texts = {text.get_text(): text for text in ax.texts}
                        spots = {label: texts[label].get_position()[1] for label in fossil + clean}
                        self.assertLess(max(spots[label] for label in fossil),
                                        min(spots[label] for label in clean))
                        names = {label: text.get_window_extent(renderer) for label, text in texts.items()}
                        right_edge = max(names[label].x1 for label in fossil + clean)
                        for group, labels in (("Fossil", fossil), ("Clean", clean)):
                            word = names[group]
                            middles = [(names[label].y0 + names[label].y1) / 2 for label in labels]
                            self.assertGreater(word.x0, right_edge)
                            self.assertLessEqual(min(middles) - 1, (word.y0 + word.y1) / 2)
                            self.assertLessEqual((word.y0 + word.y1) / 2, max(middles) + 1)
                with self.subTest(case=case):
                    # The left chart's names and brackets stay clear of the right chart's axis labels.
                    right_edge = max(text.get_window_extent(renderer).x1 for text in charts[0].texts)
                    self.assertLess(right_edge, charts[1].get_tightbbox(renderer).x0)
            finally:
                plt.close(q1)

    def q5_detail(self, example, countries=None):
        """Q5 with a configured example; countries replaces the rows behind the detail charts only."""
        from sketches.q156_plots import fossil_outcome_scatter

        settings = replace(self.settings, q5_example=example)
        row = q5_example(self.table, settings)
        return fossil_outcome_scatter(self.table, self.countries if countries is None else countries, settings,
                                      row), row

    def test_q5_detail_lines_are_the_dot(self):
        import matplotlib.pyplot as plt

        for example in ("South Africa", "Germany", "Poland"):
            with self.subTest(example=example):
                fig, row = self.q5_detail(example)
                try:
                    left, right = fig.axes[2:4]
                    lines = {line.get_label(): line for ax in (left, right) for line in ax.get_lines()}
                    share, fossil, clean = (lines[name] for name in ("clean_share_pct", "fossil_twh", "clean_twh"))
                    # The ends of the lines differ by exactly the dot's x and y.
                    self.assertAlmostEqual(share.get_ydata()[-1] - share.get_ydata()[0], row["d_clean_share_pp"],
                                           places=6)
                    self.assertAlmostEqual(fossil.get_ydata()[-1] - fossil.get_ydata()[0], row["d_fossil_twh"],
                                           places=6)
                    self.assertEqual(fossil.get_linestyle(), "-")
                    self.assertEqual(clean.get_linestyle(), "--")
                    self.assertEqual(share.get_linestyle(), "--")
                    notes = [text.get_text() for ax in (left, right) for text in ax.texts]
                    self.assertIn(f"({row['d_clean_share_pp']:+,.1f} pp)\nIts change is the scatterplot's x", " ".join(notes))
                    self.assertIn(f"({row['d_fossil_twh']:+,.1f} TWh), the scatterplot's y", " ".join(notes))
                    for ax in (left, right):  # Both ends of the period are labeled, whatever the window.
                        self.assertEqual([ax.get_xticks()[0], ax.get_xticks()[-1]], [2000, 2024])
                    low, high = left.get_ylim()
                    self.assertEqual(low, 0)
                    self.assertLessEqual(high, 100)
                    self.assertGreaterEqual(high, np.nanmax(share.get_ydata()))
                finally:
                    plt.close(fig)

    def test_share_axis_top_is_round_and_at_most_100(self):
        from sketches.q156_plots import share_top

        rows = window(self.countries.loc[self.countries["iso3"].isin(self.table["iso3"])], self.settings)
        for country, peak in rows.groupby("country")["clean_share_pct"].max().items():
            with self.subTest(country=country):
                top = share_top(peak)
                self.assertGreaterEqual(top, peak)
                self.assertLessEqual(top, 100)
                self.assertEqual(top % 5, 0)
        self.assertEqual(share_top(float("nan")), 100)

    def test_q5_detail_keeps_unknown_values_unknown(self):
        import matplotlib.pyplot as plt

        broken = self.countries.copy()
        africa = broken["country"].eq("South Africa")
        broken = broken.loc[~(africa & broken["year"].eq(2012))].copy()  # A missing row, not just a blank.
        africa = broken["country"].eq("South Africa")
        broken.loc[africa & broken["year"].eq(2024), "clean_share_pct"] = np.nan
        broken.loc[africa & broken["year"].eq(2010), "fossil_twh"] = np.nan
        broken.loc[africa & broken["year"].eq(2024), "clean_twh"] = np.nan
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            fig, _ = self.q5_detail("South Africa", broken)
        try:
            left, right = fig.axes[2:4]
            lines = {line.get_label(): line for ax in (left, right) for line in ax.get_lines()}
            years = list(lines["clean_share_pct"].get_xdata())
            self.assertEqual(years, list(range(2000, 2025)))  # The missing year stays in place as a gap.
            self.assertTrue(np.isnan(lines["clean_share_pct"].get_ydata()[years.index(2012)]))
            self.assertTrue(np.isnan(lines["clean_share_pct"].get_ydata()[-1]))
            self.assertTrue(np.isnan(lines["fossil_twh"].get_ydata()[years.index(2010)]))
            texts = [text.get_text() for ax in fig.axes for text in ax.texts]
            self.assertIn("2000 → 2024: 6.9% → unknown (change unknown)\nIts change is the scatterplot's x", texts)
            self.assertIn("Clean 2000 → 2024: 14.6 → unknown (change unknown)", " ".join(texts))
            self.assertFalse(any("nan" in text.lower() for text in texts))
            # A line that stops early keeps its name, which says its end is unknown.
            self.assertIn("Clean 2024: unknown", [text.get_text() for text in left.texts])
            self.assertIn("Clean 2024: unknown", [text.get_text() for text in right.texts])
            self.assertIn("Fossil 209", [text.get_text() for text in right.texts])
        finally:
            plt.close(fig)

    def test_q5_end_names_stay_apart_and_outside_examples_are_marked(self):
        import matplotlib.pyplot as plt

        close = self.countries.copy()
        end = close["country"].eq("South Africa") & close["year"].eq(2024)
        close.loc[end, "clean_twh"] = close.loc[end, "fossil_twh"]  # Both lines end at the same height.
        fig, _ = self.q5_detail("South Africa", close)
        try:
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            names = [text.get_window_extent(renderer) for text in fig.axes[3].texts
                     if text.get_text().startswith(("Fossil ", "Clean ")) and "→" not in text.get_text()]
            self.assertEqual(len(names), 2)
            self.assertFalse(names[0].overlaps(names[1]))
        finally:
            plt.close(fig)
        from matplotlib.text import Text

        quadrants = ("Share Up, Fossil Up", "Share Up, Fossil Down", "Share Not Up")
        for example, note in (("Germany", "Germany (-159 TWh) is below the band"),
                              ("China", "China (+5,124 TWh) is above the band"),
                              ("United Arab Emirates", "United Arab Emirates (+81 TWh) is above the band")):
            with self.subTest(example=example):
                fig, _ = self.q5_detail(example)
                try:
                    zoom = fig.axes[1]
                    fig.canvas.draw()
                    renderer = fig.canvas.get_renderer()
                    # Text.get_window_extent measures the words only, not the note's arrow.
                    texts = {text.get_text(): Text.get_window_extent(text, renderer) for text in zoom.texts}
                    self.assertIn(note, texts)
                    # The note stays inside the chart and clear of the quadrant names.
                    self.assertTrue(zoom.get_window_extent(renderer).contains(texts[note].x0, texts[note].y0))
                    self.assertTrue(zoom.get_window_extent(renderer).contains(texts[note].x1, texts[note].y1))
                    self.assertFalse(any(texts[note].overlaps(texts[name]) for name in quadrants))
                finally:
                    plt.close(fig)

    def test_year_axes_label_both_endpoints(self):
        import matplotlib.pyplot as plt
        from sketches.q156_plots import fossil_outcome_scatter, world_mix

        for start, end in ((2005, 2020), (2000, 2023), (2001, 2024)):
            with self.subTest(start=start, end=end):
                settings = replace(self.settings, start_year=start, end_year=end, q5_example="Germany")
                table = fossil_outcomes(self.countries, settings)
                q1 = world_mix(load_world(), settings)
                q5 = fossil_outcome_scatter(table, self.countries, settings, q5_example(table, settings))
                try:
                    for ax in (*q1.axes[:2], *q5.axes[2:4]):
                        ticks = list(ax.get_xticks())
                        self.assertEqual([ticks[0], ticks[-1]], [start, end])
                        self.assertTrue(all(b - a > (end - start) / 12 for a, b in zip(ticks, ticks[1:])))
                finally:
                    plt.close(q1)
                    plt.close(q5)

    def test_q1_tooltip_covers_no_layer(self):
        import matplotlib.pyplot as plt
        from sketches.q156_plots import world_mix

        for start in (2000, 2004, 2010, 2023):
            with self.subTest(start=start):
                settings = replace(self.settings, start_year=start)
                fig = world_mix(load_world(), settings)
                try:
                    ax = fig.axes[1]
                    fig.canvas.draw()
                    cursor = 2010 if start < 2010 else start
                    tooltip = next(text for text in ax.texts if text.get_text().startswith(str(cursor)))
                    box = tooltip.get_bbox_patch().get_window_extent(fig.canvas.get_renderer()).transformed(
                        ax.transData.inverted())
                    twh = mix_table(window(load_world(), settings), settings, "twh")
                    under = twh.loc[twh["year"].between(math.floor(box.x0), math.ceil(box.x1))]
                    self.assertGreater(box.y0, under.drop(columns="year").sum(axis=1).max())
                    self.assertLess(box.y1, ax.get_ylim()[1])
                finally:
                    plt.close(fig)


class ReportConsistencyTests(unittest.TestCase):
    """The report's Q1, Q5 and Q6 tables must match what the default sketches compute."""

    @classmethod
    def setUpClass(cls):
        cls.results = q156_results()
        cls.samples = q156_samples(cls.results)
        cls.settings = load_settings()
        cls.sketch = fossil_outcomes(load_country_year(), cls.settings)

    def test_report_baseline_is_the_default_config(self):
        report = self.results["settings"]
        for name in ("start_year", "end_year", "min_generation_twh", "q5_zoom_twh", "q5_example",
                     "q6_pairs", "q6_selected_pair", "groups"):
            self.assertEqual(getattr(report, name), getattr(self.settings, name))

    def test_report_does_not_read_the_sketch_config(self):
        from unittest import mock

        with mock.patch("sketches.settings.tomllib.load", side_effect=AssertionError("config was read")):
            settings = baseline_settings()
            results = q156_results()
            samples = q156_samples(results)
            f = facts(results)
            for section in (q1_section, q5_section, q6_section):
                section(results, f, lambda name: samples[name].to_string())
            cutoff_section(results, lambda table: table.to_string())
        self.assertEqual([group.label for group in settings.groups],
                         ["Wind", "Solar", "Hydro", "Nuclear", "Other Clean"])
        self.assertIsNone(settings.q5_example)

    def test_samples_match_sketch_values(self):
        q5 = self.samples["q5_fossil_outcomes_sample"].set_index("Country")
        sketch = self.sketch.set_index("country").loc[q5.index]
        np.testing.assert_allclose(q5["Fossil Generation Change (TWh)"], sketch["d_fossil_twh"])
        self.assertEqual(q5["Outcome"].tolist(), sketch["outcome"].map(OUTCOME_LABELS).tolist())
        self.assertIn("South Africa", q5.index)

        q6, _ = q6_countries(self.sketch)
        pairs = matched_pairs(q6, self.settings.q6_pairs)
        report_pairs = self.samples["q6_matched_pairs"]
        self.assertEqual(report_pairs["Fossil Fell"].tolist(), pairs["country_reduced"].tolist())
        self.assertEqual(report_pairs["Fossil Did Not Fall"].tolist(), pairs["country_other"].tolist())

        share = self.samples["q1_world_share_sample"]
        self.assertEqual(share["Year"].tolist(), [2000, 2004, 2008, 2012, 2016, 2020, 2024])
        columns = [column for column in share.columns if column.endswith("(%)")]
        np.testing.assert_allclose(share[columns].sum(axis=1), 100, atol=0.01, rtol=0)


def render(results):
    """The report text for Q1, Q6 and the cutoffs, with tables left out and line breaks as spaces."""
    f = facts(results)
    sections = {
        "q1": q1_section(results, f, lambda name: ""),
        "q6": q6_section(results, f, lambda name: ""),
        "cutoffs": cutoff_section(results, lambda table: ""),
    }
    return {name: " ".join(text.split()) for name, text in sections.items()}


class ReportTextTests(unittest.TestCase):
    """The M1 feedback points the report text answers: the start year, the sensitivity, the
    hypothesis, and the starting-mix half of Q6."""

    @classmethod
    def setUpClass(cls):
        cls.results = q156_results()
        cls.text = render(cls.results)

    def test_q1_gives_total_generation(self):
        self.assertIn("the clean share rose from 35.3% to 40.9%, but total generation grew from 15,279 TWh to "
                      "30,930 TWh.", self.text["q1"])
        self.assertIn("So fossil generation also grew, from 9,879 TWh to 18,276 TWh.", self.text["q1"])

    def test_q1_directions_follow_the_data(self):
        f = facts(self.results)
        f.update(clean_start=50, clean_end=40, generation_start=200, generation_end=100, fossil_share_start=50,
                 fossil_share_end=60, fossil_start=100, fossil_end=60)
        text = q1_section(self.results, f, lambda name: "")
        self.assertIn("the clean share fell from 50.0% to 40.0%, and total generation fell from 200 TWh to 100 TWh.", text)
        self.assertIn("Fossil generation fell from 100 TWh to 60 TWh.", text)
        self.assertNotIn("also grew", text)

    def test_start_mix_answers_the_other_half_of_q6(self):
        mix = self.results["start_mix"].set_index("fossil_reduced")
        self.assertEqual(mix["countries"].to_dict(), {True: 35, False: 69})
        self.assertEqual(mix["nuclear_countries"].to_dict(), {True: 17, False: 11})
        q6 = self.results["q6"]
        for reduced in (True, False):
            group = q6.loc[q6["fossil_reduced"].eq(reduced)]
            for label in START_MIX:
                self.assertAlmostEqual(mix.loc[reduced, label], group[f"{label.lower()}_share_pct_start"].median())
        np.testing.assert_allclose(mix.loc[True, ["Clean", "clean_q1", "clean_q3"]], [51.27, 23.48, 73.30], atol=0.01)
        np.testing.assert_allclose(mix.loc[False, ["Clean", "clean_q1", "clean_q3"]], [23.86, 5.62, 50.15], atol=0.01)
        self.assertIn("the median 2000 clean share was higher: 51.3% against 23.9%.", self.text["q6"])
        self.assertIn("The middle halves overlap", self.text["q6"])

    @staticmethod
    def start_table(reduced, coal):
        columns = [f"{label.lower()}_share_pct_start" for label in START_MIX] + ["nuclear_share_pct_start"]
        table = pd.DataFrame({name: [10.0, 30.0, 50.0, 70.0][:len(reduced)] for name in columns})
        table["coal_share_pct_start"] = coal
        return table.assign(country=list("ABCD")[:len(reduced)], fossil_reduced=reduced)

    def test_start_mix_follows_the_data(self):
        table = self.start_table([True, True, False, False], [10.0, 30.0, 50.0, 70.0])
        self.assertEqual(start_mix_summary(table).set_index("fossil_reduced").loc[True, "Coal"], 20.0)
        table.loc[0, "coal_share_pct_start"] = 90.0
        after = start_mix_summary(table).set_index("fossil_reduced")
        self.assertEqual(after.loc[True, "Coal"], 60.0)
        self.assertEqual(after.loc[False, "Coal"], 60.0)
        self.assertIn("middle halves do not overlap", start_mix_text(start_mix_summary(
            self.start_table([True, True, False, False], [10.0, 30.0, 50.0, 70.0]).assign(
                clean_share_pct_start=[80.0, 90.0, 10.0, 20.0])), 2000))

    def test_start_mix_needs_both_groups_and_known_shares(self):
        empty = start_mix_summary(self.start_table([True, True], [10.0, 30.0]))
        self.assertIn("cannot be compared", start_mix_text(empty, 2000))
        unknown = self.start_table([True, False], [10.0, None])
        with self.assertRaisesRegex(ValueError, "unknown for B"):
            start_mix_summary(unknown)

    def test_hypothesis_check_uses_countries_whose_share_rose(self):
        h = self.results["hypothesis"]
        self.assertEqual((h["eligible"], h["countries"], h["fell"], h["other"]), (79, 79, 35, 44))
        self.assertEqual((h["slower"], h["slower_fell"], h["faster"], h["faster_fell"]), (40, 30, 39, 5))
        self.assertEqual(h["faster_fell_names"], ["Costa Rica", "Ethiopia", "Kenya", "Nepal", "Uruguay"])
        self.assertIn("more frequent cuts there would contradict it", self.text["q6"])
        self.assertIn("This is consistent with the hypothesis but does not show a cause.", self.text["q6"])
        self.assertIn("The fast-growing exceptions are Costa Rica, Ethiopia, Kenya, Nepal, and Uruguay.", self.text["q6"])

    @staticmethod
    def hypothesis(rows):
        return hypothesis_text(hypothesis_check(pd.DataFrame(
            rows, columns=["country", "d_clean_share_pp", "demand_growth_pct", "fossil_reduced"],
        )))

    def test_hypothesis_reading_follows_the_rates(self):
        consistent = [("A", 1, 0, True), ("B", 1, 10, True), ("C", 1, 100, False), ("D", 1, 200, False),
                      ("E", -1, 500, True)]  # E's clean share did not rise, so it is left out.
        text = self.hypothesis(consistent)
        self.assertIn("Among the 4 countries whose clean share rose", text)
        self.assertIn("fell in 2 of the 2 at or below it", text)
        self.assertIn("consistent with the hypothesis", text)
        reversed_rows = [(c, d, g, not fell) for c, d, g, fell in consistent]
        self.assertIn("runs against the hypothesis", self.hypothesis(reversed_rows))
        equal = [("A", 1, 0, True), ("B", 1, 10, False), ("C", 1, 100, True), ("D", 1, 200, False)]
        self.assertIn("rates are equal, so the data do not support", self.hypothesis(equal))
        one_exception = [("A", 1, 0, True), ("B", 1, 10, True), ("C", 1, 20, False), ("D", 1, 100, True),
                         ("E", 1, 200, False), ("F", 1, 300, False)]
        self.assertIn("The fast-growing exception is D.", self.hypothesis(one_exception))

    def test_q5_without_a_selected_country(self):
        results = {**self.results, "example": None}
        text = q5_section(results, facts(results), lambda name: "")
        self.assertIn("No country fits the sketch's selection rule", text)
        self.assertIn("draws no line charts", text)
        self.assertNotIn("trace the selected country", text)

    def test_hypothesis_ties_empty_groups_and_missing_demand(self):
        ties = [("A", 1, 50, True), ("B", 1, 50, False), ("C", 1, 50, True), ("D", 1, 50, False)]
        self.assertIn("cannot be evaluated", self.hypothesis(ties))  # all at the median: no faster group
        self.assertIn("cannot be evaluated", self.hypothesis([("A", 1, 0, False), ("B", 1, 10, False)]))
        missing = [("A", 1, 0, True), ("B", 1, None, True), ("C", 1, 100, False), ("D", 1, 200, False)]
        self.assertIn("the 3 of the 4 countries whose clean share rose that have demand data", self.hypothesis(missing))

    def test_cutoffs_explain_the_proposal_start_year(self):
        text = self.text["cutoffs"]
        self.assertIn("the proposal started in 2010", text)
        self.assertIn("both start years compare 108 countries", text)
        self.assertIn("Whether they are a majority depends on the cutoffs.", text)
        self.assertIn("The proposal's 2010 start at 10 TWh gives 49.4% (41 of 83).", text)

    def test_majority_reading_follows_the_counts(self):
        def grid(*pairs):
            return pd.DataFrame(pairs, columns=["share_up_fossil_up", "share_up"])

        # 10001 of 20000 rounds to 50.0% but is more than half.
        self.assertIn("in all 2 settings", majority_text(grid((6, 10), (10001, 20000))))
        self.assertIn("in any of the 2 settings", majority_text(grid((5, 10), (4, 10))))
        self.assertEqual(majority_text(grid((6, 10), (4, 10))), "Whether they are a majority depends on the cutoffs.")
        with_empty = majority_text(grid((6, 10), (4, 10), (0, 0)))
        self.assertIn("depends on the cutoffs. 1 setting has no country whose clean share rose", with_empty)
        self.assertEqual(majority_text(grid((0, 0))), "No setting has a country whose clean share rose.")


class ReportBuildTests(unittest.TestCase):
    """The committed Q1, Q5 and Q6 report and its CSVs are what prep/report_q156.py builds."""

    def test_markdown_distinguishes_unknown_zero_and_boolean(self):
        table = pd.DataFrame({"Value": [None, 0, "008", True, False, "a|b"]})
        result = markdown_table(table)
        for expected in ("No Data", "| 0 |", "| 008 |", "| Yes |", "| No |", "a\\|b"):
            self.assertIn(expected, result)

    def test_report_and_csvs_rebuild_reproducibly(self):
        committed = ROOT / "reports" / TABLE_DIR
        expected = {f"{name}.csv" for name in q156_samples(q156_results())} | {"feature_dictionary.csv"}
        self.assertEqual({path.name for path in committed.glob("*.csv")}, expected)
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            # The Q2–Q4 report and tables share the folder; the build must leave them alone.
            shared = {"dataHandlingQ2Q3Q4.md": "Q2–Q4 report\n", "tablesQ2Q3Q4/feature_dictionary.csv": "Q2–Q4 fields\n"}
            for name, content in shared.items():
                (Path(directory) / name).parent.mkdir(parents=True, exist_ok=True)
                (Path(directory) / name).write_text(content)
            report = build_report(Path(directory))
            for name, content in shared.items():
                self.assertEqual((Path(directory) / name).read_text(), content, name)
            written = {path.relative_to(directory).as_posix() for path in Path(directory).rglob("*") if path.is_file()}
            self.assertEqual(written, {*shared, REPORT_NAME, *(f"{TABLE_DIR}/{name}" for name in expected)})
            text = report.read_text()
            self.assertEqual(report.name, REPORT_NAME)
            self.assertEqual(text, (ROOT / "reports" / REPORT_NAME).read_text())
            built = report.parent / TABLE_DIR
            self.assertEqual({path.name for path in built.glob("*.csv")}, expected)
            for filename in expected:
                self.assertEqual((built / filename).read_bytes(), (committed / filename).read_bytes(), filename)
            self.assertEqual(re.findall(r"^## (Q[0-9]+) —", text, re.MULTILINE), ["Q1", "Q5", "Q6"])
            # Other start years and robustness.csv belong only to the cutoff section.
            cutoffs = re.search(r"^## Cutoffs and Sensitivity\n.*?(?=^## )", text, re.MULTILINE | re.DOTALL)
            self.assertIsNotNone(cutoffs)
            self.assertIn("robustness.csv", cutoffs.group())
            rest = text.replace(cutoffs.group(), "")
            self.assertNotIn("robustness.csv", rest)
            self.assertNotIn("2010", rest)
            # Links point at committed files, not at the ignored outputs/sketches/ folder.
            self.assertNotIn("../outputs/sketches/", text)
            links = re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", text)
            self.assertTrue(links)
            for link in links:
                target = (report.parent / link) if link.startswith(TABLE_DIR) else (ROOT / "reports" / link)
                self.assertTrue(target.resolve().is_file(), link)


if __name__ == "__main__":
    unittest.main()
