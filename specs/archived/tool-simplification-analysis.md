# Tool Simplification Analysis: Office-Agent MCP Tool Surface

*Senior API and tool-surface architectural analysis — March 2026*

---

## A. Executive Architectural Judgment

The current system is not broken. It is over-specified. The 23-tool MCP surface reflects the natural growth of an implementation-first design: each new capability got a tool, each format got its own verbs, and the structure inspection layer proliferated as the document model was explored incrementally.

The result is a surface that forces an AI agent to know too much about the internals of three different Python libraries before it can do useful work. The agent must choose among `get_document_structure`, `get_document_blocks`, `get_paragraphs`, and `get_tables` before reading a Word document. It must know to call `get_slide_bundle` for a PowerPoint slide but `get_sheet_snapshot` for an Excel sheet. It must distinguish `replace_text` from `replace_block` even though both ultimately write text to a Word document.

The core tension is real and must be preserved: *discovery* (finding where something is) and *operation* (reading or changing it) are genuinely different concerns. Conflating them produces fragile designs. But they must be bridged by a stable addressing scheme — and that bridge is currently underdeveloped relative to the overall surface.

**The target:** cut 23 tools to approximately 11, with zero loss of functional power and a measurably simpler mental model for any consumer.

---

## B. Core Problem Decomposition

### The two families of concern and why they differ

**Search and retrieval** is a discovery mechanism. The agent knows something about content — a keyword, a concept, a phrase — but not its precise location in any document. Search maps from *content fragments* to *document locations*. The output is a ranked list of candidate locations, not a definitive target.

**Structural access and mutation** is an operational mechanism. The agent knows *where* it wants to act — either because it found the location via search or because it is traversing a known structure — and wants to read or change it. This requires a stable, unambiguous address.

These concerns are related but not identical:

- Search can return many candidates; access targets exactly one.
- Search is stateless with respect to the document; writes change document state and must be re-indexed.
- Search is document-type agnostic in its output (all hits look alike); structural access is inevitably document-type specific in its input (slides, paragraphs, and cells are structurally distinct).
- Search operates over the index, which may be stale; access operates over the live file, which is authoritative.

The bridge between them — the mechanism that lets a search hit safely become an access target — is the most architecturally important invariant in the system. A design that does not make this bridge explicit, stable, and robust will force the agent to perform unsafe string surgery on locators it received from search.

### Current system: where the complexity lives

The current 23-tool surface breaks down as follows:

| Family | Tools | Observation |
|---|---|---|
| Index management | `index_documents`, `refresh_document`, `list_documents` | Clean. No significant fragmentation. |
| Search and location | `search_documents`, `locate_item`, `read_item` | Slightly redundant. `locate_item` + `read_item` is a two-step operation that could be one. |
| Structure inspection | 10 tools across DOCX, PPTX, XLSX | Badly fragmented. Five DOCX tools for one concern. Inconsistent naming. |
| Write operations | 7 tools across text, block, and cell | Fragmented. Two tools do the same thing for DOCX. |

The structure inspection layer is the single largest source of accidental complexity. It has five DOCX-specific tools (`get_document_structure`, `get_document_blocks`, `get_paragraphs`, `get_tables`, `get_block_bundle`) for one concern — inspecting document structure — where two would suffice. The PPTX and XLSX equivalents are more compact but named inconsistently.

The write layer has a related problem: `replace_text` uses an `item_id` (from search), while `replace_block` uses a `block_index` (from structure inspection). These are two different coordinate systems for the same document. An agent navigating this surface must track which coordinate system it is in.

---

## C. Simplification Principles

### 1. Orthogonality

Each tool must do one thing that no other tool does. If two tools differ only in the *input coordinate* they accept (e.g., `item_id` vs. `block_index`), they are not orthogonal — they are duplicates in different dialects.

**Effect on design:** Collapse `replace_text` and `replace_block` into one write tool. Collapse all five DOCX structure tools into two. Enforce a single address space so that search outputs and structure inspection outputs are interchangeable as inputs to reads and writes.

