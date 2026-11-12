# Aurum: Cleaner Share, More Fossil Power? (Working Title)

CS-GY 6313 Information Visualization (NYU, Fall 2026), group project.
Team Aurum: Yathin Reddy Duvuru (yd3288), Yusuke Katsuki (yk3183).

Many countries raised the share of clean electricity between 2000 and 2024.
We ask whether they also generated less electricity from fossil fuels.
Of the 79 countries (out of 108 compared) that raised their clean share, 44 still generated more fossil electricity.

## Questions

1. How has the global electricity mix changed from 2000 to 2024, both in percentage shares and absolute generation (TWh)?
2. How do countries compare in their clean electricity shares in 2024? Which countries have the highest and lowest shares?
3. Which countries experienced the largest increases or decreases in clean electricity share between 2000 and 2024?
4. In countries with the largest increases in clean electricity share, how much did wind, solar, hydro, nuclear, and other clean sources each contribute?
5. Which countries increased their clean electricity share while also reducing fossil-fuel electricity generation, and which increased their clean share but still generated more fossil-fuel electricity?
6. How do electricity demand growth and the initial electricity mix in 2000 differ between countries that reduced fossil-fuel generation and those that did not?

## Run the App

The interactive app is an [Observable Framework](https://observablehq.com/framework/) project (pages in `src/`, config in `observablehq.config.js`).
It needs Node.js 18 or later.

```sh
npm install
npm run dev
```

`npm run dev` starts the live preview, usually at <http://127.0.0.1:3000>. Pages reload as you edit them.
To check that every page compiles, run `npm run build`; the static site is written to `dist/`.
The app reads the tables in `data/processed/`, so rebuild them with the steps under Rebuild the Data if they change.

## Layout

```
src/               the Observable Framework app (pages, components, data loaders)
prep/report_q234.py      source-data processing and checks
prep/report_q156.py      the Q1, Q5, and Q6 report and its tables
sketches/          configurable Matplotlib EDA views (not the final D3 app)
tests/             data-selection, configuration, map, and report tests
reports/           data-handling reports, sample tables, and feature dictionaries
data/raw/          pinned copies of the source files (do not edit)
data/processed/    the tables, made by prep/report_q234.py (do not edit by hand)
outputs/           exported sketch figures
```

## Tables

Two tables cover all six questions. Each chart picks its rows with a filter.

| Table | One row per | Used for |
|---|---|---|
| `country_year.csv` | country (and World) × year, 2000–2024 | Q1: `country == "World"` · Q2: `year == 2024 && country != "World"`, then sort by `clean_share_pct` (highest first, blanks last) · Q5 detail view: the selected country |
| `comparison_2000_2024.csv` | country, the 108 compared | Q3–Q4, and a check for Q5–Q6: the 2000 and 2024 values, the changes, demand growth, and the 2000 mix (the Q5–Q6 sketches recalculate them from `country_year.csv` for the configured dates; the Q1, Q5, and Q6 report always uses the fixed 2000–2024 baseline) |
| `robustness.csv` | setting | the main result for other start years and TWh thresholds |

## Rebuild the Data

Install [uv](https://docs.astral.sh/uv/getting-started/installation/). Python 3.11 or later is supported;
`.python-version` selects Python 3.12 for local runs.

```sh
uv sync --locked
uv run python prep/report_q234.py
```

`pyproject.toml` declares dependencies; `uv.lock` records the resolved versions.
Use `uv add <package>` to add a dependency. There is no separate pip requirements file.

The script rebuilds the current baseline tables in `data/processed/` and checks the numbers. It stops with an error if the main result changes.
The old `comparison_2010_2024.csv` stays unchanged for reference. The current baseline uses `comparison_2000_2024.csv`.
The rules (which rows count as countries, which years, how missing values are handled) are commented at the top of `prep/report_q234.py`.

## Initial EDA Sketches

The Matplotlib sketches are preliminary; the Observable Framework app is the real deliverable.
See `sketches/` for the code and `outputs/` for the exported figures.

```sh
uv run python -m sketches --preview outputs/sketchesQ2-4.png
uv run python -m unittest discover -s tests -v
```

## Reports and Sample Tables

See `reports/` for the data-handling reports, sample tables, and feature dictionaries.

## Data Notes for Sketching

- **Which countries:** Q1 uses the World row. Q2 uses every country (221). Q3–Q6 compare 108 countries:
  those with data in both 2000 and 2024 and at least 10 TWh of generation in 2024. Q6 leaves out the 4
  of them with no fossil generation in either year, so it compares 104.
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

## AI Use

Course policy allows generative AI if we disclose which parts it produced. We are responsible for any errors, and we can explain all submitted work.

| Date | Tool | What it produced | How we checked it |
|---|---|---|---|
| 2026-10-18 to 11-02 | Claude and Claude Code (Anthropic), Codex (OpenAI) | The M1 proposal draft; the repository setup and `prep/report_q234.py`; Q1, Q5, and Q6 drafts, report outlines, and tests, based on Yusuke's design ideas; the combined M2 report outline. Codex reviewed them | Yusuke reviewed the text and figures; tests check sums, counts, and that the report matches the sketches |
| 2026-10-31 | Codex (OpenAI) | Python code and Matplotlib syntax for Q2–Q4, based on plot types and visualization descriptions specified by Yathin | Automated tests check data selection, source totals, and plot structure |
