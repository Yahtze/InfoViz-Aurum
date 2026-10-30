"""Run from the repository root: uv run python -m sketches."""

import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import shutil

from .data import comparison, extremes, load_country_year, snapshot, source_changes
from .q156_data import (
    fossil_outcomes, group_summary, load_world, matched_pairs, mix_table, q5_example, q6_countries, window,
)
from .settings import ROOT, load_settings


def parse_args():
    parser = argparse.ArgumentParser(description="Generate nine exploratory electricity sketches.")
    parser.add_argument("--config", type=Path, default=ROOT / "sketches/config.toml")
    parser.add_argument("--snapshot-year", type=int)
    parser.add_argument("--start-year", type=int)
    parser.add_argument("--end-year", type=int)
    parser.add_argument("--top-n", type=int)
    parser.add_argument("--min-generation-twh", type=float)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--preview", type=Path,
        help="Also assemble the six Q2-Q4 PNGs into this PNG path; Q1, Q5 and Q6 are copied next to it.",
    )
    parser.add_argument("--format", dest="formats", action="append", choices=("png", "svg", "pdf"))
    return parser, parser.parse_args()


def main():
    parser, args = parse_args()
    try:
        settings = load_settings(args.config)
        overrides = {
            key: value for key, value in vars(args).items()
            if key not in {"config", "preview"} and value is not None
        }
        if "formats" in overrides:
            overrides["formats"] = tuple(overrides["formats"])
        if "output_dir" in overrides:
            overrides["output_dir"] = ROOT / overrides["output_dir"]
        settings = replace(settings, **overrides)
        if args.preview and "png" not in settings.formats:
            raise ValueError("--preview requires PNG output; include --format png")
        countries = load_country_year()
        current = snapshot(countries, settings.snapshot_year)
        compared = comparison(countries, settings)
        gainers, _ = extremes(compared, "d_clean_share_pp", settings.top_n, changes=True)
        contributions = {unit: source_changes(gainers, settings, unit) for unit in ("pp", "twh")}
        world = window(load_world(), settings)
        world_mix = mix_table(world, settings, "share_pct").merge(
            mix_table(world, settings, "twh"), on="year", suffixes=("_share_pct", "_twh"),
        )
        outcomes = fossil_outcomes(countries, settings)
        example = q5_example(outcomes, settings)
        q6_table, left_out = q6_countries(outcomes)
        pairs = matched_pairs(q6_table, settings.q6_pairs)
        summary = group_summary(q6_table)

        # Import rendering only after command-line and data validation.
        from .plots import (
            change_bars, endpoint_comparison, set_style,
            share_map, share_ranking, source_breakdown,
        )
        from .q156_plots import demand_pairs, fossil_outcome_scatter, world_mix as world_mix_view
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
        # Q1, Q5 and Q6 stay out of the six-image preview; --preview copies them next to it.
        q156_views = (
            (f"q1_{period}_world_mix", lambda: world_mix_view(world, settings)),
            (f"q5_{period}_fossil_outcomes", lambda: fossil_outcome_scatter(outcomes, countries, settings, example)),
            (f"q6_{period}_demand_pairs", lambda: demand_pairs(q6_table, left_out, pairs, summary, settings)),
        )
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        files = []
        for name, render in views + q156_views:
            fig = render()
            try:
                for extension in settings.formats:
                    path = settings.output_dir / f"{name}.{extension}"
                    fig.savefig(path, dpi=settings.dpi, bbox_inches="tight")
                    files.append(path.name)
            finally:
                plt.close(fig)
            print(name)

        preview_path = None
        if args.preview:
            from .preview import save_preview

            preview_path = save_preview(
                [settings.output_dir / f"{name}.png" for name, _ in views],
                ROOT / args.preview,
            )
            print(f"Saved combined preview to {preview_path}")
            for name, _ in q156_views:
                question = name.split("_")[0]
                copy = preview_path.with_name(f"{preview_path.stem}-{question}{preview_path.suffix}")
                shutil.copyfile(settings.output_dir / f"{name}.png", copy)
                print(f"Saved {question} preview to {copy}")

        tables = {
            f"q2_{settings.snapshot_year}_all_countries": current,
            f"q3_{period}_all_compared": compared,
            **{f"q4_{period}_source_{unit}": table for unit, table in contributions.items()},
            f"q1_{period}_world_mix": world_mix,
            f"q5_{period}_fossil_outcomes": outcomes,
            f"q6_{period}_matched_pairs": pairs,
        }
        for name, table in tables.items():
            path = settings.output_dir / f"{name}.csv"
            table.to_csv(path, index=False, float_format="%.4f")
            files.append(path.name)

        manifest = {
            "settings": asdict(settings),
            "input": "data/processed/country_year.csv",
            "preview": str(preview_path) if preview_path else None,
            "snapshot_countries": len(current),
            "snapshot_missing_shares": int(current["clean_share_pct"].isna().sum()),
            "comparison_countries": len(compared),
            "source_breakdown_countries": gainers["iso3"].tolist(),
            "cutoff_ties": "country name ascending; at most top_n per tail",
            "q5_example": None if example is None else example["country"],
            "q5_zoom_countries": int(outcomes["d_fossil_twh"].abs().le(settings.q5_zoom_twh).sum()),
            "q6_countries": len(q6_table),
            "q6_left_out": left_out,
            "q6_pairs": [f"{row.country_reduced} – {row.country_other}" for row in pairs.itertuples()],
            "files": files,
        }
        manifest_path = settings.output_dir / f"manifest_{settings.snapshot_year}_{period}.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, default=str) + "\n")
        print(
            f"Saved nine views to {settings.output_dir}\n"
            f"{len(current)} snapshot countries; {len(compared)} compared; "
            f"{len(gainers)} source-breakdown countries."
        )
    except (ValueError, KeyError, FileNotFoundError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
