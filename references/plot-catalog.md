# Plot catalog

The bundled renderer exposes 128 deterministic recipe names. They are grouped by evidence morphology rather than by a single software package. A recipe can be rebuilt from project-native source data; the renderer’s built-in data are smoke-test data only.

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

`protein_track`, `mutation_lollipop`, `genome_track`, `chromosome_ideogram`, `circos_overview`, `variant_burden`, `allele_frequency_spectrum`, `spatial_feature`, `spatial_grid`, `spatial_hexbin`, `spatial_dotplot`, `image_quantification`, `cell_type_composition`, `ligand_receptor_lollipop`, `mechanism_schematic`, `graphical_abstract`

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
