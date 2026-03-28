# Tools V2 Proposal

Formal proposal for a broader Office Agent MCP tool surface that provides practical object-level access to the underlying `python-docx`, `python-pptx`, and `openpyxl` capabilities while preserving compatibility with the current indexing, keyword search, semantic embedding, and hybrid search model.

Date: March 2026

## 1. Executive Summary

The current simplified MCP surface is effective for document discovery, structural inspection, and leaf-node updates. It is not sufficient for the broader class of office automation workflows that require agents to add, delete, move, copy, and reorganize meaningful document objects such as slides, shapes, paragraphs, tables, sheets, rows, and cells.

This proposal defines a Tools V2 surface built around object lifecycle operations rather than leaf-node text replacement alone.

The central design choice is:

- preserve the current indexing and search subsystem as-is in principle
- introduce a document-object layer above the three underlying libraries
- keep a compact generic MCP core
- add explicit format-specific escape hatches only where necessary

This proposal does not aim for pixel-perfect desktop publishing, macro execution, or total parity with every detail of the three libraries. It aims for strong practical coverage of the majority of office-document operations an AI agent should perform in a normal office environment.

## 2. Scope

### 2.1 Goals

Tools V2 SHALL enable an AI agent to:

- discover relevant content through indexing and search
- traverse document structures through stable locators
- inspect meaningful document objects and their children
- update content and selected properties of existing objects
- create new objects where supported
- delete existing objects where supported
- move, reorder, or copy objects where supported
- perform multi-step document edits with explicit batching semantics

### 2.2 Non-goals

Tools V2 SHALL NOT target:

- macro execution
- embedded-object execution
- raw Office desktop feature parity
- high-end DTP or pixel-perfect layout authoring
- arbitrarily large-document optimization beyond current practical limits
- unrestricted raw XML mutation as a mainstream workflow

## 3. Compatibility Guarantee

Tools V2 MUST remain compatible with the current indexing and search model.

### 3.1 Preserved capabilities

The following capabilities SHALL remain present and supported:

- explicit document indexing
- explicit document refresh/reindex
- textual search
- vector-embedding semantic search
- hybrid keyword plus semantic search
- search filtering by document and file type
- search hit previews and relevance scores

### 3.2 Compatibility guarantee

Tools V2 SHALL preserve compatibility with the current discovery model by guaranteeing that:

- the index remains the discovery layer for Office content
- search remains a first-class capability, not a compatibility shim
- semantic search continues to use persisted embeddings where configured
- hybrid search continues to combine lexical and semantic evidence
- search results continue to resolve to stable document object locators
- object mutation workflows continue to trigger reindexing of the output document version

### 3.3 Search subsystem invariants

The system SHALL guarantee all of the following:

- `index_documents` remains explicit
- `refresh_document` remains explicit
- `search_documents` or its V2 equivalent continues to support `keyword`, `semantic`, and `hybrid` modes
- every search hit returns a locator that is directly usable in object inspection and mutation workflows
- document writes MUST preserve or regenerate object addresses in a way that stale-locator errors remain detectable and explicit

This proposal is additive at the object-access layer and does not replace the indexing or embedding architecture.

## 4. Problem Statement

The current simplified MCP surface solved tool proliferation by collapsing many read and write operations into a small semantic set. That simplification left a practical gap:

- update is reasonably covered
- create is partially covered
- delete is not covered
- structural manipulation is only lightly covered

This leaves the tool surface too narrow for common office tasks such as:

- adding a slide or duplicating an existing one
- deleting a shape from a slide
- inserting a DOCX table or deleting a paragraph
- inserting worksheet rows and columns and deleting them later
- copying objects from one document region to another
- reordering blocks or container children

The result is a surface that is architecturally cleaner than the pre-simplification API but operationally underpowered for normal authoring and restructuring workflows.

## 5. Design Principles

### 5.1 Preserve discovery, expand operations

Search and indexing are not the problem. Tools V2 SHALL preserve the current discovery side and expand the operational side.

### 5.2 Object lifecycle over raw library exposure

The MCP surface SHALL expose object lifecycle operations, not direct wrappers around raw library methods.

This avoids reproducing the full complexity of the three Python libraries while still making their practical capabilities accessible.

### 5.3 Stable typed locators

Every meaningful object SHALL have a stable locator string usable across inspection, search bridging, and mutation.

### 5.4 Explicit capability reporting

Every returned object SHALL advertise what operations are supported on it.

This is necessary because not every object can be updated, deleted, or have children added.

### 5.5 Small generic core, explicit format-specific escape hatches

The core tool set SHALL be generic and regular. Format-specific tools SHALL exist only where a generic object model becomes unnatural or lossy.

### 5.6 Batched mutation support

The surface SHALL support batched edits so a realistic office workflow does not require many fragile single-step calls.

