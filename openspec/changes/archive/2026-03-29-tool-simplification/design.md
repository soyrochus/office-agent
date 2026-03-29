## Context

All 23 MCP tools are registered as `@mcp.tool`-decorated functions in `src/offagent/interfaces/mcp.py`. Supporting models live in `mcp_models.py` and format converters in `mcp_converters.py`. There is no sub-module structure per tool — this is a single-file registration surface.

The current surface has two structural problems that interact:

1. **Fragmented structure inspection.** Five DOCX tools (`get_document_structure`, `get_document_blocks`, `get_paragraphs`, `get_block_bundle`, `get_tables`), two PPTX tools (`get_presentation_structure`, `get_slide_bundle`), and two XLSX tools (`get_workbook_structure`, `get_sheet_snapshot`) all serve one concern — navigating to the right place in a document.

2. **Dual coordinate system.** `replace_text` expects an `item_id` (from search); `replace_block` expects a `block_index` (from structure inspection). These are different addresses for the same document, and no tool converts between them. A consumer must remember which discovery path it used.

## Goals / Non-Goals

**Goals:**
- Reduce the MCP surface from 23 to 11 tools
- Establish a single `locator` address space: every locator produced by any tool is valid as input to `get_node` and `write_node`
- Make format an implementation detail, not a tool-selection decision, for the generic layer
- Name format-specific tools with an explicit format prefix (`docx_`, `xlsx_`)

**Non-Goals:**
- Changes to the indexing pipeline, embedding model, or search implementation
- New document capabilities (this is a surface refactor, not a feature addition)
- Backwards compatibility shims — consumers are internal (the AI agent) and can be updated atomically with the surface
- Sub-module decomposition of `mcp.py` (not required; the file is already manageable at 11 tools)

## Decisions

### 1. Hard replacement, no shims

**Decision:** Remove old tools and add new ones in the same commit. No compatibility shims.

**Rationale:** The only consumer is an AI agent whose system prompt is updated atomically with the tool surface. There are no external API clients pinned to old tool names. Shims would require maintaining two parallel implementations, two test suites, and two sets of type models for a transitional period with no concrete benefit.

**Alternative considered:** Keep old tools alongside new ones behind a deprecation flag. Rejected because the flag would have no enforcement mechanism — the agent would see 34 tools and have to decide which to use.

---

### 2. Format dispatch inside generic tools, not at the tool boundary

**Decision:** `get_structure`, `get_section`, `get_node`, and `write_node` accept a `document_id` and dispatch to the appropriate format handler internally based on the indexed document's `file_type`.

**Rationale:** The locator string already encodes the format implicitly (e.g., `para:5`, `slide:2:shape:3`, `sheet:Sheet1!B4`). The document record in the index carries `file_type`. Tools can route without requiring the caller to specify format. This is the only design that makes format transparent at the generic-tool boundary.

**Alternative considered:** Separate generic tools per format (e.g., `docx_get_structure`, `pptx_get_structure`). Rejected because it recreates the fragmentation problem with different names.

---

### 3. Eliminate `block_index` from the tool API

**Decision:** No tool accepts or returns a `block_index`. The `locator` string (equivalent to the existing `item_id`) is the sole address primitive.

**Rationale:** `block_index` is an internal python-docx concept. It changes if the document is modified. It is not serializable across tool calls. The existing `locator`/`item_id` is already a stable, serializable address and is already used by search — extending it to cover structure inspection closes the dual-address problem.

**Implementation note:** `replace_block` used `block_index` to locate a paragraph. The new `write_node` accepts the same `locator` that `get_structure` returns for DOCX blocks. The internal implementation of `write_node` will resolve the locator to a paragraph index at call time, as the existing `replace_text` already does for `item_id`.

---

### 4. Remove `append_text`; enforce read-compute-write

**Decision:** `append_text` (append to an existing item without replacing) is removed. The equivalent workflow is `get_node` → concatenate → `write_node`.

**Rationale:** `append_text` manages partial state on behalf of the caller. It assumes the caller wants to concatenate, which is the common case but not the only case. The read-compute-write pattern is two tool calls but is explicit, auditable, and handles any text transformation — not just concatenation. The cost (one extra tool call) is worth the gain in clarity and reduced API surface.

