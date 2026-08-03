# Journal export and visual QC contract

## Default geometry

- Single-column working width: 89 mm.
- Double-column working width: 183 mm.
- Maximum default height: 247 mm.
- Use the target journal’s instructions when they differ.

## Typography

- Arial, Helvetica, or Liberation Sans-compatible font.
- Body and tick text should remain legible at final size; dense composites generally start at 7–9 pt.
- Use compact bold panel letters near the top-left; keep titles and captions distinct.
- Keep axis units, sample counts, and statistic definitions visible or in the caption.

## Colour

- Near-white canvas and pale semantic fills.
- Sequential: light neutral → pale blue/teal.
- Diverging: blue → near-white zero → rose/brick.
- Categorical: at most 4–6 accents for a dense figure.
- Never use rainbow/jet or red–green-only encoding.
- Verify grayscale and colour-vision accessibility.

## File contract

- Editable PDF and SVG for line art and text whenever possible.
- RGB PNG at ≥300 dpi for manuscript previews.
- RGB TIFF at 600 dpi, LZW compression, when the journal requests TIFF upload.
- Stable basenames across PDF/SVG/PNG/TIFF companions.
- Keep AI conceptual source images separate from final quantitative figures.

## Four-pass QC

1. Anti-pattern: no 3D, rainbow palette, filler panel, or unsupported claim.
2. Data/provenance: source paths, units, n, filters, transforms, seed, and statistics are recorded.
3. Visual logic: hero/support hierarchy, readable legends, non-colliding colorbars and long labels.
4. Rendered output: inspect final-size PNG/PDF, RGB mode, DPI, clipping, glyphs, grayscale, and SHA-256.
