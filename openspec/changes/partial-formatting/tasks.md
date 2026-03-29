## 1. Shared Fragment Model And Request Shapes

- [x] 1.1 Add shared domain models for inline fragments, text-container snapshots, and visible-text range inputs used by partial-formatting mutations
- [x] 1.2 Extend V2 mutation request validation so `create_object`, `update_object`, and `style_inline` accept additive `segments` and `range` inputs while rejecting ambiguous combinations
- [x] 1.3 Add shared fragment utility functions for splitting by character offsets and merging adjacent fragments with equivalent formatting

## 2. DOCX Partial-Formatting Support

- [x] 2.1 Add DOCX adapter helpers to read a paragraph into normalized inline fragments and visible-text offsets
- [x] 2.2 Add DOCX adapter helpers to rebuild a paragraph from normalized fragments while preserving paragraph style and paragraph-level formatting
- [x] 2.3 Extend DOCX `update_object` text-bearing paths to support segment-based paragraph rewriting
- [x] 2.4 Extend DOCX `create_object` text-bearing paths to accept optional inline segments when creating paragraph-like objects
- [x] 2.5 Extend DOCX `style_inline` handling to support parent paragraph locators plus visible-text ranges by splitting and rewriting runs
- [x] 2.6 Add explicit DOCX rejection behavior for paragraphs whose inline content cannot be safely reconstructed

## 3. PPTX Partial-Formatting Support

- [x] 3.1 Add PPTX adapter helpers to read one text-frame paragraph into normalized inline fragments and visible-text offsets
- [x] 3.2 Add PPTX adapter helpers to rebuild one text-frame paragraph from normalized fragments while preserving paragraph properties and shape structure
- [x] 3.3 Extend PPTX `update_object` text-bearing paths to support segment-based paragraph rewriting
- [x] 3.4 Extend PPTX `create_object` text-bearing paths to accept optional inline segments where text shapes are created
- [x] 3.5 Extend PPTX `style_inline` handling to support supported parent text locators plus visible-text ranges
- [x] 3.6 Add explicit PPTX rejection behavior for non-text shapes and unsupported multi-container range targets

## 4. XLSX Partial-Formatting Support

- [x] 4.1 Add XLSX adapter helpers to read a string cell as normalized plain-text or rich-text fragments
- [x] 4.2 Add XLSX adapter helpers to rewrite a supported cell from normalized fragments and promote plain strings to rich text on demand
- [x] 4.3 Extend XLSX `update_object` text-bearing paths to support segment-based rich-text rewriting for string-compatible cells
- [x] 4.4 Extend XLSX `create_object` text-bearing paths to accept optional inline segments for supported cell/text-bearing creation flows
- [x] 4.5 Extend XLSX `style_inline` handling to support parent cell locators plus visible-text ranges
- [x] 4.6 Add explicit XLSX rejection behavior for formulas, numeric cells, booleans, merged-cell edge cases, and other unsupported partial-formatting targets

## 5. Service, Locator, And MCP Integration

- [x] 5.1 Update object-service mutation orchestration to dispatch partial-formatting requests through the shared fragment-aware adapter paths without changing versioned-output and reindex behavior
- [x] 5.2 Extend typed locator handling and object resolution for any new parent/child text-container targets needed by range-based partial formatting
- [x] 5.3 Update MCP request models and tool schemas for `create_object`, `update_object`, and `style_inline` to advertise the additive `segments` and `range` fields
- [x] 5.4 Ensure MCP validation rejects unknown or incompatible partial-formatting payloads before any document mutation occurs

## 6. Verification And Regression Coverage

- [x] 6.1 Add unit tests for shared fragment split/merge normalization behavior and range validation
- [x] 6.2 Add DOCX tests for segment-based replacement, range-based inline styling, normalization, and unsupported-paragraph rejection
- [x] 6.3 Add PPTX tests for segment-based replacement, range-based inline styling, supported parent locator behavior, and non-text-target rejection
- [x] 6.4 Add XLSX tests for string-cell promotion to rich text, range-based inline styling, and unsupported-cell rejection
- [x] 6.5 Add service-layer tests covering backward-compatible plain-text mutations alongside the new `segments` and `range` workflows
- [x] 6.6 Add MCP tests verifying schema exposure, successful partial-formatting mutations, and error mapping for unsupported targets
