## Purpose

Define the contract for PPTX slide bundle and slide notes tools that return ordered semantic content for individual slides in indexed presentations.

## Requirements

### Requirement: Slide bundle retrieval
The system SHALL expose `get_slide_bundle` for indexed PPTX documents. The slide bundle SHALL return the requested slide number, ordered text blocks for text-bearing shapes on that slide, slide metadata, and the slide notes text.

#### Scenario: Client retrieves a semantic slide bundle
- **WHEN** an MCP client calls `get_slide_bundle` for a specific slide in an indexed presentation
- **THEN** the server returns the notes text, ordered text blocks, and slide metadata for that one slide

### Requirement: Slide bundles preserve shape order and identity metadata
The text blocks returned by `get_slide_bundle` SHALL preserve slide shape order and SHALL include stable metadata for each text-bearing shape, including the PowerPoint shape identifier and shape name when available.

#### Scenario: Slide bundle preserves text-block order
- **WHEN** a slide contains multiple text-bearing shapes
- **THEN** the bundle returns those text blocks in shape order with metadata that identifies each contributing shape

### Requirement: Direct slide notes access
The system SHALL expose `get_slide_notes` for indexed PPTX documents and return the notes text for the requested slide without requiring the client to parse the full slide bundle.

#### Scenario: Client retrieves notes for one slide
- **WHEN** an MCP client calls `get_slide_notes` for a slide in an indexed presentation
- **THEN** the server returns the current notes text for that slide as a structured semantic response
