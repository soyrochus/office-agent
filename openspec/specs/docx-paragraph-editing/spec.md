## Purpose

Define the docx-paragraph-editing capability for Office Agent.
## Requirements
### Requirement: Paragraph replacement
The system SHALL support replacing the full text of a resolved DOCX paragraph item while preserving paragraph-level properties, and it SHALL additionally support rewriting the paragraph from structured text segments when the caller uses the V2 object-mutation workflow.

#### Scenario: Replace updates the targeted paragraph
- **WHEN** a user runs `office-agent replace --doc <file> --item <item-id> --text "<text>"` for a DOCX paragraph item
- **THEN** the system overwrites the targeted paragraph text and preserves the first run's character formatting on the resulting paragraph content

#### Scenario: Segment-based replacement rebuilds paragraph runs
- **WHEN** a caller invokes `update_object` for a DOCX paragraph with ordered text segments
- **THEN** the system rewrites the paragraph as normalized DOCX runs that preserve the visible segment text while keeping the paragraph's style and paragraph-level formatting intact

### Requirement: Paragraph append
The system SHALL support appending text to the last run of a resolved DOCX paragraph item.

#### Scenario: Append adds text to the targeted paragraph
- **WHEN** a user runs `office-agent append --doc <file> --item <item-id> --text "<text>"` for a DOCX paragraph item
- **THEN** the system adds the provided text to the end of the targeted paragraph content

### Requirement: Paragraph edits use deterministic item targets
The system SHALL apply replace and append operations only after resolving the target to a concrete DOCX paragraph item.

#### Scenario: Edit operations target one resolved paragraph
- **WHEN** a replace or append command is invoked for a DOCX document
- **THEN** the system applies the edit to exactly one resolved paragraph item rather than rewriting unrelated document content

### Requirement: Edited DOCX content remains readable after patching
The system SHALL produce DOCX paragraph edits that can be reopened and verified after the operation completes.

#### Scenario: Reopening confirms the paragraph patch
- **WHEN** a DOCX paragraph has been replaced or appended through the system
- **THEN** reopening the document confirms that the targeted paragraph contains the expected updated text

