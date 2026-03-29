## MODIFIED Requirements

### Requirement: XLSX cell value replacement
The system SHALL support writing a new value to a resolved XLSX cell item through `office-agent write-cell`, and it SHALL additionally support rewriting a supported string cell from structured text segments when the caller uses the V2 object-mutation workflow.

#### Scenario: Write-cell updates the targeted cell
- **WHEN** a user runs `office-agent write-cell --doc <file> --sheet <name> --cell <coordinate> --value "<value>"`
- **THEN** the system overwrites the targeted workbook cell with the provided value

#### Scenario: Segment-based replacement promotes a string cell to rich text
- **WHEN** a caller invokes `update_object` for a string-compatible XLSX cell with ordered text segments
- **THEN** the system rewrites the target cell as normalized rich text representing those segments instead of flattening them into one unformatted string