## 6. Conceptual Model

Tools V2 SHALL organize the system around the following concepts:

- `document`: one indexed Office file
- `object`: one meaningful structural or content-bearing item inside a document
- `locator`: stable typed address of an object
- `object_type`: the semantic class of the object
- `parent`: the containing object or document root
- `children`: ordered contained objects
- `capabilities`: supported operations for that object
- `properties`: structured editable and non-editable metadata
- `search_hit`: discovery result pointing to an object locator
- `mutation_result`: structured result of an add, update, delete, move, or copy operation
- `batch`: atomic sequence of object mutations

## 7. Locator Model

Tools V2 SHOULD use typed, format-aware, agent-readable locators.

Examples:

- `docx:para:12`
- `docx:table:2`
- `docx:table:2:row:1:cell:3`
- `pptx:slide:4`
- `pptx:slide:4:shape:7`
- `pptx:slide:4:notes`
- `xlsx:sheet:Revenue`
- `xlsx:sheet:Revenue!B12`
- `xlsx:sheet:Revenue:row:14`

The exact string grammar may vary, but the model SHALL guarantee:

- uniqueness within one document version
- direct usability across all relevant tools
- explicit stale-locator failure on invalidation after mutation

## 8. Object Model by Format

### 8.1 DOCX

Tools V2 SHOULD treat the following as first-class object types:

- document
- section
- paragraph
- run
- table
- table_row
- table_cell
- image
- page_break

### 8.2 PPTX

Tools V2 SHOULD treat the following as first-class object types:

- presentation
- slide
- notes
- shape
- text_shape
- image_shape
- table
- table_row
- table_cell
- group_shape

### 8.3 XLSX

Tools V2 SHOULD treat the following as first-class object types:

- workbook
- worksheet
- row
- column
- cell
- range
- table
- merged_range
- formula_cell
- named_range

## 9. Generic MCP Core

The V2 core tool surface SHOULD be centered on the following generic tools.

### 9.1 `index_documents`

Purpose: index one or more Office documents or directories.

Required inputs:

- `paths`

Important optional inputs:

- `with_embeddings`

Guarantee:

- fully compatible with existing indexing semantics

### 9.2 `refresh_document`

Purpose: refresh an indexed document after external changes.

### 9.3 `list_documents`

Purpose: list indexed documents and basic metadata.

### 9.4 `search_objects`

Purpose: search indexed content and return object locators rather than only format-specific leaf identities.

Required inputs:

- `query`

Important optional inputs:

- `mode = keyword | semantic | hybrid`
- `document_id`
- `file_type`
- `object_type`
- `limit`

Guarantee:

- text indexing and vector embedding workflows remain compatible
- semantic and hybrid modes remain available
- locators remain directly usable in object inspection and mutation tools

### 9.5 `get_object`

Purpose: read one object and its structured content, metadata, properties, and capabilities.

Required inputs:

- `document_id`
- `locator`

Output shape:

- `locator`
- `object_type`
- `preview`
- `properties`
- `capabilities`
- `parent_locator`
- `child_summary`

### 9.6 `list_children`

Purpose: list ordered child objects under one container.

Required inputs:

- `document_id`
- `locator`

Important optional inputs:

- `child_type`
- `limit`

### 9.7 `create_object`

Purpose: create a new child object under a parent container.

Required inputs:

- `document_id`
- `parent_locator`
- `object_type`
- `properties`

Important optional inputs:

- `position`
- `output_mode`

### 9.8 `update_object`

Purpose: update an existing object's content or editable properties.

Required inputs:

- `document_id`
- `locator`
- `properties`

Important optional inputs:

- `output_mode`

### 9.9 `delete_object`

Purpose: remove one object from a document where the object's capabilities allow deletion.

Required inputs:

- `document_id`
- `locator`

Important optional inputs:

- `output_mode`

### 9.10 `move_object`

Purpose: reorder or reparent an object where the object model supports moving.

Required inputs:

- `document_id`
- `locator`

Important optional inputs:

- `new_parent_locator`
- `position`
- `output_mode`

### 9.11 `copy_object`

Purpose: duplicate an object and place the copy in the same or another valid parent.

Required inputs:

- `document_id`
- `locator`

Important optional inputs:

- `target_parent_locator`
- `position`
- `output_mode`

### 9.12 `batch_edit`

Purpose: execute a sequence of object operations atomically.

Required inputs:

- `document_id`
- `operations`

Important optional inputs:

- `output_mode`
- `dry_run`

Why it is required:

- real office edits frequently span multiple objects
- batching is the minimum safe mechanism for non-trivial authoring workflows

## 10. Format-Specific Escape Hatches

The generic core SHALL be supplemented by a small number of format-specific tools where the generic object model is insufficient.

### 10.1 DOCX escape hatches

