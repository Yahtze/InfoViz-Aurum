"""Tests for the lightweight TopoJSON-to-Matplotlib path loader."""

import json
import tempfile
import unittest
from pathlib import Path as FilePath

from matplotlib.path import Path

from sketches.geography import load_country_paths


REPO_ROOT = FilePath(__file__).resolve().parents[1]
ATLAS = REPO_ROOT / "data/raw/world-atlas-2.0.2-countries-50m.json"


def write_topology(directory: str, topology: dict) -> FilePath:
    path = FilePath(directory) / "synthetic.json"
    path.write_text(json.dumps(topology), encoding="utf-8")
    return path


class LoadCountryPathsTests(unittest.TestCase):
    def test_decodes_quantized_arcs_and_reversed_references(self) -> None:
        topology = {
            "type": "Topology",
            "transform": {"scale": [0.5, 0.25], "translate": [-10, 20]},
            # The second arc is stored left-to-right but referenced in reverse.
            "arcs": [
                [[0, 0], [2, 0]],
                [[0, 2], [2, 0]],
                [[0, 2], [0, -2]],
                [[2, 0], [0, 2]],
            ],
            "objects": {"countries": {"type": "GeometryCollection", "geometries": [
                {"type": "Polygon", "id": 4, "arcs": [[0, 3, -2, 2]]}
            ]}},
        }
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
            result = load_country_paths(write_topology(directory, topology))

        self.assertEqual(len(result), 1)
        country, path = result[0]
        self.assertEqual(country, "004")
        self.assertEqual(list(path.codes).count(Path.MOVETO), 1)
        self.assertEqual(list(path.codes).count(Path.CLOSEPOLY), 1)
        # Four joined arcs have four unique corners, then one close placeholder.
        self.assertEqual(len(path.vertices), 5)
        self.assertEqual(set(map(tuple, path.vertices[:-1])), {
            (-10.0, 20.0), (-9.0, 20.0), (-9.0, 20.5), (-10.0, 20.5)
        })

    def test_holes_are_subpaths_with_opposite_winding(self) -> None:
        topology = {
            "type": "Topology",
            "arcs": [
                [[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]],
                [[1, 1], [1, 3], [3, 3], [3, 1], [1, 1]],
            ],
            "objects": {"countries": {"type": "GeometryCollection", "geometries": [
                {"type": "Polygon", "id": "8", "arcs": [[0], [1]]}
            ]}},
        }
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
            country, path = load_country_paths(write_topology(directory, topology))[0]

        self.assertEqual(country, "008")
        self.assertEqual(list(path.codes).count(Path.MOVETO), 2)
        self.assertEqual(list(path.codes).count(Path.CLOSEPOLY), 2)
        starts = [i for i, code in enumerate(path.codes) if code == Path.MOVETO]
        ends = [i for i, code in enumerate(path.codes) if code == Path.CLOSEPOLY]
        rings = [path.vertices[start:end] for start, end in zip(starts, ends)]
        areas = [sum(
            x1 * y2 - x2 * y1
            for (x1, y1), (x2, y2) in zip(ring, list(ring[1:]) + [ring[0]])
        ) / 2 for ring in rings]
        self.assertGreater(areas[0], 0)
        self.assertLess(areas[1], 0)

    def test_unquantized_topology_and_multipolygon_and_missing_id(self) -> None:
        topology = {
            "type": "Topology",
            "arcs": [
                [[0, 0], [1, 0], [0, 1], [0, 0]],
                [[5, 5], [6, 5], [5, 6], [5, 5]],
            ],
            "objects": {"countries": {"type": "GeometryCollection", "geometries": [
                {"type": "MultiPolygon", "arcs": [[[0]], [[1]]]},
                {"type": "Polygon", "arcs": [[0]]},
            ]}},
        }
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
            result = load_country_paths(write_topology(directory, topology))

        self.assertEqual([country for country, _ in result], [None, None, None])
        self.assertEqual(tuple(result[0][1].vertices[1]), (1.0, 0.0))
        self.assertEqual(tuple(result[1][1].vertices[0]), (5.0, 5.0))

    def test_dateline_polygon_is_continuous_and_copied_to_both_map_edges(self) -> None:
        topology = {
            "type": "Topology",
            "arcs": [[[170, -10], [-170, -10], [-170, 10], [170, 10], [170, -10]]],
            "objects": {"countries": {"type": "GeometryCollection", "geometries": [
                {"type": "Polygon", "id": "242", "arcs": [[0]]}
            ]}},
        }
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
            paths = load_country_paths(write_topology(directory, topology))

        self.assertEqual([country for country, _ in paths], ["242", "242"])
        ranges = []
        for _, path in paths:
            ring = path.vertices[path.codes != Path.CLOSEPOLY]
            closed = [*ring[:, 0], ring[0, 0]]
            self.assertLessEqual(max(abs(b - a) for a, b in zip(closed, closed[1:])), 180)
            ranges.append((ring[:, 0].min(), ring[:, 0].max()))
        self.assertTrue(any(lo >= 170 and hi <= 190 for lo, hi in ranges))
        self.assertTrue(any(lo >= -190 and hi <= -170 for lo, hi in ranges))

    def test_ignores_non_country_objects_such_as_land(self) -> None:
        topology = {
            "type": "Topology",
            "arcs": [[[0, 0], [1, 0], [0, 1], [0, 0]]],
            "objects": {
                "countries": {"type": "GeometryCollection", "geometries": [
                    {"type": "Polygon", "id": "840", "arcs": [[0]]}
                ]},
                "land": {"type": "GeometryCollection", "geometries": [
                    {"type": "Polygon", "arcs": [[0]]}
                ]},
            },
        }
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
            paths = load_country_paths(write_topology(directory, topology))

        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0][0], "840")

    def test_loads_real_atlas_ids_and_geographic_bounds(self) -> None:
        paths = load_country_paths(ATLAS)
        self.assertGreater(len(paths), 100)
        self.assertIn(("716", paths[0][1]), paths)
        self.assertTrue(all(country is None or (len(country) == 3 and country.isdigit())
                            for country, _ in paths))
        for country, path in paths:
            coords = path.vertices[path.codes != Path.CLOSEPOLY]
            # Dateline copies can be shifted by 360 degrees for edge clipping.
            self.assertTrue((coords[:, 0] >= -540.1).all())
            self.assertTrue((coords[:, 0] <= 540.1).all())
            self.assertTrue((coords[:, 1] >= -90.1).all())
            self.assertTrue((coords[:, 1] <= 90.1).all())
            if country != "010":  # Antarctica's polar ring is intentionally omitted in the map.
                starts = (path.codes == Path.MOVETO).nonzero()[0]
                ends = (path.codes == Path.CLOSEPOLY).nonzero()[0]
                for start, end in zip(starts, ends):
                    ring = path.vertices[start:end]
                    closed = [*ring[:, 0], ring[0, 0]]
                    self.assertLessEqual(max(abs(b - a) for a, b in zip(closed, closed[1:])), 180.01)


if __name__ == "__main__":
    unittest.main()
