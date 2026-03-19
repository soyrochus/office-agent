## Purpose

Define the document-summary-commands capability for Office Agent.

## Requirements


### Requirement: Indexed document listing
The system SHALL expose `office-agent list` to return all indexed documents with document id, path, file type, modified time, and indexed item count.

#### Scenario: List shows indexed document summaries
- **WHEN** a user runs `office-agent list` after indexing one or more supported Office documents
- **THEN** the command returns one summary entry per indexed document including its id, path, type, modified time, and item count

### Requirement: Document summary command
The system SHALL expose `office-agent show --doc <file>` to return a summary of one indexed document, including its metadata and indexed item count.

#### Scenario: Show returns one document summary
- **WHEN** a user runs `office-agent show --doc <file>` for an indexed Office document
- **THEN** the command returns the indexed summary for that document rather than requiring a search or direct item read

### Requirement: Item detail command
The system SHALL support `office-agent show --doc <file> --item <item-id>` to return detailed information for one indexed item in that document.

#### Scenario: Show returns item details
- **WHEN** a user runs `office-agent show --doc <file> --item <item-id>` for an indexed item
- **THEN** the command returns the item metadata and content summary for that exact indexed item
