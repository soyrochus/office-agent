## ADDED Requirements

### Requirement: create_document triggers automatic reindex
The system SHALL index the newly created document immediately after `create_document` writes the file, making it addressable by `document_id` without a separate manual reindex step.

#### Scenario: Created document is searchable immediately
- **WHEN** `create_document` succeeds
- **THEN** the new document is indexed and its `document_id` is valid for use in subsequent tool calls without any intervening reindex command

#### Scenario: create_document result exposes the output path
- **WHEN** `create_document` succeeds
- **THEN** the returned `MutationResult` includes the path of the written and indexed file
