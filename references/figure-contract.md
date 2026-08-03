# Figure contract

Write one row per panel before rendering. The contract is the handoff between scientific reasoning, plotting code, and reviewer QC.

```text
figure_id:
core_message:
archetype: asymmetric_mixed | quantitative_grid | schematic_led | image_plate_quant
target_journal:
target_width_mm: 89 | 183
panel:
  question:
  evidence_class: observed | association | prediction | mechanism | curated_context | hypothesis
  analysis_unit: patient | sample | donor | cell | spot | pseudobulk | cell_line | gene | variant | pathway
  source_table:
  source_columns:
  accession_or_file:
  filter_or_display_subset:
  transform:
  statistic:
  uncertainty_or_n:
  missingness:
  likely_overclaim:
  caption_boundary:
script:
seed:
outputs:
hash_manifest:
```

## Reviewer gates

1. Every displayed number maps to a source column or an explicit transformation.
2. Every panel has a distinct question; filler panels are removed.
3. A display-only top-k panel retains the complete source table.
4. The analysis unit is not silently replaced by a larger count, such as cells becoming patients.
5. Mechanistic language is not stronger than the evidence class.
6. Figure and manuscript caption use the same names, denominators, and boundary terms.
7. Exported hashes, dimensions, DPI, colour mode, and vector companions are recorded.
