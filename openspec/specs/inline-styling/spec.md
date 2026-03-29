# inline-styling Specification

## Purpose
TBD - created by archiving change document-creation-and-styling. Update Purpose after archive.
## Requirements
### Requirement: Set inline style properties on a targeted element
The system SHALL set character-level style properties on a targeted run, cell, or text element via `style_inline`, using patch semantics: each property present in the request is written directly; properties absent from the request are left unchanged.

#### Scenario: Set bold on a DOCX run
- **WHEN** `style_inline` is called with a `docx:para:{n}:run:{n}` locator and `bold=true`
- **THEN** the targeted run's bold property is set to true and all other run properties are unchanged

#### Scenario: Set font name and size on a PPTX run
- **WHEN** `style_inline` is called with a `pptx:slide:{n}:shape:{n}` locator targeting a run and `font_name` and `font_size`
- **THEN** the targeted run's font name and size are updated; all other run properties are unchanged

#### Scenario: Set font color on an XLSX cell
- **WHEN** `style_inline` is called with an `xlsx:sheet:{name}!{ref}` locator and `font_color`
- **THEN** the cell's font color is updated to the specified hex RGB value

### Requirement: InlineStyle schema is explicit and bounded
The system SHALL accept inline style requests conforming to a fixed `InlineStyle` schema. Unknown fields SHALL be rejected.

Supported properties:
- `bold` (bool)
- `italic` (bool)
- `underline` (bool)
- `strike` (bool)
- `font_name` (string)
- `font_size` (number, in points)
- `font_color` (string, hex RGB e.g. "FF0000")
- `highlight` (string, color name; DOCX only — ignored with a warning on other formats)

#### Scenario: Unknown style field is rejected
- **WHEN** `style_inline` is called with a property not in the InlineStyle schema (e.g. `shadow=true`)
- **THEN** the system raises `InvalidArgumentsError` and does not modify the document

### Requirement: Explicit null in clear_fields reverts a property to inherited
The system SHALL accept an optional `clear_fields` list alongside the style object. For each field name in `clear_fields`, the system SHALL set that property to the library's inherited/unset value (e.g. `run.bold = None` in python-docx), regardless of any value supplied in the style object for the same field.

#### Scenario: Clear bold back to inherited
- **WHEN** `style_inline` is called with `clear_fields=["bold"]`
- **THEN** the targeted element's bold property is set to None (inherited from paragraph/theme), not True or False

#### Scenario: clear_fields and style object are applied together
- **WHEN** `style_inline` is called with `italic=true` in the style object and `clear_fields=["bold"]`
- **THEN** italic is set to true AND bold is cleared to inherited in the same operation

### Requirement: XLSX inline styling targets the full cell when rich-text is unavailable
The system SHALL apply inline style properties to the entire cell when partial per-character styling is not practical with openpyxl. The tool documentation SHALL state which granularity is supported.

#### Scenario: XLSX cell receives full-cell font styling
- **WHEN** `style_inline` is called on an XLSX cell locator
- **THEN** the font properties (bold, italic, font_name, font_size, font_color) are applied to the entire cell's font object

### Requirement: style_inline follows versioned-output and reindex flow
The system SHALL write to a versioned output (or in-place) and reindex after every successful `style_inline` call.

#### Scenario: Output is reindexed after inline style applied
- **WHEN** `style_inline` succeeds
- **THEN** the output document is immediately reindexed and the `MutationResult` identifies the output path

### Requirement: Invalid or unresolvable locator is rejected
The system SHALL raise `TargetNotFoundError` when the locator does not resolve to an element in the document.

#### Scenario: Out-of-range run index is rejected
- **WHEN** `style_inline` is called with a run locator whose index exceeds the paragraph's run count
- **THEN** the system raises `TargetNotFoundError` and does not modify the document

