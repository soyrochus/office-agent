## ADDED Requirements

### Requirement: Object inspection
The system SHALL expose `get_object` and `list_children` MCP tools that return structured object representations for any document object addressable by a typed locator. Every object response SHALL include the object's locator, type, preview, properties, capabilities, parent locator, and a child summary.

#### Scenario: Agent reads a document object
- **WHEN** an MCP client calls `get_object` with a valid `document_id` and `locator`
- **THEN** the server returns a structured object payload containing locator, object_type, preview, properties, capabilities, parent_locator, and child_summary

#### Scenario: Agent traverses children
- **WHEN** an MCP client calls `list_children` with a valid container locator
- **THEN** the server returns an ordered list of child object summaries with locator, object_type, and preview for each child

#### Scenario: Invalid locator rejected
- **WHEN** an MCP client calls `get_object` with a locator that does not resolve to a known object in the current document version
- **THEN** the server returns a ToolError indicating stale or invalid locator

### Requirement: Object creation
The system SHALL expose a `create_object` MCP tool that inserts a new child object under a specified parent container. The tool SHALL accept `document_id`, `parent_locator`, `object_type`, `properties`, and an optional `position`. It SHALL refuse creation if the parent's capabilities do not include `add_child`.

#### Scenario: Agent adds a paragraph to a DOCX document
- **WHEN** an MCP client calls `create_object` with a DOCX document root or section as parent and `object_type=paragraph`
- **THEN** the server inserts a new paragraph at the specified position, writes the output document, reindexes it, and returns a mutation result with the new object's locator

#### Scenario: Creation refused for non-container
- **WHEN** an MCP client calls `create_object` targeting a parent whose capabilities do not include `add_child`
- **THEN** the server returns a ToolError without modifying the document

### Requirement: Object update
The system SHALL expose an `update_object` MCP tool that modifies the content or editable properties of an existing object. The tool SHALL refuse update if the object's capabilities do not include `update`.

#### Scenario: Agent updates a paragraph's text
- **WHEN** an MCP client calls `update_object` with a DOCX paragraph locator and a `text` property
- **THEN** the server replaces the paragraph text, writes the output, reindexes it, and returns a mutation result with the previous and new text

#### Scenario: Update refused for read-only object
- **WHEN** an MCP client calls `update_object` on an object whose capabilities do not include `update`
- **THEN** the server returns a ToolError without modifying the document

### Requirement: Object deletion
The system SHALL expose a `delete_object` MCP tool that removes an object from its parent. The tool SHALL refuse deletion if the object's capabilities do not include `delete`.

#### Scenario: Agent deletes a paragraph
- **WHEN** an MCP client calls `delete_object` with a valid deletable object locator
- **THEN** the server removes the object from the document, writes the output, reindexes it, and returns a mutation result

#### Scenario: Deletion refused for protected object
- **WHEN** an MCP client calls `delete_object` on an object whose capabilities do not include `delete`
- **THEN** the server returns a ToolError without modifying the document

### Requirement: Object move and copy
The system SHALL expose `move_object` and `copy_object` MCP tools. `move_object` repositions an object within the same parent or to a new valid parent. `copy_object` duplicates an object and places the copy at a specified position in a valid parent. Both tools SHALL refuse the operation if the object's capabilities do not include `move` or `copy` respectively.

#### Scenario: Agent reorders a slide
- **WHEN** an MCP client calls `move_object` with a PPTX slide locator and a new position index
- **THEN** the server reorders the slide, writes the output, reindexes it, and returns a mutation result with the updated locator

#### Scenario: Agent duplicates a slide
- **WHEN** an MCP client calls `copy_object` with a PPTX slide locator
- **THEN** the server inserts a copy of the slide at the specified position, writes the output, reindexes it, and returns a mutation result with the new locator

#### Scenario: Move refused for immovable object
- **WHEN** an MCP client calls `move_object` on an object whose capabilities do not include `move`
- **THEN** the server returns a ToolError without modifying the document

### Requirement: Batched mutation
The system SHALL expose a `batch_edit` MCP tool that executes a sequence of object operations against a single document atomically. If any operation in the sequence fails, the entire batch MUST be discarded and the original document MUST remain unchanged. The tool SHALL accept an optional `dry_run` flag that validates operations without writing.

#### Scenario: Agent applies a multi-step edit
- **WHEN** an MCP client calls `batch_edit` with a `document_id` and an ordered list of valid operations
- **THEN** the server applies all operations to an in-memory document copy, writes the result once, reindexes it, and returns a batch mutation result listing each operation's outcome

#### Scenario: Batch fails atomically on invalid operation
- **WHEN** an MCP client calls `batch_edit` and one operation in the sequence is invalid (e.g., stale locator, unsupported capability)
- **THEN** the server discards the in-memory state and returns a ToolError identifying the failing operation; the original document is unchanged

#### Scenario: Dry run validates without writing
- **WHEN** an MCP client calls `batch_edit` with `dry_run=true`
- **THEN** the server validates all operations and returns a plan result without writing any file or triggering reindexing

### Requirement: Stale-locator safety for all mutation tools
All object mutation tools (`create_object`, `update_object`, `delete_object`, `move_object`, `copy_object`, `batch_edit`) SHALL fail explicitly with a stale-locator error if the document has been externally modified since the locator was issued.

#### Scenario: Stale locator detected before write
- **WHEN** an MCP client calls any mutation tool with a locator against a document whose content hash has changed since indexing
- **THEN** the server returns a stale-locator ToolError and does not write any output file

### Requirement: Reindexing after mutation
All successful mutation tools SHALL reindex the output document before returning.

#### Scenario: Output document is indexed after write
- **WHEN** an MCP client calls any mutation tool and the write succeeds
- **THEN** the output document is indexed (or reindexed) before the tool returns its result
