# Data Handling and Initial Sketches

## Scope and Current State

This report covers **Q2, Q3, and Q4 only**, the questions explored with the six
Matplotlib sketches. They are exploratory views, not the final D3 application.

The baseline is 2024 for the snapshot and 2010–2024 for comparisons,
with a minimum of 10 TWh generation in 2024. The sketches show
up to 10 countries per tail. This report reads the preparation baseline tables,
not custom sketch settings. Custom sketch runs export their own CSVs and settings.

The tables below contain real processed rows, not synthetic examples. They are
**case samples**, not random or population-weighted samples. Each section states
the selection rule. Q4 contains all 10 plotted countries. The report displays two
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
- Shares use electricity **generation**, not demand, as the denominator.
- Percentage points (pp) measure share differences: 20% to 30% is +10 pp, not +10% relative growth.

**Filters and Cleaning**
1. Retain 2000–2024, inclusive. The preparation code excludes 2025 as incomplete.
2. Keep country/territory rows with three-letter ISO codes. Assign XKX to Kosovo.
   Exclude regional aggregates and World from the Q2–Q4 selections.
3. Fill a blank source TWh with zero only when the known source TWh already sum to
   total generation within 0.01 TWh. Do not fill unknown totals or clean shares.
4. After that completeness check, fill a missing source share as
   100 × source TWh / generation TWh, only if generation is positive.
   Shares remain unknown for zero generation.
5. For endpoint comparisons, join by ISO3. Require known clean shares and fossil
   generation in both years and at least 10 TWh generation in 2024.
   The baseline has **108 eligible countries**. Q2 has no size threshold.
6. Map ISO3 to three-character ISO numeric IDs with pycountry. Preserve leading zeros
   such as Algeria's 012. The on_map flag tests atlas country-ID membership.
   The map reads only country geometry, preserves holes, and handles antimeridian crossings.
7. For sketches, break cutoff ties by country name and show at most 10 per tail.
   Q3 gain/loss tails exclude zero changes. The stored comparison rank is a descending
   row rank; its equal-value order does not specify the sketch's alphabetical tie policy.

### Stored Tables

| File in data/processed/ | One Row Per | Size | Uses |
| --- | --- | --- | --- |
| country_year.csv | Country or World × observed year | 5,518 × 31 | Q2; Q3–Q4 endpoint/source inputs |
| comparison_2010_2024.csv | Eligible country | 108 × 46 | Q3–Q4 |

Country-years are observed records, not a fully imputed country × year grid.
The in_comparison_set flag repeats fixed country membership across years;
it is not a test of each individual year's eligibility.

## Q2 — Country Clean Electricity Shares

**Question:** How do countries compare in their clean shares in 2024?
Which have the highest and lowest shares?

**Transformation:** select year 2024 and country/territory rows, excluding World.
Keep countries of every generation size. Sort known clean shares for the ranked tails.
Join numeric IDs to atlas geometry, but retain unmapped places in the tabular data.

**Coverage:** 221 countries and territories, including
25 with unknown clean shares.
8 places have no drawable map geometry.
A false map flag does not imply a missing electricity value.

**Sample rule:** three highest and three lowest shares, then China, Germany,
the United States, Gibraltar, Kosovo, Ukraine, and Lesotho, without duplicates.
These cases show middle values, unmapped places, unknown values, and zero generation.
Map IDs are text; keep leading zeros when importing the CSV.

