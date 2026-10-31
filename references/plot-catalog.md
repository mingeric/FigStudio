# Plot catalog

The bundled renderer exposes 129 recipe names. Most catalog entries are deterministic smoke-test renderers; `circos_lollipop_chord` is a data-driven recipe and requires input tables.

## Selection rule

Choose the smallest recipe that answers the panel question. Keep raw observations visible for small n, show signed effects and uncertainty for associations, reserve forest plots for effect/interval summaries, use survival plots only with censoring/events/risk context, and label network or mechanism links by evidence class.

## Registered recipes

### Distributions

`boxplot`, `violin_plot`, `strip_plot`, `swarm_plot`, `raincloud_plot`, `ridge_plot`, `histogram`, `kde_density`, `ecdf`, `beeswarm`, `sina_plot`, `dot_distribution`, `lollipop_distribution`, `ridgeline_density`, `empirical_cdf`, `quantile_plot`, `half_violin`, `letter_value_plot`

### Comparisons and effects

`grouped_bar`, `stacked_bar`, `100pct_stacked_bar`, `diverging_bar`, `dumbbell`, `slopegraph`, `paired_dot`, `interval_dot`, `forest_plot`, `caterpillar_plot`, `tornado_plot`, `waterfall`, `bullet_chart`, `radial_bar`, `boxen_plot`, `errorbar_summary`

### Associations and diagnostics

`scatter_plot`, `regression_plot`, `hexbin_plot`, `bubble_plot`, `scatter_density`, `marginal_scatter`, `correlogram`, `pairplot_matrix`, `volcano_plot`, `ma_plot`, `qq_plot`, `bland_altman`, `concordance_plot`, `lollipop_correlation`, `joint_density`, `contour_scatter`, `residual_plot`, `partial_residual`

### Multivariate and embeddings

`pca_scores`, `pca_loadings`, `umap_embedding`, `tsne_embedding`, `factor_analysis`, `biplot`, `parallel_coordinates`, `radar_chart`, `ternary_plot`, `mds_embedding`, `lda_embedding`, `trajectory_plot`, `sankey`, `decision_boundary`, `calibration_curve`, `coefficient_path`

### Matrices and structured tables

`heatmap`, `clustered_heatmap`, `annotated_heatmap`, `correlation_matrix`, `confusion_matrix`, `distance_matrix`, `adjacency_matrix`, `tile_plot`, `bubble_matrix`, `dot_heatmap`, `zscore_heatmap`, `oncoprint`, `missingness_matrix`, `pairwise_effect_matrix`, `enrichment_heatmap`, `matrix_profile`

### Networks and flows

`network_graph`, `force_directed_graph`, `circular_network`, `chord_diagram`, `arc_diagram`, `hive_plot`, `bipartite_network`, `alluvial_flow`, `sankey_flow`, `pathway_map`, `ligand_receptor_network`, `source_target_flow`, `edge_bundled_graph`, `tree_dendrogram`, `phylogeny_tree`, `evidence_ladder`

### Temporal and survival

`time_series`, `multi_series`, `area_chart`, `stacked_area`, `streamgraph`, `event_timeline`, `spaghetti_plot`, `control_chart`, `cumulative_incidence`, `kaplan_meier`, `survival_forest`, `risk_table`

### Genomics, spatial, and mechanism

`protein_track`, `mutation_lollipop`, `genome_track`, `chromosome_ideogram`, `circos_overview`, `circos_lollipop_chord`, `variant_burden`, `allele_frequency_spectrum`, `spatial_feature`, `spatial_grid`, `spatial_hexbin`, `spatial_dotplot`, `image_quantification`, `cell_type_composition`, `ligand_receptor_lollipop`, `mechanism_schematic`, `graphical_abstract`

## Data-driven Circos composite

`circos_lollipop_chord` consumes feature-level V2 tables and draws score lollipops, a single pale sector-name ring, prioritized collision-aware labels, and feature-anchored links in one native Matplotlib polar figure. `examples/circos_v2/` is synthetic software demonstration data only; it is not biological evidence.

