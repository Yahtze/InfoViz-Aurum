"""One configuration shared by all six sketches."""

from dataclasses import dataclass
from pathlib import Path
import math
import tomllib

from matplotlib.colors import is_color_like

ROOT = Path(__file__).resolve().parents[1]
CLEAN_SOURCES = (
    "nuclear", "hydro", "solar", "wind", "bioenergy",
    "other_renewables_excluding_bioenergy",
)


@dataclass(frozen=True)
class SourceGroup:
    label: str
    sources: tuple[str, ...]
    color: str


@dataclass(frozen=True)
class Settings:
    snapshot_year: int
    start_year: int
    end_year: int
    top_n: int
    min_generation_twh: float
    output_dir: Path
    formats: tuple[str, ...]
    dpi: int
    groups: tuple[SourceGroup, ...]
    # Q5 and Q6 (optional in the config; these are the defaults).
    q5_zoom_twh: float = 60.0
    q5_example: str | None = None
    q6_zoom_pct: float = 300.0
    q6_pairs: int = 6
    q6_selected_pair: int = 1

    def __post_init__(self):
        for name in ("snapshot_year", "start_year", "end_year", "top_n", "dpi"):
            if type(getattr(self, name)) is not int:
                raise ValueError(f"{name} must be an integer")
        if self.start_year >= self.end_year:
            raise ValueError("start_year must be before end_year")
        if self.top_n < 1 or self.dpi < 1:
            raise ValueError("top_n and dpi must be positive")
        if not math.isfinite(self.min_generation_twh) or self.min_generation_twh < 0:
            raise ValueError("min_generation_twh must be finite and nonnegative")
        if not self.formats or not set(self.formats) <= {"png", "svg", "pdf"}:
            raise ValueError("output formats must be png, svg, or pdf")
        if len(set(self.formats)) != len(self.formats):
            raise ValueError("output formats must not repeat")
        if any(not is_color_like(group.color) for group in self.groups):
            raise ValueError("Each source group must have a valid Matplotlib color")
        labels = [group.label for group in self.groups]
        if set(labels) & {"iso3", "country", "d_clean_share_pp", "total", "year", "Coal", "Gas", "Oil"}:
            raise ValueError("Source group labels must not use reserved table column names")
        if any(not label.strip() for label in labels) or len(set(labels)) != len(labels):
            raise ValueError("source group labels must be nonempty and unique")
        sources = [source for group in self.groups for source in group.sources]
        if any(not group.sources for group in self.groups):
            raise ValueError("source groups must not be empty")
        if len(sources) != len(set(sources)) or set(sources) != set(CLEAN_SOURCES):
            raise ValueError("source groups must contain each clean source exactly once")
        for name in ("q5_zoom_twh", "q6_zoom_pct"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be a positive number")
        for name in ("q6_pairs", "q6_selected_pair"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.q6_selected_pair > self.q6_pairs:
            raise ValueError("q6_selected_pair must not exceed q6_pairs")
        if self.q5_example is not None and (not isinstance(self.q5_example, str) or not self.q5_example.strip()):
            raise ValueError("q5_example must be a country name")


def load_settings(path: Path = ROOT / "sketches" / "config.toml") -> Settings:
    with path.open("rb") as handle:
        config = tomllib.load(handle)
    years, selection, output = (config[key] for key in ("years", "selection", "output"))
    q5, q6 = config.get("q5", {}), config.get("q6", {})
    directory = Path(output["directory"])
    return Settings(
        snapshot_year=years["snapshot"],
        start_year=years["start"],
        end_year=years["end"],
        top_n=selection["top_n"],
        min_generation_twh=float(selection["min_generation_twh"]),
        output_dir=directory if directory.is_absolute() else ROOT / directory,
        formats=tuple(output["formats"]),
        dpi=output["dpi"],
        groups=tuple(
            SourceGroup(group["label"], tuple(group["sources"]), group["color"])
            for group in config["groups"]
        ),
        q5_zoom_twh=q5.get("zoom_twh", 60.0),
        q5_example=q5.get("example"),
        q6_zoom_pct=q6.get("zoom_pct", 300.0),
        q6_pairs=q6.get("pairs", 6),
        q6_selected_pair=q6.get("selected_pair", 1),
    )
