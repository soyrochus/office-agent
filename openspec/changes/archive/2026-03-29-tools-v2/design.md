## Context

The current Office Agent MCP surface is built around four layers: format adapters (`docx_adapter`, `pptx_adapter`, `xlsx_adapter`), a domain model (`domain/models.py`), an orchestration layer (`app/services.py`), and an MCP interface (`interfaces/mcp.py`). The 11 current tools resolve to individual adapter calls through `AppServices`. Stale-locator detection works via SHA256 content hashes stored per document. Writes always produce a new indexed output file.

The gap is that adapters expose only leaf-node read/write operations. There is no object container traversal, no lifecycle operations beyond single-node text replacement, and no structured capability advertisement. The new object-lifecycle layer must sit between `AppServices` and the raw adapters without breaking any existing code paths.

## Goals / Non-Goals

**Goals:**
- Introduce a format-agnostic object layer that maps typed locators to document objects across all three formats
- Expose `get_object`, `list_children`, `create_object`, `update_object`, `delete_object`, `move_object`, `copy_object`, `batch_edit` as new MCP tools registered alongside existing tools
- Return per-object capability fields on every object response
- Extend the typed locator grammar and stale-locator machinery to cover all new object types
- Evolve `search_documents` → `search_objects` with backward-compatible aliasing
- Add format-specific escape hatch tools in a separate registration group
- Preserve all existing MCP tools, adapters, and indexing unchanged

**Non-Goals:**
- Replacing or refactoring the existing adapter layer internals
- Changing the SQLite schema, FTS5 indexing logic, or embedding pipeline
- Supporting raw XML mutation
- Building a migration path for external callers beyond aliasing `search_documents`

## Decisions

### D1 — Introduce a new `objects/` layer rather than extending adapters

**Decision:** Add `src/offagent/objects/` containing one resolver per format (`docx_objects.py`, `pptx_objects.py`, `xlsx_objects.py`) plus a common interface (`base.py`). The existing adapters remain unchanged.

**Rationale:** Adapters are already stable and tested. The object layer needs richer container semantics (parent/child traversal, capability computation, move/copy logic) that would bloat the adapters and create a mixed abstraction. A separate layer also makes the phased rollout clean — Phase 1 can ship `get_object` / `list_children` against only the new layer without touching adapter tests.

**Alternative considered:** Extend each adapter with new methods. Rejected because adapters are flat read/write helpers; adding recursive container logic couples the extraction pipeline to the mutation pipeline.

### D2 — Extend the existing `domain/locators.py` typed locator grammar

**Decision:** Extend the locator string grammar in `domain/locators.py` to cover the full V2 address space. The format prefix is mandatory (`docx:`, `pptx:`, `xlsx:`). Path components are colon-separated. Existing locators (`para:N`, `slide:N:S`, `sheet!A1`) remain valid and are re-expressed as `docx:para:N`, `pptx:slide:N:shape:S`, `xlsx:sheet:Name!B12` in V2 responses.

Existing short-form locators produced by search hits and current tools continue to resolve. V2 tools emit and consume only fully-qualified locators.

**Rationale:** The existing grammar is already format-aware at the adapter level. Centralising the grammar in one module keeps stale-locator detection and validation in one place. Fully-qualified locators eliminate the current ambiguity where `para:3` requires knowing which adapter to call.

**Alternative considered:** Opaque integer handle IDs (like database row IDs). Rejected because the spec requires agent-readable, stable, typed locators that survive across sessions without server state.

### D3 — Capability computation is stateless and driven by object type + context rules

**Decision:** Each format's object resolver computes `capabilities` as a frozen set at object-fetch time based on: the object's type, its position in the container hierarchy, and a small set of policy flags (e.g., whether `allow_inplace_overwrite` is set, whether the workbook has a single sheet). No capability state is persisted.

**Rationale:** Capabilities are deterministic from the document state. Persisting them would create a secondary consistency problem. Agents call `get_object` before acting, so freshness is guaranteed.

