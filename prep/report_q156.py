"""Q1, Q5 and Q6 parts of the data-handling report. prep/report.py assembles them.

The numbers come from the same sketches/q156_data.py functions the sketches use,
run at the preparation baseline (years and size threshold from prep/build.py).
"""

import pandas as pd

from prep.build import END_YEAR, MEASURES, MIN_GENERATION_TWH, RAW, ROOT, START_YEAR
from sketches.data import load_country_year
from sketches.q156_data import (
    OUTCOME_LABELS, fossil_outcomes, group_summary, growth_pct, load_world, matched_pairs, mix_table,
    q5_example, q6_countries, window,
)
from sketches.settings import Settings, SourceGroup

Q5_SAMPLE_SIZE = 12
# Net trade above this share of demand makes generation and demand differ noticeably.
TRADE_PCT = 10
RAW_NAME = {processed: raw for raw, processed in MEASURES.items()}
# The five clean groups of the default config (as in Q4). Colors are not used in the report.
BASELINE_GROUPS = (
    SourceGroup("Wind", ("wind",), "#4C78A8"),
    SourceGroup("Solar", ("solar",), "#E6AC27"),
    SourceGroup("Hydro", ("hydro",), "#3AA7A3"),
    SourceGroup("Nuclear", ("nuclear",), "#8D6BB8"),
    SourceGroup("Other Clean", ("bioenergy", "other_renewables_excluding_bioenergy"), "#5A9A78"),
)


def baseline_settings():
    """Fixed report settings: the preparation baseline and the Q5/Q6 defaults.

    They do not read sketches/config.toml, so editing the sketch config does not change the report.
    """
    return Settings(
        snapshot_year=END_YEAR, start_year=START_YEAR, end_year=END_YEAR, top_n=10,
        min_generation_twh=float(MIN_GENERATION_TWH), output_dir=ROOT / "outputs/sketches", formats=("png",),
        dpi=160, groups=BASELINE_GROUPS,
    )


def q156_results():
    settings = baseline_settings()
    countries = load_country_year()
    outcomes = fossil_outcomes(countries, settings)
    q6_table, left_out = q6_countries(outcomes)
    return {
        "settings": settings,
        "world": window(load_world(), settings),
        "outcomes": outcomes,
        "example": q5_example(outcomes, settings),
        "q6": q6_table,
        "left_out": left_out,
        "pairs": matched_pairs(q6_table, settings.q6_pairs),
        "summary": group_summary(q6_table),
    }


def q156_samples(results):
    settings, world, outcomes = results["settings"], results["world"], results["outcomes"]
    s, e = settings.start_year, settings.end_year
    years = sorted({*range(s, e + 1, 4), e})
    samples = {}
    for unit, suffix in (("share_pct", "%"), ("twh", "TWh")):
        mix = mix_table(world, settings, unit)
        table = mix.loc[mix["year"].isin(years)].rename(
            columns=lambda name: "Year" if name == "year" else f"{name} ({suffix})",
        )
        table["Total Generation (TWh)"] = world.set_index("year").loc[table["Year"], "generation_twh"].to_numpy()
        samples[f"q1_world_{'share' if unit == 'share_pct' else 'twh'}_sample"] = table.reset_index(drop=True)

    largest = outcomes.sort_values(["generation_twh_end", "country"], ascending=[False, True]).head(Q5_SAMPLE_SIZE)
    if results["example"] is not None:
        largest = pd.concat([largest, outcomes.loc[outcomes["country"].eq(results["example"]["country"])]])
    samples["q5_fossil_outcomes_sample"] = largest.drop_duplicates("iso3").assign(
        outcome=lambda table: table["outcome"].map(OUTCOME_LABELS),
    )[[
        "country", "outcome", "d_clean_share_pp", "fossil_twh_start", "fossil_twh_end", "d_fossil_twh",
        "generation_twh_end",
    ]].rename(columns={
        "country": "Country", "outcome": "Outcome", "d_clean_share_pp": "Clean Share Change (pp)",
        "fossil_twh_start": f"Fossil Generation {s} (TWh)", "fossil_twh_end": f"Fossil Generation {e} (TWh)",
        "d_fossil_twh": "Fossil Generation Change (TWh)", "generation_twh_end": f"Total Generation {e} (TWh)",
    })

    summary = results["summary"]
    samples["q6_group_summary"] = pd.DataFrame({
        "Group": summary["fossil_reduced"].map({True: "Fossil Generation Fell", False: "Did Not Fall"}),
        "Countries": summary["countries"],
        "Median Demand Growth (%)": summary["median_demand_growth_pct"],
        "Lower Quartile (%)": summary["q1_demand_growth_pct"],
        "Upper Quartile (%)": summary["q3_demand_growth_pct"],
    })
    samples["q6_matched_pairs"] = results["pairs"].rename(columns={
        "pair": "Pair", "country_reduced": "Fossil Fell",
        "demand_growth_pct_reduced": "Demand Growth, Fell (%)", "country_other": "Fossil Did Not Fall",
        "demand_growth_pct_other": "Demand Growth, Did Not Fall (%)", "gap_pp": "Gap (pp)",
    })
    return samples


