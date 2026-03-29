## ADDED Requirements

### Requirement: Map a DOCX block to a structural role
The system SHALL assign a Word-native paragraph style to a DOCX block via `set_structural_role`, using a closed set of role names that map to standard Word styles.

Supported role → Word style mapping:

| role          | Word style    |
|---------------|---------------|
| heading       | Heading {level} (requires `level` 1–9) |
| title         | Title         |
| body          | Normal        |
| table_header  | Table Heading |
| caption       | Caption       |

#### Scenario: Set heading role with level
- **WHEN** `set_structural_role` is called with `role="heading"` and `level=2` on a DOCX paragraph locator
- **THEN** the paragraph's style is set to "Heading 2"

#### Scenario: Set title role
- **WHEN** `set_structural_role` is called with `role="title"` on a DOCX paragraph locator
- **THEN** the paragraph's style is set to "Title"

#### Scenario: Set body role
- **WHEN** `set_structural_role` is called with `role="body"` on a DOCX paragraph locator
- **THEN** the paragraph's style is set to "Normal"

#### Scenario: Set table_header role
- **WHEN** `set_structural_role` is called with `role="table_header"` on a DOCX paragraph locator
- **THEN** the paragraph's style is set to "Table Heading"

#### Scenario: Set caption role
- **WHEN** `set_structural_role` is called with `role="caption"` on a DOCX paragraph locator
- **THEN** the paragraph's style is set to "Caption"

### Requirement: heading role requires a level parameter
The system SHALL require a `level` integer (1–9) when `role="heading"` and SHALL reject the call if `level` is absent or out of range.

#### Scenario: Heading role without level is rejected
- **WHEN** `set_structural_role` is called with `role="heading"` and no `level`
- **THEN** the system raises `InvalidArgumentsError`

#### Scenario: Heading role with level out of range is rejected
- **WHEN** `set_structural_role` is called with `role="heading"` and `level=10`
- **THEN** the system raises `InvalidArgumentsError`

### Requirement: set_structural_role is DOCX-only
The system SHALL raise `InvalidArgumentsError` when `set_structural_role` is called on a PPTX or XLSX document.

#### Scenario: PPTX document is rejected
- **WHEN** `set_structural_role` is called with a PPTX `document_id`
- **THEN** the system raises `InvalidArgumentsError` with a message stating the operation is only supported for DOCX

#### Scenario: XLSX document is rejected
- **WHEN** `set_structural_role` is called with an XLSX `document_id`
- **THEN** the system raises `InvalidArgumentsError` with a message stating the operation is only supported for DOCX

### Requirement: Unsupported role names are rejected
The system SHALL reject any `role` value not in the supported set.

#### Scenario: Unknown role string is rejected
- **WHEN** `set_structural_role` is called with `role="footnote"` (or any other unsupported string)
- **THEN** the system raises `InvalidArgumentsError` before modifying the document

### Requirement: Target Word style must exist in the document's style catalog
The system SHALL raise `TargetNotEditableError` if the mapped Word style is not present in the document's style catalog.

#### Scenario: Missing style raises a clear error
- **WHEN** `set_structural_role` is called and the mapped Word style (e.g. "Table Heading") does not exist in the document
- **THEN** the system raises `TargetNotEditableError` naming the missing style

### Requirement: set_structural_role follows versioned-output and reindex flow
The system SHALL write to a versioned output (or in-place) and reindex after every successful `set_structural_role` call.

#### Scenario: Output is reindexed after structural role applied
- **WHEN** `set_structural_role` succeeds
- **THEN** the output document is immediately reindexed and the `MutationResult` identifies the output path and the updated locator