### 2. Stable and unified addressing

Every document location must have one canonical address that remains valid across all tool calls in a session. An address returned by search must be passable directly to read and write tools without transformation.

**Effect on design:** The `locator` string returned by `search_documents` hits must be the same identifier accepted by structure inspection, read, and write tools. No tool should require `block_index` when another tool exposed `item_id` for the same element.

### 3. Separation of discovery from mutation

The tools that find things must not change things. The tools that change things must require an explicit target address. This makes the agent's behavior auditable: you can always tell which tool is safe to retry and which is destructive.

**Effect on design:** Read tools carry no output_mode parameter. Write tools always require an explicit locator. There is no tool that "finds and changes" in a single call.

### 4. Capability layering

The tool surface should have an inner core of general tools and an outer layer of format-specific escape hatches. The core handles 80% of use cases. The escape hatches expose format-specific power without polluting the core.

**Effect on design:** A generic `get_section` tool handles slide detail for PPTX, block detail for DOCX, and sheet snapshot for XLSX. A format-specific `xlsx.write_table` exists because bulk tabular write is an XLSX-specific primitive with no meaningful DOCX or PPTX equivalent.

### 5. Minimal but expressive primitives

Prefer one tool that does the general case over three tools that each do a subset. Add a specific tool only when the general tool cannot express the operation at all, or when forcing the general tool to cover the case makes its input schema incoherent.

**Effect on design:** One `write_node` tool handles text replacement across all formats. One `get_section` tool handles container-level inspection across all formats. Format-specific edge cases get escape hatches, not dedicated top-level tools.

### 6. Format-specific escape hatches are explicit and named

When a format-specific tool is justified, its name must signal its specificity. The agent should never be surprised to discover that a tool only works for one document type.

**Effect on design:** Generic tools have no format prefix. Format-specific escape hatches are prefixed (`pptx_`, `xlsx_`, `docx_`). An agent that sees `xlsx_write_table` knows immediately that this tool is not available for DOCX or PPTX.

---

## D. Search Model Proposal

### Unified vs. split search tools

The current `search_documents` tool already makes the right choice: one tool with a `mode` parameter (`keyword`, `semantic`, `hybrid`). This is the correct model. Textual and vector search are not conceptually different enough to warrant separate tools — they answer the same question ("where is content like this?") through different mechanisms.

**Recommendation:** Keep one search tool. Do not split it.

### Explicit vs. implicit indexing

The current design makes indexing explicit: the agent calls `index_documents` before search is possible. This is correct for an MCP surface. Implicit indexing would require the tool to silently perform potentially expensive embedding work on the agent's behalf, with no control over timing or cost. The agent benefits from knowing when indexing happens.

**Recommendation:** Keep indexing explicit. Add a `with_embeddings` option to `index_documents` (it already exists implicitly via config, but it should be a first-class tool parameter).

### Reindexing and incremental indexing

`refresh_document` exists and handles re-indexing a single document. The current model is sound: writes automatically trigger re-indexing of the affected document. The agent should not need to manage index freshness manually after a write.

**Recommendation:** Keep `refresh_document` for manual refresh. Writes remain auto-reindex. Do not expose incremental indexing as a separate tool — the atomicity of full document reindex is a correctness guarantee.

### The search unit

The current system indexes at different granularities by format:
- DOCX: paragraphs
- PPTX: text shapes
- XLSX: cells (grouped into row embeddings for semantic search)

These granularities are justified by the natural object models of each format. A DOCX paragraph is the unit of meaningful text. A PPTX shape is the unit of visual text. An XLSX cell is the atomic value unit.

**Recommendation:** Do not attempt to unify the search unit across formats. The unit should be format-native. What must be unified is the *representation* of a search hit: every hit, regardless of format, carries a `document_id`, a `locator`, a `preview`, and a `score`.

### What search results should return

A search hit should carry:

- `document_id` — which document
- `locator` — stable address, directly usable in read and write tools (this is the bridge)
- `item_type` — what kind of element was found (paragraph, shape, cell)
- `preview` — a text snippet for the agent to read
- `score` — how relevant (and optionally separate `keyword_score`, `semantic_score`)
- `match_mode` — which search mode produced this hit

