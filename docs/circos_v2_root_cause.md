# Circos V2 root-cause report

## Reproduction state

- Repository: `mingeric/FigStudio`
- Failed implementation commit: `f074cded14625ad352ec8cfa6501dbbc44492a36`
- Recipe: `circos_lollipop_chord`
- Reproduction command:

```bash
python scripts/figure_studio.py render --kind circos_lollipop_chord \
  --scores examples/circos/gene_scores.csv --links examples/circos/links.csv \
  --sectors examples/circos/sectors.csv --data-status demo \
  --formats pdf,svg,png --out examples/circos/circos_lollipop_chord
```

The reference bundle supplied with V2 contains `01_TARGET_ORIGINAL_SCREENSHOT.jpg`, its cropped Circos panel `01_TARGET_CIRCOS_CROPPED.png` (945 × 875), and the failed rendering `02_FAILED_V1_OUTPUT.png` (1816 × 2048). The V1 repository preview is also 4104 × 4626 at 600 dpi.

## Findings

1. **The chord curve collapses to the origin.** `scripts/circos_recipe.py` computed `r(t) = (r_inner - 0.04) × (1 - sin(πt)^0.85)`. At `t=0.5`, the radius is exactly zero. Every edge therefore becomes a center-converging petal. Its endpoints are also fixed at the same inner radius, not at the plotted feature point.
2. **Feature anchors silently fall back to sector centers.** `anchors.get((sector, feature), mids[sector])` accepts an absent feature and substitutes a sector midpoint. The old `links.csv` contract only carried one feature string, so mismatched or absent identifiers could still render without a diagnostic.
3. **The output is sparse by contract and synthetic by construction.** The example contains six sectors × ten placeholder rows, while the renderer labels only four features per sector. Its scores follow a repeating modulo formula, and the old contract has no p-value/FDR/effect-size ranking. This explains the G01–G08-looking, repetitive annotation pattern; it is not real research data.
4. **The track hierarchy is overbuilt.** Two adjacent annular bars (`bottom=.99,height=.10` and `bottom=.90,height=.07`) create stacked sector bands, followed by four regular unlabeled grid segments per sector. The extra band and fixed grid dominate the score marks instead of matching the single pale sector band and ranked score arc in the reference.
5. **The score scale is not self-reading.** Grid arcs are fixed fractions, but no values are written at the ticks. Signed values are reduced to absolute deviations, so their sign is not represented by radius.
6. **Label placement is decoupled from the feature order.** The score points use evenly spaced feature angles, while the chosen labels are moved to evenly spaced display slots. Leader lines connect the two, but there is no collision test or suppressed-label record.

## V2 geometry constraints

V2 tests must establish, before final exports, that each feature has one stable sector-local angle; score points and label leaders use that angle; every chord endpoint has radius `r_inner` and the exact named feature angle; and every sampled chord remains outside a non-zero open-center radius. Missing feature anchors must fail validation. Any aggregate link must be explicitly typed and reported.

The V2 examples remain marked synthetic. The reference screenshot is a visual target only and is not treated as source data or evidence.
