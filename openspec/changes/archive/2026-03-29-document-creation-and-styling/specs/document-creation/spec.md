## ADDED Requirements

### Requirement: Create empty document by format
The system SHALL create a new empty document file for a caller-specified format (docx, pptx, xlsx) at a caller-specified output path, without requiring an existing document to be registered first.

#### Scenario: Create an empty DOCX
- **WHEN** a caller invokes `create_document` with `format="docx"` and a valid output path
- **THEN** a new well-formed DOCX file is written to that path and registered in the index

#### Scenario: Create an empty PPTX
- **WHEN** a caller invokes `create_document` with `format="pptx"` and a valid output path
- **THEN** a new well-formed PPTX file is written to that path and registered in the index

#### Scenario: Create an empty XLSX
- **WHEN** a caller invokes `create_document` with `format="xlsx"` and a valid output path
- **THEN** a new well-formed XLSX file is written to that path and registered in the index

### Requirement: Created document includes standard default structure
The system SHALL initialize created documents with the format's minimum required default structure so that subsequent operations can target valid locations immediately.

#### Scenario: New DOCX includes standard Word styles
- **WHEN** a new DOCX is created
- **THEN** the document's style catalog includes the standard Word named styles (Normal, Heading 1–9, Title, Caption, etc.) so that `set_structural_role` can be applied without style-not-found errors

#### Scenario: New PPTX includes a slide layout master
- **WHEN** a new PPTX is created
- **THEN** the presentation contains at least one slide layout master so that slides can be added to it

#### Scenario: New XLSX includes a default sheet
- **WHEN** a new XLSX is created without specifying an initial sheet name
- **THEN** the workbook contains exactly one sheet named "Sheet1"

#### Scenario: New XLSX respects optional initial sheet name
- **WHEN** a new XLSX is created with `initial_sheet_name` specified
- **THEN** the workbook contains exactly one sheet with that name

### Requirement: Created document is registered in the index
The system SHALL register the newly created document in the local index immediately after writing it, making it addressable by `document_id` in subsequent tool calls.

#### Scenario: create_document returns a usable document_id
- **WHEN** `create_document` succeeds
- **THEN** the returned `MutationResult` contains a `document_id` that resolves in subsequent calls such as `add_content_block` or `style_inline`

### Requirement: create_document output path is policy-checked
The system SHALL validate the output path for a new document against the configured path policy before writing.

#### Scenario: Output path outside allowed roots is rejected
- **WHEN** a caller specifies an output path that is not within any configured allowed root
- **THEN** the system raises a policy error and does not create the file

### Requirement: create_document respects output_mode
The system SHALL support the same `output_mode` parameter as other write operations, applying versioned-output naming when `output_mode="versioned"`.

#### Scenario: Versioned output mode produces a timestamped filename
- **WHEN** `create_document` is called with `output_mode="versioned"` and a base output path
- **THEN** the actual written path follows the `<name>.edited.<timestamp>.<ext>` convention

#### Scenario: In-place output mode writes to the exact path specified
- **WHEN** `create_document` is called with `output_mode="inplace"` and `allow_inplace_overwrite` is enabled
- **THEN** the file is written to the exact output path without timestamp decoration

### Requirement: Unsupported format values are rejected
The system SHALL fail clearly when `format` is not one of "docx", "pptx", "xlsx".

#### Scenario: Invalid format string is rejected
- **WHEN** a caller passes an unrecognised format string (e.g. "pdf")
- **THEN** the system raises an `InvalidArgumentsError` before attempting any file write
