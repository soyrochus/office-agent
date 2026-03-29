# content-block-authoring Specification

## Purpose
TBD - created by archiving change document-creation-and-styling. Update Purpose after archive.
## Requirements
### Requirement: Add content block by format and block type
The system SHALL support adding a logical content block to an existing document via `add_content_block`, dispatching on a closed set of `(format, block_type)` pairs.

Supported pairs:

| format | block_type  |
|--------|-------------|
| docx   | paragraph   |
| docx   | heading     |
| docx   | table       |
| pptx   | slide       |
| pptx   | textbox     |
| xlsx   | sheet       |
| xlsx   | row         |
| xlsx   | cell        |

#### Scenario: Add a paragraph to a DOCX
- **WHEN** `add_content_block` is called with a DOCX `document_id`, `block_type="paragraph"`, and `text`
- **THEN** a new paragraph containing that text is appended to the document body

#### Scenario: Add a heading to a DOCX
- **WHEN** `add_content_block` is called with `block_type="heading"` and a `level` (1–9)
- **THEN** a new paragraph with the corresponding Word heading style (e.g. "Heading 1") is appended

#### Scenario: Add a table to a DOCX
- **WHEN** `add_content_block` is called with `block_type="table"`, `rows`, and `columns`
- **THEN** an empty table with the specified dimensions is appended to the document

#### Scenario: Add a slide to a PPTX
- **WHEN** `add_content_block` is called with a PPTX `document_id` and `block_type="slide"`
- **THEN** a new empty slide is appended to the presentation and its locator is returned

#### Scenario: Add a textbox to a PPTX
- **WHEN** `add_content_block` is called with `block_type="textbox"`, a `slide` locator, and `text`
- **THEN** a text shape containing that text is added to the specified slide

#### Scenario: Add a sheet to an XLSX
- **WHEN** `add_content_block` is called with an XLSX `document_id`, `block_type="sheet"`, and `name`
- **THEN** a new worksheet with the given name is added to the workbook

#### Scenario: Add a row to an XLSX sheet
- **WHEN** `add_content_block` is called with `block_type="row"`, a sheet locator, and `values`
- **THEN** the values are written to the next available row in that sheet

#### Scenario: Write a cell in an XLSX sheet
- **WHEN** `add_content_block` is called with `block_type="cell"`, a cell locator, and `value`
- **THEN** the specified cell is set to that value

### Requirement: Unsupported block_type for a format is rejected
The system SHALL fail clearly when a caller passes a `block_type` that is not valid for the document's format.

#### Scenario: PPTX rejects block_type="paragraph"
- **WHEN** `add_content_block` is called on a PPTX document with `block_type="paragraph"`
- **THEN** the system raises `InvalidArgumentsError` with a message naming the unsupported combination

#### Scenario: XLSX rejects block_type="slide"
- **WHEN** `add_content_block` is called on an XLSX document with `block_type="slide"`
- **THEN** the system raises `InvalidArgumentsError`

### Requirement: PPTX textbox accepts optional position and size
The system SHALL accept optional `left`, `top`, `width`, `height` parameters (in EMUs) for `block_type="textbox"`. When omitted, the system SHALL use sensible default dimensions that place the textbox in a readable central area of the slide.

#### Scenario: Textbox with explicit geometry
- **WHEN** `add_content_block` is called with `block_type="textbox"` and explicit `left`, `top`, `width`, `height`
- **THEN** the text shape is positioned at the specified coordinates

#### Scenario: Textbox with default geometry
- **WHEN** `add_content_block` is called with `block_type="textbox"` and no position/size arguments
- **THEN** the text shape is placed at a default central position with default dimensions and does not raise an error

### Requirement: add_content_block follows versioned-output and reindex flow
The system SHALL write the modified document to a versioned output path (or in-place if configured) and reindex it, returning a `MutationResult` with the locator of the newly added block.

#### Scenario: Returned locator targets the new block
- **WHEN** `add_content_block` succeeds
- **THEN** the `MutationResult.locator` is a valid canonical locator that resolves the newly created block in subsequent read or style operations

#### Scenario: Output document is reindexed
- **WHEN** `add_content_block` succeeds
- **THEN** the written output document is immediately reindexed without requiring a separate manual reindex