| Country | ISO3 | Map ID | Total Generation 2024 (TWh) | Clean Share 2024 (%) | On Map |
| --- | --- | --- | --- | --- | --- |
| Albania | ALB | 008 | 8.34 | 100.00 | Yes |
| Bhutan | BTN | 064 | 11.00 | 100.00 | Yes |
| Democratic Republic of Congo | COD | 180 | 15.92 | 100.00 | Yes |
| East Timor | TLS | 626 | 0.51 | 0.00 | Yes |
| Gambia | GMB | 270 | 0.51 | 0.00 | Yes |
| Gibraltar | GIB | 292 | 0.22 | 0.00 | No |
| China | CHN | 156 | 10,086.88 | 38.17 | Yes |
| Germany | DEU | 276 | 495.99 | 58.64 | Yes |
| United States | USA | 840 | 4,391.02 | 41.87 | Yes |
| Kosovo | XKX | No Data | 6.77 | 8.57 | No |
| Ukraine | UKR | 804 | No Data | No Data | Yes |
| Lesotho | LSO | 426 | 0.00 | No Data | Yes |

[Download CSV](tables/q2_country_shares_sample.csv)

**Sketch A — Geographic View:** a world choropleth with a common 0–100% color scale.
Gray means no matched data. The equirectangular map is not equal-area; Antarctica is omitted.
**Sketch B — Ranked View:** horizontal bars for the 10 highest and 10 lowest known shares.
Unknown values are excluded, not replaced with zero. Several leaders tie at 100%,
so the cutoff does not establish a unique best country.

Local figures: [Map](../outputs/sketches/q2_2024_map.png) ·
[Rankings](../outputs/sketches/q2_2024_ranking.png).

## Q3 — Largest Changes in Clean Share

**Question:** Which countries had the largest increases or decreases from 2010 to 2024?

**Transformation:** use the 108 eligible endpoint pairs. Calculate
d_clean_share_pp = clean_share_pct_2024 − clean_share_pct_2010.
Select the top 10 strictly positive changes and the top 10 strictly negative
changes separately. This is a percentage-point difference, not percentage growth.

**Sample rule:** three largest gains, three largest losses, plus China and India as
large-system cases outside those extreme tails. Gain Rank refers to all 108
compared countries, not to a separate loss ranking.

| Country | Gain Rank | Clean Share 2010 (%) | Clean Share 2024 (%) | Clean Share Change (pp) |
| --- | --- | --- | --- | --- |
| Denmark | 1 | 32.08 | 89.19 | 57.11 |
| United Kingdom | 2 | 23.12 | 64.93 | 41.81 |
| Netherlands | 3 | 12.84 | 53.66 | 40.82 |
| Ghana | 108 | 68.68 | 36.22 | -32.46 |
| Myanmar | 107 | 71.81 | 47.86 | -23.95 |
| Laos | 106 | 100.00 | 76.72 | -23.28 |
| China | 26 | 20.47 | 38.17 | 17.70 |
| India | 54 | 17.58 | 22.49 | 4.91 |

[Download CSV](tables/q3_share_changes_sample.csv)

**Sketch A — Change Magnitudes:** horizontal gain/loss bars with a shared zero-centered scale.
**Sketch B — Start and End Levels:** open circles mark 2010; filled diamonds mark 2024.
Both sketches use the same countries and order. Lines join endpoints, not annual trends.
This separates the size of a change from the starting and final electricity mix.

Local figures: [Changes](../outputs/sketches/q3_2010_2024_changes.png) ·
[Endpoints](../outputs/sketches/q3_2010_2024_endpoints.png).

## Q4 — Clean Sources Behind the Largest Share Gains

**Question:** Among the largest clean-share gainers, how much change came from
wind and solar compared with hydro and nuclear?

**Selection:** the top 10 positive clean-share gainers, ranked by pp, from the same
eligible comparison set. Both views use the same countries and order.
The TWh view does not reselect countries by absolute-output growth.

**Transformation:** subtract each source's start value from its end value, then sum
member-source changes in three groups:
- Wind + solar = wind + solar.
- Hydro + nuclear = hydro + nuclear.
- Other clean = bioenergy + other renewables excluding bioenergy.

These groups partition all six clean sources. Fossil sources are not included.
For pp, the grouped sum equals clean-share change. For TWh, it equals the change
in clean generation. Each share endpoint has its own total-generation denominator.

### Sample A — Source Share Changes

