"""Build baseline report and samples: uv run python -m prep.report."""

from pathlib import Path

import pandas as pd

from prep.build import (
    CLEAN, CLEAN_GROUPS, END_YEAR, MEASURES, MIN_GENERATION_TWH,
    ROOT, START_YEAR, YEARS,
)

TOP_N = 10


def load_tables():
    directory = ROOT / "data/processed"
    types = {"iso3": "string", "iso_numeric": "string"}
    return (
        pd.read_csv(directory / "country_year.csv", dtype=types),
        pd.read_csv(directory / "comparison_2010_2024.csv", dtype=types),
    )


def named_sample(table, countries):
    """Use explicit cases, not random or population-weighted samples."""
    return table.set_index("country").loc[countries].reset_index()


def build_samples(country_year, compared):
    s, e = START_YEAR, END_YEAR
    current = country_year.loc[
        country_year["year"].eq(e) & country_year["iso3"].notna()
    ].copy()
    valid = current.dropna(subset=["clean_share_pct"])
    high = valid.sort_values(["clean_share_pct", "country"], ascending=[False, True]).head(3)
    low = valid.sort_values(["clean_share_pct", "country"]).head(3)
    snapshot_sample = pd.concat([
        high, low,
        named_sample(current, ["China", "Germany", "United States", "Gibraltar", "Kosovo", "Ukraine", "Lesotho"]),
    ]).drop_duplicates("iso3")
    gains = compared.loc[compared["d_clean_share_pp"].gt(0)].sort_values(
        ["d_clean_share_pp", "country"], ascending=[False, True],
    )
    losses = compared.loc[compared["d_clean_share_pp"].lt(0)].sort_values(["d_clean_share_pp", "country"])
    change_sample = pd.concat([
        gains.head(3), losses.head(3), named_sample(compared, ["China", "India"]),
    ]).drop_duplicates("iso3")
    selected = gains.head(TOP_N)
    samples = {
        "q2_country_shares_sample": snapshot_sample[[
            "country", "iso3", "iso_numeric", "generation_twh", "clean_share_pct", "on_map",
        ]].rename(columns={
            "country": "Country", "iso3": "ISO3", "iso_numeric": "Map ID",
            "generation_twh": f"Total Generation {e} (TWh)",
            "clean_share_pct": f"Clean Share {e} (%)", "on_map": "On Map",
        }),
        "q3_share_changes_sample": change_sample[[
            "country", "rank", f"clean_share_pct_{s}", f"clean_share_pct_{e}", "d_clean_share_pp",
        ]].rename(columns={
            "country": "Country", "rank": "Gain Rank",
            f"clean_share_pct_{s}": f"Clean Share {s} (%)",
            f"clean_share_pct_{e}": f"Clean Share {e} (%)",
            "d_clean_share_pp": "Clean Share Change (pp)",
        }),
    }
    for unit in ("pp", "twh"):
        suffix, display_unit = ("share_pp", "pp") if unit == "pp" else ("twh", "TWh")
        table = selected[["country"]].rename(columns={"country": "Country"}).copy()
        source_deltas = {
            "Wind": selected[f"d_wind_{suffix}"],
            "Solar": selected[f"d_solar_{suffix}"],
            "Hydro": selected[f"d_hydro_{suffix}"],
            "Nuclear": selected[f"d_nuclear_{suffix}"],
            "Other Clean": (
                selected[f"d_bioenergy_{suffix}"]
                + selected[f"d_other_renewables_excluding_bioenergy_{suffix}"]
            ),
        }
        for label, values in source_deltas.items():
            table[f"{label} Change ({display_unit})"] = values
        endpoints = country_year.set_index(["iso3", "year"])["clean_twh"]
        net = (
            selected["d_clean_share_pp"] if unit == "pp" else
            selected["iso3"].map(endpoints.xs(e, level="year"))
            - selected["iso3"].map(endpoints.xs(s, level="year"))
        )
        components = table.iloc[:, 1:].sum(axis=1, min_count=len(source_deltas))
        if net.isna().any() or not (components - net).abs().lt(0.01).all():
            raise ValueError(f"Q4 {unit} components do not add up to net clean change")
        table[f"Net Clean Change ({display_unit})"] = net
        samples[f"q4_source_changes_{unit}"] = table
    return samples


