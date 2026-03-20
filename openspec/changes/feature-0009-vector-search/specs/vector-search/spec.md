## ADDED Requirements

### Requirement: Retrieval mode selection
The system SHALL support `keyword`, `semantic`, and `hybrid` retrieval modes across the shared search workflow, and it SHALL default to `keyword` when no explicit mode is supplied.

#### Scenario: Keyword retrieval remains the default
- **WHEN** a caller invokes search without specifying a retrieval mode
- **THEN** the system executes keyword retrieval and returns keyword-compatible search hits

#### Scenario: Unsupported retrieval mode is rejected
- **WHEN** a caller supplies a retrieval mode other than `keyword`, `semantic`, or `hybrid`
- **THEN** the interface rejects the request before executing the search

### Requirement: Embedding-enabled indexing
The system SHALL optionally generate and persist one embedding per indexed item when indexing or reindexing is run with embedding generation enabled. Embedding writes SHALL use the existing indexed item identity and SHALL complete in the same document-level indexing transaction as the refreshed item rows.

#### Scenario: Indexing with embeddings persists sidecar vectors
- **WHEN** a document is indexed with embedding generation enabled
- **THEN** the system stores one embedding row per indexed item for that document and commits the refreshed items and embeddings together

#### Scenario: Reindex refreshes embeddings after content changes
- **WHEN** a previously embedded document is reindexed with changed content and embedding generation enabled
- **THEN** the system replaces that document's stored embeddings with vectors for the newly indexed item set

### Requirement: Contextual XLSX embedding text
The system SHALL construct embedding text for indexed XLSX cells from workbook name, sheet name, cell coordinate, row context, column context, and cell value, while indexed DOCX paragraphs and PPTX text shapes SHALL use their indexed content text unchanged.

#### Scenario: XLSX cell embeddings use contextual text
- **WHEN** the system prepares an embedding input for an indexed XLSX cell
- **THEN** the submitted text includes workbook, sheet, cell, row context, column context, and cell value instead of only the raw display string

### Requirement: Semantic retrieval over indexed items
The system SHALL support semantic search by embedding the query, comparing it against stored item embeddings with cosine similarity, and returning hits that resolve to existing indexed items.

#### Scenario: Semantic search returns indexed items
- **WHEN** a user searches in semantic mode against a corpus with stored embeddings
- **THEN** the results are returned as hits for already indexed items rather than as separate vector-only records

#### Scenario: Semantic search detects missing embeddings
- **WHEN** semantic search is requested for a corpus that has no stored embeddings
- **THEN** the semantic retrieval path reports that no embeddings are available for the requested corpus

### Requirement: Hybrid retrieval and scoring
The system SHALL support hybrid search that executes both keyword and semantic retrieval, unions candidates by indexed item identity, and orders merged hits with a deterministic weighted score derived from the component retrieval scores.

#### Scenario: Hybrid search merges overlapping candidates
- **WHEN** keyword and semantic retrieval both return the same indexed item
- **THEN** the system returns one merged hit for that item with combined scoring metadata

#### Scenario: Hybrid search yields deterministic ordering
- **WHEN** multiple hybrid candidates have the same final score
- **THEN** the system applies a deterministic tie-break order so repeated searches return the same hit ordering

### Requirement: Mode-aware search hit metadata
The system SHALL attach `match_mode` and per-source score metadata to semantic and hybrid search hits, and it SHALL preserve those fields in the shared search result model for interface rendering.

#### Scenario: Hybrid hit exposes component scores
- **WHEN** a search hit is produced by hybrid retrieval
- **THEN** the hit includes keyword, semantic, and final score values alongside `match_mode="hybrid"`

#### Scenario: Semantic hit exposes semantic provenance
- **WHEN** a search hit is produced by semantic retrieval
- **THEN** the hit includes `match_mode="semantic"` and semantic score metadata for that hit
