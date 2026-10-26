# Aurum: Cleaner Share, More Fossil Power? (working title)

CS-GY 6313 Information Visualization (NYU, Fall 2026), group project.
Team Aurum: Yathin Reddy Duvuru (yd3288), Yusuke Katsuki (yk3183).

Many countries raised the share of clean electricity between 2010 and 2024.
We ask whether they also generated less electricity from fossil fuels.
Of the 83 countries (out of 108 compared) that raised their clean share, 41 still generated more fossil electricity.

## Questions

1. How has the global electricity mix changed from 2000 to 2024, both in percentage shares and absolute generation (TWh)?
2. How do countries compare in their clean electricity shares in 2024? Which countries have the highest and lowest shares?
3. Which countries experienced the largest increases or decreases in clean electricity share between 2010 and 2024?
4. In countries with the largest increases in clean electricity share, how much of the change came from wind and solar compared with hydro and nuclear?
5. Which countries increased their clean electricity share while also reducing fossil-fuel electricity generation, and which increased their clean share but still generated more fossil-fuel electricity?
6. How do electricity demand growth and the initial electricity mix in 2010 differ between countries that reduced fossil-fuel generation and those that did not?

## Layout

```
prep/build.py      all data processing, in one place
data/raw/          pinned copies of the source files (do not edit)
data/processed/    the tables, made by prep/build.py (do not edit by hand)
```

## Tables

Two tables cover all six questions. Each chart picks its rows with a filter.

| Table | One row per | Used for |
|---|---|---|
| `country_year.csv` | country (and World) × year, 2000–2024 | Q1: `country == "World"` · Q2: `year == 2024 && country != "World"`, then sort by `clean_share_pct` (highest first, blanks last) · Q5 detail view: the selected country |
| `comparison_2010_2024.csv` | country, the 108 compared | Q3–Q6: the 2010 and 2024 values, the changes, demand growth, and the 2010 mix |
| `robustness.csv` | setting | the main result for other start years and TWh thresholds |

## Rebuild the data

Python 3.11 or later.

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python prep/build.py
```

The script rebuilds every table in `data/processed/` and checks the numbers. It stops with an error if the main result changes.
The rules (which rows count as countries, which years, how missing values are handled) are commented at the top of `prep/build.py`.

## Before you sketch

- **Which countries:** Q1 uses the World row. Q2 uses every country (221). Q3–Q6 compare 108 countries:
  those with data in both 2010 and 2024 and at least 10 TWh of generation in 2024.
- **Blank means unknown, not 0.** Q2 has 25 countries with no 2024 clean share (Ukraine is one). Show them as "no data".
- **The map can't draw 8 of Q2's places** (`on_map` = false in `country_year.csv`), including Gibraltar,
  which has one of the lowest shares (0%). Pair the Q2 map with a ranked list.
- **"Clean" includes nuclear**, and shares are shares of generation, not of demand.

## Data

- **Energy:** Our World in Data, `owid_energy` (CC BY 4.0).
  <https://catalog.ourworldindata.org/energy/owid_energy/owid_energy.csv> · documentation: <https://github.com/owid/energy-data>.
  That URL always serves the latest version, so we use a copy pinned to the 30 Sep 2026 version: `data/raw/owid_energy_2026-09-30.csv`.
- **World map:** world-atlas 2.0.2, `countries-50m.json` (ISC license, made from Natural Earth).
  <https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-50m.json> · pinned copy in `data/raw/`.

## AI use

Course policy allows generative AI if we disclose which parts it produced. We are responsible for any errors, and we can explain all submitted work.

| Date | Tool | What it produced | How we checked it |
|---|---|---|---|
| 2026-10-18 | Claude (Anthropic), Codex (OpenAI) | First draft and review of the M1 proposal text | Yusuke checked each section; Yathin expanded and submitted it |
| 2026-10-25 | Claude Code (Anthropic), Codex (OpenAI) | Repository setup and `prep/build.py`; Codex reviewed them | Reviewed in a pull request before merging; the script re-checks the main numbers on every run |