**Recommendation:** The current `SearchHit` model is close to correct. The critical invariant is that `locator` must be usable directly as a node address in all downstream tools.

### Filters and scopes

The current `search_documents` already supports `file_type` and `document_id` filters. These are the right scoping axes. Deeper sub-document scoping (e.g., "search only slide 3") should be handled by the agent using `get_section` first, then working with the results from that section.

---

## E. Access and Mutation Model Proposal

### The address space problem

The current system has two address spaces:
1. `item_id` — from the search index (e.g., `para:5`, `slide:2:shape:3`, `sheet:Sheet1!B4`)
2. `block_index` — from the DOCX structure inspection tools

This is the clearest symptom of accidental complexity in the system. The agent cannot use a block_index it received from `get_document_blocks` as input to `replace_text`, which expects an `item_id`. It must map between them or call the right tool depending on which path it took to discover the target.

**Recommendation:** Collapse to one address space. The `locator` string (which is equivalent to `item_id`) is the canonical address. Structure inspection tools return `locator` values. Read tools accept `locator`. Write tools accept `locator`. `block_index` is an internal concept that must not appear in the tool API.

### Separating reads and writes

Reads and writes must be separate tool calls. There is no value in a combined "read-and-modify" tool for this surface. The separation makes each call auditable and the flow legible.

**Recommendation:** Keep reads and writes as distinct tools.

### Generic vs. type-specific mutation

The current write tools span a spectrum:
- `replace_text` and `write_cell`: semantically equivalent — replace the value at a location
- `replace_block`: semantically equivalent to `replace_text` but in a different coordinate system
- `append_paragraph`: create a new paragraph
- `append_row`: create a new row
- `write_table`: create many rows
- `append_text`: add text to an existing node without replacing it

The right decomposition is by *what kind of mutation is happening*, not by format:

- **Replace content at an existing node**: one tool, format-agnostic (`write_node`)
- **Append text to an existing node**: this is `read → compute → write_node`, not a separate primitive
- **Insert a new element at document level**: one tool, with format-specific options in the payload

`append_text` (append to existing item) is the one tool I would eliminate by design — it forces the caller to manage partial state. The agent should read the current content, concatenate, and write back. This is safer, more explicit, and removes one tool.

`write_table` (XLSX bulk write) is justified as a format-specific escape hatch because it is atomic: multiple row inserts in one operation with one reindex cycle. This is genuinely different from multiple `insert_content` calls.

### High-level vs. low-level access

The system does not need a raw library escape hatch at the tool level. The tool surface should not expose `python-pptx` objects or `openpyxl` ranges directly. If an agent needs to perform an operation the tool surface cannot express, the right answer is to extend the tool surface with a specific well-defined tool, not to expose raw Python objects over MCP.

The `get_section` tool at the container level (slide, block, sheet) is the right high-low boundary: it returns rich structural metadata about a container, which gives the agent enough context to decide what to read or write within it.

---

## F. Unified Tool-Surface Proposal

This proposal reduces 23 tools to 11, preserving all functional capabilities.

### Tool 1: `index_documents`

**Purpose:** Index one or more document paths or directories.

**Required inputs:** `paths: list[str]`

**Optional inputs:** `with_embeddings: bool` (enable semantic/hybrid search; default from config)

**Output:** Files scanned, indexed, skipped; per-file status.

**When to use:** Before any search or structure inspection. Also as part of a refresh workflow.

**Replaces:** `index_documents` (unchanged)

---

### Tool 2: `list_documents`

**Purpose:** List all indexed documents with their metadata.

**Required inputs:** None

**Optional inputs:** `file_type: str` (filter by format)

**Output:** Documents with `document_id`, `path`, `file_type`, `display_name`, `item_count`.

**When to use:** To discover what documents are available, obtain document IDs, or verify indexing status.

**Replaces:** `list_documents` (unchanged)

---

### Tool 3: `refresh_document`

