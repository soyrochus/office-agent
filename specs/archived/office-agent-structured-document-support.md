# office-agent-structured-document-support
## Change intent

Extend the **office-agent MCP server** to provide **uniform, structured access and manipulation capabilities** across:

* PowerPoint (`.pptx`)
* Excel (`.xlsx`)
* Word (`.docx`)

The extension introduces a **semantic document layer** that exposes document structure and transformation primitives through **generic MCP tools**, enabling agents to perform structured document processing without scripts or case-specific logic.

---

## Suggested change title

`office-agent-structured-document-support`

---

## One-paragraph problem statement

The current office-agent MCP server provides low-level access to Office documents, focused on indexing and locating text elements. This model is insufficient for structured document workflows, as it forces agents to reconstruct document semantics from granular elements. Additionally, support is uneven across Office formats, with no unified abstraction layer. We need to extend the MCP tool surface to expose consistent, document-level and structure-aware primitives for PowerPoint, Excel, and Word, enabling agents to extract, transform, and write structured data entirely through generic tools, without embedding case-specific logic.

---

## Design objective

Provide a **unified semantic interface** across Office formats so that an agent can:

* inspect document structure
* extract logical content units
* transform content into structured records
* write structured outputs

All interactions must occur via **generic MCP tools**.

---

## Core design constraint

* No case-specific tools
* No embedded workflows
* No scripting layer inside the MCP server

All capabilities must be:

* generic
* composable
* declarative where possible

---

## Architectural position

The extension adds a **semantic layer above existing adapters**, without replacing them.

Final layering:

1. **Low-level layer (existing)**

   * index_documents
   * locate_item
   * read_item
   * write_cell / text mutation

2. **Semantic document layer (new)**

   * structure-aware tools
   * aggregation primitives
   * transformation tools
   * structured write tools

3. **Agent layer (external)**

   * composes workflows
   * applies reasoning
   * chains tools

---

## Design principles

### 1. Uniform abstraction across formats

PowerPoint, Excel, and Word must expose **parallel concepts**:

| Concept      | PPTX         | XLSX       | DOCX       |
| ------------ | ------------ | ---------- | ---------- |
| container    | presentation | workbook   | document   |
| unit         | slide        | sheet/row  | block      |
| content unit | text block   | cell       | paragraph  |
| metadata     | shape info   | sheet info | style info |

Agents should not need format-specific reasoning beyond minimal differences.

---

### 2. Logical unit access

Tools must expose **complete logical units**, not fragments:

* full slide
* full paragraph or section
* full row

---

### 3. Deterministic first

All extraction and transformation must be deterministic unless explicitly invoking AI tools.

---

### 4. Composable primitives

Each tool performs one step:

* read
* extract
* transform
* write

No orchestration embedded.

---

## Required capability areas

---

## A. Document structure tools (all formats)

### Required tools

`get_document_structure`

* input: document_id
* output depends on type:

  * PPTX: slides
  * XLSX: sheets
  * DOCX: blocks (paragraphs, tables)

---

## B. PowerPoint tools (PPTX)

### Required tools

`get_presentation_structure`

* list slides with metadata

`get_slide_bundle`

* input: document_id, slide_number
* returns:

  * notes
  * text_blocks
  * metadata

`get_slide_notes`

* direct access to notes text

---

## C. Excel tools (XLSX)

### Required tools

`get_workbook_structure`

* list sheets

`get_sheet_snapshot`

* input: document_id, sheet
* optional range/window

`append_row`

* input:

  * document_id
  * sheet
  * values (list or dict)

`write_table`

* input:

  * rows (list of records)
  * optional mapping config

---

## D. Word tools (DOCX)

This is the main addition.

### Required tools

`get_document_blocks`

* input: document_id
* returns ordered list of blocks:

  * paragraphs
  * tables
  * headings (if detectable)

---

`get_paragraphs`

* input: document_id
* output:

  * ordered paragraphs
  * text
  * optional style metadata (heading level, etc.)

---

`get_tables`

* input: document_id
* output:

  * tables as 2D arrays
  * optional cell metadata

---

`get_block_bundle`

* input: document_id, block_index
* returns:

  * text
  * type (paragraph/table)
  * metadata

---

`append_paragraph`

* input:

  * document_id
  * text
  * optional style

---

`replace_block`

* input:

  * document_id
  * block_index
  * new content

---

### Design note for DOCX

Do NOT attempt full semantic understanding (sections, figures, etc.).

Focus on:

* paragraphs
* tables
* order

Keep it consistent and predictable.

---

## E. Extraction tools (generic)

### Required tool

`extract_fields`

* input:

  * text or structured input
  * rules/config

Rules may include:

* first sentence
* regex
* split
* keyword match
* priority sources

Output:

* key-value map
* optional warnings

---

## F. Record construction tools

### Required tool

`build_record`

* input:

  * multiple sources
  * mapping config
* output:

  * normalized record

No business logic allowed.

---

## G. AI enrichment tools (optional)

### Required tools

`summarize_text`

* input:

  * text
  * instruction

`infer_field`

* input:

  * text
  * field definition

These must be explicitly invoked.

---

## H. Iteration support

### Required tools

`list_units`

* unified abstraction:

  * slides (PPTX)
  * rows (XLSX, optional)
  * blocks (DOCX)

---

## Data model expectations

All tools return structured JSON-like objects.

### Examples

Slide bundle:

```json
{
  "slide_number": 2,
  "notes": "...",
  "text_blocks": [...]
}
```

Paragraph:

```json
{
  "index": 5,
  "text": "...",
  "style": "Heading 2"
}
```

Table:

```json
{
  "rows": [
    ["A1", "B1"],
    ["A2", "B2"]
  ]
}
```

---

## Compatibility with existing tools

Keep:

* index_documents
* locate_item
* read_item
* write_cell

They remain:

* low-level fallback tools

---

## Supported workflows (emergent, not encoded)

The system must enable, but not encode:

* slide → record → excel row
* docx paragraphs → structured data → excel
* pptx → docx transformation
* docx → summary → report generation

All achieved through tool composition.

---

## Configuration model

Tools that require rules must accept structured config:

* extraction rules
* field mappings
* output schema

JSON-compatible.

---

## Error handling

All tools must return:

* success flag
* warnings
* diagnostics
* partial results if applicable

---

## Observability

Include:

* source references (slide, paragraph index)
* intermediate values (optional debug mode)
* warnings

---

## Non-functional requirements

### Consistency

All formats follow similar patterns.

### Stability

Tool contracts must remain stable.

### Extensibility

Future:

* images
* layout inference
* cross-document linking

### Minimal dependencies

Continue:

* python-pptx
* openpyxl
* python-docx

---

## Acceptance direction

The extension is successful if:

* PPTX, XLSX, and DOCX are supported with consistent abstractions
* agents can extract structured data from all three formats using MCP tools only
* slide, paragraph, and row-level access exists
* structured records can be built generically
* Excel writing supports row-level operations
* DOCX supports paragraph and table extraction and modification
* no case-specific tools exist
* workflows are fully composable

