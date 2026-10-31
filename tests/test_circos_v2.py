"""Input contracts and renderer checks for the feature-anchored Circos V2 path."""
from __future__ import annotations

import csv
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import matplotlib
matplotlib.use("Agg")
import numpy as np
from PIL import Image
from circos_recipe import load_features_data, load_legacy_data, render


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fixture(directory: Path, n_sectors: int, per_sector: int, *, signed: bool = False,
            long_labels: bool = False, density: int = 30) -> tuple[Path, Path, Path]:
    sectors = [f"Sector {i + 1:02d}" for i in range(n_sectors)]
    features = []
    for si, sector in enumerate(sectors):
        for fi in range(per_sector):
            idx = si * per_sector + fi
            score = ((idx * 29) % 101) / 100
            if signed:
                score = (score - .5) * 2
            features.append({"sector": sector, "feature_id": f"F{fi:04d}",
                             "score": f"{score:.4f}",
                             "direction": "negative" if signed and score < 0 else "positive" if score > .5 else "neutral",
                             "label": f"Long biological feature label {si}-{fi} that should be safely truncated" if long_labels else f"F{fi:04d}",
                             "fdr": f"{((fi + si) % 99 + 1) / 1000:.3f}",
                             "effect_size": f"{score:.4f}"})
    links = []
    for i in range(density):
        a, b = i % n_sectors, (i * 7 + 3) % n_sectors
        if a == b:
            b = (b + 1) % n_sectors
        feature = f"F{i % per_sector:04d}"
        links.append({"from_sector": sectors[a], "from_feature": feature,
                      "to_sector": sectors[b], "to_feature": feature,
                      "weight": 1 + (i % 5) / 4, "link_type": "shared_feature"})
    fp, lp, sp = directory / "features.csv", directory / "links.csv", directory / "sectors.csv"
    write_csv(fp, ["sector", "feature_id", "score", "direction", "label", "fdr", "effect_size"], features)
    write_csv(lp, ["from_sector", "from_feature", "to_sector", "to_feature", "weight", "link_type"], links)
    write_csv(sp, ["sector", "display_name", "order"],
              [{"sector": name, "display_name": name, "order": i} for i, name in enumerate(sectors)])
    return fp, lp, sp


class CircosV2InputTests(unittest.TestCase):
    def test_six_sector_visual_regression_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            fp, lp, sp = fixture(Path(tmp), 6, 10, density=6)
            data = load_features_data(fp, lp, sp)
            fig = render(data, top_n=2, width_mm=90, data_status="demo")
            buffer = io.BytesIO()
            fig.savefig(buffer, format="png", dpi=48, facecolor="white")
            fig.clear()
            buffer.seek(0)
            with Image.open(buffer) as current, Image.open(Path(__file__).parent / "golden" / "circos_v2_six_sector.png") as golden:
                current_pixels = np.asarray(current.convert("RGB"), dtype=np.int16)
                golden_pixels = np.asarray(golden.convert("RGB"), dtype=np.int16)
            self.assertEqual(current_pixels.shape, golden_pixels.shape)
            diff = np.abs(current_pixels - golden_pixels)
            self.assertLessEqual(float(diff.mean()), 1.5)
            self.assertLessEqual(float(np.mean(np.max(diff, axis=2) > 15)), .01)

    def test_12_sectors_240_features_and_long_labels_render_at_90_and_180mm(self):
        with tempfile.TemporaryDirectory() as tmp:
            fp, lp, sp = fixture(Path(tmp), 12, 20, long_labels=True, density=72)
            data = load_features_data(fp, lp, sp)
            for width in (90, 180):
                fig = render(data, top_n=8, width_mm=width, max_label_chars=23, data_status="demo")
                self.assertAlmostEqual(fig.get_figwidth() * 25.4, width, delta=.1)
                self.assertEqual(fig._circos_provenance["features_drawn"], 240)
                self.assertGreater(fig._circos_provenance["labels_suppressed"], 0)
                fig.canvas.draw()
                fig.clear()

    def test_six_sector_asymmetric_sparse_and_dense_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fp, lp, sp = fixture(root, 6, 11, density=1)
            data = load_features_data(fp, lp, sp)
            fig = render(data, top_n=5, width_mm=90)
            self.assertEqual(fig._circos_provenance["links_drawn"], 1)
            fig.clear()
            _, lp, _ = fixture(root, 6, 11, density=30)
            data = load_features_data(fp, lp, sp)
            fig = render(data, top_n=4, width_mm=180)
            self.assertEqual(fig._circos_provenance["links_drawn"], 30)
            fig.clear()

    def test_signed_sparse_scores_and_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            fp, lp, sp = fixture(Path(tmp), 6, 10, signed=True, density=10)
            with self.assertRaisesRegex(ValueError, "negative score requires --signed-scores"):
                load_features_data(fp, lp, sp)
            data = load_features_data(fp, lp, sp, signed_scores=True)
            fig = render(data, signed_scores=True, baseline=0, width_mm=90)
            self.assertTrue(fig._circos_provenance["signed_scores"])
            self.assertAlmostEqual(fig._circos_provenance["scale"], 1)
            fig.clear()

    def test_missing_anchor_rejected_and_duplicate_link_deduplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fp, lp, sp = fixture(root, 6, 10, density=1)
            with lp.open("a", encoding="utf-8") as stream:
                stream.write("Sector 04,F0000,Sector 01,F0000,1,shared_feature\n")
            data = load_features_data(fp, lp, sp)
            self.assertEqual(data["provenance"]["duplicate_undirected_links_removed"], 1)
            with fp.open(encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            rows[0]["feature_id"] = "RENAMED"
            write_csv(fp, list(rows[0]), rows)
            with self.assertRaisesRegex(ValueError, "source anchor|target anchor"):
                load_features_data(fp, lp, sp)

    def test_conflicting_duplicate_and_signed_scale_overflow_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fp, lp, sp = fixture(root, 6, 10, density=1)
            with lp.open("a", encoding="utf-8") as stream:
                stream.write("Sector 04,F0000,Sector 01,F0000,2,shared_feature\n")
            with self.assertRaisesRegex(ValueError, "conflicting type or weight"):
                load_features_data(fp, lp, sp)

    def test_legacy_adapter_requires_feature_anchors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scores = root / "scores.csv"
            links = root / "links.csv"
            write_csv(scores, ["sector", "gene", "score", "direction"],
                      [{"sector": "A", "gene": "X", "score": 1, "direction": "up"},
                       {"sector": "B", "gene": "X", "score": 2, "direction": "down"}])
            write_csv(links, ["source_sector", "target_sector"],
                      [{"source_sector": "A", "target_sector": "B"}])
            with self.assertRaisesRegex(ValueError, "feature is required"):
                load_legacy_data(scores, links)


if __name__ == "__main__":
    unittest.main()
