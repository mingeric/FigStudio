# FigStudio

Scientific Figure Studio for high-impact biomedical and bioinformatics figures.

FigStudio integrates evidence-first figure planning, 128+ plot recipes, AI-assisted mechanism schematic prompts, journal-ready export, and high-impact visual QC for Nature/Cell/Science-style workflows.

## Included

- 128 registered plot recipes across distributions, comparisons, associations, multivariate plots, matrices, networks, survival, genomics, spatial, and mechanism diagrams.
- Vector-first PDF/SVG export plus RGB PNG/TIFF export with journal-oriented DPI checks.
- Pale accessible palettes, explicit figure contracts, source-data traceability, and claim-boundary review.
- AI image-generation guidance for text-free conceptual source assets; AI assets are never treated as quantitative evidence.

## Quick start

```bash
python scripts/figure_studio.py catalog
python scripts/figure_studio.py render --kind volcano_plot --out figure --seed 7
python scripts/figure_studio.py contact-sheet --out catalog_preview --limit 128
python scripts/qc_figures.py path/to/figures --output audit/figure_qc.tsv --json audit/figure_qc.json
```

Install the Python dependencies when needed:

```bash
python -m pip install -r requirements.txt
```

The governing workflow is documented in [`SKILL.md`](SKILL.md).
