# Data Handling and Initial Sketches

## Scope and Current State

This report covers **Q1–Q6**. Yathin explored Q2–Q4 with six Matplotlib sketches;
Yusuke explored Q1, Q5, and Q6 with three. They are exploratory views, not the final
D3 application.

The baseline is 2024 for the snapshot and 2000–2024 for comparisons,
with a minimum of 10 TWh generation in 2024. The sketches show
up to 10 countries per tail. This report reads the preparation baseline tables,
not custom sketch settings. Custom sketch runs export their own CSVs and settings.

[Tracked six-figure overview montage](../outputs/preview.png). Q1, Q5, and Q6 are tracked
separately: [Q1](../outputs/preview-q1.png) · [Q5](../outputs/preview-q5.png) ·
[Q6](../outputs/preview-q6.png). Individual figure files
and their data exports remain local and ignored under `outputs/sketches/`.

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
- The Q1–Q5 chart titles state **Domestic Electricity Generation**. The Q6 title names
  electricity demand, because its x-axis is demand growth. These views do not
  measure all energy use or classify imported electricity by source.
- Shares use domestic electricity **generation**, not demand, as the denominator.
- Percentage points (pp) measure share differences: 20% to 30% is +10 pp, not +10% relative growth.
- TWh (terawatt-hours) measures amounts of electricity: 1 TWh = 1 billion kWh.
- Demand is domestic generation plus net imports (OWID electricity_demand_twh).
  Generation and demand differ when a country trades electricity: 29 of the
  108 compared countries had net trade above 10% of their 2024 demand
  (15 net importers, 14 net exporters).

**Filters and Cleaning**
1. Retain 2000–2024, inclusive. The preparation code excludes 2025 as incomplete.
2. Keep country/territory rows with three-letter ISO codes. Assign XKX to Kosovo.
   Exclude regional aggregates. Q1 uses only the World row; Q2–Q6 exclude it.
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
| country_year.csv | Country or World × observed year | 5,518 × 31 | Q1 (World row); Q2; Q3–Q6 endpoint/source inputs |
| comparison_2000_2024.csv | Eligible country | 108 × 46 | Q3–Q4; Q5–Q6 recalculate the same country set |

Country-years are observed records, not a fully imputed country × year grid.
The in_comparison_set flag repeats fixed country membership across years;
it is not a test of each individual year's eligibility.

## Q1 — The World's Electricity Mix

**Question:** How has the global electricity mix changed from 2000 to 2024, in shares and in TWh?

**Transformation:** select the World row for 2000–2024. Group the sources into eight lines:
Coal, Gas, Oil, and the five clean groups used in Q4 (Wind, Solar, Hydro, Nuclear,
Other Clean). Each year's eight values add up to total generation in TWh and to 100%
in shares; the sketch code checks both within 0.01.

**What it shows:** the clean share was 35.3% in 2000, fell to
31.7% in 2007, and reached 40.9% in 2024.
Fossil generation still grew, from 9,879 TWh to 18,276 TWh,
because total generation grew. A rising clean share did not mean less fossil electricity
for the world; Q5 asks the same question for each country.

**Sample rule:** every fourth year from 2000, plus 2024. The first table matches the share chart,
the second the TWh chart.

| Year | Coal (%) | Gas (%) | Oil (%) | Wind (%) | Solar (%) | Hydro (%) | Nuclear (%) | Other Clean (%) | Total Generation (TWh) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2000 | 38.02 | 17.97 | 8.67 | 0.20 | 0.01 | 17.21 | 16.63 | 1.29 | 15,278.78 |
| 2004 | 39.03 | 20.12 | 7.26 | 0.49 | 0.02 | 16.09 | 15.62 | 1.38 | 17,414.99 |
| 2008 | 40.16 | 21.69 | 5.83 | 1.10 | 0.06 | 16.14 | 13.40 | 1.61 | 20,102.64 |
| 2012 | 39.80 | 22.92 | 5.50 | 2.35 | 0.43 | 16.26 | 10.80 | 1.94 | 22,515.66 |
| 2016 | 37.77 | 23.69 | 4.39 | 3.89 | 1.33 | 16.26 | 10.41 | 2.26 | 24,694.51 |
| 2020 | 35.31 | 23.89 | 2.90 | 5.96 | 3.19 | 16.27 | 9.91 | 2.57 | 26,723.37 |
| 2024 | 34.07 | 22.25 | 2.76 | 8.11 | 6.93 | 14.33 | 8.98 | 2.56 | 30,930.23 |

[Download CSV](tables/q1_world_share_sample.csv)

