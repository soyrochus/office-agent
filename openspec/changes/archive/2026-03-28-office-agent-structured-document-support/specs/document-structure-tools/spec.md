## ADDED Requirements

### Requirement: Generic document structure inspection
The system SHALL expose `get_document_structure` for indexed DOCX, PPTX, and XLSX documents. The response SHALL identify the requested document container and return an ordered list of logical units using a consistent top-level shape that includes unit position, unit type, preview text, and format-specific metadata.

#### Scenario: Client inspects a document through the generic structure tool
- **WHEN** an MCP client calls `get_document_structure` for an indexed Office document
- **THEN** the server returns the document identity plus an ordered list of logical units for that file type using a consistent structured response shape

### Requirement: Generic structure preserves native order
The system SHALL preserve native source ordering in structure responses: slide order for PPTX, worksheet order for XLSX, and block order for DOCX.

#### Scenario: Structure output follows source order
- **WHEN** an MCP client retrieves structure for a document that contains multiple slides, sheets, or blocks
- **THEN** the returned logical units appear in the same order as the source Office document

### Requirement: Presentation structure summaries
The system SHALL expose `get_presentation_structure` for indexed PPTX documents and return slide summaries that include slide number, preview text when available, and slide metadata needed to identify the slide as a semantic unit.

#### Scenario: Client lists slides in a presentation
- **WHEN** an MCP client calls `get_presentation_structure` for an indexed presentation
- **THEN** the server returns one structured slide summary per slide in slide-number order

### Requirement: Workbook structure summaries
The system SHALL expose `get_workbook_structure` for indexed XLSX documents and return worksheet summaries in workbook order, including sheet name and sheet-level metadata needed to identify each sheet as a semantic unit.

#### Scenario: Client lists sheets in a workbook
- **WHEN** an MCP client calls `get_workbook_structure` for an indexed workbook
- **THEN** the server returns one structured worksheet summary per sheet in workbook order
