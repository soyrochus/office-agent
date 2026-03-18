## 1. PPTX Foundation

- [x] 1.1 Add the `python-pptx` dependency and create the PPTX adapter module under `src/offagent/adapters/`
- [x] 1.2 Extend shared domain structures and locator handling for PPTX text-shape item ids, slide metadata, and shape metadata
- [x] 1.3 Add focused PPTX test fixtures that cover text-bearing shapes, non-text shapes, multi-paragraph text frames, and editable shape content

## 2. PPTX Adapter

- [x] 2.1 Implement PPTX text-shape extraction in `adapters/pptx_adapter.py` with `slide:{slide_number}:shape:{shape_id}` item ids and shape metadata
- [x] 2.2 Ensure extraction includes only shapes with text frames and excludes charts, tables, images, SmartArt, and other non-text shapes
- [x] 2.3 Implement read helpers for resolved PPTX text-shape items
- [x] 2.4 Implement text-frame replace behavior that sets replacement text on the first paragraph and clears remaining text-frame paragraphs
- [x] 2.5 Implement text-frame append behavior for editable shapes and explicit `target not editable` rejection for non-text targets

## 3. Index And Service Integration

- [x] 3.1 Extend `indexing/store.py` so PPTX items can be upserted, replaced, and queried beside existing DOCX items
- [x] 3.2 Extend service-layer indexing and reindexing flows to handle `.pptx` files and directories containing PPTX files
- [x] 3.3 Add PPTX search and read workflows that return PPTX `SearchHit` and `ItemRef` data from the shared store
- [x] 3.4 Add PPTX locate flows for `--slide <n>` and optional `--shape <id>` resolution, including multiple results for slide-only lookups
- [x] 3.5 Add PPTX replace and append workflows that resolve one editable text-shape item before patching and reindex after the update

## 4. CLI Surface

- [x] 4.1 Extend `office-agent index` and `office-agent reindex` to accept `.pptx` inputs alongside the existing DOCX path
- [x] 4.2 Extend `office-agent search <query> [--type pptx] [--doc <file>]` for PPTX text-shape search results
- [x] 4.3 Extend `office-agent locate --doc <file> --slide <n> [--shape <id>]` for PPTX slide and shape lookup
- [x] 4.4 Ensure `office-agent read`, `replace`, and `append` support PPTX text-shape item ids and report non-editable targets clearly

## 5. Testing And Verification

- [x] 5.1 Add pytest coverage for PPTX extraction, metadata capture, newline-joined text-frame indexing, and non-text exclusion
- [x] 5.2 Add pytest coverage for PPTX search, locate, and read workflows, including slide-only locate returning multiple matches where applicable
- [x] 5.3 Add pytest coverage for PPTX replace and append patch operations, non-editable target rejection, and reopen verification
- [x] 5.4 Run the PPTX-focused pytest suite and verify the CLI commands satisfy the acceptance criteria with sample presentations
