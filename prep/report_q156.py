"""Build the Q1, Q5 and Q6 data-handling report and its tables: uv run python -m prep.report_q156.

The numbers come from the same sketches/q156_data.py functions the sketches use,
run at the preparation baseline (years and size threshold from prep/buildTables.py).
reports/dataHandlingSketches.md covers Q2-Q4 and the data handling both reports share.
"""

from pathlib import Path

import pandas as pd

from prep.buildTables import END_YEAR, MEASURES, MIN_GENERATION_TWH, RAW, ROOT, START_YEAR
from sketches.data import load_country_year
from sketches.q156_data import (
    OUTCOME_LABELS, fossil_outcomes, group_summary, load_world, matched_pairs, mix_table,
    q5_example, q6_countries, window,
)
from sketches.settings import Settings, SourceGroup

Q5_SAMPLE_SIZE = 12
# Net trade above this share of demand makes generation and demand differ noticeably.
TRADE_PCT = 10
# The proposal (Oct 19) compared countries from this year; the M1 feedback asked why.
PROPOSAL_START_YEAR = 2010
# The four bars of the Q6 pair comparison; each is a <name>_share_pct column.
START_MIX = ("Coal", "Gas", "Oil", "Clean")
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
    """Fixed report settings: the preparation baseline and the Q5/Q6 values the report describes.

    They do not read sketches/config.toml, and the Q5/Q6 values are written out rather than taken
    from the Settings defaults, so neither a config edit nor a new default changes the report.
    """
    return Settings(
        snapshot_year=END_YEAR, start_year=START_YEAR, end_year=END_YEAR, top_n=10,
        min_generation_twh=float(MIN_GENERATION_TWH), output_dir=ROOT / "outputs/sketches", formats=("png",),
        dpi=160, groups=BASELINE_GROUPS, q5_zoom_twh=60.0, q5_example=None, q6_pairs=6, q6_selected_pair=1,
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
        "start_mix": start_mix_summary(q6_table),
        "hypothesis": hypothesis_check(outcomes),
    }


