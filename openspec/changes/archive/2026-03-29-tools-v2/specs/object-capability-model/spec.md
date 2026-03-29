## ADDED Requirements

### Requirement: Per-object capability advertisement
Every object returned by `get_object`, `list_children`, and any mutation result SHALL include a `capabilities` field enumerating the operations supported on that object. Capabilities SHALL be computed from the object's type, position in the container hierarchy, and applicable document policy at fetch time. The defined capability flags are: `read`, `update`, `delete`, `add_child`, `move`, `copy`, `style`.

#### Scenario: Object response includes capabilities
- **WHEN** an MCP client calls `get_object` for any indexed document object
- **THEN** the response includes a `capabilities` field listing the operations that are valid for that specific object instance

#### Scenario: Capabilities reflect container position
- **WHEN** an MCP client calls `get_object` for a document root object
- **THEN** `delete` is absent from the capabilities (document root cannot be deleted)

#### Scenario: PPTX slide advertises expected capabilities
- **WHEN** an MCP client calls `get_object` for a PPTX slide
- **THEN** the capabilities include `read`, `update`, `delete`, `add_child`, `copy`, `move`

### Requirement: Capability-gated operation enforcement
Mutation tools SHALL enforce capabilities at call time. Any mutation tool invoked on an object that does not advertise the required capability SHALL return a ToolError before attempting any document modification.

#### Scenario: Update blocked by missing capability
- **WHEN** an MCP client calls `update_object` on an object whose capabilities do not include `update`
- **THEN** the server returns a ToolError with a message indicating the operation is not supported on this object type

#### Scenario: Delete blocked by missing capability
- **WHEN** an MCP client calls `delete_object` on an object whose capabilities do not include `delete`
- **THEN** the server returns a ToolError without writing any output file

### Requirement: Capability freshness
Capabilities are computed from live document state and are not persisted. A caller that reads capabilities from one `get_object` response and acts on them in a subsequent mutation call SHALL receive a stale-locator error if the document was modified between the two calls, ensuring capabilities cannot be stale in a way that leads to a silent wrong write.

#### Scenario: Stale capabilities cause stale-locator error, not silent mutation
- **WHEN** a document is modified externally after an agent reads an object's capabilities
- **THEN** the subsequent mutation call fails with a stale-locator error before any capability check is applied
