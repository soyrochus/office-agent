## Why

Office Agent can currently style only inline structures that already exist as addressable runs, which makes partial formatting unreliable across DOCX, PPTX, and XLSX when the document does not already expose the desired segmentation. This change is needed now because the current mutation model forces callers to work around native run structure instead of letting the adapters synthesize and rewrite inline fragments on demand.

## What Changes

- Extend `style_inline` so it can target either an existing inline locator or a parent text-bearing object plus a character range.
- Extend `update_object` so text-bearing objects can be rewritten from structured text segments instead of only a flat text blob.
- Allow `create_object` to accept optional inline segments for text-bearing objects while keeping block/container creation semantics unchanged.
- Introduce a shared internal text-fragment abstraction that adapters use to read, split, normalize, and rewrite inline content across DOCX, PPTX, and XLSX.
- Define explicit failure behavior for unsupported partial-formatting targets such as non-text PPTX shapes, XLSX formulas, numeric cells, and other cases where partial inline styling cannot be safely applied.

## Capabilities

### New Capabilities
- `partial-inline-formatting`: Cross-format partial inline formatting for text-bearing objects using parent-object ranges, structured text segments, and adapter-managed fragment rewriting.

### Modified Capabilities
- `docx-paragraph-editing`: Expand DOCX paragraph editing from whole-paragraph text replacement to segment-aware rewriting that can preserve paragraph properties while rebuilding runs.
- `pptx-text-shape-editing`: Expand PPTX text-shape editing to support paragraph-level range targeting and run splitting inside text frames.
- `xlsx-cell-editing`: Expand XLSX cell editing so string cells can be promoted to rich text for partial inline formatting while unsupported cell types fail clearly.
- `mcp-service-tools`: Update existing MCP tool contracts for `create_object`, `update_object`, and `style_inline` so they accept the new range- and segment-based inputs without adding a new tool.

## Impact

- Affected code: V2 object mutation paths, shared domain models for inline fragments, format adapters for DOCX/PPTX/XLSX text rewriting, service-layer mutation dispatch, and MCP request models/tool schemas.
- Affected APIs: existing `create_object`, `update_object`, and `style_inline` inputs and validation rules; no new top-level tool is introduced.
- Dependencies and libraries: continued use of `python-docx`, `python-pptx`, and `openpyxl`, with richer use of each library's native run or rich-text structures.
- Testing: new adapter, service, and MCP acceptance coverage for range-based inline styling, segment-based updates, normalization, and unsupported-target rejection.