| Year | Coal (TWh) | Gas (TWh) | Oil (TWh) | Wind (TWh) | Solar (TWh) | Hydro (TWh) | Nuclear (TWh) | Other Clean (TWh) | Total Generation (TWh) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2000 | 5,808.81 | 2,745.57 | 1,324.32 | 31.15 | 1.02 | 2,629.67 | 2,540.46 | 197.78 | 15,278.78 |
| 2004 | 6,797.30 | 3,503.08 | 1,263.66 | 85.48 | 2.78 | 2,802.61 | 2,719.41 | 240.67 | 17,414.99 |
| 2008 | 8,074.19 | 4,360.99 | 1,171.72 | 220.85 | 11.85 | 3,245.35 | 2,694.72 | 322.97 | 20,102.64 |
| 2012 | 8,960.28 | 5,161.35 | 1,238.60 | 529.26 | 96.92 | 3,660.17 | 2,432.22 | 436.86 | 22,515.66 |
| 2016 | 9,327.96 | 5,849.92 | 1,085.11 | 960.30 | 327.47 | 4,014.75 | 2,571.05 | 557.95 | 24,694.51 |
| 2020 | 9,437.05 | 6,382.94 | 775.88 | 1,591.47 | 853.39 | 4,347.02 | 2,648.33 | 687.29 | 26,723.37 |
| 2024 | 10,538.94 | 6,882.73 | 853.84 | 2,509.50 | 2,142.65 | 4,433.65 | 2,777.11 | 791.81 | 30,930.23 |

[Download CSV](tables/q1_world_twh_sample.csv)

**Sketch:** two line charts with the same eight lines, shares (%) on the left and
generation (TWh) on the right; two charts rather than two y-axes. Fossil lines are dashed;
clean lines use the Q4 colors. **Planned interaction:** hovering a line highlights that
source in both charts and shows its share and TWh for the year.

Local figure: [World Mix](../outputs/sketches/q1_2000_2024_world_mix.png).

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

**Question:** Which countries had the largest increases or decreases from 2000 to 2024?

**Transformation:** use the 108 eligible endpoint pairs. Calculate
d_clean_share_pp = clean_share_pct_2024 − clean_share_pct_2000.
Select the top 10 strictly positive changes and the top 10 strictly negative
changes separately. This is a percentage-point difference, not percentage growth.

**Sample rule:** three largest gains, three largest losses, plus China and India as
large-system cases outside those extreme tails. Gain Rank refers to all 108
compared countries, not to a separate loss ranking.

| Country | Gain Rank | Clean Share 2000 (%) | Clean Share 2024 (%) | Clean Share Change (pp) |
| --- | --- | --- | --- | --- |
| Denmark | 1 | 15.54 | 89.19 | 73.65 |
| Portugal | 2 | 29.78 | 85.19 | 55.41 |
| Kenya | 3 | 40.37 | 91.48 | 51.11 |
| Ghana | 108 | 91.35 | 36.22 | -55.14 |
| Philippines | 107 | 42.89 | 20.47 | -22.42 |
| Peru | 106 | 81.98 | 60.11 | -21.87 |
| China | 24 | 17.87 | 38.17 | 20.29 |
| India | 48 | 16.81 | 22.49 | 5.69 |

[Download CSV](tables/q3_share_changes_sample.csv)

**Sketch A — Change Magnitudes:** horizontal gain/loss bars with a shared zero-centered scale.
**Sketch B — Start and End Levels:** open circles mark 2000; filled diamonds mark 2024.
Both sketches use the same countries and order. Lines join endpoints, not annual trends.
This separates the size of a change from the starting and final electricity mix.

Local figures: [Changes](../outputs/sketches/q3_2000_2024_changes.png) ·
[Endpoints](../outputs/sketches/q3_2000_2024_endpoints.png).

## Q4 — Clean Sources Behind the Largest Share Gains

**Question:** Among the largest clean-share gainers, how did wind, solar, hydro,
nuclear, and other clean sources each contribute to share and generation changes?

**Selection:** the top 10 positive clean-share gainers, ranked by pp, from the same
eligible comparison set. Both views use the same countries and order.
The TWh view does not reselect countries by absolute-output growth.

**Transformation:** subtract each source's start value from its end value. Keep Wind,
Solar, Hydro, and Nuclear separate. Sum bioenergy and other renewables excluding
bioenergy into Other Clean. Fossil sources are excluded.
These five components partition all six clean sources. Their sum equals the clean-share
change in pp or clean-generation change in TWh. Each share endpoint has its own
total-generation denominator.

### Sample A — Source Share Changes

