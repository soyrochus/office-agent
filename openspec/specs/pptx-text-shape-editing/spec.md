## Purpose

Define the pptx-text-shape-editing capability for Office Agent.

## Requirements


### Requirement: PPTX text-frame replace
The system SHALL support replacing the full text-frame content of a resolved PPTX text-bearing shape item.

#### Scenario: Replace overwrites the text frame
- **WHEN** a user runs `office-agent replace --doc <file> --item <item-id> --text "<text>"` for a PPTX text-bearing shape
- **THEN** the system replaces the shape text frame content by setting the new text on the first paragraph and clearing remaining paragraph content

### Requirement: PPTX text-frame append
The system SHALL support appending plain text to the existing text-frame content of a resolved PPTX text-bearing shape item.

#### Scenario: Append extends the text frame
- **WHEN** a user runs `office-agent append --doc <file> --item <item-id> --text "<text>"` for a PPTX text-bearing shape
- **THEN** the system adds the provided text to the existing text-frame content

### Requirement: Non-editable shape rejection
The system SHALL reject write attempts for PowerPoint targets that do not have text frames with the error `target not editable`.

#### Scenario: Non-text shape write is rejected
- **WHEN** a write operation targets a PowerPoint shape without a text frame
- **THEN** the system fails the operation with `target not editable`

### Requirement: Text-shape edits target one resolved item
The system SHALL apply replace and append operations only after resolving the request to one concrete PPTX text-bearing shape item.

#### Scenario: Edit operations are deterministic
- **WHEN** a replace or append command is invoked for a PPTX presentation
- **THEN** the system applies the edit to exactly one resolved text-bearing shape item rather than rewriting unrelated slide content

### Requirement: Edited PPTX content remains readable after patching
The system SHALL produce PPTX text-frame edits that can be reopened and verified after the operation completes.

#### Scenario: Reopening confirms the shape patch
- **WHEN** a PPTX text-bearing shape has been replaced or appended through the system
- **THEN** reopening the presentation confirms that the targeted shape contains the expected updated text
