## Purpose

Define the contract for XLSX sheet snapshot inspection and structured row and table write tools that operate on worksheets within indexed workbooks.

## Requirements

### Requirement: Sheet snapshot retrieval
The system SHALL expose `get_sheet_snapshot` for indexed XLSX documents. The response SHALL return a deterministic sheet snapshot for the requested worksheet, preserving row-major order and including coordinates and display values for the returned cells. The tool SHALL support an optional range or window input that limits the snapshot scope.

#### Scenario: Client retrieves a sheet snapshot window
- **WHEN** an MCP client calls `get_sheet_snapshot` for an indexed workbook sheet with a bounded range or window
- **THEN** the server returns the requested cells in row-major order with their coordinates and current display values

### Requirement: Row append writes one logical row
The system SHALL expose `append_row` for indexed XLSX documents. The tool SHALL append one logical row to the requested worksheet using either ordered values or mapped values, and it SHALL return a structured write result that identifies the output workbook path and the appended row location.

#### Scenario: Client appends a row to a worksheet
- **WHEN** an MCP client calls `append_row` with values for a target sheet in an indexed workbook
- **THEN** the server writes one new row after the current table or used range and returns a structured write result describing the appended row

### Requirement: Structured table writes support mapped records
The system SHALL expose `write_table` for indexed XLSX documents. The tool SHALL write a list of structured rows to a worksheet using either explicit column mapping or deterministic header-based mapping when the target sheet structure supports it.

#### Scenario: Client writes structured records into a worksheet
- **WHEN** an MCP client calls `write_table` with multiple rows and an explicit mapping configuration
- **THEN** the server writes the rows to the target worksheet deterministically and returns a structured write result for the produced workbook output