def q156_dictionary(country_year, results):
    """Fields Q1, Q5 and Q6 add to the Q2–Q4 dictionary."""
    s, e = results["settings"].start_year, results["settings"].end_year
    export = f"q5_{s}_{e}_fossil_outcomes.csv (sketch export)"
    stored = [
        ("demand_twh", "TWh", "Rename the OWID field; generation + net imports. Retain unknown values."),
        ("net_imports_twh", "TWh", "Rename the OWID field; negative means net exports."),
    ]
    for source in ("coal", "gas", "oil"):
        stored.append((f"{source}_twh", "TWh", "Rename the OWID field; the same zero-fill rule as the clean sources."))
        stored.append((f"{source}_share_pct", "%", "Rename the OWID field; the same fill rule as the clean-source shares."))
    rows = [("country_year.csv", name, "Renamed / Cleaned", unit, RAW_NAME[name], rule) for name, unit, rule in stored]
    rows += [
        (export, "d_fossil_twh", "Derived Difference", "TWh", "fossil_twh_end; fossil_twh_start",
         "End fossil generation minus start; not percentage growth."),
        (export, "outcome", "Derived Category", "text", "d_clean_share_pp; d_fossil_twh",
         "Clean share up (> 0 pp) with fossil down, up, or unchanged; otherwise clean share not up."),
        (export, "fossil_reduced", "Derived Flag", "boolean", "d_fossil_twh", "True if d_fossil_twh < 0 (Q6 groups)."),
        (export, "demand_growth_pct", "Derived Growth", "%", "demand_twh_end; demand_twh_start",
         "100 × (end / start − 1); blank if start demand is not positive."),
        (export, "generation_growth_pct", "Derived Growth", "%", "generation_twh_end; generation_twh_start",
         "100 × (end / start − 1); blank if start generation is not positive."),
        (export, "net_imports_share_of_demand_pct_end", "Derived Ratio", "%", "net_imports_twh_end; demand_twh_end",
         f"100 × net imports / demand in {e}; blank if demand is not positive."),
    ]
    result = pd.DataFrame(rows, columns=["Table", "Feature", "Kind", "Unit", "Inputs", "Transformation or Meaning"])
    for name, frame in (("country_year.csv", country_year), (export, results["outcomes"])):
        documented = result.loc[result["Table"].eq(name), "Feature"]
        if not set(documented).issubset(frame.columns):
            raise ValueError(f"Q1/Q5/Q6 dictionary does not match {name}")
    return result


def facts(results):
    """Numbers quoted in the text, recalculated on every build."""
    settings, world, outcomes, q6 = results["settings"], results["world"], results["outcomes"], results["q6"]
    s = settings.start_year
    clean = world.set_index("year")["clean_share_pct"]
    fossil = world.set_index("year")["fossil_twh"]
    counts = outcomes["outcome"].value_counts()
    share_up = int(outcomes["d_clean_share_pp"].gt(0).sum())
    fossil_pct = growth_pct(outcomes["fossil_twh_end"], outcomes["fossil_twh_start"])
    trade = outcomes["net_imports_share_of_demand_pct_end"]
    largest_fossil = outcomes.loc[outcomes["d_fossil_twh"].idxmax()]
    largest_demand = q6.loc[q6["demand_growth_pct"].idxmax()]
    return {
        "clean_start": clean.loc[s], "clean_end": clean.iloc[-1],
        "clean_min_year": int(clean.idxmin()), "clean_min": clean.min(),
        "fossil_start": fossil.loc[s], "fossil_end": fossil.iloc[-1],
        **{key: int(counts.get(key, 0)) for key in OUTCOME_LABELS},
        "share_up": share_up,
        "zero_fossil_start": int(outcomes["fossil_twh_start"].eq(0).sum()),
        "max_fossil_pct": fossil_pct.max(),
        "fossil_change_min": outcomes["d_fossil_twh"].min(),
        "largest_fossil": largest_fossil,
        "in_band": int(outcomes["d_fossil_twh"].abs().le(settings.q5_zoom_twh).sum()),
        "traders": int(trade.abs().gt(TRADE_PCT).sum()),
        "importers": int(trade.gt(TRADE_PCT).sum()),
        "exporters": int(trade.lt(-TRADE_PCT).sum()),
        "demand_min": q6["demand_growth_pct"].min(),
        "largest_demand": largest_demand,
        "demand_in_band": int(q6["demand_growth_pct"].le(settings.q6_zoom_pct).sum()),
    }


