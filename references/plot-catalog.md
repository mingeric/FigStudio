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

`circos_lollipop_chord` consumes `gene_scores.csv` and `links.csv`, with optional `sectors.csv`. It draws per-sector radial score lollipops, sparse prioritized gene labels, a pale sector-name band, and explicit shared-feature links in a single Matplotlib polar layout. The `examples/circos/` tables are synthetic software examples only, not biological findings.

Input contract (schema version 1.0):

- `gene_scores.csv` requires `sector,gene,score,direction`. Optional columns: `display_label,label_priority,evidence_id,sample_size`. Each `(sector,gene)` must be unique. Scores must be finite and non-negative unless `--signed-scores` is passed; in signed mode `--baseline` is the dashed mid-track reference and values extend inward or outward by absolute deviation. `--scale` optionally fixes the deviation range; otherwise the maximum absolute deviation from baseline is used. Values beyond an explicit scale are rejected rather than clipped.
- `direction` must be one of `up`, `down`, `risk`, `protective`, or `neutral`; the legend maps up/risk to blue, down/protective to coral, and neutral to teal.
- `links.csv` requires `source_sector,target_sector`; optional `feature,weight`. A link means shared feature/sector association, never a causal interaction. Missing weights default to 1 as equal contribution; explicit weights must be finite and positive. When `feature` matches a gene in both sectors, the line anchors to those gene positions; otherwise it connects sector centers.
- `sectors.csv` optionally defines `sector,display_name,order,color`. Every listed sector must occur in the score table.

Example:

```bash
python scripts/figure_studio.py render --kind circos_lollipop_chord \
  --scores examples/circos/gene_scores.csv --links examples/circos/links.csv \
  --sectors examples/circos/sectors.csv --data-status demo \
  --top-n 4 --link-limit 500 --formats pdf,svg,png --out results/circos
```

The Circos PNG is 600 dpi. PDF/SVG remain editable vector exports. `results/circos.metadata.json` records schema, input hashes, configuration, software versions, and `demo`/`real` status. `--top-n`, `--gap-degrees`, `--link-limit`, `--figsize`, `--label-orientation`, `--max-label-chars`, `--inner-radius`, and `--outer-radius` tune density and geometry. Long labels are ellipsized at the display limit while the full value remains in the input table. Colorblind-safe blue/coral/teal classes are used, and sector colors can be specified directly.

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