### D4 — `batch_edit` is serialised, not transactional

**Decision:** `batch_edit` executes operations sequentially against a single in-memory document copy, then writes the result once. On any operation failure, the partial in-memory state is discarded and the original file is unchanged. There is no two-phase commit across multiple documents.

**Rationale:** True ACID across Office XML files would require wrapping the entire python-docx/pptx/openpyxl document lifecycle in a transaction abstraction that does not exist. The single-document in-memory approach gives atomicity at the file level — the most common case — without over-engineering.

**Constraint:** `batch_edit` MUST operate on a single `document_id`. Cross-document batching is a Non-Goal.

### D5 — `search_objects` replaces `search_documents` with an alias

**Decision:** Register `search_objects` as the canonical V2 tool. Register `search_documents` as an alias that calls `search_objects` and strips the new fields (`object_type`, `match_mode`) from the response, returning the original shape. The alias is marked deprecated in the MCP tool description.

**Rationale:** The BREAKING change in the proposal is scoped to the result schema. Aliasing allows existing integrations to continue working. Removing the alias is deferred to a future breaking-change release.

### D6 — New tools are registered in a separate group in `mcp.py`

**Decision:** Add a `_register_v2_tools(mcp, services)` function below the existing tool registrations. Format-specific escape hatches are registered in `_register_escape_hatch_tools(mcp, services)`. This keeps the existing 11-tool block untouched and makes the V2 additions easy to review and audit.

### D7 — Object layer delegates writes back to existing adapter write paths where possible

**Decision:** `update_object` for text content delegates to the existing `adapter.write_node()` logic. The object layer only implements net-new write logic (create, delete, move, copy). This avoids duplicating the stale-locator check and reindex trigger already present in the adapters.

**Rationale:** `AppServices.write_node()` already handles the content-hash check, output path resolution, and reindex call correctly. Duplicating this in the object layer would create two diverging code paths for what is essentially the same mutation contract.

## Risks / Trade-offs

**Locator grammar migration** → Mitigation: Emit both short-form (for legacy tool compatibility) and long-form (for V2 tool responses) in a transitional period. The `locators.py` parser accepts both.

**`batch_edit` memory pressure on large documents** → Mitigation: Document the single-file constraint clearly; batch size is inherently bounded by the agent's tool-call budget.

**Capability computation diverges from actual mutability** → Mitigation: Any `TargetNotEditableError` raised by the adapter is surfaced as a tool error with a clear message; it does not silently succeed with wrong output. Agents learn capability limits from errors, not silent no-ops.

**`search_documents` alias drift** → Mitigation: Integration tests cover both the alias and the V2 form in the same test run.

**PPTX slide creation requires layout semantics** → Mitigation: `pptx_add_slide` is an explicit escape hatch (D6) that accepts a `layout_index` parameter; it is not attempted through the generic `create_object` path.

## Migration Plan

1. Ship Phase 1 (`get_object`, `list_children`) with the new `objects/` layer and extended locators — no breaking changes.
2. Ship Phase 2 (`create_object`, `copy_object`, `move_object`, `batch_edit`) + `search_objects` + `search_documents` alias.
3. Ship Phase 3 (`delete_object`) + all format-specific escape hatch tools.
4. Deprecation notice on `search_documents` alias added at Phase 2; removal targeted for a future major version.

Rollback at any phase: the `_register_v2_tools` block can be disabled by a config flag without touching the existing 11 tools.

## Open Questions

- Should `batch_edit` support a `dry_run` mode that validates operations without writing? The proposal mentions it as optional; decision deferred to specs.
- Should `object_capability_model` include a `style` capability flag, and if so what does it mean for XLSX (which has cell styles but no paragraph styles)? Format-specific capability sets may diverge from the generic list.
- What is the stale-locator policy when a `move_object` or `copy_object` produces a new locator for the same logical object? Resolved during `stale-locator-detection` spec delta work.
