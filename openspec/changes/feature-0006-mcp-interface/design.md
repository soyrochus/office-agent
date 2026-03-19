## Context

The current product surface is a Typer CLI rooted in [cli.py](/home/iwk/src/office-agent/src/offagent/interfaces/cli.py), with orchestration and business rules concentrated in [services.py](/home/iwk/src/office-agent/src/offagent/app/services.py). That service layer already supports the complete workflow needed by the feature brief: index and reindex, corpus search, item location, item reads, versioned writes, and stale-locator protection across DOCX, PPTX, and XLSX. Shared domain results such as `DocumentRef`, `ItemRef`, and `SearchHit` currently live as dataclasses in [models.py](/home/iwk/src/office-agent/src/offagent/domain/models.py), while configuration loading is centralized in [config.py](/home/iwk/src/office-agent/src/offagent/config.py).

This change adds a second interface layer, not a second implementation of document workflows. The MCP server must run on stdio, be exposed through `office-agent mcp`, reuse the same configuration loader, and keep `AppServices` as the single source of business logic. The main design pressure is at the boundary between the existing dataclass-based service API and the MCP Python SDK, which expects explicit tool schemas and structured error handling.

Constraints:
- The MCP layer must stay thin and avoid embedding search, locate, read, or write logic that belongs in `AppServices`.
- Stdio is the only transport in scope for this change.
- MCP inputs and outputs need stable machine-readable schemas, even though the current internal service return types are dataclasses and plain strings.
- CLI behavior must remain intact while adding a new interface entry point and dependency.
- Integration tests need to exercise the actual stdio server rather than only unit-testing wrapper functions.

## Goals / Non-Goals

**Goals:**
- Add an MCP stdio server that exposes the existing service workflows as tools without duplicating business logic.
- Introduce explicit request and response schemas for MCP tools that align with current service-layer semantics.
- Route `office-agent mcp` through the existing CLI package structure and reuse `load_config` for startup configuration.
- Map expected service failures into structured MCP errors with stable, descriptive messages.
- Add end-to-end tests that start the server and verify tool invocation across the supported file formats.

**Non-Goals:**
- Supporting SSE or streamable HTTP transports.
- Adding MCP resources, prompts, subscriptions, or other optional protocol features.
- Refactoring the full service layer from dataclasses to Pydantic models in this change.
- Changing existing business logic for indexing, search, location, reads, or writes except where interface-safe error shaping requires it.
- Introducing interface-specific configuration files or MCP-only runtime settings.

## Decisions

### 1. Add a dedicated `interfaces/mcp.py` server module and keep CLI registration in `interfaces/cli.py`

Decision:
Implement the MCP server in a new module such as `src/offagent/interfaces/mcp.py`, with `src/offagent/interfaces/cli.py` gaining a single `mcp` subcommand that loads config and launches the stdio server.

Rationale:
The project already separates interfaces from the service layer. Putting the MCP server beside the CLI keeps interface concerns isolated and lets the existing `office-agent` entry point own command registration without creating a second executable.

Alternatives considered:
- Put the full MCP server implementation directly inside `cli.py`.
  Rejected because it would overload the CLI module and blur the interface boundary.
- Create a separate console script just for MCP.
  Rejected because the feature brief explicitly calls for `office-agent mcp`.

### 2. Keep MCP tools as thin adapters over `AppServices`

Decision:
Each MCP tool handler should do only four things: validate input, construct or normalize simple Python values such as `Path`, call the corresponding `AppServices` method, and convert the result into an MCP response model.

Rationale:
`AppServices` already contains the required orchestration and error behavior, including write policies and stale-locator handling. Reusing that boundary preserves consistency with CLI behavior and avoids divergent fixes later.

Alternatives considered:
- Reimplement the workflows directly inside MCP tool handlers.
  Rejected because it would duplicate business logic and violate the feature constraints.
- Add a new MCP-specific service layer between MCP and `AppServices`.
  Rejected because the current abstraction surface is already sufficient and another layer would add indirection without clear value.

### 3. Introduce Pydantic transport models at the interface boundary instead of rewriting domain dataclasses

Decision:
Add a small set of Pydantic request and response models for the MCP surface, likely in a module such as `src/offagent/interfaces/mcp_models.py` or adjacent to the server module. Tool implementations should translate between those transport models and the existing dataclass return types from `services.py` and `domain/models.py`.

Rationale:
The brief requires schemas that can be exposed cleanly through MCP, while the current codebase uses dataclasses for domain and service results. A translation layer gives the MCP SDK explicit schemas now without forcing a cross-cutting domain-model rewrite in the same change.

Alternatives considered:
- Convert all service and domain dataclasses to Pydantic models.
  Rejected because it would expand the scope into a broad internal refactor with little direct user value for this feature.
- Expose ad hoc dictionaries from the MCP layer without typed models.
  Rejected because it weakens schema clarity and makes tool contracts harder to test.

### 4. Preserve current service method shapes and adapt only where naming differs from the feature contract

