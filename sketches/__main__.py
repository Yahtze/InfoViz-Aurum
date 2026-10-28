"""Run from the repository root: uv run python -m sketches."""

import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path

from .data import comparison, extremes, load_country_year, snapshot, source_changes
from .settings import ROOT, load_settings


def parse_args():
    parser = argparse.ArgumentParser(description="Generate six exploratory electricity sketches.")
    parser.add_argument("--config", type=Path, default=ROOT / "sketches/config.toml")
    parser.add_argument("--snapshot-year", type=int)
    parser.add_argument("--start-year", type=int)
    parser.add_argument("--end-year", type=int)
    parser.add_argument("--top-n", type=int)
    parser.add_argument("--min-generation-twh", type=float)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--format", dest="formats", action="append", choices=("png", "svg", "pdf"))
    return parser, parser.parse_args()


def main():
    parser, args = parse_args()
    try:
        settings = load_settings(args.config)
        overrides = {
            key: value for key, value in vars(args).items()
            if key != "config" and value is not None
        }
        if "formats" in overrides:
            overrides["formats"] = tuple(overrides["formats"])
        if "output_dir" in overrides:
            overrides["output_dir"] = ROOT / overrides["output_dir"]
        settings = replace(settings, **overrides)
        countries = load_country_year()
        current = snapshot(countries, settings.snapshot_year)
        compared = comparison(countries, settings)
        gainers, _ = extremes(compared, "d_clean_share_pp", settings.top_n, changes=True)
        contributions = {unit: source_changes(gainers, settings, unit) for unit in ("pp", "twh")}

        # Import rendering only after command-line and data validation.
        from .plots import (
            change_bars, endpoint_comparison, set_style,
            share_map, share_ranking, source_breakdown,
        )
        import matplotlib.pyplot as plt

        set_style()
        period = f"{settings.start_year}_{settings.end_year}"
        views = (
            (f"q2_{settings.snapshot_year}_map", lambda: share_map(current, settings)),
            (f"q2_{settings.snapshot_year}_ranking", lambda: share_ranking(current, settings)),
            (f"q3_{period}_changes", lambda: change_bars(compared, settings)),
            (f"q3_{period}_endpoints", lambda: endpoint_comparison(compared, settings)),
            (f"q4_{period}_source_share", lambda: source_breakdown(compared, settings, "pp")),
            (f"q4_{period}_source_generation", lambda: source_breakdown(compared, settings, "twh")),
        )
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        files = []
        for name, render in views:
            fig = render()
            try:
                for extension in settings.formats:
                    path = settings.output_dir / f"{name}.{extension}"
                    fig.savefig(path, dpi=settings.dpi, bbox_inches="tight")
                    files.append(path.name)
            finally:
                plt.close(fig)
            print(name)

        tables = {
            f"q2_{settings.snapshot_year}_all_countries": current,
            f"q3_{period}_all_compared": compared,
            **{f"q4_{period}_source_{unit}": table for unit, table in contributions.items()},
        }
        for name, table in tables.items():
            path = settings.output_dir / f"{name}.csv"
            table.to_csv(path, index=False, float_format="%.4f")
            files.append(path.name)

        manifest = {
            "settings": asdict(settings),
            "input": "data/processed/country_year.csv",
            "snapshot_countries": len(current),
            "snapshot_missing_shares": int(current["clean_share_pct"].isna().sum()),
            "comparison_countries": len(compared),
            "source_breakdown_countries": gainers["iso3"].tolist(),
            "cutoff_ties": "country name ascending; at most top_n per tail",
            "files": files,
        }
        manifest_path = settings.output_dir / f"manifest_{settings.snapshot_year}_{period}.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, default=str) + "\n")
        print(
            f"Saved six views to {settings.output_dir}\n"
            f"{len(current)} snapshot countries; {len(compared)} compared; "
            f"{len(gainers)} source-breakdown countries."
        )
    except (ValueError, KeyError, FileNotFoundError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
