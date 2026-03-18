## ADDED Requirements

### Requirement: XLSX cell extraction
The system SHALL extract non-empty cells from `.xlsx` workbooks across all worksheets through a dedicated XLSX adapter using `openpyxl`.

#### Scenario: Cells are extracted from each worksheet
- **WHEN** the system indexes an `.xlsx` workbook containing populated cells on multiple worksheets
- **THEN** it produces indexed cell items for the non-empty cells from every worksheet in that workbook

### Requirement: Stable XLSX cell item identifiers
The system SHALL assign each extracted cell an item identifier in the format `sheet:{sheet_name}!{coordinate}`.

#### Scenario: A cell item id matches its worksheet and coordinate
- **WHEN** the XLSX adapter extracts cell `B12` from worksheet `Budget2026`
- **THEN** the indexed item id is `sheet:Budget2026!B12`

### Requirement: XLSX cell extraction metadata
The system SHALL record worksheet name, cell coordinate, raw value, formula text when present, and a stringified display value for each extracted cell item.

#### Scenario: Formula metadata is captured for a formula cell
- **WHEN** the XLSX adapter extracts a cell containing a formula
- **THEN** the indexed item includes the worksheet name, coordinate, formula text, and the text payload used for indexing

### Requirement: Empty worksheet cells are excluded from extraction
The system SHALL not create indexed items for worksheet cells that have neither a value nor a formula.

#### Scenario: Empty cells are skipped
- **WHEN** a workbook contains blank cells between populated cells
- **THEN** those blank cells do not appear as extracted XLSX cell items
