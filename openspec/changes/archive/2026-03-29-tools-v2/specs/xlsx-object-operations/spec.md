## ADDED Requirements

### Requirement: XLSX object model
The system SHALL treat the following as first-class object types in XLSX workbooks, addressable by typed locators: `workbook`, `worksheet` (`xlsx:sheet:<Name>`), `row` (`xlsx:sheet:<Name>:row:<N>`), `column` (`xlsx:sheet:<Name>:col:<N>`), `cell` (`xlsx:sheet:<Name>!<A1>`), `range` (`xlsx:sheet:<Name>!<A1>:<Z99>`), `table`, `merged_range`, `formula_cell`, `named_range`. Each type SHALL have a defined locator grammar and a defined property set.

#### Scenario: Agent resolves a worksheet by typed locator
- **WHEN** an MCP client calls `get_object` with a locator of the form `xlsx:sheet:SheetName` for an indexed XLSX document
- **THEN** the server returns a structured worksheet object with sheet name, dimensions, row count, column count, and computed capabilities

#### Scenario: Agent resolves a cell by typed locator
- **WHEN** an MCP client calls `get_object` with a locator of the form `xlsx:sheet:SheetName!B12`
- **THEN** the server returns a structured cell object with value, data type, formula (if any), and capabilities

#### Scenario: Agent lists rows in a worksheet
- **WHEN** an MCP client calls `list_children` on a worksheet locator with `child_type=row`
- **THEN** the server returns an ordered list of row summaries for that worksheet

### Requirement: XLSX range write tool
The system SHALL expose an `xlsx_write_range` escape hatch tool that writes a two-dimensional array of values to a specified cell range in a worksheet.

#### Scenario: Agent writes a value grid to a range
- **WHEN** an MCP client calls `xlsx_write_range` with a valid range locator and a matching 2D value array
- **THEN** the server writes the values to the specified range, writes the output, reindexes, and returns a mutation result

#### Scenario: Mismatched array dimensions rejected
- **WHEN** an MCP client calls `xlsx_write_range` with a value array whose dimensions do not match the specified range
- **THEN** the server returns a ToolError without modifying the workbook

### Requirement: XLSX row and column insertion tools
The system SHALL expose `xlsx_insert_rows` and `xlsx_insert_columns` escape hatch tools that insert one or more rows or columns at a specified position in a worksheet, shifting existing content.

#### Scenario: Agent inserts rows
- **WHEN** an MCP client calls `xlsx_insert_rows` with a worksheet locator, a row number, and a count
- **THEN** the server inserts the specified number of rows at that position, writes the output, reindexes, and returns a mutation result

#### Scenario: Agent inserts columns
- **WHEN** an MCP client calls `xlsx_insert_columns` with a worksheet locator, a column index, and a count
- **THEN** the server inserts the specified number of columns at that position, writes the output, reindexes, and returns a mutation result

### Requirement: XLSX formula write tool
The system SHALL expose an `xlsx_set_formula` escape hatch tool that writes a formula string to a specified cell.

#### Scenario: Agent writes a formula
- **WHEN** an MCP client calls `xlsx_set_formula` with a valid cell locator and a formula string
- **THEN** the server writes the formula to the cell, writes the output, reindexes, and returns a mutation result

#### Scenario: Invalid formula syntax rejected
- **WHEN** an MCP client calls `xlsx_set_formula` with a formula string that fails format validation
- **THEN** the server returns a ToolError without modifying the workbook

### Requirement: XLSX cell merge tool
The system SHALL expose an `xlsx_merge_cells` escape hatch tool that merges a rectangular cell range in a worksheet.

#### Scenario: Agent merges a cell range
- **WHEN** an MCP client calls `xlsx_merge_cells` with a valid range locator
- **THEN** the server merges the cells in that range, writes the output, reindexes, and returns a mutation result

#### Scenario: Already-merged range rejected
- **WHEN** an MCP client calls `xlsx_merge_cells` with a range that overlaps an existing merged region
- **THEN** the server returns a ToolError without modifying the workbook
