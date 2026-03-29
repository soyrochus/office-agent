# partial-inline-formatting Specification

## Purpose
TBD - created by archiving change partial-formatting. Update Purpose after archive.
## Requirements
### Requirement: Inline formatting can target visible-text ranges within a text-bearing object
The system SHALL allow partial inline formatting to target either an existing inline locator or a parent text-bearing object plus a character range expressed against the target object's logical visible text.

#### Scenario: Style an existing inline locator
- **WHEN** a caller invokes `style_inline` with a resolved inline child locator such as a DOCX run
- **THEN** the system applies the requested inline style to that inline target using the existing locator semantics

#### Scenario: Style a parent object by visible-text range
- **WHEN** a caller invokes `style_inline` with a parent text-bearing object locator and a character range
- **THEN** the system resolves the range against the object's logical visible text and applies the requested inline style only to the characters inside that range

### Requirement: Text-bearing objects can be rewritten from structured inline segments
The system SHALL allow text-bearing object mutations to provide structured text segments so adapters can rebuild native inline structure deterministically instead of depending on pre-existing runs.

#### Scenario: Replace a text object with structured segments
- **WHEN** a caller invokes `update_object` for a supported text-bearing object with `segments`
- **THEN** the system rewrites that object from the provided ordered segments and preserves the resulting visible text and segment formatting

#### Scenario: Create a text-bearing object with structured segments
- **WHEN** a caller invokes `create_object` for a supported text-bearing object type with `segments`
- **THEN** the system creates the object with native inline structure derived from those segments rather than flattening them into one unformatted text run

### Requirement: Fragment rewrites are normalized after every partial-formatting mutation
The system SHALL normalize rewritten inline content after every segment-based or range-based partial-formatting mutation by merging adjacent fragments with equivalent formatting.

#### Scenario: Adjacent equivalent fragments are merged
- **WHEN** a partial-formatting mutation produces neighboring fragments with identical effective inline formatting
- **THEN** the system merges those fragments before writing the final native structure

### Requirement: Partial-formatting scope is one logical text container per mutation
The system SHALL resolve each partial-formatting mutation to exactly one logical text container.

#### Scenario: A partial-formatting mutation does not span multiple containers
- **WHEN** a caller requests partial formatting across content that would cross paragraph, shape, or cell boundaries
- **THEN** the system rejects the mutation instead of applying one range across multiple logical text containers

### Requirement: Unsupported partial-formatting targets fail clearly
The system SHALL reject partial-formatting requests when the resolved target cannot safely support range-based or segment-based inline rewriting.

#### Scenario: Unsupported XLSX target is rejected
- **WHEN** a caller requests partial inline formatting for an XLSX formula, numeric cell, or other unsupported non-string cell target
- **THEN** the system fails the mutation with an explicit error and does not rewrite the workbook

#### Scenario: Non-text target is rejected
- **WHEN** a caller requests partial inline formatting for a resolved object that is not a supported text-bearing container
- **THEN** the system fails the mutation with an explicit target-validation error

