## MODIFIED Requirements

### Requirement: SQLite store initialization
The system SHALL provide a SQLite-backed store that creates the foundational metadata, full-text, and vector-sidecar schema on first use if the database does not already exist.

#### Scenario: Schema is created on first run
- **WHEN** the store opens against an empty database path
- **THEN** it creates the `documents`, `items`, `items_fts`, `item_embeddings`, and `embedding_meta` tables required for keyword and vector search features

## ADDED Requirements

### Requirement: Embedding sidecar identity
The system SHALL persist embeddings in a sidecar table keyed by `items.storage_id` so each stored vector refers to exactly one indexed item and does not create a separate identity space.

#### Scenario: One embedding row maps to one indexed item
- **WHEN** embeddings are stored for indexed document items
- **THEN** each embedding row uses the indexed item's `storage_id` as its primary key

### Requirement: Embedding regime validation
The system SHALL persist the active embedding model metadata alongside stored embeddings and SHALL reject embedding writes when the configured model regime does not match the stored metadata.

#### Scenario: Indexing rejects incompatible embedding metadata
- **WHEN** embedding generation is requested against an index whose stored embedding metadata conflicts with the configured model or dimensions
- **THEN** the indexing flow fails before writing incompatible embeddings
