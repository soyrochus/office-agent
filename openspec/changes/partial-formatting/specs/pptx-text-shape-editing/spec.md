## MODIFIED Requirements

### Requirement: PPTX text-frame replace
The system SHALL support replacing the full text-frame content of a resolved PPTX text-bearing shape item, and it SHALL additionally support rewriting a supported text paragraph from structured text segments when the caller uses the V2 object-mutation workflow.

#### Scenario: Replace overwrites the text frame
- **WHEN** a user runs `office-agent replace --doc <file> --item <item-id> --text "<text>"` for a PPTX text-bearing shape
- **THEN** the system replaces the shape text frame content by setting the new text on the first paragraph and clearing remaining paragraph content

#### Scenario: Segment-based replacement rebuilds PPTX runs
- **WHEN** a caller invokes `update_object` for a supported PPTX text paragraph with ordered text segments
- **THEN** the system rewrites that paragraph as normalized PPTX runs while preserving the containing paragraph properties and shape structure