---

### 5. `get_structure` returns section-level locators; `get_section` returns node-level locators

**Decision:** The two structural tools form a two-level hierarchy. `get_structure` returns one entry per section (DOCX block, PPTX slide, XLSX sheet), each with a `locator` valid as `section_id` in `get_section`. `get_section` returns one entry per leaf node within that section, each with a `locator` valid as `node_id` in `get_node` and `write_node`.

**Rationale:** This mirrors the document model (Document → Section → Node) from the analysis. It avoids the "structure inspection returns too much detail" problem that led to the proliferation of format-specific bundle tools. An agent navigating a large PPTX does not need the full text of every slide to pick the right one — `get_structure` gives it slide titles and locators; `get_section` gives it the full slide payload for the one it chose.

---

### 6. `write_node` defaults to versioned output

**Decision:** `write_node` (and `insert_content`, `xlsx_insert_rows`) default to `output_mode: "versioned"`, producing a new timestamped file. `"inplace"` is available as an option.

**Rationale:** Existing `replace_text` already behaves this way. Preserving the default avoids silent data loss for callers who do not think about output modes. The agent's system prompt should explain that after a write, the `output_path` document is the live version and should be re-indexed or used as the new `document_id`.

---

### 7. `docx_get_tables` is a justified format-specific escape hatch

**Decision:** Keep a format-specific `docx_get_tables` tool (renamed from `get_tables`).

**Rationale:** `get_structure` for a DOCX document returns all blocks, including tables. But it returns them as section entries with previews, not as structured row arrays. An agent that needs to reason about table content (e.g., "find the row where column A is 'Q1'") needs the cell data. `get_section` on a table block returns its rows — but only for one block at a time. `docx_get_tables` returns all tables as row arrays in one call. This is a genuine efficiency and ergonomics advantage for table-heavy DOCX workflows. XLSX has no equivalent need because `get_section` returns the full cell grid directly.

## Risks / Trade-offs

**Write-then-document-id drift** → The versioned output creates a new file with a different path and a new `document_id`. The agent must update its working `document_id` after any write. This is the existing behavior and is documented in tool descriptions, but it remains a cognitive burden. *Mitigation:* `write_node` output explicitly includes the new `document_id` in its response.

**Locator stale after write** → A locator from the pre-write version of a document may be structurally valid but point to the wrong content in the post-write version if surrounding elements shifted. *Mitigation:* Locator stability within a session is only guaranteed for the same document version. The existing `stale-locator-detection` spec covers this invariant.

**`get_section` payload size for large XLSX sheets** → `get_section` for a large worksheet could return thousands of cells. *Mitigation:* The optional `cell_range` parameter on `get_section` for XLSX allows the agent to limit the snapshot window.

**Agent learning curve on new tool names** → Removing 12 familiar tool names will require updating the agent system prompt and any eval fixtures that reference old tool names. *Mitigation:* Handled as a paired change — tool surface and system prompt update in the same deployment.

## Migration Plan

1. Delete all 12 removed tool handler functions from `mcp.py`
2. Remove their input/output models from `mcp_models.py` and `mcp_converters.py`
3. Add 7 new tool handler functions for the new tools
4. Add new input/output models for the new tools
5. Update tool descriptions and parameter docstrings for the 3 unchanged tools (`index_documents`, `list_documents`, `refresh_document`) to reflect the new surface context
6. Update agent system prompt to describe the 11-tool surface and the locator universality invariant
7. Delete test files for removed tools; add test files for new tools

No database migration, no index format change, no file system migration required.

**Rollback:** Git revert. No persistent state is affected by the tool surface change.

## Open Questions

- Should `get_structure` for DOCX include table-type blocks inline (with row count but no cell data), or only return paragraph-type blocks? The analysis indicates table blocks should appear in the structure outline — this needs to be confirmed in the spec.
- Should `write_node` for XLSX cells accept a raw Python value (int, float, str) or always require a string that gets type-coerced? The existing `write_cell` accepts a string; preserving that avoids a behavior change.
