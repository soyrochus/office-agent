## ADDED Requirements

### Requirement: Ordered document block retrieval
The system SHALL expose `get_document_blocks` for indexed DOCX documents and return an ordered sequence of logical blocks from the source document body. The returned blocks SHALL include paragraphs and tables in document order, with block index, block type, preview text, and available metadata such as paragraph style or heading status.

#### Scenario: Client lists document blocks in source order
- **WHEN** an MCP client calls `get_document_blocks` for an indexed Word document that contains paragraphs and tables
- **THEN** the server returns paragraphs and tables in the same order they appear in the document body

### Requirement: Paragraph collection retrieval
The system SHALL expose `get_paragraphs` for indexed DOCX documents and return ordered paragraph records with paragraph text and available style metadata, including heading-related metadata when present.

#### Scenario: Client retrieves paragraph records
- **WHEN** an MCP client calls `get_paragraphs` for an indexed Word document
- **THEN** the server returns the document paragraphs in order with text and available style metadata

### Requirement: Table collection retrieval
The system SHALL expose `get_tables` for indexed DOCX documents and return each table as a structured two-dimensional array in document order, with table metadata when available.

#### Scenario: Client retrieves table content from a document
- **WHEN** an MCP client calls `get_tables` for an indexed Word document that contains tables
- **THEN** the server returns the document tables in order with row and cell content preserved

### Requirement: Block bundle retrieval
The system SHALL expose `get_block_bundle` for indexed DOCX documents and return the full semantic content for the requested block index, including block type, text or table content, and available metadata for that block.

#### Scenario: Client retrieves one document block bundle
- **WHEN** an MCP client calls `get_block_bundle` for a valid block index in an indexed Word document
- **THEN** the server returns the complete semantic representation for that one block

### Requirement: Paragraph append writes a new terminal block
The system SHALL expose `append_paragraph` for indexed DOCX documents. The tool SHALL append one paragraph at the end of the document body, optionally applying a requested style, and SHALL return a structured write result that identifies the output document path and the appended block.

#### Scenario: Client appends a paragraph to a document
- **WHEN** an MCP client calls `append_paragraph` with text for an indexed Word document
- **THEN** the server appends a new paragraph at the end of the document and returns a structured write result describing the appended block

### Requirement: Block replacement updates paragraph blocks and rejects table replacement
The system SHALL expose `replace_block` for indexed DOCX documents. In the initial release, the tool SHALL replace the content of paragraph blocks and SHALL reject replacement requests that target table blocks with an explicit error.

#### Scenario: Client replaces a paragraph block
- **WHEN** an MCP client calls `replace_block` for a paragraph block in an indexed Word document
- **THEN** the server writes the updated paragraph content and returns a structured write result for the produced document output

#### Scenario: Client attempts to replace a table block
- **WHEN** an MCP client calls `replace_block` for a table block in an indexed Word document
- **THEN** the server rejects the request with an explicit error indicating that table block replacement is not supported
