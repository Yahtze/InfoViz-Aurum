"""Q1, Q5 and Q6: the world mix, fossil outcomes, and demand-growth pairs.

Like data.py, everything is recalculated from country_year.csv for the configured
years, so changing the dates changes the calculations, not just the labels.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from .data import comparison, snapshot
from .settings import ROOT, Settings

FOSSIL_SOURCES = ("coal", "gas", "oil")
# Same names and order as prep/build.py.
OUTCOMES = ("share_up_fossil_down", "share_up_fossil_up", "share_up_fossil_flat", "share_not_up")
OUTCOME_LABELS = {
    "share_up_fossil_down": "Clean Share Up, Fossil Down",
    "share_up_fossil_up": "Clean Share Up, Fossil Up",
    "share_up_fossil_flat": "Clean Share Up, Fossil Unchanged",
    "share_not_up": "Clean Share Not Up",
}
# Endpoint fields Q5 and Q6 need beyond data.METRICS.
EXTRA = (
    "demand_twh", "net_imports_twh",
    *(f"{source}_{unit}" for source in FOSSIL_SOURCES for unit in ("twh", "share_pct")),
)


def load_world(path: Path = ROOT / "data/processed/country_year.csv") -> pd.DataFrame:
    """The World row for every year (data.load_country_year drops it)."""
    table = pd.read_csv(path, dtype={"iso3": "string", "iso_numeric": "string"})
    world = table.loc[table["country"].eq("World")].sort_values("year").copy()
    if world.empty or world["year"].duplicated().any():
        raise ValueError("country_year.csv needs exactly one World row per year")
    return world


def window(rows: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    """Rows from the start year to the end year; both endpoints must exist."""
    available = set(rows["year"])
    for year in (settings.start_year, settings.end_year):
        if year not in available:
            raise ValueError(f"Year {year} is unavailable for {rows['country'].iloc[0]}")
    return rows.loc[rows["year"].between(settings.start_year, settings.end_year)]


def mix_table(rows: pd.DataFrame, settings: Settings, unit: str) -> pd.DataFrame:
    """One column per line: Coal, Gas, Oil, then the configured clean groups.

    unit is "twh" or "share_pct". Unknown values stay unknown (a gap in the line).
    Complete rows must add up to generation (TWh) or to 100% (shares).
    """
    if unit not in {"twh", "share_pct"}:
        raise ValueError("mix unit must be twh or share_pct")
    rows = rows.sort_values("year")
    table = pd.DataFrame({"year": rows["year"].to_numpy()})
    groups = [(name.title(), (name,)) for name in FOSSIL_SOURCES]
    groups += [(group.label, group.sources) for group in settings.groups]
    for label, sources in groups:
        values = rows[[f"{source}_{unit}" for source in sources]]
        table[label] = values.sum(axis=1, min_count=len(sources)).to_numpy()
    lines = table.drop(columns="year")
    total = rows["generation_twh"].to_numpy() if unit == "twh" else np.full(len(rows), 100.0)
    complete = lines.notna().all(axis=1).to_numpy() & ~np.isnan(total)
    if unit == "share_pct":
        complete &= rows["generation_twh"].gt(0).to_numpy()
    gap = np.abs(lines.sum(axis=1).to_numpy() - total)[complete]
    if (gap >= 0.01).any():
        raise ValueError(f"Mix groups do not add up to {'generation' if unit == 'twh' else '100%'}")
    return table


def growth_pct(end: pd.Series, start: pd.Series) -> pd.Series:
    # Undefined (blank) when the start value is not positive, as in prep/build.py.
    return 100 * (end / start.where(start > 0) - 1)


def fossil_outcomes(countries: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    """The comparison countries (same rule as data.comparison) with Q5 and Q6 measures."""
    table = comparison(countries, settings)
    for year, suffix in ((settings.start_year, "_start"), (settings.end_year, "_end")):
        extra = snapshot(countries, year)[["iso3", *EXTRA]].add_suffix(suffix)
        table = table.merge(
            extra.rename(columns={f"iso3{suffix}": "iso3"}), on="iso3", how="left", validate="one_to_one",
        )
    table["d_fossil_twh"] = table["fossil_twh_end"] - table["fossil_twh_start"]
    share_up = table["d_clean_share_pp"] > 0
    table["outcome"] = np.select(
        [share_up & (table["d_fossil_twh"] < 0), share_up & (table["d_fossil_twh"] > 0), share_up],
        list(OUTCOMES[:3]), OUTCOMES[3],
    )
    table["fossil_reduced"] = table["d_fossil_twh"] < 0
    table["demand_growth_pct"] = growth_pct(table["demand_twh_end"], table["demand_twh_start"])
    table["generation_growth_pct"] = growth_pct(table["generation_twh_end"], table["generation_twh_start"])
    demand_end = table["demand_twh_end"].where(table["demand_twh_end"] > 0)
    table["net_imports_share_of_demand_pct_end"] = 100 * table["net_imports_twh_end"] / demand_end
    return table.sort_values("country").reset_index(drop=True)


def q5_example(table: pd.DataFrame, settings: Settings):
    """The country selected in the static Q5 sketch, or None.

    Default rule: the largest end-year generator among "share up, fossil up"
    countries inside the enlarged band. A configured example must be a compared country.
    """
    if settings.q5_example is not None:
        match = table.loc[table["country"].eq(settings.q5_example)]
        if match.empty:
            raise ValueError(f"Q5 example {settings.q5_example!r} is not a compared country")
        return match.iloc[0]
    candidates = table.loc[
        table["outcome"].eq("share_up_fossil_up") & table["d_fossil_twh"].abs().le(settings.q5_zoom_twh)
    ]
    if candidates.empty:
        return None
    return candidates.sort_values(["generation_twh_end", "country"], ascending=[False, True]).iloc[0]


def q6_countries(table: pd.DataFrame):
    """Leave out countries with no fossil generation at both endpoints: they had nothing to cut."""
    none = table["fossil_twh_start"].eq(0) & table["fossil_twh_end"].eq(0)
    return table.loc[~none].copy(), table.loc[none, "country"].sort_values().tolist()


def matched_pairs(table: pd.DataFrame, n: int) -> pd.DataFrame:
    """Pairs with the closest demand growth: one country that reduced fossil generation,
    one that did not, each country used once. Greedy by the smallest gap; ties by name.

    The pairs illustrate exceptions to the group comparison; they are not a sample.
    """
    known = table.dropna(subset=["demand_growth_pct"])
    reduced = known.loc[known["fossil_reduced"], ["country", "demand_growth_pct"]]
    other = known.loc[~known["fossil_reduced"], ["country", "demand_growth_pct"]]
    candidates = reduced.merge(other, how="cross", suffixes=("_reduced", "_other"))
    candidates["gap_pp"] = (
        candidates["demand_growth_pct_reduced"] - candidates["demand_growth_pct_other"]
    ).abs()
    candidates = candidates.sort_values(["gap_pp", "country_reduced", "country_other"])
    pairs, used = [], set()
    for row in candidates.itertuples(index=False):
        if row.country_reduced in used or row.country_other in used:
            continue
        used.update((row.country_reduced, row.country_other))
        pairs.append(row._asdict())
        if len(pairs) == n:
            break
    result = pd.DataFrame(pairs, columns=candidates.columns)
    result.insert(0, "pair", range(1, len(result) + 1))
    return result


def group_summary(table: pd.DataFrame) -> pd.DataFrame:
    """The Q6 answer: demand growth across all countries in each group."""
    rows = []
    for reduced in (True, False):
        values = table.loc[table["fossil_reduced"].eq(reduced), "demand_growth_pct"].dropna()
        rows.append({
            "fossil_reduced": reduced,
            "countries": len(values),
            "median_demand_growth_pct": values.median(),
            "q1_demand_growth_pct": values.quantile(0.25),
            "q3_demand_growth_pct": values.quantile(0.75),
        })
    return pd.DataFrame(rows)
