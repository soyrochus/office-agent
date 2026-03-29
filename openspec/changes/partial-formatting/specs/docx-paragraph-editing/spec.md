## MODIFIED Requirements

### Requirement: Paragraph replacement
The system SHALL support replacing the full text of a resolved DOCX paragraph item while preserving paragraph-level properties, and it SHALL additionally support rewriting the paragraph from structured text segments when the caller uses the V2 object-mutation workflow.

#### Scenario: Replace updates the targeted paragraph
- **WHEN** a user runs `office-agent replace --doc <file> --item <item-id> --text "<text>"` for a DOCX paragraph item
- **THEN** the system overwrites the targeted paragraph text and preserves the first run's character formatting on the resulting paragraph content

#### Scenario: Segment-based replacement rebuilds paragraph runs
- **WHEN** a caller invokes `update_object` for a DOCX paragraph with ordered text segments
- **THEN** the system rewrites the paragraph as normalized DOCX runs that preserve the visible segment text while keeping the paragraph's style and paragraph-level formatting intact
