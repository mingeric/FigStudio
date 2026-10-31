import csv
import sys
import tempfile
import unittest
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from circos_recipe import load_data, render  # noqa: E402
from figure_studio import export_figure, render_kind  # noqa: E402


class CircosRecipeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, columns, rows):
        path = self.root / name
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle); writer.writerow(columns); writer.writerows(rows)
        return path

    def data(self, sector_sizes=(8, 10, 12), links=None, long=False):
        names = [f"Sector{i}" for i in range(len(sector_sizes))]
        score_rows = []
        for si, (sector, size) in enumerate(zip(names, sector_sizes)):
            for gi in range(size):
                gene = ("VeryLongGeneLabel_" + "X" * 45 + str(gi)) if long else f"Gene{gi}"
                score_rows.append([sector, gene, gi + 1, ("up", "down", "risk", "protective", "neutral")[gi % 5], "", 0])
        scores = self.write("scores.csv", ["sector", "gene", "score", "direction", "display_label", "label_priority"], score_rows)
        link_feature = score_rows[1][1] if long else "Gene1"
        link_rows = links if links is not None else [[names[i], names[i+1], link_feature, 1] for i in range(len(names)-1)]
        link_path = self.write("links.csv", ["source_sector", "target_sector", "feature", "weight"], link_rows)
        sectors = self.write("sectors.csv", ["sector", "display_name", "order", "color"], [[n, n, i, "#DCE8EF"] for i, n in enumerate(names)])
        return load_data(scores, link_path, sectors), scores, link_path, sectors

    def test_many_asymmetric_sectors_mixed_directions_and_long_labels(self):
        data, *_ = self.data((8, 9, 10, 11, 12, 13, 20), long=True)
        fig = render(data, top_n=2)
        self.assertEqual(len(fig.axes), 1)
        self.assertGreater(len(fig.axes[0].collections), 0)
        label_texts = [text.get_text() for text in fig.axes[0].texts if text.get_text().startswith("VeryLong")]
        self.assertTrue(label_texts)
        self.assertTrue(all(len(label) <= 18 and label.endswith("…") for label in label_texts))
        plt.close(fig)

    def test_empty_links_and_limit_are_stable(self):
        data, *_ = self.data(links=[])
        fig0 = render(data); lines0 = len(fig0.axes[0].lines); plt.close(fig0)
        data, *_ = self.data()
        fig1 = render(data, link_limit=1); lines1 = len(fig1.axes[0].lines); plt.close(fig1)
        fig2 = render(data, link_limit=2); lines2 = len(fig2.axes[0].lines); plt.close(fig2)
        self.assertEqual(lines1 - lines0, 1)
        self.assertEqual(lines2 - lines1, 1)

    def test_missing_data_and_invalid_sectors_fail_clearly(self):
        with self.assertRaisesRegex(ValueError, "requires --features and --links"):
            render_kind("circos_lollipop_chord")
        with self.assertRaisesRegex(ValueError, "absent from gene_scores.csv"):
            self.data(links=[["missing", "Sector1", "Gene1", 1]])

    def test_missing_score_column_and_duplicate_feature_link_fail(self):
        bad = self.write("bad.csv", ["sector", "gene", "direction"], [["A", "G", "up"]])
        with self.assertRaisesRegex(ValueError, "missing required columns: score"):
            load_data(bad, self.write("emptylinks.csv", ["source_sector", "target_sector"], []))
        duplicate = [["Sector0", "Sector1", "Gene1", 1], ["Sector0", "Sector1", "Gene1", 2]]
        with self.assertRaisesRegex(ValueError, "conflicting type or weight"):
            self.data(links=duplicate)

    def test_nonfinite_or_negative_scores_and_unknown_directions_fail(self):
        score = self.write("s.csv", ["sector", "gene", "score", "direction"], [["A", "G", "nan", "up"]])
        links = self.write("l.csv", ["source_sector", "target_sector"], [])
        with self.assertRaisesRegex(ValueError, "must be finite"):
            load_data(score, links)
        unknown = self.write("unknown.csv", ["sector", "gene", "score", "direction"], [["A", "G", 1, "causal"]])
        with self.assertRaisesRegex(ValueError, "unknown direction"):
            load_data(unknown, links)
        negative = self.write("negative.csv", ["sector", "gene", "score", "direction"], [["A", "G", -2, "down"]])
        with self.assertRaisesRegex(ValueError, "requires --signed-scores"):
            load_data(negative, links)
        data = load_data(negative, links, signed_scores=True)
        self.assertTrue(data["signed_scores"])
        fig = render(data, baseline=0)
        self.assertGreater(len(fig.axes[0].lines), 0)
        plt.close(fig)
        with self.assertRaisesRegex(ValueError, "exceeds the configured symmetric scale"):
            render(data, baseline=0, score_scale=1)
        zero_weight = self.write("zero.csv", ["source_sector", "target_sector", "feature", "weight"], [["A", "A", "G", 0]])
        with self.assertRaisesRegex(ValueError, "must be finite and positive"):
            load_data(self.write("positive.csv", ["sector", "gene", "score", "direction"], [["A", "G", 1, "up"], ["B", "G", 1, "up"]]), zero_weight)

    def test_fixed_input_produces_identical_artist_geometry(self):
        data, *_ = self.data()
        fig_a = render(data); fig_b = render(data)
        self.assertEqual([line.get_xydata().tolist() for line in fig_a.axes[0].lines], [line.get_xydata().tolist() for line in fig_b.axes[0].lines])
        plt.close(fig_a); plt.close(fig_b)

    def test_vector_and_600_dpi_png_signatures(self):
        data, *_ = self.data()
        fig = render(data)
        base = self.root / "figure"
        paths = export_figure(fig, base, ["pdf", "svg", "png"], png_dpi=600)
        self.assertEqual(paths[0].read_bytes()[:4], b"%PDF")
        self.assertIn(b"<svg", paths[1].read_bytes()[:1000])
        self.assertEqual(paths[2].read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        from PIL import Image
        with Image.open(paths[2]) as image:
            self.assertEqual(image.mode, "RGB")
            self.assertGreaterEqual(image.info["dpi"][0], 599)
        plt.close(fig)


if __name__ == "__main__":
    unittest.main()
