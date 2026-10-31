---
name: scientific-figure-studio
description: Design, draw, export, and critically review traceable biomedical and bioinformatics figures for Nature/Cell/Science-style submission. Use for manuscript figures, mechanisms, graphical abstracts, multi-panel composites, journal TIFF/PDF/SVG export, AI-assisted conceptual schematics, or any request for publication-grade scientific plots. Includes a tested catalog of 129 plot recipes and a native Python renderer.
---

# Scientific Figure Studio

Use this skill as the single workflow for scientific figure production. It integrates evidence-first high-impact design, SCI journal formatting, conceptual mechanism schematics, AI-image source handling, native plotting, and rendered-output QC.

## Operating contract

- Start from one claim, one evidence class, and one analysis unit per figure.
- Separate `observed`, `association`, `prediction`, `mechanism`, `curated context`, and `hypothesis` in labels and captions.
- Preserve all source data. If a top-k display is used, retain the complete table and record the filter.
- Never upgrade RNA co-expression to protein interaction, single-cell detection to spatial localization, DepMap to patient response, observational Cox to causality, or virtual perturbation to experimental knockout.
- Keep a traceable panel → source table/columns → statistic → script → export hash chain.
- Use near-white canvases, pale semantic colours, restrained accents, readable gutters, editable vector text, and no rainbow/jet or red–green-only encoding.

## Workflow

### 1. Freeze the figure contract

Write a contract before plotting:

`panel | question | evidence class | data unit | source table/columns | statistic | display transform | risk`

Drop filler panels. Choose an archetype from:

- `asymmetric_mixed`: one hero atlas, network, heatmap, track, or overview plus smaller support plots;
- `quantitative_grid`: only when panels are genuinely parallel and share scales;
- `schematic_led`: mechanism/workflow/model first, data panels as constraints;
- `image_plate_quant`: primary microscopy/spatial images paired with quantitative readouts.

Use the reading order `context → focal result → orthogonal validation → boundary/next step`.

### 2. Select a plot recipe

The bundled renderer exposes 129 recipes across distributions, comparisons, associations, multivariate views, matrices, networks/flows, temporal/survival analyses, genomics, spatial analysis, and mechanism diagrams. Inspect or render the catalog before inventing a new chart:

```bash
python scripts/figure_studio.py catalog
python scripts/figure_studio.py render --kind volcano_plot --out figure --seed 7
python scripts/figure_studio.py render --kind circos_lollipop_chord --scores examples/circos/gene_scores.csv --links examples/circos/links.csv --sectors examples/circos/sectors.csv --data-status demo --formats pdf,svg,png --out results/circos
python scripts/figure_studio.py contact-sheet --out catalog_preview --limit 129
```

Use the catalog as a starting point, not as a reason to force a template. Pass real source arrays through a native plotting script when the project provides them; demo data are only for smoke tests and examples.

For `circos_lollipop_chord`, follow the versioned CSV contract in [references/plot-catalog.md](references/plot-catalog.md). Links represent shared-feature associations and do not establish causality. The example CSVs are synthetic placeholders, never biological findings. Export includes editable PDF/SVG, 600 dpi PNG, and a metadata JSON with input SHA-256 hashes and data status.

### 3. Apply the visual system

- Default dimensions: 89 mm single-column or 183 mm double-column; keep height ≤247 mm unless the target journal specifies otherwise.
- Use Arial/Helvetica/Liberation Sans-compatible typography, compact bold panel letters, explicit axis units, and sufficient label gutters.
- Use sequential light-neutral → pale blue/teal scales and diverging blue → near-white → rose/brick scales.
- Use redundant encodings: position plus shape/line style/label, not colour alone.
- For dense figures, make the hero panel visually dominant and keep colorbars, legends, and long y labels out of neighbouring gutters.

### 4. Treat mechanism and AI assets correctly

When a conceptual schematic is requested, use the built-in image generation tool by default for a text-free source illustration, then copy the selected source into the project. Add exact labels, arrows, evidence tags, and boundary notes with native vector code. Keep the AI base under a source-asset name such as `*_ai_base.png`; it must not be the sole quantitative or causal reference.

Use solid links for supported/observed relationships and dashed links for hypotheses or proposed mechanisms. Mark the result `CONCEPTUAL MODEL` or `HYPOTHESIS` when appropriate. If image generation is unavailable, produce a code-native schematic rather than fabricating evidence.

### 5. Export and QC

Use the bundled renderer for deterministic demo assets and the project’s native plotting script for real figures:

```bash
python scripts/figure_studio.py render --kind mechanism_schematic --out mechanism --formats pdf,svg,png,tiff
python scripts/figure_studio.py render --kind circos_lollipop_chord --scores examples/circos/gene_scores.csv --links examples/circos/links.csv --sectors examples/circos/sectors.csv --data-status demo --formats pdf,svg,png --out results/circos
python scripts/qc_figures.py path/to/figures --output audit/figure_qc.tsv --json audit/figure_qc.json
```

The default contract is editable PDF/SVG plus RGB PNG ≥300 dpi and RGB TIFF 600 dpi when a TIFF upload is required. Run anti-pattern, data/provenance, visual-logic, and rendered-output checks. Open final PNG/PDF at target size and inspect clipping, label collisions, missing glyphs, grayscale, colour-vision accessibility, and caption alignment.

`qc` distinguishes final raster assets from `*_ai_base.png` source assets. A source asset is reported, not silently treated as a failed final figure.

### 6. Deliver the audit package

Provide:

- figure contract and panel/source map;
- native plotting code and complete source tables;
- final PDF/SVG/RGB PNG/RGB TIFF exports as applicable;
- contact sheet or rapid-review preview;
- QC table with dimensions, mode, DPI, vector companions, and SHA-256;
- evidence-boundary notes for exploratory, network, curated, and conceptual panels;
- unresolved scientific, author-side, repository, and journal-specific gates.

## Resource map

- [references/plot-catalog.md](references/plot-catalog.md): 129 registered recipes and selection guidance.
- [references/figure-contract.md](references/figure-contract.md): panel-level provenance and evidence-boundary template.
- [references/journal-export.md](references/journal-export.md): dimensions, typography, colour, raster/vector, and QC standards.
- `scripts/figure_studio.py`: catalog, deterministic rendering, mechanism fallback, export, and contact-sheet CLI.
- `scripts/qc_figures.py`: standalone final-asset QC with source-AI exclusion and manifest output.
- `requirements.txt`: minimal runtime dependencies for the native renderer and raster export.

## Hard stops

Stop and report before calling a package submission-ready if a main panel lacks provenance, the rendered text is illegible, figures contradict source tables/manuscript claims, the requested mechanism is unsupported by the evidence, or a journal-required editable/vector asset is missing.