| Country | Wind Change (pp) | Solar Change (pp) | Hydro Change (pp) | Nuclear Change (pp) | Other Clean Change (pp) | Net Clean Change (pp) |
| --- | --- | --- | --- | --- | --- | --- |
| Denmark | 46.39 | 10.78 | -0.03 | 0.00 | 16.51 | 73.65 |
| Portugal | 29.94 | 15.00 | 5.30 | 0.00 | 5.16 | 55.41 |
| Kenya | 16.36 | 4.98 | -7.02 | 0.00 | 36.78 | 51.11 |
| Netherlands | 26.43 | 17.83 | -0.09 | -1.54 | 3.20 | 45.82 |
| Ireland | 36.27 | 3.51 | -1.12 | 0.00 | 2.84 | 41.49 |
| Greece | 21.14 | 19.73 | -0.70 | 0.00 | 1.24 | 41.41 |
| United Kingdom | 29.06 | 5.20 | 0.68 | -8.27 | 13.08 | 39.74 |
| Belarus | 0.44 | 0.57 | 0.76 | 34.24 | 1.20 | 37.20 |
| Czechia | 0.92 | 4.93 | 1.24 | 22.15 | 6.68 | 35.91 |
| Spain | 20.00 | 20.74 | -0.54 | -8.75 | 1.53 | 32.97 |

[Download CSV](tables/q4_source_changes_pp.csv)

### Sample B — Source Generation Changes

| Country | Wind Change (TWh) | Solar Change (TWh) | Hydro Change (TWh) | Nuclear Change (TWh) | Other Clean Change (TWh) | Net Clean Change (TWh) |
| --- | --- | --- | --- | --- | --- | --- |
| Denmark | 16.17 | 3.78 | -0.01 | 0.00 | 5.76 | 25.70 |
| Portugal | 14.17 | 7.09 | 3.57 | 0.00 | 2.57 | 27.40 |
| Kenya | 2.17 | 0.66 | 1.79 | 0.00 | 5.77 | 10.39 |
| Netherlands | 32.65 | 21.81 | -0.05 | -0.36 | 4.69 | 58.74 |
| Ireland | 11.35 | 1.09 | -0.08 | 0.00 | 0.91 | 13.27 |
| Greece | 12.10 | 11.26 | -0.11 | 0.00 | 0.71 | 23.96 |
| United Kingdom | 82.34 | 14.79 | 0.67 | -44.47 | 36.21 | 89.54 |
| Belarus | 0.20 | 0.26 | 0.37 | 15.69 | 0.55 | 17.07 |
| Czechia | 0.67 | 3.59 | 0.90 | 16.11 | 4.86 | 26.13 |
| Spain | 57.47 | 58.28 | 6.15 | -7.68 | 4.69 | 118.91 |

[Download CSV](tables/q4_source_changes_twh.csv)

**Sketch A:** diverging stacked changes in share, in pp.
**Sketch B:** diverging stacked generation changes, in TWh.
Right-hand segments show increases; left-hand segments show declines.
The diamond marks the **signed sum**, not the edge of the positive stack.

For example, UK wind rises by 82.34 TWh and solar by
14.79 TWh; hydro rises by 0.67 TWh,
while nuclear declines by 44.47 TWh. Other Clean increases
by 36.21 TWh. These five source contributions sum to net
clean growth of 89.54 TWh; the separate values make the nuclear
decline visible rather than masking it within a broader category.

This is an accounting breakdown, not proof of cause. A source can gain TWh but lose share
when total generation grows faster. Missing source values cause the sketch calculation
to fail rather than being treated as zero.

Local figures: [Source Shares](../outputs/sketches/q4_2000_2024_source_share.png) ·
[Source Generation](../outputs/sketches/q4_2000_2024_source_generation.png).

## Q5 — Clean Share and Fossil Generation

**Question:** Which countries raised their clean share while cutting fossil generation,
and which raised it but still generated more fossil electricity?

**Transformation:** use the same 108 eligible countries as Q3–Q4. Calculate
d_fossil_twh = fossil_twh_2024 − fossil_twh_2000, then sort each country into one of four
outcomes: clean share up and fossil down, up and fossil up, up and fossil unchanged,
or clean share not up. Fossil change stays in TWh. Percentage change is not used:
4 countries had no fossil generation in 2000, and small starting values
give changes as large as 32,700%.

**Result:** 35 countries raised their clean share and cut fossil
generation; 44 raised it and still generated more fossil electricity;
0 raised it with fossil generation unchanged; 29 did not
raise it. Of the 79 countries whose clean share rose, 55.7%
also generated more fossil electricity.