def feature_dictionary(country_year, compared):
    """Describe only the stored fields used for Q2–Q4 and their eligibility rules."""
    entries = []

    def add(table, feature, kind, unit, inputs, rule):
        entries.append({
            "Table": table, "Feature": feature, "Kind": kind, "Unit": unit,
            "Inputs": inputs, "Transformation or Meaning": rule,
        })

    shared = {
        "iso3": ("Normalized ID", "text", "iso_code; country", "Copy iso_code; assign XKX to Kosovo."),
        "iso_numeric": ("Derived ID", "text", "iso3; pycountry", "Look up ISO numeric code; preserve three characters and leading zeros."),
        "country": ("Copied", "text", "country", "Country/territory name; exclude World from these questions."),
    }
    for name, metadata in shared.items():
        add("country_year.csv", name, *metadata)
        add("comparison_2010_2024.csv", name, *metadata)
    add("country_year.csv", "year", "Filtered", "year", "year", f"Keep {YEARS[0]}–{YEARS[1]}, inclusive; select the snapshot or endpoint year.")
    add("country_year.csv", "on_map", "Derived Flag", "boolean", "iso_numeric; atlas country IDs", "True if the ID exists in the atlas countries object.")
    add("country_year.csv", "in_comparison_set", "Derived Flag", "boolean", "iso3; comparison IDs", "Fixed baseline country membership repeated on every year, not year-specific eligibility.")
    measures = {"generation_twh", "clean_share_pct", "clean_twh", "fossil_twh"}
    measures.update(f"{source}_{suffix}" for source in CLEAN for suffix in ("twh", "share_pct"))
    for raw, processed in MEASURES.items():
        if processed not in measures:
            continue
        rule = "Rename the OWID field; retain unknown values."
        if processed in {f"{source}_twh" for source in CLEAN}:
            rule += " Fill a missing source with 0 only when known source TWh sum matches generation within 0.01 TWh."
        if processed in {f"{source}_share_pct" for source in CLEAN}:
            rule += " For complete source totals and positive generation, fill missing share as 100 × source TWh / generation TWh."
        if processed == "fossil_twh":
            rule += " Used for endpoint coverage eligibility, not as a Q4 component."
        add("country_year.csv", processed, "Renamed / Cleaned", "%" if processed.endswith("_pct") else "TWh", raw, rule)

    table = "comparison_2010_2024.csv"
    add(table, "rank", "Derived Rank", "integer", "d_clean_share_pp", "1-based descending row rank across the comparison set; CSV ties have no specified alphabetical policy.")
    for year in (START_YEAR, END_YEAR):
        for measure in ("clean_share_pct", "fossil_twh"):
            add(table, f"{measure}_{year}", "Joined Endpoint", "%" if measure.endswith("_pct") else "TWh",
                f"country_year.{measure}; iso3; year", f"Inner-join endpoints on ISO3; select year {year}.")
    add(table, f"generation_twh_{END_YEAR}", "Joined Endpoint", "TWh", "country_year.generation_twh", f"Total generation in {END_YEAR}; used for the eligibility threshold.")
    add(table, "d_clean_share_pp", "Derived Difference", "percentage points", f"clean_share_pct_{START_YEAR}; clean_share_pct_{END_YEAR}", "End share minus start share; not percentage growth.")
    for source in CLEAN:
        for suffix, measure, unit in (("share_pp", "share_pct", "percentage points"), ("twh", "twh", "TWh")):
            add(table, f"d_{source}_{suffix}", "Derived Difference", unit,
                f"{source}_{measure}_{START_YEAR}; {source}_{measure}_{END_YEAR}", "End source value minus start source value.")
    for suffix, unit in (("share_pp", "percentage points"), ("twh", "TWh")):
        members = CLEAN_GROUPS["other_clean"]
        add(table, f"d_other_clean_{suffix}", "Derived Sum", unit,
            "; ".join(f"d_{source}_{suffix}" for source in members),
            "Sum bioenergy and other renewables excluding bioenergy; the four other clean sources are shown separately.")

    result = pd.DataFrame(entries)
    for name, frame in (("country_year.csv", country_year), (table, compared)):
        documented = result.loc[result["Table"].eq(name), "Feature"]
        if not set(documented).issubset(frame.columns) or documented.duplicated().any():
            raise ValueError(f"Feature dictionary does not match {name}")
    return result


