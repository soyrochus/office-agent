## MODIFIED Requirements

### Requirement: Search, locate, and read tools
The system SHALL expose MCP tools for `search_objects`, `locate_item`, and `read_item` that preserve the same document-query behavior as the shared application service layer. `search_objects` SHALL accept an optional `mode` parameter with values `keyword`, `semantic`, or `hybrid`, defaulting to `keyword`. Every search hit returned by `search_objects` SHALL include `document_id`, `locator`, `object_type`, `preview`, `score`, and `match_mode`. The `locator` field SHALL be directly usable in `get_object`, `update_object`, `delete_object`, `move_object`, and `copy_object`. The legacy tool name `search_documents` SHALL remain available as a deprecated alias that returns the pre-V2 hit shape (omitting `object_type` and `match_mode`) for backward compatibility.

#### Scenario: Client searches and reads indexed content
- **WHEN** an MCP client indexes a fixture document and then calls `search_objects`, `locate_item`, and `read_item` with matching inputs
- **THEN** the server returns the same hit, locator, and content data that the equivalent application-service workflow would produce

#### Scenario: Client selects retrieval mode
- **WHEN** an MCP client calls `search_objects` with `mode="semantic"` or `mode="hybrid"`
- **THEN** the server executes the corresponding retrieval mode and returns mode-aware search hits from the shared service layer

#### Scenario: Search hit locator is usable in object tools
- **WHEN** an MCP client calls `search_objects` and receives a hit with a `locator` field
- **THEN** calling `get_object` with that `document_id` and `locator` succeeds and returns a structured object payload

#### Scenario: Legacy alias returns pre-V2 shape
- **WHEN** an MCP client calls the deprecated `search_documents` tool
- **THEN** the server returns search hits without `object_type` and `match_mode` fields, preserving the pre-V2 response shape