**Scale:** fossil change runs from -182.4 TWh to
+5,123.9 TWh (China). On one linear axis,
85 of the 108 countries fall within ±60 TWh and overlap near zero. The sketch
shows the overview and an enlarged ±60 TWh band, both linear and with the same x scale.

**Selected country:** the static sketch selects the largest 2024 generator among the
"share up, fossil up" countries inside the band. With this rule the selected country is **South Africa**: +8.7 pp clean share, +12.7 TWh fossil generation. Its mix appears below the
scatterplots in the Q1 charts.

**Sample rule:** the 12 largest 2024 generators, plus the selected country.

| Country | Outcome | Clean Share Change (pp) | Fossil Generation 2000 (TWh) | Fossil Generation 2024 (TWh) | Fossil Generation Change (TWh) | Total Generation 2024 (TWh) |
| --- | --- | --- | --- | --- | --- | --- |
| China | Clean Share Up, Fossil Up | 20.29 | 1,113.30 | 6,237.20 | 5,123.90 | 10,086.88 |
| United States | Clean Share Up, Fossil Down | 12.81 | 2,697.28 | 2,552.53 | -144.75 | 4,391.02 |
| India | Clean Share Up, Fossil Up | 5.69 | 475.35 | 1,578.43 | 1,103.08 | 2,036.52 |
| Russia | Clean Share Up, Fossil Up | 2.34 | 582.89 | 774.74 | 191.85 | 1,209.31 |
| Japan | Clean Share Not Up | -6.92 | 679.52 | 698.37 | 18.85 | 1,016.39 |
| Brazil | Clean Share Not Up | -1.78 | 30.62 | 78.68 | 48.06 | 745.72 |
| Canada | Clean Share Up, Fossil Down | 5.11 | 165.57 | 142.04 | -23.53 | 636.79 |
| South Korea | Clean Share Up, Fossil Up | 0.96 | 177.37 | 375.91 | 198.54 | 625.38 |
| France | Clean Share Up, Fossil Down | 4.21 | 49.57 | 28.66 | -20.91 | 561.78 |
| Germany | Clean Share Up, Fossil Down | 22.61 | 363.93 | 205.13 | -158.80 | 495.99 |
| Saudi Arabia | Clean Share Up, Fossil Up | 2.16 | 138.69 | 444.82 | 306.13 | 454.64 |
| Iran | Clean Share Up, Fossil Up | 3.97 | 115.53 | 367.39 | 251.86 | 395.79 |
| South Africa | Clean Share Up, Fossil Up | 8.74 | 196.07 | 208.75 | 12.68 | 247.52 |

[Download CSV](tables/q5_fossil_outcomes_sample.csv)

**Sketch:** two scatterplots (x = clean-share change in pp, y = fossil change in TWh).
Color and marker shape both show the outcome. **Planned interaction:** clicking a dot or
choosing a country from a menu shows that country's mix over 2000–2024.

Local figure: [Fossil Outcomes](../outputs/sketches/q5_2000_2024_fossil_outcomes.png).

## Q6 — Demand Growth and the Starting Mix

**Question:** How do demand growth and the 2000 mix differ between countries that reduced
fossil generation and those that did not?

**Transformation:** start from the Q5 table. Leave out 4 countries with zero
fossil generation in both 2000 and 2024 (Bhutan, Democratic Republic of Congo, Iceland, Paraguay); they had no fossil
generation to cut. That leaves 104. Calculate
demand_growth_pct = 100 × (demand_2024 / demand_2000 − 1). Group countries by
fossil_reduced (d_fossil_twh < 0).

**Result:** the group comparison answers Q6. Median demand growth was
10.4% where fossil generation fell and
165.3% where it did not.

| Group | Countries | Median Demand Growth (%) | Lower Quartile (%) | Upper Quartile (%) |
| --- | --- | --- | --- | --- |
| Fossil Generation Fell | 35 | 10.41 | 2.80 | 30.35 |
| Did Not Fall | 69 | 165.27 | 79.25 | 231.50 |

[Download CSV](tables/q6_group_summary.csv)

**Matched pairs:** for each country whose fossil generation fell, the sketch finds a
country whose fossil generation did not fall with the closest demand growth. It takes the
smallest gaps first, uses each country once, and breaks ties by name. The
6 pairs show exceptions to the group pattern: similar demand growth,
opposite fossil outcomes. They are illustrations, not a sample.