**Purpose:** Re-index a previously indexed document, updating content and embeddings.

**Required inputs:** `document_id: str`

**Output:** Updated document metadata and indexing summary.

**When to use:** When the source file has been modified outside of the tool surface, or after a manual file operation.

**Replaces:** `refresh_document` (unchanged)

---

### Tool 4: `search_documents`

**Purpose:** Search indexed document content using keyword, semantic, or hybrid matching.

**Required inputs:** `query: str`

**Optional inputs:** `mode: "keyword" | "semantic" | "hybrid"` (default: `"keyword"`), `document_id: str`, `file_type: str`, `limit: int` (default: 20)

**Output:** Ranked hits, each with `document_id`, `locator`, `item_type`, `preview`, `score`, `match_mode`.

**Invariant:** Every `locator` in the output is valid as a `node_id` in `get_node` and `write_node`.

**When to use:** To discover relevant document locations from a content query. The primary entry point for most agent workflows.

**Replaces:** `search_documents` (unchanged except removing `locate_item` as a separate tool — use `get_node` after search)

---

### Tool 5: `get_structure`

**Purpose:** Return the top-level structural outline of an indexed document in a format-aware way.

**Required inputs:** `document_id: str`

**Optional inputs:** None

**Output:** A list of *sections* — the natural first-level subdivisions of the document:
- DOCX: ordered blocks with `locator`, `block_type` (paragraph/table), `preview`, style metadata
- PPTX: slides with `slide_number`, `locator`, `preview`
- XLSX: worksheets with `sheet_name`, `locator`, `preview`, `cell_count`

Each section entry carries a `locator` usable as `section_id` in `get_section` and as `node_id` in `get_node`.

**When to use:** As the structural entry point for a document when the agent is not using search. Use this to understand what a document contains before drilling into specific sections.

**Replaces:** `get_document_structure`, `get_document_blocks`, `get_paragraphs`, `get_presentation_structure`, `get_workbook_structure` — all five current format-specific top-level structure tools.

---

### Tool 6: `get_section`

**Purpose:** Return the full semantic payload for one document section — a slide, a block (paragraph or table), or a worksheet.

**Required inputs:** `document_id: str`, `section_id: str` (locator from `get_structure` or `search_documents`)

**Optional inputs:** For XLSX only: `cell_range: str` (e.g., `"A1:D10"`) to limit snapshot size.

**Output:** Rich section detail, format-specific:
- DOCX paragraph block: text, style, runs with formatting
- DOCX table block: rows as `list[list[str]]`, cell metadata
- PPTX slide: ordered `text_blocks[]`, `notes_text`, layout metadata
- XLSX sheet: `cells[]` with `coordinate`, `display_value`, `formula`, `metadata`

**When to use:** After `get_structure` to drill into one section, or after `search_documents` to understand the context around a hit. The primary tool for reading structured content.

**Replaces:** `get_slide_bundle`, `get_slide_notes`, `get_block_bundle`, `get_tables`, `get_sheet_snapshot` — and the `locate_item` use case when the goal is structural inspection rather than raw text.

---

### Tool 7: `get_node`

**Purpose:** Read the current content of a single leaf node, directly from the source document.

**Required inputs:** `document_id: str`, `node_id: str` (locator)

**Output:** `node_id`, `item_type`, `text`, `metadata`.

**When to use:** To read the current text of a specific item before writing to it. Accepts any `locator` from search hits or structure inspection. The agent should use this rather than relying on the `preview` in search results, which may be stale.

**Replaces:** `read_item`, and the read-only use case of `locate_item`.

---

### Tool 8: `write_node`

**Purpose:** Replace the content of an existing node with new content.

**Required inputs:** `document_id: str`, `node_id: str` (locator), `content: str`

**Optional inputs:** `output_mode: "versioned" | "inplace"` (default: `"versioned"`)

**Output:** `output_path`, `node_id`, `new_text`, `previous_text`.

**Invariant:** Automatically re-indexes the output document. The `output_path` document is indexed, not the original.