Decision:
Map MCP tool names and arguments to the existing service API, even where the names differ slightly. For example, `index_documents(paths)` can call `index_path` for each input path, `refresh_document(document_id)` can resolve the stored document path and then call `reindex_path`, `search_documents` wraps `search_corpus`, and write tools delegate to `replace_item_text`, `append_item_text`, and `write_cell_value`.

Rationale:
The current service methods already model the needed workflows but are optimized for the CLI boundary, which often works with paths rather than document ids. A narrow adapter layer lets the MCP contract stay user-facing and stable while preserving the internal API.

Alternatives considered:
- Rename all service methods to match MCP terminology before adding the interface.
  Rejected because the behavior can be adapted cheaply at the edge and wholesale renaming adds avoidable churn.
- Expose the CLI command surface directly as MCP tools.
  Rejected because the CLI formats output for humans, not structured protocol callers.

### 5. Add a document-id resolution helper in the service or interface layer for MCP refresh and read flows

Decision:
Add one narrow helper for resolving a stored `document_id` to its canonical path using the SQLite index, then reuse it in MCP-only workflows that naturally identify a document by id rather than path.

Rationale:
The proposed MCP contract includes `refresh_document(document_id)` and several responses already include `document_id`. Resolving ids centrally avoids leaking direct store queries through every tool handler and keeps refresh semantics consistent with existing indexed state.

Alternatives considered:
- Change the MCP contract to use only filesystem paths.
  Rejected because the feature brief already calls for document-id-based refresh and the indexed store already has stable document ids.
- Query the SQLite store independently inside each MCP tool.
  Rejected because repeated low-level queries would duplicate resolution logic and error handling.

### 6. Normalize known application exceptions into structured MCP errors

Decision:
Map expected failures such as `FileNotFoundError`, `LookupError`, `ValueError`, `RuntimeError`, and `StaleLocatorError` into MCP protocol errors with stable messages and machine-usable metadata where supported by the SDK. Unexpected exceptions should still surface as internal errors after logging-safe wrapping.

Rationale:
The CLI currently maps these failures to exit codes and stderr text. MCP clients need protocol-level errors instead of process exit semantics, but the underlying distinction between user-correctable failures and internal faults still matters.

Alternatives considered:
- Return error-shaped success payloads from tools.
  Rejected because it weakens protocol correctness and complicates client handling.
- Let raw Python exceptions bubble through the SDK.
  Rejected because it produces unstable messages and implementation leakage.

### 7. Test the interface with subprocess-backed stdio integration tests

Decision:
Add integration tests that launch `office-agent mcp` as a subprocess, perform the MCP initialization and tool-call sequence over stdio, and verify both schema shape and semantic parity for representative DOCX, PPTX, and XLSX workflows.

Rationale:
The key risk in this change is the protocol boundary, not the underlying business logic. The existing service tests already validate most domain behavior, so the new coverage should focus on server startup, tool registration, schema conformance, and error mapping across the real transport.

Alternatives considered:
- Unit-test only the Python functions behind the MCP handlers.
  Rejected because it would miss stdio startup, protocol registration, and serialization issues.
- Skip integration coverage because service tests already exist.
  Rejected because the acceptance criteria explicitly require a working MCP client or harness.

## Risks / Trade-offs

- [Transport models can drift from service dataclasses over time] -> Keep conversion helpers centralized and cover response shapes in integration tests.
- [Document-id-based refresh introduces a store lookup path not used by the CLI today] -> Implement one shared resolver with clear not-found errors and use it everywhere the MCP layer needs document ids.
- [The MCP SDK may encourage inline decorators that mix protocol and business concerns] -> Keep handlers thin and route all real work through `AppServices`.
- [Introducing a new dependency can affect local setup and `doctor` expectations] -> Add the SDK to project dependencies and extend environment validation if startup should fail fast when MCP support is missing.
- [Stdio protocol tests can be brittle if they depend on timing rather than message boundaries] -> Use a deterministic test harness that performs formal initialize, list-tools, and call-tool exchanges instead of sleeping or scraping logs.

## Migration Plan

1. Add the MCP SDK dependency and create the new MCP interface module plus any transport-model helpers.
2. Register `office-agent mcp` in the Typer app and wire startup through `load_config`.
3. Implement tool handlers for index, refresh, list, search, locate, read, replace, append, and write-cell by delegating to `AppServices`.
4. Add document-id resolution and exception-to-MCP error translation utilities needed by the MCP boundary.
5. Add subprocess-based integration tests that validate server startup, tool listing, successful workflows, and representative error cases.

Rollback:
Remove the MCP dependency, `mcp` subcommand, and interface module. The existing CLI and service layers remain unchanged because this feature is additive at the interface boundary.

## Open Questions

- Which MCP Python SDK package and server API should be treated as the project standard so the implementation matches current upstream conventions?
- Should `index_documents(paths)` return one aggregated summary object or a per-path result list when multiple inputs are supplied?
- Should `list_documents()` include filesystem paths directly in its response payload, or should it prefer document ids and display metadata with paths treated as implementation detail?
