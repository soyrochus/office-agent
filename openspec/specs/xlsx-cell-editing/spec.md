## Purpose

Define the xlsx-cell-editing capability for Office Agent.
## Requirements
### Requirement: XLSX cell value replacement
The system SHALL support writing a new value to a resolved XLSX cell item through `office-agent write-cell`, and it SHALL additionally support rewriting a supported string cell from structured text segments when the caller uses the V2 object-mutation workflow.

#### Scenario: Write-cell updates the targeted cell
- **WHEN** a user runs `office-agent write-cell --doc <file> --sheet <name> --cell <coordinate> --value "<value>"`
- **THEN** the system overwrites the targeted workbook cell with the provided value

#### Scenario: Segment-based replacement promotes a string cell to rich text
- **WHEN** a caller invokes `update_object` for a string-compatible XLSX cell with ordered text segments
- **THEN** the system rewrites the target cell as normalized rich text representing those segments instead of flattening them into one unformatted string

### Requirement: XLSX append for string-compatible cells
The system SHALL support appending text to a resolved XLSX cell item only when the existing cell is empty or contains a string-compatible value.

#### Scenario: Append adds text to a compatible cell
- **WHEN** a user runs `office-agent append --doc <file> --item <item-id> --text "<text>"` for an empty or string-valued XLSX cell
- **THEN** the system appends the provided text to that targeted cell content

### Requirement: Unsupported XLSX append targets are rejected
The system SHALL reject append operations for numeric or formula XLSX cells with an explicit error directing the user to `write-cell`.

#### Scenario: Append rejects a numeric or formula cell
- **WHEN** a user attempts to append text to a numeric cell or a formula cell in an XLSX workbook
- **THEN** the system fails the operation with an explicit message telling the user to use `write-cell`

### Requirement: XLSX edits use deterministic cell targets
The system SHALL apply write and append operations only after resolving the request to one concrete worksheet cell item.

#### Scenario: Cell edits target one resolved workbook cell
- **WHEN** a write-cell or append command is invoked for an indexed `.xlsx` workbook
- **THEN** the system applies the edit to exactly one resolved worksheet cell item rather than modifying unrelated workbook content

### Requirement: Edited XLSX content remains readable after patching
The system SHALL produce XLSX cell edits that can be reopened and verified after the operation completes.

#### Scenario: Reopening confirms the workbook cell patch
- **WHEN** an XLSX cell has been updated through `write-cell` or `append`
- **THEN** reopening the workbook confirms that the targeted cell contains the expected updated value