**When to use:** To replace text in any indexed item — a DOCX paragraph, a PPTX text shape, or an XLSX cell. The single mutation primitive for replacing existing content.

**Replaces:** `replace_text`, `replace_block`, `write_cell`, and the write case of `append_text` (the agent reads with `get_node`, concatenates, then writes back with `write_node`).

---

### Tool 9: `insert_content`

**Purpose:** Insert new content into a document at a logical position.

**Required inputs:** `document_id: str`, `content: str`

**Optional inputs:**
- `style_name: str` — DOCX paragraph style (e.g., `"Heading 2"`)
- `after_node_id: str` — insert after this locator (default: append to end)
- `output_mode: "versioned" | "inplace"` (default: `"versioned"`)

**Output:** `output_path`, `new_node_id`, `preview`.

**When to use:** To append a new paragraph to a DOCX document. PPTX slide insertion is not supported at this level (slides require layout and master relationships that cannot be expressed as a content string — use format-specific tooling if needed). XLSX row insertion is handled by `xlsx_insert_rows`.

**Replaces:** `append_paragraph`, `append_text` (when appending a new element, not extending an existing one).

---

### Tool 10: `xlsx_insert_rows`

**Purpose:** Append one or more rows to an XLSX worksheet in a single atomic operation.

**Required inputs:** `document_id: str`, `sheet_name: str`, and one of:
- `rows: list[list[str]]` — positional rows
- `records: list[dict[str, str]]` — column-mapped rows

**Optional inputs:** `output_mode: "versioned" | "inplace"`

**Output:** `output_path`, `rows_inserted`, `first_row_locator`.

**When to use:** To append tabular data to an XLSX worksheet. This is the XLSX-specific bulk write primitive. Use instead of multiple `write_node` calls for table data.

**Replaces:** `append_row`, `write_table`.

---

### Tool 11: `docx_get_tables`

**Purpose:** Return DOCX tables as structured arrays, one entry per table.

**Required inputs:** `document_id: str`

**Optional inputs:** None

**Output:** `tables[]` — each with `locator`, `table_index`, `rows: list[list[str]]`, `preview`.

**When to use:** When the agent needs structured table data from a DOCX document. `get_section` returns table rows but only for one block; this returns all tables in the document in one call.

**Replaces:** `get_tables`.

---

### Summary: 23 tools → 11 tools

| New tool | Replaces |
|---|---|
| `index_documents` | `index_documents` |
| `list_documents` | `list_documents` |
| `refresh_document` | `refresh_document` |
| `search_documents` | `search_documents`, `locate_item` (partially) |
| `get_structure` | `get_document_structure`, `get_document_blocks`, `get_paragraphs`, `get_presentation_structure`, `get_workbook_structure` |
| `get_section` | `get_slide_bundle`, `get_slide_notes`, `get_block_bundle`, `get_sheet_snapshot` |
| `get_node` | `read_item`, `locate_item` |
| `write_node` | `replace_text`, `replace_block`, `write_cell` |
| `insert_content` | `append_paragraph`, `append_text` |
| `xlsx_insert_rows` | `append_row`, `write_table` |
| `docx_get_tables` | `get_tables` |

---

## G. Format-Specific Boundaries

### What should be unified across all formats

**Addressing:** All formats share the same `locator` string format (already implemented). Every tool that accepts a location accepts a locator. No tool should have format-specific variants of its primary input.

**Search semantics:** `search_documents` returns the same hit structure for all formats. The agent does not need to know the format to interpret search results.

**Metadata access:** `list_documents` and the document-level metadata returned by `get_structure` should have a common shape across formats: `document_id`, `path`, `file_type`, `display_name`, `modified_time`.

**Content extraction:** `get_node` returns text for all formats. The agent does not need to know the format to read a node.

**Write verb:** `write_node` replaces content for all formats. The agent does not need to know the format to write a node.

### What must remain format-specific

**Section structure:** The sections returned by `get_structure` are format-native. A DOCX section is a block (paragraph or table). A PPTX section is a slide. An XLSX section is a worksheet. These are structurally incompatible — they cannot be unified without hiding essential information.