def definitions(results, f):
    """Extra bullets for the shared Definitions list."""
    e = results["settings"].end_year
    return f"""- TWh (terawatt-hours) measures amounts of electricity: 1 TWh = 1 billion kWh.
- Demand is domestic generation plus net imports (OWID {RAW_NAME["demand_twh"]}).
  Generation and demand differ when a country trades electricity: {f["traders"]} of the
  {len(results["outcomes"])} compared countries had net trade above {TRADE_PCT}% of their {e} demand
  ({f["importers"]} net importers, {f["exporters"]} net exporters)."""


def q1_section(results, f, sample):
    s, e = results["settings"].start_year, results["settings"].end_year
    return f"""## Q1 — The World's Electricity Mix

**Question:** How has the global electricity mix changed from {s} to {e}, in shares and in TWh?

**Transformation:** select the World row for {s}–{e}. Group the sources into eight lines:
Coal, Gas, Oil, and the five clean groups used in Q4 (Wind, Solar, Hydro, Nuclear,
Other Clean). Each year's eight values add up to total generation in TWh and to 100%
in shares; the sketch code checks both within 0.01.

**What it shows:** the clean share was {f["clean_start"]:.1f}% in {s}, fell to
{f["clean_min"]:.1f}% in {f["clean_min_year"]}, and reached {f["clean_end"]:.1f}% in {e}.
Fossil generation still grew, from {f["fossil_start"]:,.0f} TWh to {f["fossil_end"]:,.0f} TWh,
because total generation grew. A rising clean share did not mean less fossil electricity
for the world; Q5 asks the same question for each country.

**Sample rule:** every fourth year from {s}, plus {e}. The first table matches the share chart,
the second the TWh chart.

{sample("q1_world_share_sample")}

{sample("q1_world_twh_sample")}

**Sketch:** two line charts with the same eight lines, shares (%) on the left and
generation (TWh) on the right; two charts rather than two y-axes. Fossil lines are dashed;
clean lines use the Q4 colors. **Planned interaction:** hovering a line highlights that
source in both charts and shows its share and TWh for the year.

Local figure: [World Mix](../outputs/sketches/q1_{s}_{e}_world_mix.png)."""


def q5_section(results, f, sample):
    settings = results["settings"]
    s, e, zoom = settings.start_year, settings.end_year, settings.q5_zoom_twh
    n = len(results["outcomes"])
    up_up = f["share_up_fossil_up"]
    example = results["example"]
    if example is None:
        selected = "No country fits the rule for these settings, so no country is selected."
    else:
        selected = (
            f"With this rule the selected country is **{example['country']}**: "
            f"{example['d_clean_share_pp']:+.1f} pp clean share, {example['d_fossil_twh']:+.1f} TWh fossil generation."
        )
    largest = f["largest_fossil"]
    return f"""## Q5 — Clean Share and Fossil Generation

**Question:** Which countries raised their clean share while cutting fossil generation,
and which raised it but still generated more fossil electricity?

**Transformation:** use the same {n} eligible countries as Q3–Q4. Calculate
d_fossil_twh = fossil_twh_{e} − fossil_twh_{s}, then sort each country into one of four
outcomes: clean share up and fossil down, up and fossil up, up and fossil unchanged,
or clean share not up. Fossil change stays in TWh. Percentage change is not used:
{f["zero_fossil_start"]} countries had no fossil generation in {s}, and small starting values
give changes as large as {f["max_fossil_pct"]:,.0f}%.

**Result:** {f["share_up_fossil_down"]} countries raised their clean share and cut fossil
generation; {up_up} raised it and still generated more fossil electricity;
{f["share_up_fossil_flat"]} raised it with fossil generation unchanged; {f["share_not_up"]} did not
raise it. Of the {f["share_up"]} countries whose clean share rose, {100 * up_up / f["share_up"]:.1f}%
also generated more fossil electricity.

**Scale:** fossil change runs from {f["fossil_change_min"]:,.1f} TWh to
{largest["d_fossil_twh"]:+,.1f} TWh ({largest["country"]}). On one linear axis,
{f["in_band"]} of the {n} countries fall within ±{zoom:g} TWh and overlap near zero. The sketch
shows the overview and an enlarged ±{zoom:g} TWh band, both linear and with the same x scale.

**Selected country:** the static sketch selects the largest {e} generator among the
"share up, fossil up" countries inside the band. {selected} Its mix appears below the
scatterplots in the Q1 charts.

**Sample rule:** the {Q5_SAMPLE_SIZE} largest {e} generators, plus the selected country.

{sample("q5_fossil_outcomes_sample")}

**Sketch:** two scatterplots (x = clean-share change in pp, y = fossil change in TWh).
Color and marker shape both show the outcome. **Planned interaction:** clicking a dot or
choosing a country from a menu shows that country's mix over {s}–{e}.

Local figure: [Fossil Outcomes](../outputs/sketches/q5_{s}_{e}_fossil_outcomes.png)."""


