## 1. XLSX Foundation

- [ ] 1.1 Add the `openpyxl` dependency and create the XLSX adapter module under `src/offagent/adapters/`
- [ ] 1.2 Extend shared domain and locator handling for XLSX cell item ids, worksheet metadata, and `write-cell` operations
- [ ] 1.3 Add focused XLSX test fixtures that cover multiple worksheets, string cells, numeric cells, empty cells, and formula cells

## 2. XLSX Adapter

- [ ] 2.1 Implement XLSX cell extraction in `adapters/xlsx_adapter.py` with `sheet:{sheet_name}!{coordinate}` item ids and cell metadata
- [ ] 2.2 Ensure extraction indexes only non-empty cells and captures formula text plus stringified search content
- [ ] 2.3 Implement read helpers for resolved XLSX cell items
- [ ] 2.4 Implement `write-cell` behavior that updates one targeted workbook cell with consistent value coercion
- [ ] 2.5 Implement append behavior for empty or string-compatible cells and explicit rejection for numeric or formula targets

## 3. Index And Service Integration

- [ ] 3.1 Extend indexing and validation helpers so `.xlsx` files are treated as indexable inputs beside DOCX and PPTX
- [ ] 3.2 Extend shared store usage so XLSX cell items are upserted, replaced, and queried through the existing document and FTS tables
- [ ] 3.3 Add XLSX indexing and reindexing flows in the service layer for individual workbook files and directories containing workbooks
- [ ] 3.4 Add XLSX search, locate, and read workflows that return cell `SearchHit` and `ItemRef` data from the shared store
- [ ] 3.5 Add XLSX write and append workflows that resolve one concrete cell target, patch the workbook, and reindex the updated file

## 4. CLI Surface

- [ ] 4.1 Extend `office-agent index` and `office-agent reindex` to accept `.xlsx` inputs alongside the existing DOCX and PPTX flows
- [ ] 4.2 Extend `office-agent search <query> [--type xlsx] [--doc <file>]` for XLSX cell search results
- [ ] 4.3 Add `office-agent locate --doc <file> --sheet <name> --cell <coordinate>` for direct XLSX cell lookup
- [ ] 4.4 Ensure `office-agent read`, `append`, and the new `write-cell` command support XLSX cell item ids and report unsupported append targets clearly

## 5. Testing And Verification

- [ ] 5.1 Add pytest coverage for XLSX extraction, stable item ids, metadata capture, and empty-cell exclusion
- [ ] 5.2 Add pytest coverage for XLSX indexing, search, locate, read, and reindex workflows
- [ ] 5.3 Add pytest coverage for XLSX `write-cell` and append operations, including rejection for numeric and formula cells plus reopen verification
- [ ] 5.4 Run the XLSX-focused pytest suite and verify the CLI commands satisfy the acceptance criteria with sample workbooks
