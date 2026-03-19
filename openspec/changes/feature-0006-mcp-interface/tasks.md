## 1. MCP Server Foundation

- [x] 1.1 Add the official MCP Python SDK to project dependencies and update any startup validation needed for the new interface
- [x] 1.2 Create the MCP server module under `src/offagent/interfaces/` and wire stdio server startup through a dedicated entry function
- [x] 1.3 Add the `office-agent mcp` Typer subcommand and route it through the shared `load_config` path used by existing CLI commands

## 2. Transport Schemas And Shared Adapters

- [x] 2.1 Add Pydantic request and response models for the MCP tool surface without replacing the existing domain dataclasses
- [x] 2.2 Implement conversion helpers from `DocumentRef`, `ItemRef`, `SearchHit`, `IndexSummary`, and `PatchResult` into MCP response models
- [x] 2.3 Add a shared document-id resolution helper that maps indexed `document_id` values back to canonical document paths for MCP-only workflows

## 3. MCP Tool Handlers

- [x] 3.1 Implement MCP tools for `index_documents`, `refresh_document`, and `list_documents` as thin wrappers over `AppServices`
- [x] 3.2 Implement MCP tools for `search_documents`, `locate_item`, and `read_item` with argument normalization and structured responses
- [x] 3.3 Implement MCP tools for `replace_text`, `append_text`, and `write_cell` so they preserve existing write semantics and return structured write results
- [x] 3.4 Register the complete tool list and ensure each tool advertises explicit input schemas during MCP tool discovery

## 4. Error Mapping And Protocol Behavior

- [x] 4.1 Map expected service-layer failures into structured MCP errors with stable, descriptive messages
- [x] 4.2 Preserve stale-locator failures as a distinct MCP error path for write operations against drifted source files
- [x] 4.3 Ensure unexpected handler failures surface as internal MCP errors without leaking raw Python exception details

## 5. Integration Testing And Verification

- [x] 5.1 Add a subprocess-based stdio MCP test harness that initializes the server, lists tools, and performs tool calls deterministically
- [x] 5.2 Add integration tests covering document indexing, search, locate, and read flows through MCP against the fixture corpus
- [x] 5.3 Add integration tests covering `replace_text`, `append_text`, and `write_cell` MCP workflows, including cross-format behavior and structured results
- [x] 5.4 Add integration tests for expected MCP error responses, including invalid inputs and stale-locator failures
- [x] 5.5 Run the relevant test suite and verify the MCP acceptance criteria end to end
