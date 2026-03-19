## Purpose

Define the docx-paragraph-extraction capability for Office Agent.

## Requirements


### Requirement: DOCX paragraph extraction
The system SHALL extract paragraphs from `.docx` files in document order through a dedicated DOCX adapter using `python-docx`.

#### Scenario: Paragraphs are extracted in source order
- **WHEN** the system indexes a `.docx` file containing multiple paragraphs
- **THEN** it produces paragraph items in the same order they appear in the source document

### Requirement: Stable paragraph item identifiers
The system SHALL assign each extracted paragraph an item identifier in the format `para:{n}`, where `n` is the paragraph index in document order, including empty paragraphs.

#### Scenario: Empty paragraphs preserve index stability
- **WHEN** a `.docx` document contains empty paragraphs between non-empty paragraphs
- **THEN** the extracted item ids still reflect the original paragraph positions without collapsing the empty entries

### Requirement: Paragraph extraction metadata
The system SHALL record paragraph text, paragraph index, style name when available, and heading status for each extracted paragraph item.

#### Scenario: Style metadata is captured
- **WHEN** the DOCX adapter extracts a paragraph with an available style name
- **THEN** the indexed item includes the paragraph text, paragraph index, style name, and whether the style indicates a heading

### Requirement: Table content is excluded from paragraph extraction
The system SHALL ignore Word table cell content during paragraph extraction for this feature.

#### Scenario: Table cells are skipped
- **WHEN** a `.docx` file contains text inside table cells
- **THEN** that text does not appear as extracted paragraph items for indexing
