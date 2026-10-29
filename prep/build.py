"""Build the processed tables from the pinned OWID file.

Run from the repository root:

    python prep/build.py

It reads the pinned files in data/raw/, writes data/processed/*.csv,
and then runs checks. It stops with an error if a check fails.

Rules:
- Countries are rows with a 3-letter iso_code; regions and "World" have none.
  Kosovo has no code in OWID, so it gets XKX. The World row is kept for Q1.
- Years 2000-2024 (2025 is incomplete).
- The comparison (Q3-Q6) uses countries with data in both 2000 and 2024 and >= 10 TWh generation in 2024 (108 countries).
- "Clean" is OWID's "low-carbon" (renewables plus nuclear); "fossil" is coal + gas + oil.
- Missing values: a blank source TWh becomes 0 only when the other sources add up to total generation;
  a blank source share is then computed as TWh / generation (and stays blank when generation is 0);
  a blank total stays blank (unknown, not 0); a growth rate is blank when the starting value is 0.
- world-atlas ids are ISO numeric codes kept as text with leading zeros ("012").
  In D3, d3.autoType would turn "012" into 12, so keep that column as text.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pycountry

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "owid_energy_2026-09-30.csv"
ATLAS = ROOT / "data" / "raw" / "world-atlas-2.0.2-countries-50m.json"
OUT = ROOT / "data" / "processed"

# Analysis settings. Change them only here.
# robustness.csv shows how the main result moves when they change.
YEARS = (2000, 2024)  # 2025 has data for only 126 countries
START_YEAR, END_YEAR = YEARS  # the full-horizon comparison (Q3-Q6)
COMPARISON_NAME = f"comparison_{START_YEAR}_{END_YEAR}"
MIN_GENERATION_TWH = 10  # the comparison only: generation in END_YEAR

# Countries that OWID lists without an iso_code. XKX is the code the EU and IMF use for Kosovo.
# ("Serbia and Montenegro" also has no code, but it has no data after 2005.)
NO_ISO_CODE = {"Kosovo": "XKX"}

FOSSIL = ["coal", "gas", "oil"]
CLEAN = ["nuclear", "hydro", "solar", "wind", "bioenergy", "other_renewables_excluding_bioenergy"]
SOURCES = FOSSIL + CLEAN
# Groups from the proposal: wind and solar vs. hydro and nuclear, other clean sources apart.
CLEAN_GROUPS = {
    "wind_solar": ["wind", "solar"],
    "hydro_nuclear": ["hydro", "nuclear"],
    "other_clean": ["bioenergy", "other_renewables_excluding_bioenergy"],
}

# OWID column -> short name used in the output files.
# "clean" is OWID's "low-carbon": all renewables plus nuclear.
MEASURES = {
    "electricity_generation_twh": "generation_twh",
    "electricity_demand_twh": "demand_twh",
    "electricity_net_imports_twh": "net_imports_twh",
    "low_carbon_electricity_share_pct": "clean_share_pct",
    "low_carbon_electricity_twh": "clean_twh",
    "fossil_fuels_electricity_share_pct": "fossil_share_pct",
    "fossil_fuels_electricity_twh": "fossil_twh",
    **{f"{s}_electricity_twh": f"{s}_twh" for s in SOURCES},
    **{f"{s}_electricity_share_pct": f"{s}_share_pct" for s in SOURCES},
}

# Expected values for the pinned raw file and the baseline settings above.
EXPECTED = {"countries": 108, "share_up": 79, "share_up_fossil_up": 44}


def iso_numeric(alpha3):
    """ISO 3166-1 numeric code ("840" for USA), the id that world-atlas uses."""
    country = pycountry.countries.get(alpha_3=alpha3)
    return country.numeric if country else None


def atlas_ids():
    atlas = json.loads(ATLAS.read_text())
    return {g["id"] for g in atlas["objects"]["countries"]["geometries"] if "id" in g}


def fill_missing_sources(df):
    """Treat a missing source as 0 when the other sources already add up to total generation.

    A blank source in OWID then means "none of this source", and every table uses the same rule.
    A missing total (generation or clean share) stays missing: that is unknown, not 0.
    """
    df = df.copy()
    twh = [f"{s}_electricity_twh" for s in SOURCES]
    share = [f"{s}_electricity_share_pct" for s in SOURCES]
    gen = df["electricity_generation_twh"]
    complete = gen.notna() & ((df[twh].fillna(0).sum(axis=1) - gen).abs() < 0.01)
    # Some regional totals (e.g. "Europe (EI)") lack a breakdown by source; we do not use them.
    used = df["iso_code"].notna() | (df["country"] == "World")
    assert complete[used & gen.notna()].all(), "Some country-years have sources that do not add up to generation"
    df.loc[complete, twh] = df.loc[complete, twh].fillna(0)
    # A blank share is computed from the source's TWh, so it is 0 only when the TWh is 0.
    # Shares are undefined when generation is 0 (e.g. Lesotho 2024), so leave them blank there.
    positive = complete & (gen > 0)
    for t, s in zip(twh, share):
        df.loc[positive, s] = df.loc[positive, s].fillna(100 * df.loc[positive, t] / gen[positive])
    return df


def load():
    df = pd.read_csv(RAW)
    df = df[df["year"].between(*YEARS)]
    df["iso_code"] = df["iso_code"].fillna(df["country"].map(NO_ISO_CODE))
    return fill_missing_sources(df)


def countries_only(df):
    # Regions and "World" have no iso_code; countries have 3 letters.
    c = df[df["iso_code"].str.fullmatch(r"[A-Z]{3}", na=False)].copy()
    c["iso_numeric"] = c["iso_code"].map(iso_numeric)
    return c


def snapshot(c, year):
    rows = c[c["year"] == year].set_index("iso_code")
    return rows[list(MEASURES)].rename(columns=MEASURES).add_suffix(f"_{year}")


def growth_pct(end, start):
    return 100 * (end / start.where(start > 0) - 1)


def compare(c, start=START_YEAR, end=END_YEAR, min_twh=MIN_GENERATION_TWH):
    """One row per country with data in both years and enough generation in `end`."""
    names = c[c["year"] == end].set_index("iso_code")[["country", "iso_numeric"]]
    t = names.join(snapshot(c, start), how="inner").join(snapshot(c, end), how="inner")
    needed = [f"clean_share_pct_{start}", f"clean_share_pct_{end}", f"fossil_twh_{start}", f"fossil_twh_{end}"]
    t = t.dropna(subset=needed)
    t = t[t[f"generation_twh_{end}"] >= min_twh].copy()

    t["d_clean_share_pp"] = t[f"clean_share_pct_{end}"] - t[f"clean_share_pct_{start}"]
    t["d_fossil_twh"] = t[f"fossil_twh_{end}"] - t[f"fossil_twh_{start}"]
    # Undefined (blank) when a country had no fossil generation in the start year.
    t["d_fossil_pct"] = growth_pct(t[f"fossil_twh_{end}"], t[f"fossil_twh_{start}"])

    share_up = t["d_clean_share_pp"] > 0
    t["outcome"] = np.select(
        [share_up & (t["d_fossil_twh"] < 0), share_up & (t["d_fossil_twh"] > 0), share_up],
        ["share_up_fossil_down", "share_up_fossil_up", "share_up_fossil_flat"],
        "share_not_up",
    )
    return t.rename_axis("iso3").reset_index()


def country_year(df, c, comparison, map_ids):
    """Every country and the World, every year: Q1 (World), Q2 (2024), and the Q5 detail view."""
    world = df[df["country"] == "World"].copy()
    rows = pd.concat([world, c])
    out = pd.DataFrame({
        "iso3": rows["iso_code"],
        "iso_numeric": rows["iso_numeric"],
        "country": rows["country"],
        "year": rows["year"],
        # False for places the map cannot draw (e.g. Gibraltar): show them in a list next to the map.
        "on_map": rows["iso_numeric"].isin(map_ids),
        "in_comparison_set": rows["iso_code"].isin(comparison["iso3"]),
    })
    out = out.join(rows[list(MEASURES)].rename(columns=MEASURES))
    # World first, then countries A-Z.
    return (out.assign(not_world=out["country"] != "World")
               .sort_values(["not_world", "country", "year"])
               .drop(columns="not_world"))


def comparison_table(t):
    """The 108 compared countries, one row each, ranked by change in clean share (Q3-Q6)."""
    s, e = START_YEAR, END_YEAR
    out = t[["iso3", "iso_numeric", "country", "outcome"]].copy()
    out["fossil_reduced"] = t["d_fossil_twh"] < 0

    # Q3, Q5: change in clean share and in fossil generation.
    for col in [f"clean_share_pct_{s}", f"clean_share_pct_{e}", "d_clean_share_pp",
                f"fossil_twh_{s}", f"fossil_twh_{e}", "d_fossil_twh", "d_fossil_pct"]:
        out[col] = t[col]

    # Q4: which clean sources drove the change, in two candidate measures (M1 feedback point 1).
    # d_<source>_share_pp adds up exactly to d_clean_share_pp; d_<source>_twh is the change in generation.
    for src in CLEAN:
        out[f"d_{src}_share_pp"] = t[f"{src}_share_pct_{e}"] - t[f"{src}_share_pct_{s}"]
    for src in CLEAN:
        out[f"d_{src}_twh"] = t[f"{src}_twh_{e}"] - t[f"{src}_twh_{s}"]
    for group, members in CLEAN_GROUPS.items():
        out[f"d_{group}_share_pp"] = out[[f"d_{m}_share_pp" for m in members]].sum(axis=1)
        out[f"d_{group}_twh"] = out[[f"d_{m}_twh" for m in members]].sum(axis=1)

    # Q6: demand growth and the starting mix.
    # Demand = generation + net imports, so the two differ for importers and exporters.
    out[f"generation_twh_{e}"] = t[f"generation_twh_{e}"]
    out["generation_growth_pct"] = growth_pct(t[f"generation_twh_{e}"], t[f"generation_twh_{s}"])
    out[f"demand_twh_{s}"] = t[f"demand_twh_{s}"]
    out[f"demand_twh_{e}"] = t[f"demand_twh_{e}"]
    out["demand_growth_pct"] = growth_pct(t[f"demand_twh_{e}"], t[f"demand_twh_{s}"])
    demand_end = t[f"demand_twh_{e}"].where(t[f"demand_twh_{e}"] > 0)
    out[f"net_imports_share_of_demand_pct_{e}"] = 100 * t[f"net_imports_twh_{e}"] / demand_end
    for src in SOURCES:
        out[f"{src}_share_pct_{s}"] = t[f"{src}_share_pct_{s}"]

    out = out.sort_values("d_clean_share_pp", ascending=False)
    out.insert(0, "rank", range(1, len(out) + 1))
    return out


def robustness(c):
    """Does the main result hold if the threshold or the start year changes? (M1 feedback point 3)"""
    rows = []
    for start in (2000, 2005, 2010, 2015):
        for min_twh in (0, 5, 10, 20, 50):
            t = compare(c, start=start, min_twh=min_twh)
            up = t["d_clean_share_pp"] > 0
            both = up & (t["d_fossil_twh"] > 0)
            rows.append({
                "start_year": start,
                "end_year": END_YEAR,
                "min_generation_twh": min_twh,
                "countries": len(t),
                "share_up": int(up.sum()),
                "share_up_fossil_up": int(both.sum()),
                "pct_of_share_up": round(100 * both.sum() / up.sum(), 1),
            })
    return pd.DataFrame(rows)


def close(a, b, tol):
    return ((a - b).abs() < tol).all()


def check(c, tables, comparison, map_ids):
    assert not c.duplicated(["iso_code", "year"]).any(), "Duplicate country-year rows"

    cy = tables["country_year"]
    world = cy[cy["country"] == "World"]
    years = list(range(YEARS[0], YEARS[1] + 1))
    assert world["year"].tolist() == years, "World is missing years"
    assert close(world[[f"{s}_twh" for s in SOURCES]].sum(axis=1), world["generation_twh"], 0.01), \
        "World: the sources do not add up to total generation"

    # Each endpoint on its own, so that equal errors in both years cannot cancel out.
    for y in (START_YEAR, END_YEAR):
        assert close(comparison[[f"{s}_twh_{y}" for s in SOURCES]].sum(axis=1), comparison[f"generation_twh_{y}"], 0.01), \
            f"{y}: sources do not add up to generation"
        assert close(comparison[[f"{s}_share_pct_{y}" for s in CLEAN]].sum(axis=1), comparison[f"clean_share_pct_{y}"], 0.01), \
            f"{y}: clean sources do not add up to the clean share"
        assert close(comparison[[f"{s}_twh_{y}" for s in CLEAN]].sum(axis=1), comparison[f"clean_twh_{y}"], 0.01), \
            f"{y}: clean sources do not add up to clean generation"

    cmp = tables[COMPARISON_NAME].set_index("iso3")
    base = comparison.set_index("iso3").loc[cmp.index]
    assert close(cmp[[f"d_{s}_share_pp" for s in CLEAN]].sum(axis=1), cmp["d_clean_share_pp"], 0.01), \
        "Q4: source changes (pp) do not add up to the change in clean share"
    assert close(cmp[[f"d_{s}_twh" for s in CLEAN]].sum(axis=1),
                 base[f"clean_twh_{END_YEAR}"] - base[f"clean_twh_{START_YEAR}"], 0.01), \
        "Q4: source changes (TWh) do not add up to the change in clean generation"

    not_on_map = comparison.loc[~comparison["iso_numeric"].isin(map_ids), "country"].tolist()
    assert not not_on_map, f"Comparison countries the map cannot draw: {not_on_map}"

    for name, table in tables.items():
        numbers = table.select_dtypes("number")
        assert not np.isinf(numbers.to_numpy()).any(), f"{name}: infinite values"

    found = {
        "countries": len(comparison),
        "share_up": int((comparison["d_clean_share_pp"] > 0).sum()),
        "share_up_fossil_up": int((comparison["outcome"] == "share_up_fossil_up").sum()),
    }
    assert found == EXPECTED, f"Main result changed: {found} (expected {EXPECTED})"
    return found


def write(table, path):
    # Lowercase true/false, so that d3.autoType reads them as booleans.
    table = table.copy()
    for col in table.select_dtypes("bool"):
        table[col] = table[col].map({True: "true", False: "false"})
    table.to_csv(path, index=False, float_format="%.4f")


def main():
    df = load()
    c = countries_only(df)
    comparison = compare(c)
    map_ids = atlas_ids()

    tables = {
        "country_year": country_year(df, c, comparison, map_ids),
        COMPARISON_NAME: comparison_table(comparison),
        "robustness": robustness(c),
    }

    found = check(c, tables, comparison, map_ids)

    OUT.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        write(table, OUT / f"{name}.csv")
        print(f"{name}.csv: {len(table)} rows, {table.shape[1]} columns")
    cy = tables["country_year"]
    off_map = cy.loc[(cy["year"] == END_YEAR) & ~cy["on_map"] & (cy["country"] != "World"), "country"].tolist()
    print(f"{END_YEAR} countries the map cannot draw ({len(off_map)}): {', '.join(off_map)}")
    print(f"Checks passed. {found['share_up_fossil_up']} of {found['share_up']} countries "
          f"raised their clean share but generated more fossil electricity "
          f"({found['countries']} countries compared, {START_YEAR}-{END_YEAR}).")


if __name__ == "__main__":
    main()
