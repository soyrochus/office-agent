# Document Creation And Styling

Prompt for the code generation agent.

This prompt is intentionally limited to a compact creation-and-styling surface that is consistent with the current Office Agent architecture and with the verified MCP gaps.

It is aligned with the current implementation because it adds only these missing capability areas:

- new document creation for DOCX, PPTX, and XLSX
- generic content-block creation for the three formats
- inline styling
- block styling
- DOCX-only structural role mapping

It does not add broader functionality that was identified as missing but is outside this request, including:

- Markdown or HTML import/conversion
- template management
- arbitrary output-mode redesign beyond creation at an explicit output path
- chart/image/media authoring APIs
- semantic roles for PPTX or XLSX
- one monolithic generic mutation tool

The implementation should fit the existing adapter, service, typed-locator, and MCP-wrapper structure already used in the codebase.

## Prompt

Adjust office-agent in order to expose a small, balanced set of generic tools for document creation and styling.

Do not create case-specific tools.
Do not create one giant tool with excessive arguments.
Find a good balance: as few tools as possible, but each tool must remain clear, coherent, and usable.

## Functional scope

Implement support for these styling layers:

### 1. Inline styling - all three formats

Support character-level or text-level styling where the underlying format allows it.

Required properties:

- bold
- italic
- underline
- font family
- font size
- font color
- optional extras if naturally supported by the library:
- strikethrough
- highlight / fill where applicable

### 2. Block styling - all three formats

Support styling at block/container level.

Required coverage:

- paragraph properties
- alignment
- indentation / list level where applicable
- spacing where naturally available
- cell style for Excel
- block-level text formatting where appropriate

Examples by format:

- DOCX: paragraph formatting
- PPTX: paragraph formatting and paragraph level
- XLSX: cell style / alignment / wrapping / number format if easy to support

### 3. Structural role mapping - DOCX only

For Word only, support a structural mapping layer with these roles:

- heading
- title
- body
- table header
- caption

This MUST be implemented only for DOCX.
Do not fake equivalent structural roles for PPTX or XLSX.

### 4. Document creation

Add the ability to create new documents for all three formats.

Required:

- create empty DOCX
- create empty PPTX
- create empty XLSX

Also support creating initial content units:

- DOCX: paragraph, heading, table
- PPTX: slide, textbox
- XLSX: sheet, row, cell content

## Architectural requirements

Keep the number of tools low.

Target a compact tool surface such as:

1. create_document
2. add_content_block
3. style_inline
4. style_block
5. set_structural_role

You MAY adjust the exact names, but stay close to this size.
Do not exceed this unless clearly necessary.
Do not collapse everything into one universal mutation tool.

The tools must be generic across formats wherever reasonable.

The implementation should extend the current service and MCP layers rather than bypassing them.
Use typed request models and structured target references consistent with the existing locator-driven design.

## Tool design guidance

### create_document

Use this to create a new Office document.

It should:

- accept format: docx, pptx, xlsx
- accept output path
- optionally accept minimal initialization options

Do not overload it with content creation responsibilities beyond minimal initialization.

### add_content_block

Use this to add a logical content unit to a document.

Examples:

- DOCX paragraph
- DOCX heading
- DOCX table
- PPTX slide
- PPTX textbox
- XLSX sheet
- XLSX row or cell content

This tool should be generic but not vague.
Use a limited set of block types.
Do not push all styling arguments into this tool.

### style_inline

Use this for inline / character-level styling.

It must support:

- DOCX runs
- PPTX text runs
- XLSX rich text when possible, and full-cell text styling when partial styling is not practical

This tool should accept:

- a target reference
- text range or inline element selector where applicable
- a compact inline style object

Keep the inline style schema explicit and reusable.

### style_block

Use this for block-level styling.

It must support:

- DOCX paragraph formatting
- PPTX paragraph formatting
- XLSX cell style and alignment

Accept:

- target reference
- compact block style object

### set_structural_role

This applies only to DOCX.

It should map a block to one of:

- heading
- title
- body
- table header
- caption

Implement this through Word styles or equivalent Word-native constructs.
If called on PPTX or XLSX, fail cleanly with a clear error.

## Data model requirements

Define compact, explicit style schemas.

Suggested structure:

InlineStyle:

- bold
- italic
- underline
- font_name
- font_size
- font_color
- strike
- highlight

BlockStyle:

- alignment
- indent_level
- left_indent
- right_indent
- spacing_before
- spacing_after
- line_spacing
- wrap_text
- vertical_alignment
- fill_color
- border
- number_format

Do not force every format to support every field.
Unsupported properties must be ignored with warnings or rejected clearly, depending on what is safer.
Prefer explicit validation over silent no-ops when a property cannot be applied.

## Targeting model

Define a clean target reference model so tools can identify where styling or content applies.

Examples:

- DOCX paragraph index
- DOCX run index
- PPTX slide index + shape index + paragraph index + run index
- XLSX sheet name + cell reference
- XLSX rich text segment reference if supported

Keep target references structured and explicit.
Do not rely on fragile free-text selectors.

The targeting model should remain compatible with the existing typed-locator approach used by Office Agent.

## Format-specific expectations

### DOCX

Support:

- document creation
- paragraph creation
- run-level inline styling
- paragraph-level block styling
- structural role mapping using Word-native styles where possible
- basic table creation
- table header and caption treatment where feasible

### PPTX

Support:

- presentation creation
- slide creation
- textbox creation
- run-level inline styling
- paragraph-level block styling
- list/indentation level where possible

Do not invent Word-like semantic roles.

### XLSX

Support:

- workbook creation
- sheet creation
- cell writing
- whole-cell styling
- rich text / partial-cell styling if practical with openpyxl
- alignment and wrapping
- basic number format support if easy

Do not invent heading semantics.

## Error handling

Be strict but usable.

- Fail clearly on invalid references
- Fail clearly on unsupported structural role usage outside DOCX
- Return structured errors
- Avoid silent no-ops unless explicitly justified

## Implementation constraints

- Python only
- Use the three libraries directly
- No native compilation
- No unnecessary framework dependency
- Prefer typed models and clear helper functions
- Keep public tool count low
- Keep each tool coherent

Preserve the current indexing and search model.
New creation and styling capabilities should integrate with the existing document registration, output, and reindex flow rather than introducing a parallel execution path.

## Code organization

Produce a maintainable structure with:

- adapters per format
- shared style models
- shared target reference models
- MCP tool wrappers
- tests

Suggested modules:

- models/styles.py
- models/targets.py
- adapters/docx_adapter.py
- adapters/pptx_adapter.py
- adapters/xlsx_adapter.py
- tools/create_document.py
- tools/add_content_block.py
- tools/style_inline.py
- tools/style_block.py
- tools/set_structural_role.py

You may vary names, but preserve this separation.

Use the existing repository structure where practical. If equivalent modules already exist, extend them instead of introducing redundant parallel modules.

## Tests

Add tests for:

- creating each document format
- applying inline styling in each format
- applying block styling in each format
- applying DOCX structural roles
- rejecting DOCX-only structural roles on PPTX/XLSX

## Important balancing instruction

Minimize the number of tools.
Do not over-minimize.

Prefer a small set of well-scoped generic tools over:

- many micro-tools
- one monolithic tool with too many arguments

Aim for the smallest tool surface that still keeps:

- creation
- inline styling
- block styling
- DOCX structural mapping

cleanly separated.

Before finalizing, review the tool API and reduce unnecessary overlap.
But do not merge tools that operate on genuinely different abstraction levels.