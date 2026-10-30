"""Keep report samples and documentation tied to the processed baseline."""

from pathlib import Path
import re
import tempfile
import unittest

import numpy as np
import pandas as pd

from prep.report import (
    TOP_N, build_report, build_samples, feature_dictionary, load_tables,
    markdown_table,
)
from prep.report_q156 import q156_results, q156_samples
from sketches.data import comparison, extremes, load_country_year, source_changes
from sketches.settings import ROOT, load_settings


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.country_year, cls.compared = load_tables()
        cls.samples = build_samples(cls.country_year, cls.compared)

    def test_dictionary_covers_only_q2_q3_q4_fields(self):
        dictionary = feature_dictionary(self.country_year, self.compared)
        self.assertEqual(len(dictionary), 46)
        self.assertFalse(dictionary.duplicated(["Table", "Feature"]).any())
        for name, table in (
            ("country_year.csv", self.country_year),
            ("comparison_2000_2024.csv", self.compared),
        ):
            documented = set(dictionary.loc[dictionary["Table"].eq(name), "Feature"])
            self.assertTrue(documented.issubset(table.columns))
        self.assertEqual(set(dictionary["Table"]), {"country_year.csv", "comparison_2000_2024.csv"})
        self.assertFalse(dictionary["Feature"].str.contains("demand|outcome|fossil_reduced|growth").any())
        self.assertFalse(dictionary["Feature"].str.contains("d_wind_solar|d_hydro_nuclear").any())
        self.assertFalse(dictionary.isna().any().any())

    def test_dictionary_rejects_missing_required_feature(self):
        changed = self.compared.drop(columns="d_clean_share_pp")
        with self.assertRaisesRegex(ValueError, "does not match comparison"):
            feature_dictionary(self.country_year, changed)

    def test_samples_cover_only_questions_worked_on(self):
        self.assertEqual(set(self.samples), {
            "q2_country_shares_sample", "q3_share_changes_sample",
            "q4_source_changes_pp", "q4_source_changes_twh",
        })

    def test_q2_sample_includes_missing_zero_and_unmapped_cases(self):
        table = self.samples["q2_country_shares_sample"].set_index("Country")
        self.assertEqual(len(table), 12)
        self.assertEqual(table.loc["Albania", "Map ID"], "008")
        self.assertEqual(table.loc["Gibraltar", "Clean Share 2024 (%)"], 0)
        self.assertFalse(table.loc["Gibraltar", "On Map"])
        self.assertTrue(pd.isna(table.loc["Ukraine", "Clean Share 2024 (%)"]))
        self.assertEqual(table.loc["Lesotho", "Total Generation 2024 (TWh)"], 0)
        self.assertTrue(pd.isna(table.loc["Lesotho", "Clean Share 2024 (%)"]))

    def test_q3_contains_both_change_directions(self):
        table = self.samples["q3_share_changes_sample"]
        self.assertEqual(len(table), 8)
        self.assertEqual(table["Country"].iloc[0], "Denmark")
        self.assertTrue(table["Clean Share Change (pp)"].gt(0).any())
        self.assertTrue(table["Clean Share Change (pp)"].lt(0).any())

    def test_q4_countries_match_both_default_sketches(self):
        settings = load_settings()
        selected, _ = extremes(
            comparison(load_country_year(), settings), "d_clean_share_pp", TOP_N, changes=True,
        )
        for unit, suffix in (("pp", "pp"), ("twh", "TWh")):
            with self.subTest(unit=unit):
                table = self.samples[f"q4_source_changes_{unit}"]
                self.assertEqual(table["Country"].tolist(), selected["country"].tolist())
                labels = ["Wind", "Solar", "Hydro", "Nuclear", "Other Clean"]
                columns = [f"{group} Change ({suffix})" for group in labels]
                self.assertEqual(columns, table.columns[1:-1].tolist())
                np.testing.assert_allclose(
                    table[columns].sum(axis=1), table[f"Net Clean Change ({suffix})"], atol=0.001, rtol=0,
                )
                # The report samples must reproduce the current configured sketch's
                # source values, not merely preserve an independent total.
                sketch_table = source_changes(selected, settings, unit).set_index("country")
                report_table = table.set_index("Country")
                for label in labels:
                    np.testing.assert_allclose(
                        report_table[f"{label} Change ({suffix})"],
                        sketch_table.loc[report_table.index, label], atol=0.001, rtol=0,
                    )
                np.testing.assert_allclose(
                    report_table[f"Net Clean Change ({suffix})"],
                    sketch_table.loc[report_table.index, "total"], atol=0.001, rtol=0,
                )


    def test_markdown_distinguishes_unknown_zero_and_boolean(self):
        table = pd.DataFrame({"Value": [None, 0, "008", True, False, "a|b"]})
        result = markdown_table(table)
        for expected in ("No Data", "| 0 |", "| 008 |", "| Yes |", "| No |", "a\\|b"):
            self.assertIn(expected, result)

    def test_report_and_csvs_rebuild_reproducibly(self):
        names = [*self.samples, *q156_samples(q156_results())]
        expected = {f"{name}.csv" for name in names} | {"feature_dictionary.csv"}
        self.assertEqual({path.name for path in (ROOT / "reports/tables").glob("*.csv")}, expected)
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            report = build_report(Path(directory))
            text = report.read_text()
            self.assertEqual(text, (ROOT / "reports/data-handling.md").read_text())
            self.assertEqual(
                {path.name for path in (report.parent / "tables").glob("*.csv")}, expected,
            )
            self.assertEqual(
                re.findall(r"^## (Q[0-9]+) —", text, re.MULTILINE), ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"],
            )
            # Other start years and robustness.csv belong only to the cutoff section.
            cutoffs = re.search(r"^## Cutoffs and Sensitivity\n.*?(?=^## )", text, re.MULTILINE | re.DOTALL)
            self.assertIsNotNone(cutoffs)
            self.assertIn("robustness.csv", cutoffs.group())
            rest = text.replace(cutoffs.group(), "")
            self.assertNotIn("robustness.csv", rest)
            self.assertIn("2000–2024 for comparisons", text)
            self.assertNotIn("2010", rest)
            self.assertIn("[Tracked six-figure overview montage](../outputs/preview.png)", text)
            self.assertIn("Individual figure files", text)
            self.assertNotIn("Wind + Solar Change", text)
            self.assertNotIn("Hydro + Nuclear Change", text)
            self.assertIn("Wind Change (TWh)", text)
            self.assertIn("Solar Change (TWh)", text)
            self.assertIn("Nuclear Change (TWh)", text)
            for link in re.findall(r"\]\((tables/[^)]+\.csv)\)", text):
                self.assertTrue((report.parent / link).is_file(), link)
            for filename in expected:
                self.assertEqual(
                    (report.parent / "tables" / filename).read_bytes(),
                    (ROOT / "reports/tables" / filename).read_bytes(),
                )
            current = pd.read_csv(
                report.parent / "tables/q2_country_shares_sample.csv", dtype={"Map ID": "string"},
            ).set_index("Country")
            self.assertEqual(current.loc["Albania", "Map ID"], "008")
            self.assertTrue(pd.isna(current.loc["Ukraine", "Clean Share 2024 (%)"]))


if __name__ == "__main__":
    unittest.main()
