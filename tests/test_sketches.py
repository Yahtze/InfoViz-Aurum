"""Tests for the EDA data contract, independent of the final D3 app."""

from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

from sketches.data import comparison, extremes, load_country_year, snapshot, source_changes
from sketches.settings import CLEAN_SOURCES, ROOT, SourceGroup, load_settings


class SketchDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = load_settings()
        cls.countries = load_country_year()
        cls.compared = comparison(cls.countries, cls.settings)

    def test_snapshot_keeps_missing_values_and_non_map_places(self):
        current = snapshot(self.countries, 2024)
        self.assertEqual(len(current), 221)
        self.assertEqual(int(current["clean_share_pct"].isna().sum()), 25)
        self.assertEqual(int((~current["on_map"]).sum()), 8)
        self.assertNotIn("World", current["country"].tolist())
        self.assertEqual(
            current.loc[current["country"].eq("Algeria"), "iso_numeric"].iloc[0], "012",
        )

    def test_default_comparison_matches_pinned_table(self):
        expected = pd.read_csv(ROOT / "data/processed/comparison_2000_2024.csv").set_index("iso3")
        actual = self.compared.set_index("iso3").loc[expected.index]
        self.assertEqual(len(actual), 108)
        np.testing.assert_allclose(
            actual["d_clean_share_pp"], expected["d_clean_share_pp"], atol=0.00011, rtol=0,
        )
        self.assertEqual(int(actual["d_clean_share_pp"].gt(0).sum()), 79)
        for field, year in (("start", 2000), ("end", 2024)):
            np.testing.assert_allclose(
                actual[f"clean_share_pct_{field}"], expected[f"clean_share_pct_{year}"],
                atol=0.00011, rtol=0,
            )
        gainers, _ = extremes(actual.reset_index(), "d_clean_share_pp", 10, changes=True)
        self.assertEqual(gainers.iloc[0]["country"], "Denmark")

    def test_alternate_dates_recalculate_endpoints(self):
        settings = replace(self.settings, start_year=2005, end_year=2020, snapshot_year=2020)
        table = comparison(self.countries, settings)
        denmark = table.set_index("iso3").loc["DNK"]
        source = self.countries.set_index(["iso3", "year"])
        expected = source.loc[("DNK", 2020), "clean_share_pct"] - source.loc[("DNK", 2005), "clean_share_pct"]
        self.assertAlmostEqual(denmark["d_clean_share_pp"], expected)
        self.assertNotAlmostEqual(
            denmark["d_clean_share_pp"],
            self.compared.set_index("iso3").loc["DNK", "d_clean_share_pp"],
        )

    def test_threshold_changes_country_selection(self):
        expanded = comparison(self.countries, replace(self.settings, min_generation_twh=0))
        self.assertGreater(len(expanded), len(self.compared))
        self.assertTrue(set(self.compared["iso3"]) <= set(expanded["iso3"]))

    def test_source_components_add_to_total_in_both_units(self):
        for unit in ("pp", "twh"):
            with self.subTest(unit=unit):
                table = source_changes(self.compared, self.settings, unit)
                np.testing.assert_allclose(
                    table[[group.label for group in self.settings.groups]].sum(axis=1),
                    table["total"], atol=0.001, rtol=0,
                )
        # Nuclear can decline even among the largest clean-share gainers.
        table = source_changes(self.compared, self.settings, "twh").set_index("iso3")
        self.assertLess(table.loc["GBR", "Nuclear"], 0)
        self.assertGreater(table.loc["GBR", "Hydro"], 0)

    def test_regrouping_preserves_totals(self):
        groups = tuple(SourceGroup(source, (source,), "#123456") for source in CLEAN_SOURCES)
        settings = replace(self.settings, groups=groups)
        for unit in ("pp", "twh"):
            actual = source_changes(self.compared, settings, unit)
            self.assertEqual(len(actual.columns), 10)
            np.testing.assert_allclose(
                actual[list(CLEAN_SOURCES)].sum(axis=1), actual["total"], atol=0.001, rtol=0,
            )

    def test_missing_source_is_not_zero(self):
        table = self.compared.head(1).copy()
        table["wind_twh_start"] = np.nan
        with self.assertRaisesRegex(ValueError, "incomplete source"):
            source_changes(table, self.settings, "twh")

    def test_inconsistent_sources_fail(self):
        table = self.compared.head(1).copy()
        table["wind_twh_end"] += 1
        with self.assertRaisesRegex(ValueError, "do not add up"):
            source_changes(table, self.settings, "twh")

    def test_unavailable_year_is_clear(self):
        with self.assertRaisesRegex(ValueError, "Year 1999 is unavailable"):
            snapshot(self.countries, 1999)

    def test_empty_comparison_is_clear(self):
        with self.assertRaisesRegex(ValueError, "No countries"):
            comparison(self.countries, replace(self.settings, min_generation_twh=1e10))


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.table = pd.DataFrame({
            "iso3": ["AAA", "BBB", "CCC", "DDD", "EEE"],
            "country": ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"],
            "value": [10, 10, -5, 0, np.nan],
        })

    def test_ties_are_alphabetical(self):
        high, low = extremes(self.table, "value", 1, changes=True)
        self.assertEqual(high["iso3"].tolist(), ["AAA"])
        self.assertEqual(low["iso3"].tolist(), ["CCC"])

    def test_snapshot_tails_do_not_overlap_or_include_nan(self):
        high, low = extremes(self.table, "value", 3)
        self.assertFalse(set(high["iso3"]) & set(low["iso3"]))
        self.assertEqual(len(high) + len(low), 4)

    def test_change_tails_do_not_include_zero_or_wrong_sign(self):
        high, low = extremes(self.table, "value", 10, changes=True)
        self.assertTrue(high["value"].gt(0).all())
        self.assertTrue(low["value"].lt(0).all())

    def test_empty_gain_tail(self):
        high, low = extremes(self.table.loc[self.table["value"].le(0)], "value", 10, changes=True)
        self.assertTrue(high.empty)
        self.assertEqual(len(low), 1)


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.settings = load_settings()

    def test_default_groups_keep_major_sources_separate(self):
        self.assertEqual(
            [(group.label, group.sources) for group in self.settings.groups],
            [
                ("Wind", ("wind",)), ("Solar", ("solar",)),
                ("Hydro", ("hydro",)), ("Nuclear", ("nuclear",)),
                ("Other Clean", ("bioenergy", "other_renewables_excluding_bioenergy")),
            ],
        )

    def test_rejects_invalid_settings(self):
        for change in (
            {"start_year": 2024}, {"top_n": 0}, {"dpi": 0},
            {"min_generation_twh": -1}, {"min_generation_twh": float("nan")},
            {"formats": ()}, {"formats": ("jpeg",)}, {"formats": ("png", "png")},
            {"snapshot_year": 2024.5},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(self.settings, **change)

    def test_rejects_incomplete_duplicate_and_unknown_sources(self):
        for groups in (
            self.settings.groups[:1],
            (*self.settings.groups, self.settings.groups[0]),
            (SourceGroup("Unknown", ("coal",), "blue"),),
        ):
            with self.subTest(groups=groups), self.assertRaises(ValueError):
                replace(self.settings, groups=groups)

    def test_rejects_bad_colors_and_reserved_labels(self):
        for group in (
            SourceGroup("All", CLEAN_SOURCES, "not-a-color"),
            SourceGroup("total", CLEAN_SOURCES, "blue"),
        ):
            with self.subTest(group=group), self.assertRaises(ValueError):
                replace(self.settings, groups=(group,))


class PlotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = load_settings()
        cls.compared = comparison(load_country_year(), cls.settings)

    def test_titles_and_axes_use_title_case_without_subtitles(self):
        from sketches.plots import (
            change_bars, endpoint_comparison, share_map, share_ranking, source_breakdown,
        )
        import matplotlib.pyplot as plt

        current = snapshot(load_country_year(), self.settings.snapshot_year)
        cases = (
            (
                lambda: share_map(current, self.settings),
                "Domestic Electricity Generation: Clean Share by Country · 2024",
                ["", ""], ["", "Clean Share of Electricity Generation (%)"],
            ),
            (
                lambda: share_ranking(current, self.settings),
                "Domestic Electricity Generation: Highest and Lowest Clean Shares · 2024",
                ["Highest Shares", "Lowest Shares"], ["Clean Share (%)"] * 2,
            ),
            (
                lambda: change_bars(self.compared, self.settings),
                "Domestic Electricity Generation: Largest Clean-Share Changes · 2000–2024",
                ["Largest Increases", "Largest Decreases"],
                ["Change in Clean Share (Percentage Points)"] * 2,
            ),
            (
                lambda: endpoint_comparison(self.compared, self.settings),
                "Domestic Electricity Generation: Clean Shares at Start and End · 2000–2024",
                ["Largest Increases", "Largest Decreases"], ["Clean Share (%)"] * 2,
            ),
            (
                lambda: source_breakdown(self.compared, self.settings, "pp"),
                "Domestic Electricity Generation: Clean-Source Share Changes · 2000–2024",
                [""], ["Change in Share of Total Electricity Generation (Percentage Points)"],
            ),
            (
                lambda: source_breakdown(self.compared, self.settings, "twh"),
                "Domestic Electricity Generation: Clean-Source Output Changes · 2000–2024",
                [""], ["Change in Electricity Generation (TWh)"],
            ),
        )
        for render, title, panel_titles, axis_labels in cases:
            with self.subTest(title=title):
                fig = render()
                try:
                    self.assertEqual(len(fig.texts), 2)  # Title and bottom data note only.
                    self.assertEqual(fig.texts[0].get_text(), title)
                    self.assertIn("Domestic Electricity Generation", title)
                    fig.canvas.draw()
                    bounds = fig.texts[0].get_window_extent(fig.canvas.get_renderer())
                    self.assertGreaterEqual(bounds.x0, 0)
                    self.assertLessEqual(bounds.x1, fig.bbox.width)
                    self.assertTrue(fig.texts[1].get_text().startswith("Source: OWID"))
                    self.assertLess(fig.texts[1].get_position()[1], 0.1)
                    self.assertEqual([ax.get_title() for ax in fig.axes], panel_titles)
                    self.assertEqual([ax.get_xlabel() for ax in fig.axes], axis_labels)
                finally:
                    plt.close(fig)

    def test_legends_use_title_case(self):
        from sketches.plots import share_map, source_breakdown
        import matplotlib.pyplot as plt

        current = snapshot(load_country_year(), self.settings.snapshot_year)
        fig = share_map(current, self.settings)
        try:
            self.assertEqual(
                [text.get_text() for text in fig.axes[0].get_legend().get_texts()],
                ["No Matched Data"],
            )
        finally:
            plt.close(fig)
        settings = replace(
            self.settings,
            groups=tuple(replace(group, label=group.label.lower()) for group in self.settings.groups),
        )
        for unit in ("pp", "twh"):
            fig = source_breakdown(self.compared, settings, unit)
            try:
                labels = [text.get_text() for text in fig.axes[0].get_legend().get_texts()]
                self.assertEqual(
                    labels, ["Wind", "Solar", "Hydro", "Nuclear", "Other Clean", "Net Clean Change"],
                )
                fig.canvas.draw()
                renderer = fig.canvas.get_renderer()
                bounds = fig.axes[0].get_legend().get_window_extent(renderer)
                self.assertGreaterEqual(bounds.x0, 0)
                self.assertLessEqual(bounds.x1, fig.bbox.width)
                self.assertGreaterEqual(bounds.y0, 0)
                self.assertLessEqual(bounds.y1, fig.bbox.height)
            finally:
                plt.close(fig)

    def test_regrouped_source_extremes_have_padding(self):
        from sketches.plots import source_breakdown
        import matplotlib.pyplot as plt

        settings = replace(
            self.settings,
            groups=tuple(SourceGroup(source, (source,), f"C{i}") for i, source in enumerate(CLEAN_SOURCES)),
        )
        fig = source_breakdown(self.compared, settings, "pp")
        try:
            selected, _ = extremes(self.compared, "d_clean_share_pp", settings.top_n, changes=True)
            table = source_changes(selected, settings, "pp")
            columns = [group.label for group in settings.groups]
            lower, upper = fig.axes[0].get_xlim()
            self.assertLess(lower, table[columns].clip(upper=0).sum(axis=1).min())
            self.assertGreater(upper, table[columns].clip(lower=0).sum(axis=1).max())
        finally:
            plt.close(fig)

    def test_empty_change_directions_render(self):
        from sketches.plots import change_bars, endpoint_comparison, source_breakdown
        import matplotlib.pyplot as plt

        for sign in (1, -1):
            table = self.compared.loc[(self.compared["d_clean_share_pp"] * sign).gt(0)]
            for render in (change_bars, endpoint_comparison):
                with self.subTest(sign=sign, render=render.__name__):
                    fig = render(table, self.settings)
                    plt.close(fig)
            if sign == -1:
                fig = source_breakdown(table, self.settings, "pp")
                self.assertEqual(len(fig.axes[0].patches), 0)
                plt.close(fig)


class CommandTests(unittest.TestCase):
    def test_png_export_with_alternate_dates(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            output = Path(directory) / "figures"
            result = subprocess.run(
                [
                    sys.executable, "-m", "sketches", "--snapshot-year", "2020",
                    "--start-year", "2005", "--end-year", "2020", "--top-n", "3",
                    "--format", "png", "--output-dir", str(output),
                    "--preview", str(Path(directory) / "preview.png"),
                ],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("UserWarning", result.stderr)
            self.assertEqual(len(list(output.glob("*.png"))), 9)
            self.assertEqual(len(list(output.glob("*.csv"))), 7)
            self.assertFalse(list(output.glob("*.svg")))
            self.assertTrue((Path(directory) / "preview.png").is_file())
            for question in ("q1", "q5", "q6"):
                copy = Path(directory) / f"preview-{question}.png"
                self.assertEqual(copy.read_bytes(), next(output.glob(f"{question}_*.png")).read_bytes())
            manifest = json.loads((output / "manifest_2020_2005_2020.json").read_text())
            self.assertEqual(manifest["settings"]["start_year"], 2005)
            self.assertEqual(manifest["settings"]["end_year"], 2020)
            self.assertEqual(manifest["preview"], str(Path(directory) / "preview.png"))
            self.assertEqual(len(manifest["source_breakdown_countries"]), 3)
            self.assertEqual(len(manifest["q6_pairs"]), manifest["settings"]["q6_pairs"])

    def test_preview_requires_png_before_writing_output(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            output = Path(directory) / "figures"
            result = subprocess.run(
                [
                    sys.executable, "-m", "sketches", "--format", "svg",
                    "--output-dir", str(output), "--preview", str(Path(directory) / "preview.png"),
                ],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--preview requires PNG", result.stderr)
            self.assertFalse(output.exists())
            self.assertFalse((Path(directory) / "preview.png").exists())

    def test_bad_year_fails_without_output(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            output = Path(directory) / "figures"
            result = subprocess.run(
                [sys.executable, "-m", "sketches", "--snapshot-year", "1999", "--output-dir", str(output)],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Year 1999 is unavailable", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
