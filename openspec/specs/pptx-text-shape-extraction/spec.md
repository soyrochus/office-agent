## Purpose

Define the pptx-text-shape-extraction capability for Office Agent.

## Requirements


### Requirement: PPTX text-shape extraction
The system SHALL extract searchable items from `.pptx` files by traversing slides and selecting only shapes where `has_text_frame` is true.

#### Scenario: Only text-bearing shapes are extracted
- **WHEN** the system indexes a presentation containing both text-bearing and non-text shapes
- **THEN** it creates indexed items only for shapes with text frames

### Requirement: Stable PPTX shape item identifiers
The system SHALL assign each extracted text-bearing shape an item identifier in the format `slide:{slide_number}:shape:{shape_id}`.

#### Scenario: Item ids reflect slide and shape identity
- **WHEN** a presentation contains editable text shapes across multiple slides
- **THEN** each extracted item id encodes the slide number and PowerPoint shape id for that text-bearing shape

### Requirement: PPTX shape metadata capture
The system SHALL record slide number, shape id, shape index, shape name when available, text-frame text, and placeholder status for each extracted text-bearing shape.

#### Scenario: Shape metadata is indexed with extracted content
- **WHEN** the PPTX adapter extracts a text-bearing shape
- **THEN** the indexed item includes its slide number, shape id, shape index, shape name if present, text-frame text, and placeholder flag

### Requirement: Text-frame paragraphs are concatenated for indexing
The system SHALL concatenate text-frame paragraph content with newline separators when producing the indexed text for a PPTX text-bearing shape.

#### Scenario: Multi-paragraph text frames retain readable structure
- **WHEN** a text-bearing shape contains multiple paragraphs in its text frame
- **THEN** the indexed text preserves their order using newline separators
