## ADDED Requirements

### Requirement: XLSX item indexing
The system SHALL persist extracted XLSX cell items in the local index so search, locate, and read workflows operate on indexed cell metadata rather than scanning workbooks at query time.

#### Scenario: Indexed XLSX cells are stored for later query
- **WHEN** a user runs `office-agent index` on an `.xlsx` file or a directory containing `.xlsx` files
- **THEN** the system stores workbook metadata and extracted cell items for those files in the local index

### Requirement: XLSX cell search
The system SHALL support searching indexed XLSX cell content and return matching cell hits with score, locator, preview, and workbook context.

#### Scenario: Search returns the matching cell
- **WHEN** a user runs `office-agent search "known text" --type xlsx` for content contained in an indexed workbook cell
- **THEN** the system returns the corresponding cell hit with its sheet-and-cell locator and preview text

### Requirement: Direct XLSX cell location
The system SHALL resolve `office-agent locate --doc <file> --sheet <name> --cell <coordinate>` to the cell `ItemRef` for the requested indexed workbook cell.

#### Scenario: Locate resolves a worksheet cell reference
- **WHEN** a user locates worksheet `Sheet1` cell `B12` from an indexed `.xlsx` file
- **THEN** the system returns the `ItemRef` for `sheet:Sheet1!B12` from that workbook

### Requirement: XLSX cell read
The system SHALL read the current source value for a resolved XLSX cell item from the workbook file.

#### Scenario: Read returns the current cell content
- **WHEN** a user runs `office-agent read --doc <file> --item <item-id>` for an existing XLSX cell item
- **THEN** the system returns the current value of that source workbook cell

### Requirement: Forced XLSX reindex
The system SHALL support reindexing a specific XLSX file to refresh stored cell items after the workbook changes.

#### Scenario: Reindex refreshes stored cell content
- **WHEN** a user runs `office-agent reindex <path>` for a changed `.xlsx` file
- **THEN** the system replaces the stored cell items for that workbook with the newly extracted set
