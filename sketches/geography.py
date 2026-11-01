"""Small TopoJSON reader for plotting country outlines with Matplotlib.

Supports Topology objects containing Polygon and MultiPolygon geometries, with
arc-based rings and optional quantization transforms. Coordinates are returned
as unprojected longitude/latitude. Rings are unwrapped across the antimeridian;
seam-crossing polygons have shifted copies for clipping at both map edges.
GeometryCollections nested inside other GeometryCollections and non-polygon
geometry types are intentionally ignored.
"""

from __future__ import annotations

import json
from pathlib import Path as FilePath
from typing import Any

from matplotlib.path import Path


def _decode_arcs(topology: dict[str, Any]) -> list[list[tuple[float, float]]]:
    """Decode TopoJSON arcs, including per-arc delta encoding and transforms."""
    transform = topology.get("transform")
    if transform is not None:
        scale = transform["scale"]
        translate = transform["translate"]

    decoded: list[list[tuple[float, float]]] = []
    for arc in topology["arcs"]:
        points: list[tuple[float, float]] = []
        x = y = 0.0
        for position in arc:
            if transform is None:
                px, py = position[:2]
            else:
                x += position[0]
                y += position[1]
                px = x * scale[0] + translate[0]
                py = y * scale[1] + translate[1]
            points.append((float(px), float(py)))
        decoded.append(points)
    return decoded


def _stitch_ring(references: list[int], arcs: list[list[tuple[float, float]]]) -> list[tuple[float, float]]:
    """Join referenced arcs, omitting shared endpoints (and the closing point)."""
    points: list[tuple[float, float]] = []
    for reference in references:
        index = reference if reference >= 0 else ~reference
        arc = arcs[index]
        if reference < 0:
            arc = list(reversed(arc))
        if points and arc and points[-1] == arc[0]:
            points.extend(arc[1:])
        else:
            points.extend(arc)
    if len(points) > 1 and points[-1] == points[0]:
        points.pop()
    return points


def _unwrap_ring(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Move each longitude to the nearest 360-degree copy of its predecessor."""
    if not points:
        return []
    unwrapped = [points[0]]
    for longitude, latitude in points[1:]:
        previous = unwrapped[-1][0]
        longitude += 360 * round((previous - longitude) / 360)
        unwrapped.append((longitude, latitude))
    return unwrapped


def _signed_area(points: list[tuple[float, float]]) -> float:
    return sum(
        x1 * y2 - x2 * y1
        for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1])
    ) / 2


def _polygon_path(rings: list[list[int]], arcs: list[list[tuple[float, float]]]) -> Path:
    """Create a seam-continuous compound path with oppositely wound holes."""
    unwrapped = [_unwrap_ring(_stitch_ring(ring, arcs)) for ring in rings]
    outer_center = (
        (min(x for x, _ in unwrapped[0]) + max(x for x, _ in unwrapped[0])) / 2
        if unwrapped and unwrapped[0] else 0
    )
    vertices: list[tuple[float, float]] = []
    codes: list[int] = []
    for ring_index, points in enumerate(unwrapped):
        if len(points) < 3:
            continue
        if ring_index:
            # A hole can unwrap one full turn away from its exterior; align centers.
            center = (min(x for x, _ in points) + max(x for x, _ in points)) / 2
            shift = 360 * round((outer_center - center) / 360)
            points = [(x + shift, y) for x, y in points]
        # Non-zero winding fill treats oppositely oriented subpaths as holes.
        want_positive = ring_index == 0
        if (_signed_area(points) > 0) != want_positive:
            points.reverse()
        vertices.extend(points)
        vertices.append(points[0])  # CLOSEPOLY ignores this placeholder coordinate.
        codes.extend([Path.MOVETO, *([Path.LINETO] * (len(points) - 1)), Path.CLOSEPOLY])
    return Path(vertices, codes)


def _dateline_copies(path: Path) -> list[Path]:
    """Return shifted copies so seam-crossing pieces appear at both map edges."""
    if not len(path.vertices):
        return [path]
    longitudes = path.vertices[path.codes != Path.CLOSEPOLY, 0]
    shifts = [0]
    if longitudes.min() < -180:
        shifts.append(360)
    if longitudes.max() > 180:
        shifts.append(-360)
    return [
        Path(path.vertices + [shift, 0], path.codes)
        for shift in shifts
    ]


def load_country_paths(atlas_path: FilePath) -> list[tuple[str | None, Path]]:
    """Return one Matplotlib compound path per Polygon in a TopoJSON atlas.

    Country identifiers are the TopoJSON IDs, left-padded to three characters;
    missing IDs remain ``None``. Polygon holes remain subpaths in the same Path.
    Seam-crossing polygons may return shifted path copies with longitudes outside
    [-180, 180], intended to be clipped by the plotting axes.
    """
    topology = json.loads(atlas_path.read_text(encoding="utf-8"))
    if topology.get("type") != "Topology":
        raise ValueError("Expected a TopoJSON Topology")
    arcs = _decode_arcs(topology)
    paths: list[tuple[str | None, Path]] = []

    def add_geometry(geometry: dict[str, Any]) -> None:
        geometry_type = geometry.get("type")
        if geometry_type == "Polygon":
            polygons = [geometry.get("arcs", [])]
        elif geometry_type == "MultiPolygon":
            polygons = geometry.get("arcs", [])
        else:
            return
        raw_id = geometry.get("id")
        identifier = None if raw_id is None else str(raw_id).zfill(3)
        for rings in polygons:
            if rings:
                polygon = _polygon_path(rings, arcs)
                paths.extend((identifier, path) for path in _dateline_copies(polygon))

    def visit(obj: dict[str, Any]) -> None:
        if obj.get("type") == "GeometryCollection":
            for geometry in obj.get("geometries", []):
                add_geometry(geometry)
        else:
            add_geometry(obj)

    countries = topology.get("objects", {}).get("countries")
    if countries is not None:
        visit(countries)
    return paths
