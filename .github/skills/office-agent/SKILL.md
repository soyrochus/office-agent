---
name: office-agent
description: Use the office-agent MCP for Word, Excel, and PowerPoint document operations in this workspace. Fall back to the local office-agent CLI only when the MCP is unavailable.
license: MIT
compatibility: Requires the workspace MCP server named office-agent when available.
metadata:
  author: workspace
  version: "1.0"
---

Use this skill whenever the user asks to inspect, search, index, locate, read, or modify Microsoft Office documents in this workspace.

Supported formats:
- DOCX (Word)
- XLSX (Excel)
- PPTX (PowerPoint)

Office-document work in this workspace must follow an MCP-first workflow.

## Core Rule

For any operation involving DOCX, XLSX, or PPTX files, use the office-agent MCP tools first.

Only use the local CLI fallback if the MCP is not available. "Not available" means one of these:
- the office-agent MCP tools are not exposed in the current session
- the MCP server cannot be started or connected to
- MCP calls fail repeatedly because of transport or availability issues rather than a document or user-input error

Do not bypass MCP just because a CLI command also exists.

## MCP Server Context

This workspace configures the MCP server in `.vscode/mcp.json` as `office-agent`.

When MCP is available, prefer these tool families:
- index documents
- list documents
- search documents
- locate item
- read item
- append text
- replace text
- write cell
- refresh document

## Required Behavior

1. Treat Office documents as MCP-managed content, not as zip archives or generic binary files.
2. Prefer indexed-document workflows over ad hoc file parsing.
3. If the target document is not indexed yet, index it through MCP before searching or editing.
4. Use write operations that match the document type:
   - DOCX: replace text, append text
   - PPTX: replace text, append text
   - XLSX: write cell, append text only when appropriate
5. When reporting results, include the document name and locator or item id when available.

## MCP-First Workflow

### Search or discovery

Use MCP to:
- list indexed documents if you need to see what is already available
- index one or more Office files if the target is not indexed
- search indexed content for the requested text

### Direct navigation

If the user gives a locator or document and position, use MCP locate and read operations instead of manual extraction.

### Edits

For edits, use MCP write tools first. After a write, rely on MCP refresh or the tool's normal indexing behavior if needed before subsequent reads.

## CLI Fallback

If MCP is unavailable, use the local tool through the workspace CLI:

```bash
uv run office-agent --help
```

Preferred fallback commands:

```bash
uv run office-agent index <path>
uv run office-agent search "<query>"
uv run office-agent locate --doc <path> ...
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

Those are workflow or user-input issues and should be handled through the MCP path.

## Guardrails

- Do not use raw file reads, zip inspection, XML scraping, or third-party Office parsers when MCP is available.
- Do not edit DOCX, XLSX, or PPTX files directly outside office-agent unless the user explicitly asks for a non-office-agent approach.
- If MCP is unavailable and you fall back to CLI, state that clearly.
- Keep the operation scoped to the requested Office document task.

## Response Pattern

When this skill is used, behave like this:

1. Confirm the Office document task.
2. Use office-agent MCP tools first.
3. If indexing is required, do that before search or edit.
4. If MCP is unavailable, say so briefly and use `uv run office-agent ...`.
5. Return the relevant document identifiers, locators, and results.