**Section detail:** `get_section` returns different payloads per format. A PPTX slide has `notes_text` and an ordered `text_blocks` list. An XLSX sheet has `cells` with `coordinate`, `formula`, and `display_value`. A DOCX table block has `rows`. These are format-specific because the underlying object models are genuinely different.

**Bulk tabular write:** `xlsx_insert_rows` is justified as a format-specific tool because:
1. The concept of a "row" of typed cells is intrinsic to XLSX.
2. Atomic multi-row insert with one reindex cycle is an efficiency invariant that matters for large workbooks.
3. DOCX and PPTX have no equivalent operation.

**Table structure inspection:** `docx_get_tables` is justified because DOCX tables are a distinct structural element that cannot be naturally discovered through `get_structure` (which lists blocks, some of which are tables, but does not return the table row data at that level). XLSX has no equivalent need because `get_section` returns the cell grid directly.

**Format-specific operations that do not currently exist but may be needed:**
- PPTX slide insertion (requires layout/master context; cannot be expressed as plain text content)
- DOCX list item insertion (requires style and list continuation context)

These should be added as format-prefixed tools if and when needed, rather than being folded into `insert_content` with opaque option flags.

---

## H. Recommended End-State Architecture

### Conceptual model

The system is organized around five first-class concepts:

```
Document
  └── has many Sections (slides, blocks, sheets)
        └── has many Nodes (text shapes, paragraphs, cells)
              └── has text content and metadata

SearchIndex
  └── maps content fragments to (Document, Node) pairs
        └── returns Hits carrying (document_id, locator, preview, score)

Locator
  └── stable string address for a Section or Node
  └── produced by: search_documents, get_structure, get_section
  └── consumed by: get_section, get_node, write_node, insert_content
```

Relations:
- Every `Hit.locator` is a valid `node_id` in `get_node` and `write_node`.
- Every `Section.locator` from `get_structure` is a valid `section_id` in `get_section`.
- Every `Node.locator` from `get_section` is a valid `node_id` in `get_node` and `write_node`.
- Writes produce a new `output_path` and re-index it. The original `document_id` is now stale; the agent must use the new document's ID or re-index explicitly.

### Layers

**Layer 1 — Discovery**
Tools: `index_documents`, `list_documents`, `search_documents`
Purpose: Build and query the index. The agent starts here when it does not know where relevant content is.

**Layer 2 — Structural inspection**
Tools: `get_structure`, `get_section`, `get_node`, `docx_get_tables`
Purpose: Traverse the document object model. The agent uses this when it knows which document to work with but needs to navigate its structure.

**Layer 3 — Mutation**
Tools: `write_node`, `insert_content`, `xlsx_insert_rows`
Purpose: Modify documents. Always requires a locator from Layer 1 or 2. Always triggers re-indexing.

**Layer 4 — Index management**
Tools: `refresh_document`
Purpose: Maintain index freshness for documents modified outside the tool surface.

### Key invariants

1. **Locator stability within a session:** A locator returned by any read tool is valid as input to any other read or write tool in the same session, for the same document version.

2. **Write-then-reindex atomicity:** Every write tool reindexes the output document before returning. The agent never observes a state where the document has been written but the index has not caught up.

3. **No coordinate system divergence:** No tool returns an address that is only valid as input to a subset of other tools. One address space, period.

4. **Format transparency in generic tools:** Generic tools (`get_node`, `write_node`) do not require the agent to specify the document format. Format is inferred from the `document_id`.

5. **Format opacity in specific tools:** Format-specific tools (`xlsx_insert_rows`, `docx_get_tables`) are clearly named and fail gracefully if called on the wrong document type.

---

## I. Migration Path

### What to deprecate first

**Highest priority (confusing or redundant):**
- `locate_item` — fully superseded by `get_node`. Its output is a subset of `get_node`. Deprecate immediately.
- `get_document_blocks` — superseded by `get_structure`. The concept of a "block" at the tool level is an implementation leak. Deprecate alongside `get_structure` introduction.
- `replace_block` — superseded by `write_node` (accepts the same locator). Deprecate when `write_node` ships.
- `append_text` — remove in favor of the read-compute-write pattern. This is the one removal that changes the agent's workflow, so communicate it clearly.

