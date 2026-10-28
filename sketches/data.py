"""Select countries and calculate changes from the year-indexed table.

Do not use the fixed-endpoint comparison CSV here: changing the sketch dates
must change the calculations, not just the chart labels.
"""

from pathlib import Path

import pandas as pd

from .settings import CLEAN_SOURCES, ROOT, Settings

METRICS = (
    "clean_share_pct", "clean_twh", "fossil_twh", "generation_twh",
    *(f"{source}_{unit}" for source in CLEAN_SOURCES for unit in ("share_pct", "twh")),
)


def load_country_year(path: Path = ROOT / "data/processed/country_year.csv") -> pd.DataFrame:
    table = pd.read_csv(path, dtype={"iso3": "string", "iso_numeric": "string"})
    required = {"iso3", "iso_numeric", "country", "year", "on_map", *METRICS}
    missing = required - set(table.columns)
    if missing:
        raise ValueError(f"country_year.csv is missing columns: {sorted(missing)}")
    countries = table.loc[table["iso3"].notna() & table["country"].ne("World")].copy()
    if countries.duplicated(["iso3", "year"]).any():
        raise ValueError("Duplicate country-year records")
    return countries


def snapshot(countries: pd.DataFrame, year: int) -> pd.DataFrame:
    available = sorted(countries["year"].unique())
    if year not in available:
        raise ValueError(
            f"Year {year} is unavailable. Available years: {available[0]}–{available[-1]}. "
            "Update and rebuild the processed data to use other years."
        )
    return countries.loc[countries["year"].eq(year)].copy()


def comparison(countries: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    start = snapshot(countries, settings.start_year)[["iso3", *METRICS]]
    end = snapshot(countries, settings.end_year)[["iso3", "country", *METRICS]]
    table = start.merge(end, on="iso3", suffixes=("_start", "_end"), validate="one_to_one")
    # Match the preparation pipeline's comparison selection.
    table = table.dropna(subset=[
        "clean_share_pct_start", "clean_share_pct_end", "fossil_twh_start", "fossil_twh_end",
    ])
    table = table.loc[table["generation_twh_end"].ge(settings.min_generation_twh)].copy()
    if table.empty:
        raise ValueError("No countries meet the comparison settings")
    table["d_clean_share_pp"] = table["clean_share_pct_end"] - table["clean_share_pct_start"]
    return table


def extremes(table: pd.DataFrame, column: str, n: int, *, changes: bool = False):
    """Return high/low rows; break cutoff ties by country name.

    Change charts use strictly positive gains and strictly negative losses.
    Snapshot tails do not overlap when the requested n exceeds half the data.
    """
    valid = table.dropna(subset=[column])
    high_pool = valid.loc[valid[column].gt(0)] if changes else valid
    high = high_pool.sort_values([column, "country"], ascending=[False, True]).head(n)
    low_pool = valid.loc[valid[column].lt(0)] if changes else valid.loc[~valid["iso3"].isin(high["iso3"])]
    low = low_pool.sort_values([column, "country"], ascending=[True, True]).head(n)
    return high.copy(), low.copy()


def source_changes(selected: pd.DataFrame, settings: Settings, unit: str) -> pd.DataFrame:
    """Group source deltas without replacing unknown values with zero."""
    if unit not in {"pp", "twh"}:
        raise ValueError("source unit must be pp or twh")
    suffix = "share_pct" if unit == "pp" else "twh"
    result = selected[["iso3", "country", "d_clean_share_pp"]].copy()
    for group in settings.groups:
        start = selected[[f"{source}_{suffix}_start" for source in group.sources]]
        end = selected[[f"{source}_{suffix}_end" for source in group.sources]]
        # min_count prevents a partial group from looking complete.
        result[group.label] = (
            end.sum(axis=1, min_count=len(group.sources))
            - start.sum(axis=1, min_count=len(group.sources))
        )
    labels = [group.label for group in settings.groups]
    if result[labels].isna().any().any():
        raise ValueError("Selected countries have incomplete source data; do not plot blanks as zero")
    expected = (
        selected["d_clean_share_pp"] if unit == "pp"
        else selected["clean_twh_end"] - selected["clean_twh_start"]
    )
    if expected.isna().any() or not (result[labels].sum(axis=1) - expected).abs().lt(0.01).all():
        raise ValueError("Source contributions do not add up to the clean electricity change")
    result["total"] = expected
    return result