| Pair | Fossil Fell | Demand Growth, Fell (%) | Fossil Did Not Fall | Demand Growth, Did Not Fall (%) | Gap (pp) |
| --- | --- | --- | --- | --- | --- |
| 1 | Netherlands | 10.41 | South Africa | 10.42 | 0.00 |
| 2 | Greece | 7.25 | Serbia | 7.21 | 0.05 |
| 3 | Sweden | -7.47 | Japan | -7.57 | 0.10 |
| 4 | Costa Rica | 75.59 | Uzbekistan | 75.38 | 0.20 |
| 5 | Hungary | 26.15 | Tajikistan | 25.88 | 0.26 |
| 6 | Australia | 29.89 | Cuba | 29.27 | 0.61 |

[Download CSV](tables/q6_matched_pairs.csv)

**Scale:** demand growth runs from -18.9% to +4,066.7%
(Cambodia). 89 of the 104 countries are at or below 300%,
so the sketch shows the overview and an enlarged band up to 300%, both linear.

**Sketch:** two scatterplots (x = demand growth, y = clean share in 2000) with each group's
median as a dashed line; bars compare the selected pair's 2000 mix, and a table shows their
numbers. **Planned interaction:** a button for each pair rings both countries and updates
the bars and the table.

Local figure: [Demand Pairs](../outputs/sketches/q6_2000_2024_demand_pairs.png).

## Cutoffs and Sensitivity

**Start year 2000:** the processed tables begin in 2000. In the raw OWID file, 81
places have generation data in 1999 and 211 in 2000, so an earlier start would
compare a much smaller set of countries.

**Size threshold 10 TWh in 2024:** in a small system, one new plant can move the
clean share by many points. The threshold keeps 108 of the 193
countries with data in both 2000 and 2024.

**Sensitivity:** data/processed/robustness.csv recalculates the Q5 result for four start
years and five thresholds: the percentage of countries with a rising clean share that also
generated more fossil electricity.

| Start Year | ≥ 0 TWh (%) | ≥ 5 TWh (%) | ≥ 10 TWh (%) | ≥ 20 TWh (%) | ≥ 50 TWh (%) |
| --- | --- | --- | --- | --- | --- |
| 2000 | 59.90 | 56.40 | 55.70 | 56.90 | 53.70 |
| 2005 | 52.50 | 48.90 | 49.40 | 50.00 | 50.00 |
| 2010 | 51.40 | 47.50 | 49.40 | 47.10 | 52.20 |
| 2015 | 46.70 | 45.70 | 46.70 | 45.80 | 47.90 |

Across these 20 settings, the value ranges from 45.7% to
59.9%. The baseline is 55.7%
(44 of 79).

## Created and Derived Features

[Feature dictionary](tables/feature_dictionary.csv): **60 columns**
used for Q1–Q6, with units, input fields, and transformation rules.
It covers the relevant fields in the two processed tables and the Q5–Q6 measures
that the sketches derive, not unrelated fields.
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
| demand_twh, net_imports_twh | Rename OWID demand and net imports | TWh; demand = generation + net imports |
| Coal, gas, and oil TWh and shares | Rename; same missing-value rules as clean sources | TWh or %; Q1 lines and Q6 start mix |
| d_fossil_twh, outcome, fossil_reduced | End minus start fossil generation; four outcomes | TWh; categories (Q5) and groups (Q6) |
| demand_growth_pct, generation_growth_pct | 100 × (end / start − 1) | %; blank if the start is not positive |

Sketch exports use _start and _end suffixes rather than year suffixes. Their source tables
use configurable group labels as columns and total for net clean change.
Custom sketch groups must include every clean source exactly once.

## Limits

Results depend on the window, size threshold, and endpoint coverage. Small systems remain
in Q2 but not necessarily in Q3–Q4. Some places cannot appear on the map.
Case samples do not establish population-level distributions.
No country-average or generation-weighted aggregation is used in these samples.
Q4 aggregates source changes within each country, not across countries.
Q5 and Q6 show associations, not causes. The Q6 pairs are chosen by a rule to show
exceptions; they are not a sample.

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
- sketches/q156_data.py checks that the eight Q1 lines add up to generation and to 100%,
  and recalculates the Q5 outcomes and the Q6 groups and pairs for configured dates.
- prep/report.py checks that documented Q1–Q6 fields exist, checks Q4
  group sums, and rebuilds this report and its CSV tables from processed values.
- The overview montage is tracked at outputs/preview.png, and Q1, Q5, and Q6 at
  outputs/preview-q1.png, preview-q5.png, and preview-q6.png. Individual figure links
  point to local, ignored files under outputs/sketches/; regenerate with the default config.
- Processed values already use four decimals. The report only rounds for display.
  It does not edit raw data or impute missing values.
