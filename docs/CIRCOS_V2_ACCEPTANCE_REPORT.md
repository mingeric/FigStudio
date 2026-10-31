# Circos composite rebuild V2 acceptance report

## Result

The native feature-anchored Circos renderer is implemented in FigStudio and FigFrame. Reference screenshots were supplied in `/Users/mingsmacbook/Downloads/FIGSTUDIO_CIRCOS_VISUAL_REFERENCES.zip`; the target panel, failed V1 render, and rebuilt V2 render are compared in `gallery/circos_v2_comparison.png`.

The included 12-sector, 240-feature tables and resulting figure are **synthetic demonstration data only**. The rendering workflow and geometric contract pass software acceptance; scientific acceptance on real data remains pending because no source study tables or evidence contract were supplied.

## Acceptance checks

| Area | Status | Evidence |
|---|---|---|
| Root-cause report | PASS | `docs/circos_v2_root_cause.md` records the V1 center-collapse, midpoint fallback, sparse synthetic inputs, excess bands, and unlabeled/signed score scale. |
| Shared feature geometry | PASS | Seven geometry tests establish one feature angle reused for score points, label leaders, and chord endpoints. |
| Open-center Bezier links | PASS | Cubic polar Beziers end at exact feature angles and shared inner score radius; tests assert every sampled curve remains above radius zero. Missing feature anchors fail validation. |
| V2 source contract | PASS | `features.csv` includes per-sector feature IDs, score, direction, labels and optional evidence ranking columns. `links.csv` has explicit feature endpoints and foreign-key validation. Duplicate handling is deterministic and conflicts fail. |
| Score semantics | PASS | Non-negative and signed maps are linear; signed baselines preserve the sign, and user scales reject overflow rather than clipping. Tick values and mapping are stated on-figure. |
| Density / labels | PASS | Renderer cases cover six asymmetric sectors and twelve sectors with 240 features, sparse/dense links, long labels, rank prioritization, bbox collision/clipping suppression, and a suppression-reason CSV. |
| Track styling | PASS | One pale sector band, a minimal score grid, semantic blue/coral/gray score markers, and neutral teal weighted links. No stack of decorative sector bands. |
| Fixed-size exports | PASS | 90 mm: 2125×2125 RGB PNG at 600 dpi; 180 mm: 4251×4251 RGB PNG at 600 dpi. Each has PDF and SVG siblings. |
| Reproducibility | PASS | Input snapshots, `.config.yaml`, `.manifest.json` with SHA-256 values, `.metadata.json`, `.suppressed_labels.csv`, and `.qc.json` are emitted per output stem. |
| Real-data scientific validity | HOLD | Synthetic examples prove renderer behavior only. Replace all example inputs with source-traceable real data and confirm the score definition, direction semantics, link evidence, ranking, and manuscript claim before scientific interpretation. |

## Reproduction and verification

```bash
python -m unittest discover -s tests -v
python scripts/figure_studio.py render --kind circos_lollipop_chord \
  --features examples/circos_v2/features.csv \
  --links examples/circos_v2/links.csv \
  --sectors examples/circos_v2/sectors.csv --data-status demo \
  --top-k 4 --width-mm 90 --formats pdf,svg,png \
  --out examples/circos_v2/circos_v2_90mm
python scripts/figure_studio.py render --kind circos_lollipop_chord \
  --features examples/circos_v2/features.csv \
  --links examples/circos_v2/links.csv \
  --sectors examples/circos_v2/sectors.csv --data-status demo \
  --top-k 4 --width-mm 180 --formats pdf,svg,png \
  --out examples/circos_v2/circos_v2_180mm
python scripts/qc_figures.py examples/circos_v2 \
  --output examples/circos_v2/figure_qc.tsv \
  --json examples/circos_v2/figure_qc.json
```

The V1 examples and exports in `examples/circos/` remain intact as historical comparison inputs. The new renderer uses a separate `examples/circos_v2/` output stem.
