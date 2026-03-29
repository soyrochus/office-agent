---
name: office-documents
description: Use the workspace Office/document-agent MCP for Word, Excel, and PowerPoint operations. Force MCP-first workflows and use the latest OpenSpec-documented capabilities before any fallback.
license: MIT
compatibility: Requires the workspace MCP server named office-agent when available.
metadata:
  author: workspace
  version: "2.0"
---

Use this skill whenever the user asks to inspect, search, index, navigate, create, transform, style, or modify Microsoft Office documents in this workspace.

Supported formats:
- DOCX (Word)
- XLSX (Excel)
- PPTX (PowerPoint)

Office-document work in this workspace must follow a strict MCP-first workflow.

## Core Rule

For any operation involving DOCX, XLSX, or PPTX files, you MUST use the workspace Office/document-agent MCP first. In this workspace, that MCP server is `office-agent` as configured in `.vscode/mcp.json`.

Only use the local CLI fallback if the MCP is not available. "Not available" means one of these:
- the office-agent MCP tools are not exposed in the current session
- the MCP server cannot be started or connected to
- MCP calls fail repeatedly because of transport or availability issues rather than a document or user-input error

Do not bypass MCP just because a CLI command or a local library exists.

Do not use `read_file`, zip inspection, XML scraping, `python-docx`, `python-pptx`, `openpyxl`, or any other direct file-manipulation approach for normal DOCX/PPTX/XLSX work when MCP can handle the task.

## MCP Server Context

This workspace configures the MCP server in `.vscode/mcp.json` as `office-agent`.

When MCP is available, prefer the latest OpenSpec-documented tool surface instead of older locate/replace/append mental models.

### Preferred MCP tool families

Discovery and indexing:
- `index_documents`
- `list_documents`
- `refresh_document`
- `search_objects`
- `search_documents` only as a deprecated compatibility alias

Structured navigation:
- `get_structure`
- `get_section`
- `get_node`
- `docx_get_tables`

Typed object traversal:
- `get_object`
- `list_children`

Generic V2 object lifecycle:
- `create_object`
- `update_object`
- `move_object`
- `copy_object`
- `batch_edit`
- `delete_object`

Cross-format mutation and insertion:
- `write_node`
- `insert_content`
- `xlsx_insert_rows`

Document creation and styling:
- `create_document`
- `add_content_block`
- `style_inline`
- `style_block`
- `set_structural_role`

Format-specific escape hatches:
- DOCX: `docx_set_paragraph_style`, `docx_insert_page_break`, `docx_add_table`, `docx_merge_table_cells`
- PPTX: `pptx_add_slide`, `pptx_duplicate_slide`, `pptx_set_slide_layout`, `pptx_add_text_shape`
- XLSX: `xlsx_write_range`, `xlsx_insert_columns`, `xlsx_set_formula`, `xlsx_merge_cells`

Latest OpenSpec partial-formatting extensions:
- Prefer additive range-based inputs on `style_inline` when the advertised MCP schema supports parent text containers plus character ranges
- Prefer additive segment-based inputs on `create_object` and `update_object` when the advertised MCP schema supports structured text segments
- Do not invent a separate partial-formatting tool when the existing mutation tools already advertise the newer fields

## Required Behavior

1. Treat Office documents as MCP-managed content, not as zip archives or generic binary files.
2. Prefer indexed-document and object-model workflows over ad hoc file parsing.
3. If the target document is not indexed yet, index it through MCP before searching or editing.
4. Prefer the newest generic MCP capabilities before falling back to older or narrower patterns.
5. For complex multi-step edits, prefer `batch_edit` over a fragile sequence of independent single-step writes.
6. For document creation and styling tasks, prefer `create_document`, `add_content_block`, `style_inline`, `style_block`, and `set_structural_role` before dropping to format-specific escape hatches.
7. For structural navigation, prefer `get_structure`/`get_section` and `get_object`/`list_children` instead of reconstructing structure manually.
8. For search, prefer `search_objects`; treat `search_documents` as compatibility-only unless there is a clear reason to use it.
9. For partial formatting, use the existing mutation tools with their additive range/segment fields when the schema advertises them; respect documented format-specific limitations.
10. When reporting results, include the document name and the relevant locator, node id, object type, or output path when available.