def q6_section(results, f, sample):
    settings = results["settings"]
    s, e, zoom = settings.start_year, settings.end_year, settings.q6_zoom_pct
    q6, left_out = results["q6"], results["left_out"]
    largest = f["largest_demand"]
    reduced, other = (results["summary"].set_index("fossil_reduced").loc[flag] for flag in (True, False))
    return f"""## Q6 — Demand Growth and the Starting Mix

**Question:** How do demand growth and the {s} mix differ between countries that reduced
fossil generation and those that did not?

**Transformation:** start from the Q5 table. Leave out {len(left_out)} countries with zero
fossil generation in both {s} and {e} ({", ".join(left_out) or "none"}); they had no fossil
generation to cut. That leaves {len(q6)}. Calculate
demand_growth_pct = 100 × (demand_{e} / demand_{s} − 1). Group countries by
fossil_reduced (d_fossil_twh < 0).

**Result:** the group comparison answers Q6. Median demand growth was
{reduced["median_demand_growth_pct"]:.1f}% where fossil generation fell and
{other["median_demand_growth_pct"]:.1f}% where it did not.

{sample("q6_group_summary")}

**Matched pairs:** for each country whose fossil generation fell, the sketch finds a
country whose fossil generation did not fall with the closest demand growth. It takes the
smallest gaps first, uses each country once, and breaks ties by name. The
{len(results["pairs"])} pairs show exceptions to the group pattern: similar demand growth,
opposite fossil outcomes. They are illustrations, not a sample.

{sample("q6_matched_pairs")}

**Scale:** demand growth runs from {f["demand_min"]:+,.1f}% to {largest["demand_growth_pct"]:+,.1f}%
({largest["country"]}). {f["demand_in_band"]} of the {len(q6)} countries are at or below {zoom:,.0f}%,
so the sketch shows the overview and an enlarged band up to {zoom:,.0f}%, both linear.

**Sketch:** two scatterplots (x = demand growth, y = clean share in {s}) with each group's
median as a dashed line; bars compare the selected pair's {s} mix, and a table shows their
numbers. **Planned interaction:** a button for each pair rings both countries and updates
the bars and the table.

Local figure: [Demand Pairs](../outputs/sketches/q6_{s}_{e}_demand_pairs.png)."""


def raw_coverage(years):
    """Places (three-letter ISO codes) with generation data in each year of the raw file."""
    raw = pd.read_csv(RAW, usecols=["iso_code", "year", "electricity_generation_twh"])
    known = raw.loc[raw["iso_code"].str.fullmatch(r"[A-Z]{3}", na=False) & raw["electricity_generation_twh"].notna()]
    return {year: int(known["year"].eq(year).sum()) for year in years}


def cutoff_section(results, markdown_table):
    s, e = results["settings"].start_year, results["settings"].end_year
    coverage = raw_coverage((s - 1, s))
    robustness = pd.read_csv(ROOT / "data/processed/robustness.csv")
    pivot = robustness.pivot(index="start_year", columns="min_generation_twh", values="pct_of_share_up")
    table = pivot.reset_index().rename(
        columns=lambda name: "Start Year" if name == "start_year" else f"≥ {name:g} TWh (%)",
    )
    baseline = robustness.set_index(["start_year", "min_generation_twh"]).loc[(s, MIN_GENERATION_TWH)]
    unfiltered = robustness.set_index(["start_year", "min_generation_twh"]).loc[(s, 0), "countries"]
    return f"""## Cutoffs and Sensitivity

**Start year {s}:** the processed tables begin in {s}. In the raw OWID file, {coverage[s - 1]}
places have generation data in {s - 1} and {coverage[s]} in {s}, so an earlier start would
compare a much smaller set of countries.

**Size threshold {MIN_GENERATION_TWH:g} TWh in {e}:** in a small system, one new plant can move the
clean share by many points. The threshold keeps {int(baseline["countries"])} of the {int(unfiltered)}
countries with data in both {s} and {e}.

**Sensitivity:** data/processed/robustness.csv recalculates the Q5 result for four start
years and five thresholds: the percentage of countries with a rising clean share that also
generated more fossil electricity.

{markdown_table(table)}

Across these {pivot.size} settings, the value ranges from {pivot.min().min():.1f}% to
{pivot.max().max():.1f}%. The baseline is {baseline["pct_of_share_up"]:.1f}%
({int(baseline["share_up_fossil_up"])} of {int(baseline["share_up"])})."""
