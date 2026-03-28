## Why

The current Office Agent surface is optimized for indexing, search, and item-level reads and writes, which forces clients to reconstruct document semantics from low-level fragments. We need a uniform semantic layer across DOCX, PPTX, and XLSX so agents can inspect structure and perform deterministic structured transformations through generic MCP tools instead of format-specific workflows.

## What Changes

- Add generic document-structure tools that expose top-level structure for Word, PowerPoint, and Excel documents.
- Add PowerPoint semantic retrieval tools for slide-level bundles and notes access.
- Add Excel semantic retrieval and write tools for sheet snapshots, row appends, and table writes.
- Add Word semantic retrieval tools for ordered document blocks and paragraph-oriented access beyond the indexed paragraph search surface.
- Extend the MCP service tool contract and schemas to advertise and validate the new semantic tool surface.

## Capabilities

### New Capabilities

- `document-structure-tools`: Cross-format tools for retrieving document, presentation, workbook, and document-block structure in a consistent semantic shape.
- `pptx-slide-bundles`: PowerPoint slide-level semantic access, including slide metadata, bundled text blocks, and speaker notes retrieval.
- `xlsx-structured-table-writes`: Excel sheet snapshots and structured row/table write operations that work on logical workbook data instead of single-cell edits.
- `docx-document-blocks`: Word document block and paragraph access that exposes ordered paragraphs, headings, and tables as logical document units.

### Modified Capabilities

- `mcp-service-tools`: Expand the MCP tool catalog, schemas, and response contracts to include the new semantic document tools across DOCX, PPTX, and XLSX.

## Impact

- Shared document service and MCP server tool registration
- DOCX, PPTX, and XLSX adapters plus semantic aggregation layer
- Tool input/output transport models and schema validation
- Integration and acceptance coverage for structured document workflows