| Country | Wind + Solar Change (pp) | Hydro + Nuclear Change (pp) | Other Clean Change (pp) | Net Clean Change (pp) |
| --- | --- | --- | --- | --- |
| Denmark | 48.82 | 0.01 | 8.29 | 57.11 |
| United Kingdom | 31.81 | -0.89 | 10.90 | 41.81 |
| Netherlands | 41.78 | -0.45 | -0.50 | 40.82 |
| Finland | 25.59 | 12.52 | -1.02 | 37.09 |
| Belarus | 1.00 | 34.97 | 0.94 | 36.92 |
| Ireland | 30.67 | 0.35 | 2.12 | 33.14 |
| Portugal | 27.78 | 1.30 | 3.10 | 32.18 |
| United Arab Emirates | 8.67 | 22.92 | 0.12 | 31.71 |
| Cambodia | 6.91 | 25.14 | -0.51 | 31.54 |
| Greece | 36.64 | -6.92 | 0.91 | 30.63 |

[Download CSV](tables/q4_source_changes_pp.csv)

### Sample B — Source Generation Changes

| Country | Wind + Solar Change (TWh) | Hydro + Nuclear Change (TWh) | Other Clean Change (TWh) | Net Clean Change (TWh) |
| --- | --- | --- | --- | --- |
| Denmark | 16.37 | 0.00 | 2.47 | 18.84 |
| United Kingdom | 87.74 | -19.38 | 27.83 | 96.19 |
| Netherlands | 51.25 | -0.41 | -0.36 | 50.48 |
| Finland | 21.13 | 11.18 | -0.58 | 31.73 |
| Belarus | 0.46 | 16.04 | 0.46 | 16.96 |
| Ireland | 9.83 | 0.17 | 0.69 | 10.69 |
| Portugal | 12.04 | -1.26 | 1.14 | 11.92 |
| United Arab Emirates | 15.39 | 40.63 | 0.21 | 56.23 |
| Cambodia | 1.07 | 4.34 | 0.07 | 5.48 |
| Greece | 20.94 | -3.89 | 0.52 | 17.57 |

[Download CSV](tables/q4_source_changes_twh.csv)

**Sketch A:** diverging stacked changes in share, in pp.
**Sketch B:** diverging stacked generation changes, in TWh.
Right-hand segments show increases; left-hand segments show declines.
The diamond marks the **signed sum**, not the edge of the positive stack.

For example, UK wind + solar increases by 87.74 TWh,
hydro + nuclear changes by -19.38 TWh, and other clean
increases by 27.83 TWh. Net clean growth is
96.19 TWh. The positive stack extends beyond the net diamond
because a declining group offsets part of the growth, not because fossil sources are included.

This is an accounting breakdown, not proof of cause. A source can gain TWh but lose share
when total generation grows faster. Missing source values cause the sketch calculation
to fail rather than being treated as zero.

Local figures: [Source Shares](../outputs/sketches/q4_2010_2024_source_share.png) ·
[Source Generation](../outputs/sketches/q4_2010_2024_source_generation.png).

## Created and Derived Features

[Feature dictionary](tables/feature_dictionary.csv): **50 stored columns**
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
| Grouped source deltas | Sum member-source changes | pp or TWh; keep negative changes |
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
    uv run python -m sketches
    uv run python -m prep.report
    uv run python -m unittest discover -s tests -v

- prep/build.py checks source totals, clean shares, endpoint consistency, map coverage,
  finite values, and the main country counts.
- sketches/data.py recalculates selections and source changes for configured dates.
  Source groups must sum to net change within 0.01 in the relevant unit.
- prep/report.py checks that documented Q2–Q4 fields exist, checks Q4
  group sums, and rebuilds this report and its CSV tables from processed values.
- Figure links point to local, ignored files under outputs/. Regenerate figures with
  the default sketch config to use the baseline links.
- Processed values already use four decimals. The report only rounds for display.
  It does not edit raw data or impute missing values.