**Second priority (safe but redundant):**
- `get_paragraphs` — superseded by `get_structure` (for the list) and `get_section` (for paragraph detail).
- `get_tables` — superseded by `docx_get_tables` (a rename, not a removal).
- `get_document_structure` — superseded by `get_structure`.

**Third priority (rename for consistency):**
- `get_presentation_structure` → folded into `get_structure`
- `get_workbook_structure` → folded into `get_structure`
- `get_slide_bundle` → `get_section` (with `section_id` = slide locator)
- `get_sheet_snapshot` → `get_section` (with optional `cell_range`)
- `get_block_bundle` → `get_section` (with `section_id` = block locator)
- `get_slide_notes` → absorbed into `get_section` response (which already includes `notes_text`)

### Compatibility shims

During transition, the existing tools can remain operational while the new tools are introduced. The following shim mappings are straightforward:

| Old tool | Shim strategy |
|---|---|
| `locate_item(doc, locator)` | Returns `get_node(doc, locator)` output with legacy field names |
| `replace_block(doc, block_index, text)` | Resolves `block_index` to locator, calls `write_node` |
| `get_document_blocks(doc)` | Returns `get_structure(doc)` output filtered to DOCX sections |
| `get_slide_notes(doc, slide)` | Returns `get_section(doc, slide_locator).notes_text` |
| `append_row(doc, sheet, values)` | Calls `xlsx_insert_rows(doc, sheet, rows=[values])` |
| `write_table(doc, sheet, rows)` | Calls `xlsx_insert_rows(doc, sheet, rows=rows)` |

### What the agent needs to know

The agent's system prompt or tool description should be updated to communicate:

1. **The locator is universal.** Any locator from any tool is valid as input to `get_node` and `write_node`. The agent does not need to format-match.

2. **`get_structure` is the entry point for structural navigation.** If the agent is not using search, start here.

3. **`get_section` gives full detail for one container.** A slide, a block, or a sheet — pass its locator.

4. **`write_node` replaces all node content.** For append workflows, read first, compute, then write.

5. **Format-specific tools are explicitly named.** If a tool name starts with `xlsx_` or `docx_`, it only works for that format.

---

## J. Final Concise Recommendation

**Preferred conceptual model:** Document → Section → Node, with a universal Locator that bridges discovery to operation.

**Preferred simplification strategy:** Collapse format-specific variants of the same concern into one format-aware generic tool. Retain format-specific tools only when the operation has no meaningful generic expression.

**Recommended balance:** 8 generic tools, 3 format-specific escape hatches. The generic layer handles all common workflows. The format-specific layer handles tabular bulk write (XLSX) and structured table extraction (DOCX). No other format-specific tools are warranted by the current capabilities.

**Minimum core tool set (8 tools):**
`index_documents`, `list_documents`, `refresh_document`, `search_documents`, `get_structure`, `get_section`, `get_node`, `write_node`

These eight tools are sufficient for: indexing, searching (all modes), navigating document structure, reading any node, and modifying any node. No format knowledge required.

**Advanced escape hatches (3 tools):**
`insert_content` (new DOCX paragraphs), `xlsx_insert_rows` (XLSX tabular writes), `docx_get_tables` (DOCX structured tables)

**Key invariants the API must guarantee:**
1. Every locator returned by any tool is valid as input to `get_node` and `write_node`.
2. Every write call reindexes before returning.
3. No tool exposes a format-specific coordinate system (block_index, shape_id as raw integers) in its primary interface.
4. Format-specific tools fail explicitly, not silently, when called on the wrong document type.

**The single most important change:** Eliminate the dual coordinate system (`item_id` vs `block_index`) and replace it with one universal `locator`. Everything else follows from this. An agent that can trust that every address it holds is valid everywhere does not need to remember which tool it used to discover that address.
