## MODIFIED Requirements

### Requirement: SQLite store initialization
The system SHALL provide a SQLite-backed store that creates the foundational metadata, full-text, and vector-sidecar schema on first use if the database does not already exist. The vector-sidecar schema SHALL include the tables needed for per-item embeddings and the additional tables needed to persist XLSX row embeddings plus row-to-cell mappings.

#### Scenario: Schema is created on first run
- **WHEN** the store opens against an empty database path
- **THEN** it creates the `documents`, `items`, `items_fts`, `item_embeddings`, `embedding_meta`, and the XLSX row-embedding mapping tables required for keyword and vector search features

### Requirement: Embedding sidecar identity
The system SHALL persist non-XLSX embeddings in a sidecar table keyed by `items.storage_id` so each stored vector refers to exactly one indexed item. For XLSX row embeddings, the system SHALL persist vectors under a dedicated row-embedding identity and SHALL maintain a queryable mapping from each row embedding to the contributing indexed cell `storage_id` values and coordinates.

#### Scenario: Non-XLSX embeddings remain item keyed
- **WHEN** embeddings are stored for indexed DOCX or PPTX items
- **THEN** each embedding row uses the indexed item's `storage_id` as its primary key

#### Scenario: XLSX row embeddings map back to indexed cells
- **WHEN** embeddings are stored for indexed XLSX content
- **THEN** each row embedding record uses a dedicated row identity and has persisted mapping records that identify the contributing indexed cell `storage_id` values and coordinates for that row

## ADDED Requirements

### Requirement: XLSX row embedding replacement
The system SHALL replace XLSX row embeddings and their row-to-cell mappings for a document as one refresh set so stale row mappings are not retained after reindexing.

#### Scenario: Reindex removes stale XLSX row mappings
- **WHEN** an XLSX document with stored row embeddings is reindexed after rows or contributing cells change
- **THEN** the store removes that document's old row embeddings and row-to-cell mappings before persisting the refreshed row embedding set

### Requirement: Embedding regime validation
The system SHALL persist the active embedding model metadata alongside stored vectors and SHALL reject embedding writes when the configured model regime does not match the stored metadata, including writes to XLSX row-embedding tables.

#### Scenario: Indexing rejects incompatible embedding metadata
- **WHEN** embedding generation is requested against an index whose stored embedding metadata conflicts with the configured model or dimensions
- **THEN** the indexing flow fails before writing incompatible per-item or XLSX row embeddings