def start_mix_summary(table):
    """The other half of Q6: each group's start-year mix, as medians like the demand summary.

    Medians of separate sources need not add up to 100%. Every share must be known, so each
    median covers the whole group.
    """
    columns = [f"{label.lower()}_share_pct_start" for label in START_MIX] + ["nuclear_share_pct_start"]
    unknown = table.loc[table[columns].isna().any(axis=1), "country"].tolist()
    if unknown:
        raise ValueError(f"Q6 start-year shares are unknown for {', '.join(unknown)}")
    rows = []
    for reduced in (True, False):
        group = table.loc[table["fossil_reduced"].eq(reduced)]
        row = {"fossil_reduced": reduced, "countries": len(group)}
        for label in START_MIX:
            row[label] = group[f"{label.lower()}_share_pct_start"].median()
        row["clean_q1"] = group["clean_share_pct_start"].quantile(0.25)
        row["clean_q3"] = group["clean_share_pct_start"].quantile(0.75)
        row["nuclear_countries"] = int(group["nuclear_share_pct_start"].gt(0).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def hypothesis_check(outcomes):
    """The proposal's hypothesis, among countries whose clean share rose: are fossil cuts less common
    where demand grew faster? Slower means at or below their median demand growth, faster above it."""
    eligible = outcomes.loc[outcomes["d_clean_share_pp"].gt(0)]
    up = eligible.dropna(subset=["demand_growth_pct"])
    fell = up["fossil_reduced"]
    split = up["demand_growth_pct"].median()
    slower = up["demand_growth_pct"].le(split)
    return {
        "eligible": len(eligible), "countries": len(up), "fell": int(fell.sum()), "other": int((~fell).sum()),
        "split": split, "slower": int(slower.sum()), "faster": int((~slower).sum()),
        "slower_fell": int((slower & fell).sum()), "faster_fell": int((~slower & fell).sum()),
        "faster_fell_names": sorted(up.loc[~slower & fell, "country"]),
    }


def and_list(items):
    items = list(items)
    if len(items) < 3:
        return " and ".join(items)
    return f"{', '.join(items[:-1])}, and {items[-1]}"


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
    mix = results["start_mix"]
    samples["q6_start_mix"] = pd.DataFrame({
        "Group": mix["fossil_reduced"].map({True: "Fossil Generation Fell", False: "Did Not Fall"}),
        "Countries": mix["countries"],
        **{f"Median {label} {s} (%)": mix[label] for label in START_MIX},
        "Clean Lower Quartile (%)": mix["clean_q1"],
        "Clean Upper Quartile (%)": mix["clean_q3"],
        f"Countries With Nuclear {s}": mix["nuclear_countries"],
    })
    samples["q6_matched_pairs"] = results["pairs"].rename(columns={
        "pair": "Pair", "country_reduced": "Fossil Fell",
        "demand_growth_pct_reduced": "Demand Growth, Fell (%)", "country_other": "Fossil Did Not Fall",
        "demand_growth_pct_other": "Demand Growth, Did Not Fall (%)", "gap_pp": "Gap (pp)",
    })
    return samples


def q156_dictionary(country_year, results):
    """Fields Q1, Q5 and Q6 add to the Q2–Q4 dictionary (reports/tables/feature_dictionary.csv)."""
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
    generation = world.set_index("year")["generation_twh"]
    counts = outcomes["outcome"].value_counts()
    share_up = int(outcomes["d_clean_share_pp"].gt(0).sum())
    trade = outcomes["net_imports_share_of_demand_pct_end"]
    largest_fossil = outcomes.loc[outcomes["d_fossil_twh"].idxmax()]
    largest_demand = q6.loc[q6["demand_growth_pct"].idxmax()]
    return {
        "clean_start": clean.loc[s], "clean_end": clean.iloc[-1],
        "fossil_start": fossil.loc[s], "fossil_end": fossil.iloc[-1],
        "generation_start": generation.loc[s], "generation_end": generation.iloc[-1],
        "fossil_share_start": 100 * fossil.loc[s] / generation.loc[s],
        "fossil_share_end": 100 * fossil.iloc[-1] / generation.iloc[-1],
        **{key: int(counts.get(key, 0)) for key in OUTCOME_LABELS},
        "share_up": share_up,
        "zero_fossil_start": int(outcomes["fossil_twh_start"].eq(0).sum()),
        "largest_fossil": largest_fossil,
        "in_band": int(outcomes["d_fossil_twh"].abs().le(settings.q5_zoom_twh).sum()),
        "traders": int(trade.abs().gt(TRADE_PCT).sum()),
        "importers": int(trade.gt(TRADE_PCT).sum()),
        "exporters": int(trade.lt(-TRADE_PCT).sum()),
        "largest_demand": largest_demand,
    }


def definitions(results, f):
    """Definitions Q1, Q5 and Q6 add to the shared ones in reports/dataHandlingSketches.md."""
    e = results["settings"].end_year
    return f"""- TWh (terawatt-hours) measures amounts of electricity: 1 TWh = 1 billion kWh.
- Demand is domestic generation plus net imports (OWID {RAW_NAME["demand_twh"]}).
  Generation and demand differ when a country trades electricity: {f["traders"]} of the
  {len(results["outcomes"])} compared countries had net trade above {TRADE_PCT}% of their {e} demand
  ({f["importers"]} net importers, {f["exporters"]} net exporters)."""


def moved(start, end, up="grew"):
    return up if end > start else "fell" if end < start else "stayed the same,"


def world_amounts(f):
    """Q1's share-versus-amount reading, with the directions taken from the data."""
    clean = (f"the clean share {moved(f['clean_start'], f['clean_end'], 'rose')} from {f['clean_start']:.1f}% "
             f"to {f['clean_end']:.1f}%")
    generation = (f"total generation {moved(f['generation_start'], f['generation_end'])} from "
                  f"{f['generation_start']:,.0f} TWh to {f['generation_end']:,.0f} TWh")
    amount = f"{f['fossil_start']:,.0f} TWh to {f['fossil_end']:,.0f} TWh"
    if f["fossil_share_end"] < f["fossil_share_start"] and f["fossil_end"] > f["fossil_start"]:
        return f"{clean}, but {generation}. So fossil generation also grew, from {amount}."
    return f"{clean}, and {generation}. Fossil generation {moved(f['fossil_start'], f['fossil_end'])} from {amount}."


def q1_section(results, f, sample):
    s, e = results["settings"].start_year, results["settings"].end_year
    years = f"every fourth year from {s} through {e}" if (e - s) % 4 == 0 else f"every fourth year from {s}, plus {e}"
    return f"""## Q1 — The World's Electricity Mix

**Question:** How has the global electricity mix changed from {s} to {e}, in shares and in TWh?

**Transformation:** select the World row for {s}–{e}. Group the sources into Coal, Gas, Oil,
Wind, Solar, Hydro, Nuclear, and Other Clean. The sketch checks that each year's values add up
to total generation and to 100% within 0.01.

**Result:** {world_amounts(f)}
Q5 asks the same question for each country.

**Sample:** {years}. The first table gives shares, the second TWh.

{sample("q1_world_share_sample")}

{sample("q1_world_twh_sample")}

**Sketch:** two stacked area charts with the same eight layers, in shares (%) and in TWh.
Fossil layers are grays at the bottom, and a dark line marks their top. Clean layers use the
Q4 colors. Brackets label the Fossil and Clean groups, so the split does not rely on color alone.
The top of the TWh stack is total generation.
**Planned interaction:** a cursor marks the year in both charts, and a tooltip lists every
source. Clicking a source's name shows it alone as a line in both units, because middle layers
are hard to compare in a stack.

![Q1 World Mix sketch](../outputs/sketchesQ1.png)"""


def q5_section(results, f, sample):
    settings = results["settings"]
    s, e, zoom = settings.start_year, settings.end_year, settings.q5_zoom_twh
    n = len(results["outcomes"])
    up_up, flat = f["share_up_fossil_up"], f["share_up_fossil_flat"]
    up_up = f"{up_up} ({100 * up_up / f['share_up']:.1f}%) still generated more"
    down = f"{f['share_up_fossil_down']} cut fossil generation"
    result = f"{down}, {flat} kept it unchanged, and {up_up}" if flat else f"{down} and {up_up}"
    zero = f["zero_fossil_start"]
    in_tw = f", because {zero} countries had no fossil generation in {s}" if zero else ""
    example = results["example"]
    rule = f'the largest {e} generator among the "share up, fossil up" countries inside the ±{zoom:g} TWh band'
    if example is None:
        selected = (f"the {Q5_SAMPLE_SIZE} largest {e} generators. No country fits the sketch's selection rule, "
                    f"{rule}, for these settings.")
        detail = "No country is selected, so the sketch draws no line charts below them."
    else:
        selected = (f"the {Q5_SAMPLE_SIZE} largest {e} generators, plus {example['country']}. "
                    f"The sketch selects {example['country']} as {rule}.")
        detail = (f"Below them, two line charts trace the selected country over {s}–{e}: its clean share, "
                  "and its fossil (solid gray) and clean (dashed green) generation.")
    largest = f["largest_fossil"]
    return f"""## Q5 — Clean Share and Fossil Generation

**Question:** Which countries raised their clean share while cutting fossil generation,
and which raised it but still generated more fossil electricity?

**Transformation:** use the {n} countries of Q3–Q4. Calculate
d_fossil_twh = fossil_twh_{e} − fossil_twh_{s}. Sort each country into one of four
outcomes: clean share up with fossil down, up, or unchanged, or clean share not up.
Fossil change stays in TWh{in_tw}.

**Result:** of the {f["share_up"]} countries whose clean share rose, {result}.

**Sample:** {selected}

{sample("q5_fossil_outcomes_sample")}

**Sketch:** two scatterplots of clean-share change (x, pp) and fossil change (y, TWh): all
countries, and an enlarged ±{zoom:g} TWh band with the same x scale. The band holds {f["in_band"]} of the {n}
countries, which overlap near zero next to {largest["country"]}'s {largest["d_fossil_twh"]:+,.1f} TWh. Color and marker
shape both show the outcome. {detail}
**Planned interaction:** clicking a dot or choosing a country from a menu redraws the lines,
and a tooltip lists each source by year.

![Q5 Fossil Outcomes sketch](../outputs/sketchesQ5.png)"""


def start_mix_text(mix, s):
    fell, other = (mix.set_index("fossil_reduced").loc[flag] for flag in (True, False))
    if not (fell["countries"] and other["countries"]):
        return "one of the groups is empty, so their starting mixes cannot be compared."
    overlap = fell["clean_q1"] <= other["clean_q3"] and other["clean_q1"] <= fell["clean_q3"]
    compared = "higher" if fell["Clean"] > other["Clean"] else "lower" if fell["Clean"] < other["Clean"] else "the same"
    return " ".join([
        f"where fossil generation fell, the median {s} clean share was {compared}: "
        f"{fell['Clean']:.1f}% against {other['Clean']:.1f}%.",
        "The middle halves overlap, so the starting share alone does not separate the groups." if overlap
        else "The middle halves do not overlap.",
        f"The table gives the medians of the four {s} shares; separate medians need not add up to 100%.",
    ])


def hypothesis_text(h):
    """The proposal's hypothesis, tested among countries whose clean share rose (see hypothesis_check)."""
    if h["countries"] == h["eligible"]:
        tested = f"the {h['countries']} countries whose clean share rose"
    else:
        tested = f"the {h['countries']} of the {h['eligible']} countries whose clean share rose that have demand data"
    text = ["the proposal expected fossil cuts to be less common where demand grew fast; more frequent cuts there "
            "would contradict it."]
    if not all(h[key] for key in ("fell", "other", "slower", "faster")):
        return " ".join(text + ["One of the groups is empty, so this comparison cannot be evaluated."])
    slower_rate, faster_rate = h["slower_fell"] * h["faster"], h["faster_fell"] * h["slower"]
    text.append(f"Among {tested}, split at their median demand growth ({h['split']:.1f}%), fossil generation fell "
                f"in {h['slower_fell']} of the {h['slower']} at or below it and in {h['faster_fell']} of the "
                f"{h['faster']} above it.")
    if slower_rate > faster_rate:
        text.append("This is consistent with the hypothesis but does not show a cause.")
        names = h["faster_fell_names"]
        if len(names) == 1:
            text.append(f"The fast-growing exception is {names[0]}.")
        elif names:
            text.append(f"The fast-growing exceptions are {and_list(names)}.")
    elif slower_rate == faster_rate:
        text.append("The rates are equal, so the data do not support the hypothesis.")
    else:
        text.append("Cuts were more common in the faster-growing group, which runs against the hypothesis.")
    return " ".join(text)


def q6_section(results, f, sample):
    settings = results["settings"]
    s, e = settings.start_year, settings.end_year
    q6, left_out = results["q6"], results["left_out"]
    largest = f["largest_demand"]
    leave = (f"Leave out the {len(left_out)} countries with no fossil generation in either year, which leaves {len(q6)}."
             if left_out else f"No country lacks fossil generation in both years, so all {len(q6)} stay.")
    return f"""## Q6 — Demand Growth and the Starting Mix

**Question:** How do demand growth and the {s} mix differ between countries that reduced
fossil generation and those that did not?

**Transformation:** start from the Q5 table. {leave} Calculate
demand_growth_pct = 100 × (demand_{e} / demand_{s} − 1). Group countries by
fossil_reduced (d_fossil_twh < 0).

**Sample A — Groups:** demand growth by group.

{sample("q6_group_summary")}

**Starting mix:** {start_mix_text(results["start_mix"], s)}

{sample("q6_start_mix")}

**Hypothesis check:** {hypothesis_text(results["hypothesis"])}

**Sample B — Matched Pairs:** for each country whose fossil generation fell, find the country
with the closest demand growth whose fossil generation did not fall. Take the smallest gaps
first, use each country once, and break ties by name. The {len(results["pairs"])} pairs illustrate exceptions,
not a sample.

{sample("q6_matched_pairs")}

**Sketch:** five charts, each with one box per group (quartiles and median) and every country
as a dot: demand growth, then the {s} share of coal, gas, oil, and clean generation on a
common 0–100% scale. Demand growth uses a log scale of demand_{e} / demand_{s} (1× = no
change), labeled as percent change, because {largest["country"]}'s {largest["demand_growth_pct"]:+,.1f}% would crowd the rest.
A country's dot keeps the same height within its group in every chart.
**Planned interaction:** hovering a dot highlights that country in all five charts; a pair
button rings both countries of the pair.

![Q6 Demand Pairs sketch](../outputs/sketchesQ6.png)"""


def raw_coverage(years):
    """Places (three-letter ISO codes) with generation data in each year of the raw file."""
    raw = pd.read_csv(RAW, usecols=["iso_code", "year", "electricity_generation_twh"])
    known = raw.loc[raw["iso_code"].str.fullmatch(r"[A-Z]{3}", na=False) & raw["electricity_generation_twh"].notna()]
    return {year: int(known["year"].eq(year).sum()) for year in years}


def majority_text(grid):
    """Whether "clean share up, fossil up" countries are a majority in each setting, from the counts
    (the percentages in robustness.csv are rounded)."""
    empty = int(grid["share_up"].eq(0).sum())
    grid = grid.loc[grid["share_up"].gt(0)]
    up, base, n = grid["share_up_fossil_up"], grid["share_up"], len(grid)
    above = int((2 * up > base).sum())
    skipped = ""
    if empty == 1:
        skipped = " 1 setting has no country whose clean share rose, so it is left out."
    elif empty:
        skipped = f" {empty} settings have no country whose clean share rose, so they are left out."
    if n == 0:
        return "No setting has a country whose clean share rose."
    if above == n:
        return f"They are a majority of the countries whose clean share rose in all {n} settings.{skipped}"
    if above == 0:
        return f"They are not a majority of the countries whose clean share rose in any of the {n} settings.{skipped}"
    return f"Whether they are a majority depends on the cutoffs.{skipped}"


def cutoff_section(results, markdown_table):
    s, e = results["settings"].start_year, results["settings"].end_year
    coverage = raw_coverage((s - 1, s))
    robustness = pd.read_csv(ROOT / "data/processed/robustness.csv")
    pivot = robustness.pivot(index="start_year", columns="min_generation_twh", values="pct_of_share_up")
    table = pivot.reset_index().rename(
        columns=lambda name: "Start Year" if name == "start_year" else f"≥ {name:g} TWh (%)",
    )
    grid = robustness.set_index(["start_year", "min_generation_twh"])
    baseline = grid.loc[(s, MIN_GENERATION_TWH)]
    unfiltered = grid.loc[(s, 0), "countries"]
    proposal = grid.loc[(PROPOSAL_START_YEAR, MIN_GENERATION_TWH)]
    if proposal["countries"] == baseline["countries"]:
        same = f"At {MIN_GENERATION_TWH:g} TWh, both start years compare {int(baseline['countries'])} countries."
    else:
        same = (f"At {MIN_GENERATION_TWH:g} TWh, a {PROPOSAL_START_YEAR} start would compare "
                f"{int(proposal['countries'])} countries; {s} compares {int(baseline['countries'])}.")
    fewest = int(robustness["share_up_fossil_up"].min())
    holds = (f"every setting has at least {fewest} countries whose clean share and fossil generation both rose, "
             "so the gap between share and amount appears with every cutoff."
             if fewest else "at least one setting has no country whose clean share and fossil generation both rose.")
    return f"""## Cutoffs and Sensitivity

**Start year {s}:** the proposal started in {PROPOSAL_START_YEAR}. The comparisons now start in {s}, like Q1.
{same} An earlier start would compare fewer: the
raw OWID file has generation data for {coverage[s - 1]} places in {s - 1} and {coverage[s]} in {s}.

**Size threshold {MIN_GENERATION_TWH:g} TWh in {e}:** in a small system, one new plant can move the clean share
by many points. The threshold keeps {int(baseline["countries"])} of the {int(unfiltered)} countries with data in both years.

**Sensitivity:** data/processed/robustness.csv recalculates the Q5 result for four start
years and five thresholds: the percentage of countries with a rising clean share that also
generated more fossil electricity.

{markdown_table(table)}

**Result:** {holds} {majority_text(robustness)}
The proposal's {PROPOSAL_START_YEAR} start at {MIN_GENERATION_TWH:g} TWh gives {proposal["pct_of_share_up"]:.1f}% \
({int(proposal["share_up_fossil_up"])} of {int(proposal["share_up"])}).
The grid checks only the Q5 result, not Q6."""


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


REPORT_NAME = "dataHandlingQ1Q5Q6.md"
TABLE_DIR = "tablesQ1Q5Q6"


def build_report(output_dir=ROOT / "reports"):
    results = q156_results()
    country_year = load_country_year()
    samples = q156_samples(results)
    dictionary = q156_dictionary(country_year, results)
    numbers = facts(results)
    output_dir = Path(output_dir)
    table_dir = output_dir / TABLE_DIR
    table_dir.mkdir(parents=True, exist_ok=True)
    for name, table in {**samples, "feature_dictionary": dictionary}.items():
        table.to_csv(table_dir / f"{name}.csv", index=False, float_format="%.4f")

    def sample(name):
        return markdown_table(samples[name]) + f"\n\n[Download CSV]({TABLE_DIR}/{name}.csv)"

    settings = results["settings"]
    s, e, n = settings.start_year, settings.end_year, len(results["outcomes"])
    report = f"""# Data Handling for Q1, Q5, and Q6

## Scope and Current State

This report covers **Q1, Q5, and Q6**, the questions Yusuke explored with three Matplotlib
sketches. [Data Handling and Initial Sketches](dataHandlingSketches.md) covers Q2–Q4. The
sketches are exploratory views, not the final D3 application.

Both reports use the same data, definitions, filters, and stored tables, described in
[Shared Data Handling](dataHandlingSketches.md#shared-data-handling). This report adds what
Q1, Q5, and Q6 need beyond that, and explains the start year and the size threshold.

The baseline is {s}–{e}, with a minimum of {MIN_GENERATION_TWH:g} TWh generation in {e} for the
country comparisons. Q1 reads the World row of country_year.csv. Q5 recalculates the
comparison from country_year.csv with fixed baseline settings; it uses the same {n} countries
as comparison_{s}_{e}.csv, and the tests check that the two agree. Q6 starts from these {n}
and keeps {len(results["q6"])}: it leaves out the {len(results["left_out"])} with no fossil generation in either year.
Custom sketch settings never change this report.

The tables below contain real processed rows, not synthetic examples. They are
**case samples**, not random or population-weighted samples. Each section states
the selection rule. The report displays two decimal places; downloadable CSVs retain
four decimals where applicable. **No Data** means unknown, not zero. CSV samples use blank
cells for the same unknown values. Q5 and Q6 show associations, not causes.

## Additional Definitions and Filters

- Q1 uses only the World row. Q5 and Q6 exclude it, as Q2–Q4 do.
- The Q1 and Q5 chart titles state **Domestic Electricity Generation**, like Q2–Q4. The Q6
  title names electricity demand, because its x-axis is demand growth.
{definitions(results, numbers)}

{q1_section(results, numbers, sample)}

{q5_section(results, numbers, sample)}

{q6_section(results, numbers, sample)}

{cutoff_section(results, markdown_table)}

## Created and Derived Features

[Feature dictionary]({TABLE_DIR}/feature_dictionary.csv): **{len(dictionary)} columns** that
Q1, Q5, and Q6 use beyond the [Q2–Q4 feature dictionary](tables/feature_dictionary.csv), with
units, input fields, and transformation rules. Generation, the clean share, and the clean
sources are documented there.

| Feature or Family | Transformation | Unit or Rule |
| --- | --- | --- |
| demand_twh, net_imports_twh | Rename OWID demand and net imports | TWh; demand = generation + net imports |
| Coal, gas, and oil TWh and shares | Rename; same missing-value rules as clean sources | TWh or %; Q1 layers and Q6 start mix |
| d_fossil_twh, outcome, fossil_reduced | End minus start fossil generation; four outcomes | TWh; categories (Q5) and groups (Q6) |
| demand_growth_pct, generation_growth_pct | 100 × (end / start − 1) | %; blank if the start is not positive |

## Reproduction and Checks

Run from the repository root:

    uv sync --locked
    uv run python prep/buildTables.py
    uv run python -m sketches --preview outputs/sketchesQ2-4.png
    uv run python -m prep.report_q156
    uv run python -m unittest discover -s tests -v

- sketches/q156_data.py checks that the eight Q1 groups add up to generation and to 100%,
  and recalculates the Q5 outcomes and the Q6 groups and pairs for configured dates.
- prep/report_q156.py checks that the documented fields exist, and rebuilds this report and
  its CSV tables from processed values. tests/test_q156.py checks that the report's tables
  match what the default sketches compute.
- The figures are tracked at outputs/sketchesQ1.png, sketchesQ5.png, and sketchesQ6.png.
- Processed values already use four decimals. The report only rounds for display.
  It does not edit raw data or impute missing values.
"""
    path = output_dir / REPORT_NAME
    path.write_text(report, encoding="utf-8")
    print(f"{path}: {len(samples)} result tables; {len(dictionary)} documented features")
    return path


if __name__ == "__main__":
    build_report()
