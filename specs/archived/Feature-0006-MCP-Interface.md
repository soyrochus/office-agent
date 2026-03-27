# Feature 0006 — MCP Interface

## Goal

Expose all application services as MCP tools over stdio transport, making the agent usable from any MCP-compatible client without duplicating business logic.

## Scope

### Included

* `interfaces/mcp.py` — thin MCP server using the official MCP Python SDK
* Transport: stdio (required); SSE/streamable HTTP explicitly deferred
* All required MCP tools implemented as thin wrappers over `app/services.py`:
  * `index_documents(paths: list[str]) -> IndexResult`
  * `refresh_document(document_id: str) -> IndexResult`
  * `list_documents() -> list[DocumentRef]`
  * `search_documents(query: str, file_type: str | None, document_id: str | None, limit: int = 20) -> list[SearchHit]`
  * `locate_item(document_id: str, locator: str) -> ItemRef`
  * `read_item(document_id: str, item_id: str) -> ReadResult`
  * `replace_text(document_id: str, item_id: str, new_text: str, output_mode: str = "versioned") -> WriteResult`
  * `append_text(document_id: str, item_id: str, text_to_add: str, output_mode: str = "versioned") -> WriteResult`
  * `write_cell(document_id: str, sheet: str, cell: str, value: str, output_mode: str = "versioned") -> WriteResult`
* MCP server launch via `office-agent mcp` subcommand
* Tool input/output schemas defined via Pydantic models shared with the CLI service layer
* Error mapping: service-layer exceptions map to structured MCP error responses with descriptive messages

### Excluded

* MCP resources and prompts (optional per spec §8.2)
* SSE or streamable HTTP transport
* Any business logic not already implemented in F1–F5

## Design Constraints

* The MCP layer must contain zero business logic — all logic lives in `app/services.py`
* Tool schemas must be derivable from the same Pydantic models used by the CLI
* No separate config for MCP; reuse the shared config loader

## CLI Entry Point

```
office-agent mcp
```

Starts the MCP server on stdio. No additional arguments required for MVP.

## Acceptance Criteria

* `office-agent mcp` starts without error and responds to MCP tool list request
* Each tool returns a result structure matching its defined schema
* Tool behavior is identical to the equivalent CLI command for all three file formats
* An MCP client (or test harness) can complete a full index → search → locate → read → replace cycle against the fixture corpus
* Integration tests start the server, invoke each tool, and validate schema and result content