Input contract (schema version 2.0):

- `features.csv` requires `sector,feature_id,score,direction`. Optional columns: `label,p_value,fdr,effect_size,rank,study_id`. Each `(sector,feature_id)` is unique. Scores and all supplied numeric values must be finite; p-value/FDR lie in `[0,1]`. Negative scores require `--signed-scores`. In signed mode, `--baseline` maps to the track midpoint and `--scale` fixes the symmetric deviation range; otherwise the maximum absolute deviation from baseline is used. Values outside an explicit scale are rejected, never clipped.
- `direction` accepts `positive,negative,neutral`; legacy aliases `up,risk,down,protective` are preserved. Positive/up/risk use blue, negative/down/protective use coral, neutral uses gray. Score sign and direction are separate inputs and both are retained.
- `links.csv` requires `from_sector,from_feature,to_sector,to_feature`; optional `weight,link_type`. Both endpoint keys must exist in `features.csv`. `shared_feature` links require identical feature IDs observed in at least two sectors. Duplicate undirected endpoint pairs with identical type/weight are deduplicated and counted; conflicting duplicates fail. Missing weight defaults to 1. Sector-only links and silent sector-center fallback are not supported. Links are associations and do not establish causality.
- `sectors.csv` optionally defines `sector,display_name,order,color`. Each row must refer to a sector present in the feature table. Feature angles are computed once and reused for score marks, label leaders, and link endpoints.
- Sector spans are proportional to feature count. Labels are prioritized by explicit rank, then FDR/p-value, effect magnitude, and score deviation; `--top-k` limits candidates per sector. Collision/clipping-suppressed labels, along with the reason, are retained in a CSV sidecar.
- The score ticks are numerically stated in the figure key. Only one pale sector band is drawn. Chords are cubic Beziers with endpoints at exact feature angles and the inner score-track radius; their sampled radii remain positive so the center stays open. Teal chord color does not encode direction; width represents weight and is capped at the 95th percentile.

Example:

```bash
python scripts/figure_studio.py render --kind circos_lollipop_chord \
  --features examples/circos_v2/features.csv --links examples/circos_v2/links.csv \
  --sectors examples/circos_v2/sectors.csv --data-status demo \
  --top-k 4 --width-mm 180 --formats pdf,svg,png --out results/circos_v2
```

The PNG is RGB at 600 dpi; PDF/SVG are editable vector outputs. Alongside each output stem the renderer writes `.source_*.csv` input snapshots, `.config.yaml`, `.manifest.json` with SHA-256 hashes, `.metadata.json`, `.suppressed_labels.csv`, and `.qc.json`. The `--scores` option remains a legacy adapter for old tables, but legacy links must carry a feature identifier present in both sectors. `--gap-degrees`, `--start-angle`, optional `--link-limit`, `--label-orientation`, `--max-label-chars`, `--chord-tension`, and `--bundle-strength` control layout and links. Long display labels are ellipsized while their full value remains in the source table.

## Evidence-aware mapping

| Evidence need | Prefer | Add explicitly |
|---|---|---|
| Small-n distribution | `strip_plot`, `swarm_plot`, `raincloud_plot` | raw points, replicate unit, center/spread |
| Signed association | `scatter_plot`, `regression_plot`, `forest_plot`, `volcano_plot` | effect size, interval or n, multiplicity |
| Composition | `100pct_stacked_bar`, `cell_type_composition`, `dot_heatmap` | denominator and unit of replication |
| Spatial context | `spatial_feature`, `spatial_grid`, `spatial_hexbin` | specimen/sample identity and image availability |
| Network hypothesis | `ligand_receptor_network`, `source_target_flow`, `evidence_ladder` | co-expression versus inferred communication |
| Mechanism | `mechanism_schematic`, `graphical_abstract` | solid/dashed evidence semantics and conceptual label |
| Survival | `kaplan_meier`, `survival_forest`, `risk_table` | censoring, events, at-risk counts, validation status |
