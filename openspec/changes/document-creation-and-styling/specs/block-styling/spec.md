## ADDED Requirements

### Requirement: Set block style properties on a targeted element
The system SHALL set block-level formatting properties on a targeted paragraph, shape, or cell via `style_block`, using patch semantics: each property present in the request is written; properties absent are left unchanged.

#### Scenario: Set alignment on a DOCX paragraph
- **WHEN** `style_block` is called with a `docx:para:{n}` locator and `alignment="center"`
- **THEN** the paragraph's alignment is set to centered and all other paragraph properties are unchanged

#### Scenario: Set indentation on a PPTX paragraph
- **WHEN** `style_block` is called with a PPTX paragraph locator and `indent_level=1`
- **THEN** the paragraph's indentation level is set to 1

#### Scenario: Set alignment and wrap_text on an XLSX cell
- **WHEN** `style_block` is called with an `xlsx:sheet:{name}!{ref}` locator, `alignment="center"`, and `wrap_text=true`
- **THEN** the cell's horizontal alignment is set to center and text wrapping is enabled

### Requirement: BlockStyle schema is explicit and bounded
The system SHALL accept block style requests conforming to a fixed `BlockStyle` schema. Unknown fields SHALL be rejected.

Supported properties:
- `alignment` (string: "left", "center", "right", "justify")
- `indent_level` (int; DOCX/PPTX list indentation)
- `left_indent` (number, in points)
- `right_indent` (number, in points)
- `spacing_before` (number, in points)
- `spacing_after` (number, in points)
- `line_spacing` (number, multiplier or points depending on format)
- `wrap_text` (bool; XLSX only — ignored with a warning on other formats)
- `vertical_alignment` (string: "top", "center", "bottom"; XLSX only)
- `fill_color` (string, hex RGB; XLSX cell fill only)
- `number_format` (string; XLSX only)

#### Scenario: Unknown block style field is rejected
- **WHEN** `style_block` is called with a property not in the BlockStyle schema
- **THEN** the system raises `InvalidArgumentsError` and does not modify the document

### Requirement: Format-specific BlockStyle properties are silently warned on unsupported formats
The system SHALL emit a warning (not an error) when a BlockStyle property that is only meaningful for one format is passed for a different format, and SHALL skip applying that property.

#### Scenario: wrap_text on a DOCX paragraph emits a warning
- **WHEN** `style_block` is called with a DOCX locator and `wrap_text=true`
- **THEN** the operation succeeds, other applicable properties are applied, and a warning is recorded that `wrap_text` is not applicable to DOCX

### Requirement: Explicit null in clear_fields reverts a block property to inherited
The system SHALL accept an optional `clear_fields` list. For each field name listed, the system SHALL clear that property to the format's default/inherited value.

#### Scenario: Clear spacing_before back to default
- **WHEN** `style_block` is called with `clear_fields=["spacing_before"]`
- **THEN** the paragraph's spacing_before is reset to the inherited/default value for that document's style

### Requirement: style_block follows versioned-output and reindex flow
The system SHALL write to a versioned output (or in-place) and reindex after every successful `style_block` call.

#### Scenario: Output is reindexed after block style applied
- **WHEN** `style_block` succeeds
- **THEN** the output document is immediately reindexed and the `MutationResult` identifies the output path

### Requirement: Invalid or unresolvable locator is rejected
The system SHALL raise `TargetNotFoundError` when the locator does not resolve to a valid block element.

#### Scenario: Non-existent paragraph index is rejected
- **WHEN** `style_block` is called with a paragraph locator whose index is out of range
- **THEN** the system raises `TargetNotFoundError` and does not modify the document
