# unified-structure-access Specification

## Purpose
TBD - created by archiving change tool-simplification. Update Purpose after archive.
## Requirements
### Requirement: get_structure returns a format-aware section outline
The system SHALL expose a `get_structure` tool that accepts a `document_id` and returns a flat list of top-level sections for the indexed document. The section type SHALL be determined by the document's `file_type` without requiring the caller to specify a format parameter. For DOCX, sections SHALL be ordered blocks (paragraphs and tables). For PPTX, sections SHALL be slides. For XLSX, sections SHALL be worksheets. Each section entry SHALL carry a `locator` that is valid as a `section_id` in `get_section`.

#### Scenario: DOCX structure lists ordered blocks with locators
- **WHEN** a caller invokes `get_structure` on an indexed DOCX document
- **THEN** the response contains one entry per block in document order, each with `locator`, `block_type` (`paragraph` or `table`), `preview`, and style metadata

#### Scenario: PPTX structure lists slides with locators
- **WHEN** a caller invokes `get_structure` on an indexed PPTX document
- **THEN** the response contains one entry per slide, each with `slide_number`, `locator`, and `preview`

#### Scenario: XLSX structure lists worksheets with locators
- **WHEN** a caller invokes `get_structure` on an indexed XLSX document
- **THEN** the response contains one entry per worksheet, each with `sheet_name`, `locator`, `preview`, and `cell_count`

#### Scenario: Section locators from get_structure are valid section_ids
- **WHEN** a caller passes a `locator` returned by `get_structure` as the `section_id` argument to `get_section`
- **THEN** `get_section` returns the full payload for that section without error

### Requirement: get_section returns the full semantic payload for one section
The system SHALL expose a `get_section` tool that accepts a `document_id` and a `section_id` (a locator) and returns the complete structured content of that section. The payload format SHALL be determined by the document's `file_type`. For a DOCX paragraph block, the payload SHALL include text, style, and run-level formatting. For a DOCX table block, the payload SHALL include rows as a list of lists of strings with cell metadata. For a PPTX slide, the payload SHALL include an ordered `text_blocks` list, `notes_text`, and layout metadata. For XLSX, the payload SHALL include `cells` with `coordinate`, `display_value`, `formula`, and metadata. `get_section` SHALL accept an optional `cell_range` parameter for XLSX to limit the snapshot window.

#### Scenario: DOCX paragraph section returns text and style metadata
- **WHEN** a caller invokes `get_section` with a DOCX paragraph block locator
- **THEN** the response includes the paragraph text, style name, and a list of runs with inline formatting attributes

#### Scenario: DOCX table section returns structured row data
- **WHEN** a caller invokes `get_section` with a DOCX table block locator
- **THEN** the response includes `rows` as a list of lists of strings and per-cell metadata

#### Scenario: PPTX slide section includes notes and text blocks
- **WHEN** a caller invokes `get_section` with a PPTX slide locator
- **THEN** the response includes an ordered `text_blocks` list for each text shape, a `notes_text` field, and layout metadata

#### Scenario: XLSX sheet section returns cell grid
- **WHEN** a caller invokes `get_section` with an XLSX worksheet locator
- **THEN** the response includes a `cells` list, each entry carrying `coordinate`, `display_value`, `formula`, and metadata

#### Scenario: XLSX cell_range limits the snapshot
- **WHEN** a caller invokes `get_section` on an XLSX worksheet with `cell_range="A1:D10"`
- **THEN** the response contains only cells within the specified range

#### Scenario: Node locators from get_section are valid node_ids
- **WHEN** a caller passes a leaf node locator from a `get_section` response to `get_node` or `write_node`
- **THEN** the tool resolves the node without error and returns or modifies the correct content