def markdown_table(table):
    def cell(value):
        if pd.isna(value):
            return "No Data"
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if isinstance(value, float):
            return f"{value:,.2f}"
        return str(value).replace("|", "\\|").replace("\n", " ")

    rows = ["| " + " | ".join(map(str, table.columns)) + " |",
            "| " + " | ".join("---" for _ in table.columns) + " |"]
    rows.extend("| " + " | ".join(cell(value) for value in row) + " |"
                for row in table.itertuples(index=False, name=None))
    return "\n".join(rows)


def build_report(output_dir=ROOT / "reports"):
    country_year, compared = load_tables()
    samples = build_samples(country_year, compared)
    dictionary = feature_dictionary(country_year, compared)
    output_dir = Path(output_dir)
    table_dir = output_dir / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    for name, table in {**samples, "feature_dictionary": dictionary}.items():
        table.to_csv(table_dir / f"{name}.csv", index=False, float_format="%.4f")

    def sample(name):
        return markdown_table(samples[name]) + f"\n\n[Download CSV](tables/{name}.csv)"

    s, e = START_YEAR, END_YEAR
    current = country_year.loc[country_year["year"].eq(e) & country_year["iso3"].notna()]
    uk = samples["q4_source_changes_twh"].set_index("Country").loc["United Kingdom"]
    report = f"""# Data Handling and Initial Sketches

## Scope and Current State

This report covers **Q2, Q3, and Q4 only**, the questions explored with the six
Matplotlib sketches. They are exploratory views, not the final D3 application.

The baseline is {e} for the snapshot and {s}–{e} for comparisons,
with a minimum of {MIN_GENERATION_TWH:g} TWh generation in {e}. The sketches show
up to {TOP_N} countries per tail. This report reads the preparation baseline tables,
not custom sketch settings. Custom sketch runs export their own CSVs and settings.

[Tracked six-figure overview montage](../outputs/preview.png). Individual figure files
and their data exports remain local and ignored under `outputs/sketches/`.

The tables below contain real processed rows, not synthetic examples. They are
**case samples**, not random or population-weighted samples. Each section states
the selection rule. Q4 contains all {TOP_N} plotted countries. The report displays two
decimal places; downloadable CSVs retain four decimals where applicable. Rounding
can make displayed sums differ by 0.01. **No Data** means unknown, not zero.
CSV samples use blank cells for the same unknown values.

## Shared Data Handling

**Sources**
- Energy: pinned OWID energy file, data/raw/owid_energy_2026-09-30.csv (CC BY 4.0).
  Processing reads the local copy because the upstream download changes over time.
- Map: pinned world-atlas 2.0.2, data/raw/world-atlas-2.0.2-countries-50m.json
  (ISC; geometry from Natural Earth).

**Definitions**
- Clean electricity is nuclear, hydro, wind, solar, bioenergy, and other renewables
  excluding bioenergy. “Clean” is our short name for OWID's low-carbon category.
- Fossil electricity is coal + gas + oil. These are electricity measures, not total energy use.
- All six chart titles state **Domestic Electricity Generation**. These views do not
  measure all energy use or classify imported electricity by source.
- Shares use domestic electricity **generation**, not demand, as the denominator.
- Percentage points (pp) measure share differences: 20% to 30% is +10 pp, not +10% relative growth.

**Filters and Cleaning**
1. Retain {YEARS[0]}–{YEARS[1]}, inclusive. The preparation code excludes 2025 as incomplete.
2. Keep country/territory rows with three-letter ISO codes. Assign XKX to Kosovo.
   Exclude regional aggregates and World from the Q2–Q4 selections.
3. Fill a blank source TWh with zero only when the known source TWh already sum to
   total generation within 0.01 TWh. Do not fill unknown totals or clean shares.
4. After that completeness check, fill a missing source share as
   100 × source TWh / generation TWh, only if generation is positive.
   Shares remain unknown for zero generation.
5. For endpoint comparisons, join by ISO3. Require known clean shares and fossil
   generation in both years and at least {MIN_GENERATION_TWH:g} TWh generation in {e}.
   The baseline has **{len(compared)} eligible countries**. Q2 has no size threshold.
6. Map ISO3 to three-character ISO numeric IDs with pycountry. Preserve leading zeros
   such as Algeria's 012. The on_map flag tests atlas country-ID membership.
   The map reads only country geometry, preserves holes, and handles antimeridian crossings.
7. For sketches, break cutoff ties by country name and show at most {TOP_N} per tail.
   Q3 gain/loss tails exclude zero changes. The stored comparison rank is a descending
   row rank; its equal-value order does not specify the sketch's alphabetical tie policy.

### Stored Tables

| File in data/processed/ | One Row Per | Size | Uses |
| --- | --- | --- | --- |
| country_year.csv | Country or World × observed year | {len(country_year):,} × {len(country_year.columns)} | Q2; Q3–Q4 endpoint/source inputs |
| comparison_2010_2024.csv | Eligible country | {len(compared)} × {len(compared.columns)} | Q3–Q4 |

Country-years are observed records, not a fully imputed country × year grid.
The in_comparison_set flag repeats fixed country membership across years;
it is not a test of each individual year's eligibility.

## Q2 — Country Clean Electricity Shares

**Question:** How do countries compare in their clean shares in {e}?
Which have the highest and lowest shares?

**Transformation:** select year {e} and country/territory rows, excluding World.
Keep countries of every generation size. Sort known clean shares for the ranked tails.
Join numeric IDs to atlas geometry, but retain unmapped places in the tabular data.

**Coverage:** {len(current)} countries and territories, including
{int(current["clean_share_pct"].isna().sum())} with unknown clean shares.
{int((~current["on_map"]).sum())} places have no drawable map geometry.
A false map flag does not imply a missing electricity value.

**Sample rule:** three highest and three lowest shares, then China, Germany,
the United States, Gibraltar, Kosovo, Ukraine, and Lesotho, without duplicates.
These cases show middle values, unmapped places, unknown values, and zero generation.
Map IDs are text; keep leading zeros when importing the CSV.

{sample("q2_country_shares_sample")}

**Sketch A — Geographic View:** a world choropleth with a common 0–100% color scale.
Gray means no matched data. The equirectangular map is not equal-area; Antarctica is omitted.
**Sketch B — Ranked View:** horizontal bars for the {TOP_N} highest and {TOP_N} lowest known shares.
Unknown values are excluded, not replaced with zero. Several leaders tie at 100%,
so the cutoff does not establish a unique best country.

Local figures: [Map](../outputs/sketches/q2_{e}_map.png) ·
[Rankings](../outputs/sketches/q2_{e}_ranking.png).

## Q3 — Largest Changes in Clean Share

**Question:** Which countries had the largest increases or decreases from {s} to {e}?

**Transformation:** use the {len(compared)} eligible endpoint pairs. Calculate
d_clean_share_pp = clean_share_pct_{e} − clean_share_pct_{s}.
Select the top {TOP_N} strictly positive changes and the top {TOP_N} strictly negative
changes separately. This is a percentage-point difference, not percentage growth.

**Sample rule:** three largest gains, three largest losses, plus China and India as
large-system cases outside those extreme tails. Gain Rank refers to all {len(compared)}
compared countries, not to a separate loss ranking.

{sample("q3_share_changes_sample")}

**Sketch A — Change Magnitudes:** horizontal gain/loss bars with a shared zero-centered scale.
**Sketch B — Start and End Levels:** open circles mark {s}; filled diamonds mark {e}.
Both sketches use the same countries and order. Lines join endpoints, not annual trends.
This separates the size of a change from the starting and final electricity mix.

Local figures: [Changes](../outputs/sketches/q3_{s}_{e}_changes.png) ·
[Endpoints](../outputs/sketches/q3_{s}_{e}_endpoints.png).

## Q4 — Clean Sources Behind the Largest Share Gains

**Question:** Among the largest clean-share gainers, how did wind, solar, hydro,
nuclear, and other clean sources each contribute to share and generation changes?

**Selection:** the top {TOP_N} positive clean-share gainers, ranked by pp, from the same
eligible comparison set. Both views use the same countries and order.
The TWh view does not reselect countries by absolute-output growth.

**Transformation:** subtract each source's start value from its end value. Keep Wind,
Solar, Hydro, and Nuclear separate. Sum bioenergy and other renewables excluding
bioenergy into Other Clean. Fossil sources are excluded.
These five components partition all six clean sources. Their sum equals the clean-share
change in pp or clean-generation change in TWh. Each share endpoint has its own
total-generation denominator.

### Sample A — Source Share Changes

{sample("q4_source_changes_pp")}

### Sample B — Source Generation Changes

{sample("q4_source_changes_twh")}

**Sketch A:** diverging stacked changes in share, in pp.
**Sketch B:** diverging stacked generation changes, in TWh.
Right-hand segments show increases; left-hand segments show declines.
The diamond marks the **signed sum**, not the edge of the positive stack.

For example, UK wind rises by {uk["Wind Change (TWh)"]:.2f} TWh and solar by
{uk["Solar Change (TWh)"]:.2f} TWh; hydro rises by {uk["Hydro Change (TWh)"]:.2f} TWh,
while nuclear declines by {abs(uk["Nuclear Change (TWh)"]):.2f} TWh. Other Clean increases
by {uk["Other Clean Change (TWh)"]:.2f} TWh. These five source contributions sum to net
clean growth of {uk["Net Clean Change (TWh)"]:.2f} TWh; the separate values make the nuclear
decline visible rather than masking it within a broader category.

This is an accounting breakdown, not proof of cause. A source can gain TWh but lose share
when total generation grows faster. Missing source values cause the sketch calculation
to fail rather than being treated as zero.

Local figures: [Source Shares](../outputs/sketches/q4_{s}_{e}_source_share.png) ·
[Source Generation](../outputs/sketches/q4_{s}_{e}_source_generation.png).

## Created and Derived Features

[Feature dictionary](tables/feature_dictionary.csv): **{len(dictionary)} stored columns**
used for Q2–Q4, with units, input fields, and transformation rules.
It covers the relevant fields in the two processed tables, not unrelated fields.
Copied/renamed source measures are distinguished from newly derived features.

| Feature or Family | Transformation | Unit or Rule |
| --- | --- | --- |
| generation_twh | Rename OWID total electricity generation | TWh; threshold and share denominator |
| clean_share_pct, clean_twh | Rename OWID low-carbon fields | % or TWh; includes nuclear |
| fossil_twh and its endpoints | Rename and join fossil generation | TWh; endpoint coverage eligibility only |
| Clean-source TWh and shares | Rename; apply conditional missing-value rules | TWh or %; missing is not zero |
| iso3, iso_numeric | Normalize ID; map ISO3 to numeric code | Text; preserve leading zeros |
| on_map, in_comparison_set | Test map-ID or baseline-country membership | Boolean |
| Year-suffixed endpoint measures | Join endpoints by ISO3 | Original units |
| d_clean_share_pp; source share deltas | End share minus start share | Percentage points |
| Clean-source TWh deltas | End generation minus start generation | TWh |
| Other Clean deltas | Sum bioenergy and other renewables excluding bioenergy changes | pp or TWh; keep negative changes |
| rank | Sort eligible countries by clean-share gain | 1-based row rank |

Sketch exports use _start and _end suffixes rather than year suffixes. Their source tables
use configurable group labels as columns and total for net clean change.
Custom sketch groups must include every clean source exactly once.

## Limits

Results depend on the window, size threshold, and endpoint coverage. Small systems remain
in Q2 but not necessarily in Q3–Q4. Some places cannot appear on the map.
Case samples do not establish population-level distributions.
No country-average or generation-weighted aggregation is used in these samples.
Q4 aggregates source changes within each country, not across countries.

## Reproduction and Checks

Run from the repository root:

    uv sync --locked
    uv run python prep/build.py
    uv run python -m sketches --preview outputs/preview.png
    uv run python -m prep.report
    uv run python -m unittest discover -s tests -v

- prep/build.py checks source totals, clean shares, endpoint consistency, map coverage,
  finite values, and the main country counts.
- sketches/data.py recalculates selections and source changes for configured dates.
  Source groups must sum to net change within 0.01 in the relevant unit.
- prep/report.py checks that documented Q2–Q4 fields exist, checks Q4
  group sums, and rebuilds this report and its CSV tables from processed values.
- The overview montage is tracked at outputs/preview.png. Individual figure links
  point to local, ignored files under outputs/sketches/; regenerate with the default config.
- Processed values already use four decimals. The report only rounds for display.
  It does not edit raw data or impute missing values.
"""
    path = output_dir / "data-handling.md"
    path.write_text(report, encoding="utf-8")
    print(f"{path}: {len(samples)} result tables; {len(dictionary)} documented features")
    return path


if __name__ == "__main__":
    build_report()
