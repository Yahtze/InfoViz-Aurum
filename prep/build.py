"""Build the processed tables for every question from the pinned OWID file.

Run from the repository root:

    python prep/build.py

It reads the pinned files in data/raw/, writes data/processed/*.csv,
and then runs checks. It stops with an error if a check fails.

Rules:
- Countries are rows with a 3-letter iso_code; regions and "World" have none.
  Kosovo has no code in OWID, so it gets XKX.
- Years 2000-2024 (2025 is incomplete). Q1 uses the World row, Q2 every country.
- Q3-Q6 compare countries with data in both 2010 and 2024 and >= 10 TWh generation in 2024 (108 countries).
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
BACKGROUND_YEARS = (2000, 2024)  # Q1 (2025 has data for only 126 countries)
START_YEAR, END_YEAR = 2010, 2024  # country comparison (Q3-Q6)
MIN_GENERATION_TWH = 10  # Q3-Q6 only: generation in END_YEAR

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

# OWID column -> short name used in every output file.
# "clean" is OWID's "low-carbon": all renewables plus nuclear.
MEASURES = {
    "low_carbon_electricity_share_pct": "clean_share_pct",
    "low_carbon_electricity_twh": "clean_twh",
    "fossil_fuels_electricity_twh": "fossil_twh",
    "electricity_generation_twh": "generation_twh",
    "electricity_demand_twh": "demand_twh",
    "electricity_net_imports_twh": "net_imports_twh",
    **{f"{s}_electricity_share_pct": f"{s}_share_pct" for s in SOURCES},
    **{f"{s}_electricity_twh": f"{s}_twh" for s in SOURCES},
}

# Expected values for the pinned raw file. Update them if you replace the file.
EXPECTED = {"countries": 108, "share_up": 83, "share_up_fossil_up": 41}


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
    df = df[df["year"].between(*BACKGROUND_YEARS)]
    df["iso_code"] = df["iso_code"].fillna(df["country"].map(NO_ISO_CODE))
    return fill_missing_sources(df)


def countries_only(df):
    # Regions and "World" have no iso_code; countries have 3 letters.
    c = df[df["iso_code"].str.fullmatch(r"[A-Z]{3}", na=False)].copy()
    c["iso_numeric"] = c["iso_code"].map(iso_numeric)
    return c


def mix_columns(rows):
    """Source mix in TWh and share, in the same columns for the world and for countries."""
    out = rows[["year"]].copy()
    for s in SOURCES:
        out[f"{s}_twh"] = rows[f"{s}_electricity_twh"]
        out[f"{s}_share_pct"] = rows[f"{s}_electricity_share_pct"]
    out["generation_twh"] = rows["electricity_generation_twh"]
    out["clean_share_pct"] = rows["low_carbon_electricity_share_pct"]
    out["fossil_twh"] = rows["fossil_fuels_electricity_twh"]
    return out


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


def q1_world_mix(df):
    world = df[df["country"] == "World"]
    return mix_columns(world)


def q2_share_2024(c, comparison, map_ids):
    # Every country, not only the comparison set: the map shows the whole world.
    # Countries without data keep an empty value, so the map can show "no data".
    rows = c[c["year"] == END_YEAR]
    out = pd.DataFrame({
        "iso3": rows["iso_code"],
        "iso_numeric": rows["iso_numeric"],
        "country": rows["country"],
        "clean_share_pct": rows["low_carbon_electricity_share_pct"],
        "generation_twh": rows["electricity_generation_twh"],
        "in_comparison_set": rows["iso_code"].isin(comparison["iso3"]),
        # False for places the map cannot draw (e.g. Gibraltar): show them in a list next to the map.
        "on_map": rows["iso_numeric"].isin(map_ids),
    })
    return out.sort_values("clean_share_pct", ascending=False, na_position="last")


def q3_share_change(t):
    out = t[["iso3", "iso_numeric", "country",
             f"clean_share_pct_{START_YEAR}", f"clean_share_pct_{END_YEAR}", "d_clean_share_pp"]]
    out = out.sort_values("d_clean_share_pp", ascending=False)
    out.insert(0, "rank", range(1, len(out) + 1))
    return out


def q4_clean_sources(t):
    """Two candidate measures of which clean sources drove the change (M1 feedback point 1).

    d_<source>_share_pp: change in that source's share, in percentage points.
        These add up exactly to d_clean_share_pp.
    d_<source>_twh: change in that source's generation, in TWh.
    """
    out = t[["iso3", "country", "d_clean_share_pp"]].copy()
    for s in CLEAN:
        out[f"d_{s}_share_pp"] = t[f"{s}_share_pct_{END_YEAR}"] - t[f"{s}_share_pct_{START_YEAR}"]
    for s in CLEAN:
        out[f"d_{s}_twh"] = t[f"{s}_twh_{END_YEAR}"] - t[f"{s}_twh_{START_YEAR}"]
    for group, members in CLEAN_GROUPS.items():
        out[f"d_{group}_share_pp"] = out[[f"d_{s}_share_pp" for s in members]].sum(axis=1)
        out[f"d_{group}_twh"] = out[[f"d_{s}_twh" for s in members]].sum(axis=1)
    out = out.sort_values("d_clean_share_pp", ascending=False)
    out.insert(0, "rank", range(1, len(out) + 1))
    return out


def q5_share_vs_fossil(t):
    return t[["iso3", "iso_numeric", "country", "d_clean_share_pp",
              f"fossil_twh_{START_YEAR}", f"fossil_twh_{END_YEAR}", "d_fossil_twh", "d_fossil_pct",
              f"generation_twh_{END_YEAR}", "outcome"]]


def q5_mix_by_year(c, t):
    # Detail view: selecting a country in the scatterplot shows its mix over time.
    rows = c[c["iso_code"].isin(t["iso3"])]
    out = mix_columns(rows)
    out.insert(0, "country", rows["country"])
    out.insert(0, "iso3", rows["iso_code"])
    return out


def q6_demand_and_mix(t):
    s, e = START_YEAR, END_YEAR
    out = t[["iso3", "country", "outcome"]].copy()
    out["fossil_reduced"] = t["d_fossil_twh"] < 0
    out[f"demand_twh_{s}"] = t[f"demand_twh_{s}"]
    out[f"demand_twh_{e}"] = t[f"demand_twh_{e}"]
    out["demand_growth_pct"] = growth_pct(t[f"demand_twh_{e}"], t[f"demand_twh_{s}"])
    # Demand = generation + net imports, so the two differ for importers and exporters.
    out["generation_growth_pct"] = growth_pct(t[f"generation_twh_{e}"], t[f"generation_twh_{s}"])
    demand_end = t[f"demand_twh_{e}"].where(t[f"demand_twh_{e}"] > 0)
    out[f"net_imports_share_of_demand_pct_{e}"] = 100 * t[f"net_imports_twh_{e}"] / demand_end
    # Initial mix: share of each source in the start year.
    for src in SOURCES:
        out[f"{src}_share_pct_{s}"] = t[f"{src}_share_pct_{s}"]
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

    world = tables["q1_world_mix"]
    years = list(range(BACKGROUND_YEARS[0], BACKGROUND_YEARS[1] + 1))
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

    q4 = tables["q4_clean_sources"].set_index("iso3")
    base = comparison.set_index("iso3").loc[q4.index]
    assert close(q4[[f"d_{s}_share_pp" for s in CLEAN]].sum(axis=1), q4["d_clean_share_pp"], 0.01), \
        "Q4: source changes (pp) do not add up to the change in clean share"
    assert close(q4[[f"d_{s}_twh" for s in CLEAN]].sum(axis=1),
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
        "q1_world_mix": q1_world_mix(df),
        "q2_share_2024": q2_share_2024(c, comparison, map_ids),
        "q3_share_change": q3_share_change(comparison),
        "q4_clean_sources": q4_clean_sources(comparison),
        "q5_share_vs_fossil": q5_share_vs_fossil(comparison),
        "q5_mix_by_year": q5_mix_by_year(c, comparison),
        "q6_demand_and_mix": q6_demand_and_mix(comparison),
        "robustness": robustness(c),
    }

    found = check(c, tables, comparison, map_ids)

    OUT.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        write(table, OUT / f"{name}.csv")
        print(f"{name}.csv: {len(table)} rows")
    q2 = tables["q2_share_2024"]
    off_map = q2.loc[~q2["on_map"], "country"].tolist()
    print(f"Q2 rows the map cannot draw ({len(off_map)}): {', '.join(off_map)}")
    print(f"Checks passed. {found['share_up_fossil_up']} of {found['share_up']} countries "
          f"raised their clean share but generated more fossil electricity "
          f"({found['countries']} countries compared, {START_YEAR}-{END_YEAR}).")


if __name__ == "__main__":
    main()