Candidate tools:

- `docx_set_paragraph_style`
- `docx_insert_page_break`
- `docx_add_table`
- `docx_merge_table_cells`

### 10.2 PPTX escape hatches

Candidate tools:

- `pptx_add_slide`
- `pptx_duplicate_slide`
- `pptx_set_slide_layout`
- `pptx_add_text_shape`

These are necessary because slide creation and shape placement are not cleanly expressible as generic parent-child creation without layout semantics.

### 10.3 XLSX escape hatches

Candidate tools:

- `xlsx_write_range`
- `xlsx_insert_rows`
- `xlsx_insert_columns`
- `xlsx_set_formula`
- `xlsx_merge_cells`

These are necessary because worksheets have strong two-dimensional semantics that exceed a simple object-tree model.

## 11. Capability Model

Every object returned by Tools V2 SHALL include explicit capabilities.

Example capability fields:

- `read`
- `update`
- `delete`
- `add_child`
- `move`
- `copy`
- `style`

Example:

- a DOCX paragraph may support `read`, `update`, `delete`, `move`, `copy`
- a PPTX slide may support `read`, `update`, `delete`, `add_child`, `copy`, `move`
- an XLSX worksheet may support `read`, `add_child`, `update` but not `delete` if workbook policy disallows it

This capability model is required so the agent can act without guessing which operations are valid.

## 12. Search and Embedding Compatibility Detail

Tools V2 SHALL leave text indexing and vector embedding/searching intact.

### 12.1 Search as discovery

Search remains the primary discovery mechanism.

`search_objects` SHALL preserve:

- keyword search over indexed textual content
- semantic search over stored embeddings
- hybrid search over keyword and semantic evidence

### 12.2 Search unit strategy

The indexed unit MAY remain format-native.

Examples:

- DOCX paragraphs
- PPTX text shapes
- XLSX cells or row-level semantic groupings

Tools V2 does not require a single standardized search unit. It requires a standardized search result contract.

### 12.3 Search bridge guarantee

Every search hit SHALL include:

- `document_id`
- `locator`
- `object_type`
- `preview`
- `score`
- `match_mode`

The `locator` SHALL be directly usable in:

- `get_object`
- `update_object`
- `delete_object`
- `move_object`
- `copy_object`

This is the compatibility bridge between the current indexing architecture and the V2 object-lifecycle architecture.

## 13. Mutation Semantics

### 13.1 Output modes

All mutation tools SHALL continue to support `versioned` and `inplace` output modes.

### 13.2 Reindexing

All successful mutation tools SHALL reindex the output document before returning.

### 13.3 Stale locators

All mutation tools SHALL fail explicitly on stale locators.

### 13.4 Validation

Mutation tools SHALL validate object-type-specific property payloads before writing.

## 14. Migration Strategy

Tools V2 SHOULD be introduced as an additive layer rather than a breaking replacement.

### 14.1 Preserve V1 discovery tools

The current indexing and search tools SHOULD remain available or be aliased to their V2 equivalents.

### 14.2 Map current V1 tools into V2 concepts

- `get_node` maps naturally to a narrow form of `get_object`
- `write_node` maps naturally to a narrow form of `update_object`
- `insert_content` maps to `create_object` for DOCX paragraphs
- `xlsx_insert_rows` maps to `create_object` or `xlsx_insert_rows` as an XLSX-native bulk escape hatch

### 14.3 Introduce container-first access gradually

The first implementation phase SHOULD add object-capability inspection and container traversal before full delete and move support.

### 14.4 Deletion last

Delete support SHOULD be introduced after create, update, and batch semantics are stable, because delete creates the highest correctness risk.

## 15. Recommended Phasing

### Phase 1

- introduce `get_object`
- introduce `list_children`
- introduce `update_object` as a compatibility facade over existing write behavior
- preserve indexing and search unchanged

### Phase 2

- introduce `create_object`
- introduce `copy_object`
- introduce `move_object`
- introduce `batch_edit`

### Phase 3

- introduce `delete_object`
- add format-specific escape hatches for PPTX slide and shape creation, DOCX table creation, and XLSX structural worksheet operations

## 16. Final Recommendation

Office Agent SHOULD evolve from a node-editing MCP surface into an object-lifecycle MCP surface.

The preferred architecture is:

- preserve the current indexing and search subsystem
- preserve keyword, semantic, and hybrid search modes
- keep search hits as the discovery bridge into object operations
- adopt stable typed locators for all meaningful objects
- expose a small generic CRUD-style but capability-aware object core
- supplement the core with a narrow, explicit set of format-specific tools
- require reindexing and stale-locator safety for all mutations

This approach gives the agent broad practical access to the underlying libraries without collapsing into raw-library chaos, without discarding the current search architecture, and without requiring perfect parity with every low-level Office feature.
