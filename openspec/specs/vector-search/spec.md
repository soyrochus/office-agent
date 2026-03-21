## Purpose

Define semantic and hybrid vector-search behavior for Office Agent.

## Requirements

### Requirement: Retrieval mode selection
The system SHALL support `keyword`, `semantic`, and `hybrid` retrieval modes across the shared search workflow, and it SHALL default to `keyword` when no explicit mode is supplied.

#### Scenario: Keyword retrieval remains the default
- **WHEN** a caller invokes search without specifying a retrieval mode
- **THEN** the system executes keyword retrieval and returns keyword-compatible search hits

#### Scenario: Unsupported retrieval mode is rejected
- **WHEN** a caller supplies a retrieval mode other than `keyword`, `semantic`, or `hybrid`
- **THEN** the interface rejects the request before executing the search

### Requirement: Embedding-enabled indexing
The system SHALL optionally generate and persist one embedding per indexed item when indexing or reindexing is run with embedding generation enabled, except for XLSX where the system SHALL generate one embedding per text-bearing worksheet row. Embedding writes SHALL commit in the same document-level indexing transaction as the refreshed item rows, and XLSX row embeddings SHALL retain a mapping to the contributing indexed cell items for that row.

#### Scenario: Indexing with embeddings persists sidecar vectors
- **WHEN** a non-XLSX document is indexed with embedding generation enabled
- **THEN** the system stores one embedding row per indexed item for that document and commits the refreshed items and embeddings together

#### Scenario: Reindex refreshes embeddings after content changes
- **WHEN** a previously embedded non-XLSX document is reindexed with changed content and embedding generation enabled
- **THEN** the system replaces that document's stored embeddings with vectors for the newly indexed item set

#### Scenario: XLSX indexing with embeddings persists row vectors
- **WHEN** an XLSX document is indexed with embedding generation enabled
- **THEN** the system stores one embedding row for each worksheet row that contains at least one text-like cell, stores a mapping to the contributing indexed cell items for each row embedding, and commits the refreshed cell items and row embeddings together

#### Scenario: Reindex refreshes XLSX row embeddings after content changes
- **WHEN** a previously embedded XLSX document is reindexed with changed content and embedding generation enabled
- **THEN** the system replaces that document's stored row embeddings and row-to-cell mappings with records for the newly indexed row set

### Requirement: Contextual XLSX embedding text
The system SHALL construct XLSX embedding text from workbook name, sheet name, row number, and the ordered text-bearing cell values that contribute to a row embedding. Numeric-only, empty, and otherwise non-text-like XLSX cells SHALL NOT contribute to the row embedding text, while indexed DOCX paragraphs and PPTX text shapes SHALL use their indexed content text unchanged.

#### Scenario: XLSX row embeddings use filtered row text
- **WHEN** the system prepares an embedding input for an indexed XLSX row that contains both labels and numeric values
- **THEN** the submitted text includes workbook, sheet, row, and the contributing text-like cell content for that row while excluding numeric-only cells from the embedding payload

### Requirement: Semantic retrieval over indexed items
The system SHALL support semantic search by embedding the query, comparing it against stored vectors, and returning hits that resolve to existing indexed items. For XLSX, semantic retrieval SHALL search row embeddings and resolve each winning row hit to a deterministic contributing cell item while preserving row-level provenance in the hit metadata.

#### Scenario: Semantic search returns indexed items
- **WHEN** a user searches in semantic mode against a non-XLSX corpus with stored embeddings
- **THEN** the results are returned as hits for already indexed items rather than as separate vector-only records

#### Scenario: Semantic XLSX search returns a cell-backed hit
- **WHEN** a user searches in semantic mode against an XLSX corpus with stored row embeddings
- **THEN** each returned hit resolves to an existing indexed cell item rather than to a vector-only row record

#### Scenario: Semantic search detects missing embeddings
- **WHEN** semantic search is requested for a corpus that has no stored embeddings
- **THEN** the semantic retrieval path reports that no embeddings are available for the requested corpus

### Requirement: Hybrid retrieval and scoring
The system SHALL support hybrid search that executes both keyword and semantic retrieval, unions candidates by the returned indexed item identity, and orders merged hits with a deterministic weighted score derived from the component retrieval scores. For XLSX, row-derived semantic candidates SHALL be normalized to representative contributing cell identities before the hybrid merge occurs.

#### Scenario: Hybrid search merges overlapping candidates
- **WHEN** keyword and semantic retrieval both return the same non-XLSX indexed item
- **THEN** the system returns one merged hit for that item with combined scoring metadata

#### Scenario: Hybrid search merges XLSX keyword and row-semantic candidates
- **WHEN** keyword retrieval returns an indexed XLSX cell and semantic retrieval returns a row embedding that resolves to that same cell
- **THEN** the system returns one merged hit for that cell with combined scoring metadata

#### Scenario: Hybrid search yields deterministic ordering
- **WHEN** multiple hybrid candidates have the same final score
- **THEN** the system applies a deterministic tie-break order so repeated searches return the same hit ordering

### Requirement: Mode-aware search hit metadata
The system SHALL attach `match_mode` and per-source score metadata to semantic and hybrid search hits, and it SHALL preserve those fields in the shared search result model for interface rendering. For XLSX row-derived semantic or hybrid hits, the metadata SHALL also retain the matched sheet and row plus the contributing cell coordinates used to resolve the surfaced cell hit.

#### Scenario: Hybrid hit exposes component scores
- **WHEN** a search hit is produced by non-XLSX hybrid retrieval
- **THEN** the hit includes keyword, semantic, and final score values alongside `match_mode="hybrid"`

#### Scenario: Hybrid hit exposes XLSX row provenance
- **WHEN** a search hit is produced from an XLSX row embedding during hybrid retrieval
- **THEN** the hit includes `match_mode="hybrid"`, component score metadata, and row provenance identifying the matched row and contributing cell coordinates

#### Scenario: Semantic hit exposes semantic provenance
- **WHEN** a search hit is produced by non-XLSX semantic retrieval
- **THEN** the hit includes `match_mode="semantic"` and semantic score metadata for that hit

#### Scenario: Semantic hit exposes XLSX row provenance
- **WHEN** a search hit is produced from an XLSX row embedding during semantic retrieval
- **THEN** the hit includes `match_mode="semantic"`, semantic score metadata, and row provenance identifying the matched row and contributing cell coordinates
