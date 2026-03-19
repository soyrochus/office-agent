## Why

The application already has the service layer needed for indexing, search, read, and write workflows, but those capabilities are only available through the local CLI. Exposing the same operations through MCP now makes the agent usable from MCP-compatible clients without forking business logic or creating a second integration surface to maintain.

## What Changes

- Add an MCP server on stdio using the official MCP Python SDK and expose it through the `office-agent mcp` CLI entry point.
- Expose the existing document workflows in `app/services.py` as MCP tools for indexing, refresh, listing, search, locate, read, replace, append, and cell writes.
- Define MCP tool input and output schemas from the same Pydantic models used by the service and CLI layers so results stay consistent across interfaces.
- Map service-layer failures to structured MCP errors with descriptive messages instead of leaking raw exceptions across the protocol boundary.
- Add integration coverage that starts the MCP server, exercises the tool surface against the fixture corpus, and verifies schema-valid responses across supported file types.

## Capabilities

### New Capabilities
- `mcp-stdio-server`: Start an MCP server over stdio from `office-agent mcp`, advertise the Office Agent tool surface, and reuse the shared application configuration.
- `mcp-service-tools`: Expose the existing indexing, search, locate, read, replace, append, refresh, list, and write-cell service operations as MCP tools with shared request and response schemas.
- `mcp-error-mapping`: Translate service-layer failures into structured MCP error responses with stable messages suitable for MCP clients and integration tests.

### Modified Capabilities
None.

## Impact

This change affects CLI command dispatch, a new `interfaces/mcp.py` integration layer, shared schema definitions used by the service boundary, and the test harness needed to drive MCP tool calls over stdio. It also introduces the official MCP Python SDK as an interface dependency while preserving `app/services.py` as the single source of business logic.
