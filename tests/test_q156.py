"""Tests for Q1, Q5 and Q6: the world mix, fossil outcomes, and demand-growth pairs."""

from dataclasses import replace
import math
import unittest
import warnings

import numpy as np
import pandas as pd

from prep.report_q156 import baseline_settings, q156_results, q156_samples
from sketches.data import load_country_year
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
        self.assertEqual((settings.q6_zoom_pct, settings.q6_pairs, settings.q6_selected_pair), (300, 6, 1))

    def test_rejects_invalid_q5_q6_settings(self):
        settings = load_settings()
        for change in (
            {"q5_zoom_twh": 0}, {"q5_zoom_twh": -1}, {"q5_zoom_twh": math.nan}, {"q5_zoom_twh": True},
            {"q6_zoom_pct": math.inf}, {"q6_pairs": 0}, {"q6_pairs": 2.0},
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
            demand_pairs(q6, left_out, matched_pairs(q6, settings.q6_pairs), group_summary(q6), settings),
        )

    def test_titles_notes_and_interaction_boxes(self):
        import matplotlib.pyplot as plt
        from sketches.plots import set_style

        set_style()
        titles = (
            "Domestic Electricity Generation: World Mix by Source · 2000–2024",
            "Domestic Electricity Generation: Clean-Share Change vs. Fossil Change · 2000–2024",
            "Electricity Demand Growth and Fossil Generation Outcomes · 2000–2024",
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

    def test_q6_overview_axis_with_one_country(self):
        import matplotlib.pyplot as plt

        # Only the United States is left, with negative demand growth.
        settings = replace(self.settings, end_year=2001, min_generation_twh=3000.0)
        fig = self.render(settings)[2]
        try:
            ax = fig.axes[0]
            growth = ax.collections[0].get_offsets()[:, 0].tolist() + ax.collections[1].get_offsets()[:, 0].tolist()
            self.assertEqual(len(growth), 1)
            self.assertLess(growth[0], 0)
            left, right = ax.get_xlim()
            self.assertLess(left, right)
            self.assertTrue(all(left < value < right for value in growth))
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
        for name in ("start_year", "end_year", "min_generation_twh", "q5_zoom_twh", "q5_example", "q6_zoom_pct",
                     "q6_pairs", "q6_selected_pair", "groups"):
            self.assertEqual(getattr(report, name), getattr(self.settings, name))

    def test_report_does_not_read_the_sketch_config(self):
        from unittest import mock

        with mock.patch("sketches.settings.tomllib.load", side_effect=AssertionError("config was read")):
            settings = baseline_settings()
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


if __name__ == "__main__":
    unittest.main()
