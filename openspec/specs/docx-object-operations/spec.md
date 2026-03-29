# docx-object-operations Specification

## Purpose
TBD - created by archiving change tools-v2. Update Purpose after archive.
## Requirements
### Requirement: DOCX object model
The system SHALL treat the following as first-class object types in DOCX documents, addressable by typed locators of the form `docx:<type>:<index>` or nested variants: `document`, `section`, `paragraph`, `run`, `table`, `table_row`, `table_cell`, `image`, `page_break`. Each type SHALL have a defined locator grammar and a defined property set.

#### Scenario: Agent resolves a DOCX paragraph by typed locator
- **WHEN** an MCP client calls `get_object` with a locator of the form `docx:para:N` for an indexed DOCX document
- **THEN** the server returns a structured paragraph object with text, style_name, is_heading, runs, and computed capabilities

#### Scenario: Agent resolves a nested DOCX table cell
- **WHEN** an MCP client calls `get_object` with a locator of the form `docx:table:T:row:R:cell:C`
- **THEN** the server returns a structured table cell object with its text content and capabilities

#### Scenario: Agent lists paragraphs in a DOCX document
- **WHEN** an MCP client calls `list_children` on a `docx:document` root locator with `child_type=paragraph`
- **THEN** the server returns an ordered list of paragraph object summaries for that document

### Requirement: DOCX paragraph style tool
The system SHALL expose a `docx_set_paragraph_style` escape hatch tool that applies a named paragraph style to an existing paragraph. The tool SHALL validate that the style name exists in the document's style catalog before writing.

#### Scenario: Agent applies a heading style
- **WHEN** an MCP client calls `docx_set_paragraph_style` with a valid paragraph locator and a style name present in the document
- **THEN** the server applies the style, writes the output, reindexes, and returns a mutation result

#### Scenario: Unknown style name rejected
- **WHEN** an MCP client calls `docx_set_paragraph_style` with a style name not present in the document
- **THEN** the server returns a ToolError without modifying the document

### Requirement: DOCX table creation tool
The system SHALL expose a `docx_add_table` escape hatch tool that inserts a new table with specified row and column counts at a given position. The tool SHALL accept optional column widths and a table style name.

#### Scenario: Agent inserts a table
- **WHEN** an MCP client calls `docx_add_table` with a target document, row count, column count, and optional position
- **THEN** the server inserts the table at the specified position in the document body, writes the output, reindexes, and returns a mutation result with the new table's locator

### Requirement: DOCX page break insertion tool
The system SHALL expose a `docx_insert_page_break` escape hatch tool that inserts a page break at a specified paragraph position.

#### Scenario: Agent inserts a page break
- **WHEN** an MCP client calls `docx_insert_page_break` with a valid position locator
- **THEN** the server inserts a page break paragraph at that position, writes the output, reindexes, and returns a mutation result

### Requirement: DOCX table cell merge tool
The system SHALL expose a `docx_merge_table_cells` escape hatch tool that merges a rectangular range of cells within a table.

#### Scenario: Agent merges table cells
- **WHEN** an MCP client calls `docx_merge_table_cells` with valid start and end cell locators within the same table
- **THEN** the server merges the specified cell range, writes the output, reindexes, and returns a mutation result

#### Scenario: Non-rectangular merge rejected
- **WHEN** an MCP client calls `docx_merge_table_cells` with cell locators that do not form a valid rectangular range
- **THEN** the server returns a ToolError without modifying the document