## MCP-First Workflow

### Search or discovery

Use MCP to:
- list indexed documents if you need to see what is already available
- index one or more Office files if the target is not indexed
- search indexed content with `search_objects` unless compatibility requires `search_documents`

### Direct navigation

If the user gives a locator or document and position, use MCP structure/object tools instead of manual extraction.

Preferred order:
1. `get_structure` or `search_objects` to find the relevant area
2. `get_section` or `get_object` to inspect the target
3. `list_children` for typed traversal below the target
4. `get_node` only when the task is truly leaf-text oriented

### Edits

For edits, use MCP mutation tools first. After a write, rely on the tool's normal reindex behavior and continue from the returned `document_id`, `output_path`, or locator.

Preferred order:
1. `update_object` or `write_node` for direct replacements
2. `create_object` or `insert_content` for insertion
3. `batch_edit` for related multi-object edits
4. `style_inline` and `style_block` for presentation changes
5. Format-specific escape hatches only when the generic surface is insufficient

### Creation and authoring

For new Office artifacts or authored content:
- use `create_document` to create DOCX/PPTX/XLSX outputs
- use `add_content_block` for the compact cross-format creation surface
- use `set_structural_role` only for DOCX structural mapping
- use `docx_add_table`, `pptx_add_text_shape`, or XLSX escape hatches when the generic block tool is not the best fit

### Partial formatting and structured text

When the MCP schema advertises the latest OpenSpec extensions:
- use `style_inline` with parent text-object locators plus ranges for partial inline styling
- use `create_object` or `update_object` with structured text segments for mixed-format text
- follow documented behavior differences across formats

Current documented limitations to remember:
- DOCX and PPTX partial formatting is range/fragment based when supported by the surfaced schema
- XLSX partial inline styling may fall back to full-cell styling when rich-text granularity is not supported or practical
- unsupported targets must fail cleanly; do not switch away from MCP merely because a format rejects a given target

## CLI Fallback

If MCP is unavailable, use the local tool through the workspace CLI:

```bash
uv run office-agent --help
```

Preferred fallback commands:

```bash
uv run office-agent index <path>
uv run office-agent search "<query>"
uv run office-agent read --doc <path> --item <item-id>
uv run office-agent replace --doc <path> --item <item-id> --text "<text>"
uv run office-agent append --doc <path> --item <item-id> --text "<text>"
uv run office-agent write-cell --doc <path> --sheet <name> --cell <coord> --value "<value>"
```

Use CLI fallback only after you have determined that MCP is unavailable. Do not switch to CLI because of a normal business-rule error such as:
- document not indexed yet
- locator not found
- target not editable
- invalid sheet, cell, paragraph, or shape reference
- unsupported partial-formatting target
- style validation failure

Those are workflow or user-input issues and should be handled through the MCP path.

## Guardrails

- Do not use raw file reads, zip inspection, XML scraping, or third-party Office parsers when MCP is available.
- Do not edit DOCX, XLSX, or PPTX files directly outside office-agent unless the user explicitly asks for a non-office-agent approach.
- Do not prefer deprecated or compatibility-only paths when a newer OpenSpec-documented MCP capability exists.
- Do not flatten Office tasks into plain text workflows when the typed object model can preserve structure.
- Do not ignore MCP schemas for `create_object`, `update_object`, or `style_inline`; inspect and use the newer additive fields when they are surfaced.
- If MCP is unavailable and you fall back to CLI, state that clearly.
- Keep the operation scoped to the requested Office document task.

## Response Pattern

When this skill is used, behave like this:

1. Confirm the Office document task.
2. Use `office-agent` MCP tools first and prefer the latest OpenSpec-documented surface.
3. If indexing is required, do that before search, traversal, or edit.
4. For structure-aware tasks, use `get_structure`/`get_section` or `get_object`/`list_children` before mutating.
5. For multi-step edits, creation, styling, or partial formatting, prefer the relevant existing MCP tools over ad hoc workarounds.
6. If MCP is unavailable, say so briefly and use `uv run office-agent ...`.
7. Return the relevant document identifiers, locators, output paths, and mutation results.