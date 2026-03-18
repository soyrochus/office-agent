## 1. Configuration And Versioning Foundation

- [ ] 1.1 Add `output_directory` and `allow_inplace_overwrite` to the application configuration model and config loading paths
- [ ] 1.2 Create a shared versioning module that generates `<name>.edited.<timestamp>.<ext>` output paths using sortable UTC timestamps
- [ ] 1.3 Add focused tests for configuration parsing and versioned output path generation

## 2. Stale Locator Validation

- [ ] 2.1 Add a dedicated stale-locator error type and service-layer content-hash validation helpers for indexed documents
- [ ] 2.2 Implement deterministic item-id re-resolution for changed source files across DOCX, PPTX, and XLSX write workflows
- [ ] 2.3 Ensure write flows fail with the stale-locator error when re-resolution cannot safely recover the target item

## 3. Write Workflow Integration

- [ ] 3.1 Extend DOCX, PPTX, and XLSX write service methods with output-mode handling and default versioned writes
- [ ] 3.2 Route all write operations through the shared versioning policy so adapters save to the selected output path instead of always writing in place
- [ ] 3.3 Reindex every successfully written output file and return the written output path in the patch result
- [ ] 3.4 Preserve source-path behavior for explicit in-place writes only when configuration allows overwrite

## 4. CLI Surface And Error Handling

- [ ] 4.1 Update CLI write command behavior and docs-facing output so versioned write paths are reported consistently
- [ ] 4.2 Surface stale-locator failures through the CLI with exit code `3`
- [ ] 4.3 Decide and implement whether CLI write commands expose explicit output-mode selection or rely on configuration defaults for this feature

## 5. Cross-Format Testing And Verification

- [ ] 5.1 Add pytest coverage for versioned outputs and automatic reindex behavior for DOCX writes
- [ ] 5.2 Add pytest coverage for versioned outputs and automatic reindex behavior for PPTX writes
- [ ] 5.3 Add pytest coverage for versioned outputs and automatic reindex behavior for XLSX writes
- [ ] 5.4 Add pytest coverage for stale-locator detection, deterministic re-resolution, and in-place overwrite policy enforcement
- [ ] 5.5 Run the cross-format pytest suite and verify the versioning acceptance criteria end to end
