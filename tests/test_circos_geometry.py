"""Numeric geometry tests run before any V2 rendering/export work."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from circos_geometry import feature_angles, link_geometry, score_radii, sector_intervals


def fixture(n_sectors: int, n_features: int) -> tuple[list[str], list[dict[str, object]]]:
    names = [f"S{i:02d}" for i in range(n_sectors)]
    rows = []
    for index in range(n_features):
        sector = names[index % n_sectors]
        score = ((index * 37) % 101) / 100
        rows.append({"sector": sector, "feature_id": f"F{index:04d}", "_score": score})
    return names, rows


class CircosGeometryTests(unittest.TestCase):
    def test_six_sector_asymmetric_layout_maps_all_features_monotonically(self):
        names, rows = fixture(6, 63)
        counts = {name: sum(row["sector"] == name for row in rows) for name in names}
        intervals = sector_intervals(names, counts, gap_degrees=2.5, start_degrees=-37)
        anchors = feature_angles(rows, intervals)
        self.assertEqual(len(anchors), 63)
        self.assertAlmostEqual(sum(arc.span for arc in intervals.values()) + math.radians(2.5)*6, 2*math.pi)
        self.assertNotEqual(len({round(arc.span, 8) for arc in intervals.values()}), 1)
        for name, arc in intervals.items():
            angles = [angle for (sector, _), angle in anchors.items() if sector == name]
            self.assertEqual(angles, sorted(angles))
            self.assertGreater(min(angles), arc.start)
            self.assertLess(max(angles), arc.end)

    def test_twelve_sector_two_hundred_plus_feature_layout_and_sparse_dense_links(self):
        names, rows = fixture(12, 240)
        counts = {name: sum(row["sector"] == name for row in rows) for name in names}
        intervals = sector_intervals(names, counts, gap_degrees=1.5)
        anchors = feature_angles(rows, intervals)
        sparse = [{"from_sector": names[0], "from_feature": "F0000", "to_sector": names[6], "to_feature": "F0006"}]
        dense = []
        for i in range(60):
            source_index, target_index = i, i + 120
            dense.append({"from_sector": names[source_index % 12], "from_feature": f"F{source_index:04d}",
                          "to_sector": names[target_index % 12], "to_feature": f"F{target_index:04d}"})
        self.assertEqual(len(link_geometry(sparse, anchors, inner_radius=.53)), 1)
        paths = link_geometry(dense, anchors, inner_radius=.53, tension=.74, bundle_strength=.025)
        self.assertEqual(len(paths), 60)
        self.assertTrue(all(path.radius.min() > 0 for path in paths))

    def test_chord_endpoints_are_named_feature_angles_at_inner_radius(self):
        names, rows = fixture(6, 60)
        counts = {name: 10 for name in names}
        anchors = feature_angles(rows, sector_intervals(names, counts, gap_degrees=2))
        link = {"from_sector": "S00", "from_feature": "F0000", "to_sector": "S03", "to_feature": "F0003"}
        path, = link_geometry([link], anchors, inner_radius=.57, tension=.7)
        self.assertAlmostEqual(path.radius[0], .57)
        self.assertAlmostEqual(path.radius[-1], .57)
        self.assertAlmostEqual(path.theta[0], anchors[("S00", "F0000")])
        delta = (path.theta[-1] - anchors[("S03", "F0003")]) % (2*math.pi)
        self.assertAlmostEqual(min(delta, 2*math.pi-delta), 0)
        self.assertGreater(path.radius.min(), .2)

    def test_missing_named_anchor_fails_instead_of_using_sector_midpoint(self):
        with self.assertRaisesRegex(ValueError, "missing feature anchor"):
            link_geometry([{"from_sector": "S00", "from_feature": "MISSING",
                            "to_sector": "S01", "to_feature": "F0001"}], {}, inner_radius=.5)

    def test_signed_score_radius_preserves_sign_and_zero_baseline(self):
        rows = [{"sector": "A", "feature_id": "n", "_score": -2.0},
                {"sector": "A", "feature_id": "z", "_score": 0.0},
                {"sector": "A", "feature_id": "p", "_score": 4.0}]
        radii, info = score_radii(rows, inner_radius=.6, outer_radius=.9, baseline=0, signed=True, scale=4)
        self.assertLess(radii[("A", "n")], info["baseline_radius"])
        self.assertAlmostEqual(radii[("A", "z")], info["baseline_radius"])
        self.assertGreater(radii[("A", "p")], info["baseline_radius"])
        self.assertAlmostEqual(radii[("A", "p")], .9)
        with self.assertRaisesRegex(ValueError, "negative scores require signed=True"):
            score_radii(rows, inner_radius=.6, outer_radius=.9)

    def test_nonnegative_score_radius_is_linear_and_zero_is_baseline(self):
        rows = [{"sector": "A", "feature_id": "0", "_score": 0.0},
                {"sector": "A", "feature_id": "5", "_score": 5.0},
                {"sector": "A", "feature_id": "10", "_score": 10.0}]
        radii, info = score_radii(rows, inner_radius=.6, outer_radius=.9, scale=10)
        self.assertAlmostEqual(radii[("A", "0")], .6)
        self.assertAlmostEqual(radii[("A", "5")], .75)
        self.assertAlmostEqual(radii[("A", "10")], .9)
        self.assertFalse(info["signed"])

    def test_geometry_is_deterministic(self):
        first = fixture(6, 60)
        second = fixture(6, 60)
        intervals_a = sector_intervals(first[0], {name: 10 for name in first[0]})
        intervals_b = sector_intervals(second[0], {name: 10 for name in second[0]})
        self.assertEqual(feature_angles(first[1], intervals_a), feature_angles(second[1], intervals_b))


if __name__ == "__main__":
    unittest.main()
