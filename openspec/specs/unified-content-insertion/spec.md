# unified-content-insertion Specification

## Purpose
TBD - created by archiving change tool-simplification. Update Purpose after archive.
## Requirements
### Requirement: insert_content appends a new paragraph to a DOCX document
The system SHALL expose an `insert_content` tool that accepts a `document_id` and a `content` string and inserts a new paragraph into the target DOCX document. The tool SHALL accept an optional `style_name` (DOCX paragraph style, e.g., `"Heading 2"`), an optional `after_node_id` locator (insert after this node; default is end of document), and an optional `output_mode` (`"versioned"` or `"inplace"`, defaulting to `"versioned"`). The response SHALL include `output_path`, `new_node_id`, and `preview`. `insert_content` SHALL only operate on DOCX documents; calls against PPTX or XLSX SHALL fail with an explicit error indicating the format is not supported.

#### Scenario: insert_content appends a paragraph at the end of a DOCX document
- **WHEN** a caller invokes `insert_content` on an indexed DOCX document with `content` and no `after_node_id`
- **THEN** a new paragraph containing the content is appended at the end of the output document and `new_node_id` in the response is a valid locator for the new paragraph

#### Scenario: insert_content inserts a paragraph after a specific node
- **WHEN** a caller invokes `insert_content` with an `after_node_id` pointing to an existing DOCX paragraph
- **THEN** the new paragraph appears immediately after that node in the output document

#### Scenario: insert_content applies the requested paragraph style
- **WHEN** a caller invokes `insert_content` with `style_name="Heading 2"`
- **THEN** the new paragraph in the output document has the `Heading 2` style applied

#### Scenario: insert_content fails explicitly for non-DOCX documents
- **WHEN** a caller invokes `insert_content` on a PPTX or XLSX document
- **THEN** the tool returns an error that identifies the document format and states that `insert_content` only supports DOCX

### Requirement: xlsx_insert_rows appends rows to an XLSX worksheet atomically
The system SHALL expose an `xlsx_insert_rows` tool that accepts a `document_id`, a `sheet_name`, and either a `rows` parameter (list of positional string lists) or a `records` parameter (list of column-mapped string dicts), and appends the rows to the specified worksheet in a single atomic operation. The tool SHALL accept an optional `output_mode`. The response SHALL include `output_path`, `rows_inserted`, and `first_row_locator`. The tool SHALL re-index the output document once after all rows are inserted, not once per row. `xlsx_insert_rows` SHALL only operate on XLSX documents.

#### Scenario: xlsx_insert_rows appends positional rows
- **WHEN** a caller invokes `xlsx_insert_rows` with `rows=[["A", "B"], ["C", "D"]]` on a valid worksheet
- **THEN** the two rows are appended to the worksheet in order and `rows_inserted` in the response equals 2

#### Scenario: xlsx_insert_rows appends column-mapped records
- **WHEN** a caller invokes `xlsx_insert_rows` with `records=[{"Name": "Alice", "Score": "95"}]` on a valid worksheet
- **THEN** the record is appended as a row with values placed in the columns matching the dict keys

#### Scenario: xlsx_insert_rows triggers a single reindex after all inserts
- **WHEN** a caller invokes `xlsx_insert_rows` with multiple rows
- **THEN** the output document is indexed exactly once after all rows are written, and `first_row_locator` is a valid node_id for the first inserted cell

#### Scenario: xlsx_insert_rows fails explicitly for non-XLSX documents
- **WHEN** a caller invokes `xlsx_insert_rows` on a DOCX or PPTX document
- **THEN** the tool returns an error that identifies the document format and states that `xlsx_insert_rows` only supports XLSX

### Requirement: docx_get_tables returns all DOCX tables as structured arrays
The system SHALL expose a `docx_get_tables` tool that accepts a `document_id` and returns all tables in the document as structured arrays in a single call. Each table entry SHALL include a `locator`, a `table_index`, `rows` as a list of lists of strings, and a `preview`. `docx_get_tables` SHALL only operate on DOCX documents and SHALL fail explicitly for PPTX or XLSX.

#### Scenario: docx_get_tables returns all tables in a DOCX document
- **WHEN** a caller invokes `docx_get_tables` on an indexed DOCX document containing multiple tables
- **THEN** the response includes one entry per table, each with `locator`, `table_index`, `rows`, and `preview`

#### Scenario: docx_get_tables table locators are valid node_ids
- **WHEN** a caller passes the `locator` from a `docx_get_tables` entry to `get_section`
- **THEN** `get_section` returns the structured row data for that table block without error

#### Scenario: docx_get_tables fails explicitly for non-DOCX documents
- **WHEN** a caller invokes `docx_get_tables` on a PPTX or XLSX document
- **THEN** the tool returns an error that identifies the document format and states that `docx_get_tables` only supports DOCX

