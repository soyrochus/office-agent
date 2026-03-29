## ADDED Requirements

### Requirement: get_node reads a single leaf node from the live document
The system SHALL expose a `get_node` tool that accepts a `document_id` and a `node_id` (locator) and returns the current content of that node directly from the source file. The response SHALL include `node_id`, `item_type`, `text`, and `metadata`. The tool SHALL infer document format from the `document_id` without requiring a format parameter. The content returned SHALL reflect the live file, not the search index cache.

#### Scenario: get_node returns current text for a DOCX paragraph
- **WHEN** a caller invokes `get_node` with a DOCX paragraph locator
- **THEN** the response includes the current paragraph text as stored in the file, even if the search index has not been refreshed since the last write

#### Scenario: get_node accepts any locator produced by the tool surface
- **WHEN** a caller passes a locator obtained from `search_documents`, `get_structure`, or `get_section` to `get_node`
- **THEN** `get_node` resolves the node and returns its content without error

#### Scenario: get_node works uniformly across DOCX, PPTX, and XLSX
- **WHEN** a caller invokes `get_node` on a node from a DOCX, PPTX, or XLSX document
- **THEN** the response carries the same fields (`node_id`, `item_type`, `text`, `metadata`) regardless of format

### Requirement: write_node replaces content at an existing node
The system SHALL expose a `write_node` tool that accepts a `document_id`, a `node_id` (locator), and a `content` string, and replaces the current text of that node with the new content. The tool SHALL infer document format from the `document_id`. The tool SHALL accept an optional `output_mode` parameter (`"versioned"` or `"inplace"`) defaulting to `"versioned"`. The response SHALL include `output_path`, `node_id`, `new_text`, and `previous_text`. The tool SHALL re-index the output document before returning.

#### Scenario: write_node replaces a DOCX paragraph and re-indexes
- **WHEN** a caller invokes `write_node` on a DOCX paragraph locator with new content
- **THEN** the paragraph in the output document contains the new text, the response carries `previous_text` with the original content, and the output document is indexed before the tool returns

#### Scenario: write_node replaces a PPTX text shape
- **WHEN** a caller invokes `write_node` on a PPTX text shape locator with new content
- **THEN** the text shape in the output presentation contains the new text and the response identifies the output path

#### Scenario: write_node replaces an XLSX cell value
- **WHEN** a caller invokes `write_node` on an XLSX cell locator with a new string value
- **THEN** the cell in the output workbook contains the new value and the response identifies the output path

#### Scenario: write_node in versioned mode produces a new file
- **WHEN** a caller invokes `write_node` with `output_mode="versioned"`
- **THEN** the response `output_path` is a new timestamped file distinct from the original document path

#### Scenario: write_node in inplace mode modifies the original file
- **WHEN** a caller invokes `write_node` with `output_mode="inplace"`
- **THEN** the response `output_path` is the same path as the original document and the original file reflects the new content

### Requirement: Universal locator address space
The system SHALL guarantee that every locator string returned by any tool (`search_documents`, `get_structure`, `get_section`, `get_node`) is directly usable as the `node_id` argument to `get_node` and `write_node` for the same document version, without transformation. No tool SHALL return an address that is only valid as input to a subset of other tools.

#### Scenario: Search hit locator is valid for get_node
- **WHEN** a caller passes the `locator` field from a `search_documents` hit directly to `get_node`
- **THEN** `get_node` resolves the node and returns its content without error

#### Scenario: Search hit locator is valid for write_node
- **WHEN** a caller passes the `locator` field from a `search_documents` hit directly to `write_node` with new content
- **THEN** `write_node` applies the replacement and returns a valid write result

#### Scenario: Structure locator is valid for write_node
- **WHEN** a caller uses a locator from `get_structure` or `get_section` as the `node_id` in `write_node`
- **THEN** `write_node` applies the replacement without requiring any locator transformation
