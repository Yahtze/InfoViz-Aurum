"""Keep the full-horizon preparation baseline and its consumers in sync."""

import unittest

import pandas as pd

from prep import build
from sketches.settings import load_settings


class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = build.load()
        cls.countries = build.countries_only(cls.raw)
        cls.compared = build.compare(cls.countries)
        cls.map_ids = build.atlas_ids()
        cls.tables = {
            "country_year": build.country_year(
                cls.raw, cls.countries, cls.compared, cls.map_ids,
            ),
            build.COMPARISON_NAME: build.comparison_table(cls.compared),
            "robustness": build.robustness(cls.countries),
        }

    def test_default_settings_use_full_horizon(self):
        settings = load_settings()
        self.assertEqual(build.YEARS, (2000, 2024))
        self.assertEqual((build.START_YEAR, build.END_YEAR), build.YEARS)
        self.assertEqual((settings.start_year, settings.end_year), build.YEARS)
        self.assertEqual(settings.snapshot_year, build.END_YEAR)
        self.assertEqual(settings.min_generation_twh, build.MIN_GENERATION_TWH)
        self.assertEqual(build.COMPARISON_NAME, "comparison_2000_2024")

    def test_pinned_raw_data_passes_baseline_checks(self):
        found = build.check(self.countries, self.tables, self.compared, self.map_ids)
        self.assertEqual(found, {
            "countries": 108, "share_up": 79, "share_up_fossil_up": 44,
        })

    def test_processed_comparison_matches_raw_rebuild(self):
        saved = pd.read_csv(
            build.OUT / f"{build.COMPARISON_NAME}.csv",
            dtype={"iso3": "string", "iso_numeric": "string"},
        )
        rebuilt = self.tables[build.COMPARISON_NAME].reset_index(drop=True)
        pd.testing.assert_frame_equal(
            saved, rebuilt, check_dtype=False, check_exact=False, atol=0.000051, rtol=0,
        )
        self.assertIn("clean_share_pct_2000", saved)
        self.assertIn("coal_share_pct_2000", saved)
        self.assertIn("demand_twh_2000", saved)
        self.assertFalse(any("2010" in column for column in saved))

    def test_legacy_comparison_is_retained(self):
        legacy = pd.read_csv(build.OUT / "comparison_2010_2024.csv")
        self.assertEqual(len(legacy), 108)
        self.assertIn("clean_share_pct_2010", legacy)
        self.assertEqual(int(legacy["d_clean_share_pp"].gt(0).sum()), 83)
        self.assertEqual(int(legacy["outcome"].eq("share_up_fossil_up").sum()), 41)

    def test_robustness_contains_the_main_result(self):
        rows = self.tables["robustness"]
        baseline = rows.loc[
            rows["start_year"].eq(build.START_YEAR)
            & rows["end_year"].eq(build.END_YEAR)
            & rows["min_generation_twh"].eq(build.MIN_GENERATION_TWH)
        ]
        self.assertEqual(len(baseline), 1)
        self.assertEqual(
            baseline.iloc[0][list(build.EXPECTED)].to_dict(), build.EXPECTED,
        )

    def test_comparison_requires_start_year_coverage(self):
        changed = self.countries.copy()
        changed.loc[
            changed["iso_code"].eq("DNK") & changed["year"].eq(2000),
            "low_carbon_electricity_share_pct",
        ] = float("nan")
        self.assertNotIn("DNK", build.compare(changed)["iso3"].tolist())

    def test_country_year_preserves_the_full_timeline(self):
        table = self.tables["country_year"]
        world = table.loc[table["country"].eq("World")]
        self.assertEqual(world["year"].tolist(), list(range(2000, 2025)))
        members = table.loc[table["in_comparison_set"], "iso3"]
        self.assertEqual(set(members), set(self.compared["iso3"]))


if __name__ == "__main__":
    unittest.main()
