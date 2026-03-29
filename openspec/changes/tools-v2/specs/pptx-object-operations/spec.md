## ADDED Requirements

### Requirement: PPTX object model
The system SHALL treat the following as first-class object types in PPTX presentations, addressable by typed locators of the form `pptx:<type>:<index>` or nested variants: `presentation`, `slide`, `notes`, `shape`, `text_shape`, `image_shape`, `table`, `table_row`, `table_cell`, `group_shape`. Each type SHALL have a defined locator grammar and a defined property set.

#### Scenario: Agent resolves a PPTX slide by typed locator
- **WHEN** an MCP client calls `get_object` with a locator of the form `pptx:slide:N` for an indexed PPTX document
- **THEN** the server returns a structured slide object with title, layout name, shape count, child summary, and computed capabilities

#### Scenario: Agent resolves a shape within a slide
- **WHEN** an MCP client calls `get_object` with a locator of the form `pptx:slide:N:shape:S`
- **THEN** the server returns a structured shape object with shape type, text content (if applicable), position, size, and capabilities

#### Scenario: Agent lists shapes in a slide
- **WHEN** an MCP client calls `list_children` on a `pptx:slide:N` locator
- **THEN** the server returns an ordered list of shape object summaries for that slide

### Requirement: PPTX slide creation tool
The system SHALL expose a `pptx_add_slide` escape hatch tool that appends a new slide to the presentation using a specified slide layout. The tool SHALL accept a `layout_index` or `layout_name` parameter.

#### Scenario: Agent adds a blank slide
- **WHEN** an MCP client calls `pptx_add_slide` with a valid `document_id` and `layout_index`
- **THEN** the server appends a new slide with the specified layout, writes the output, reindexes, and returns a mutation result with the new slide's locator

#### Scenario: Invalid layout rejected
- **WHEN** an MCP client calls `pptx_add_slide` with a `layout_index` that does not exist in the presentation's slide master
- **THEN** the server returns a ToolError without modifying the presentation

### Requirement: PPTX slide duplication tool
The system SHALL expose a `pptx_duplicate_slide` escape hatch tool that copies an existing slide and inserts the copy at a specified position.

#### Scenario: Agent duplicates a slide
- **WHEN** an MCP client calls `pptx_duplicate_slide` with a valid slide locator and a target position
- **THEN** the server inserts a copy of the slide at the target position, writes the output, reindexes, and returns a mutation result with the new slide's locator

### Requirement: PPTX slide layout assignment tool
The system SHALL expose a `pptx_set_slide_layout` escape hatch tool that reassigns an existing slide to a different slide layout.

#### Scenario: Agent reassigns a slide layout
- **WHEN** an MCP client calls `pptx_set_slide_layout` with a valid slide locator and a target layout
- **THEN** the server applies the new layout to the slide, writes the output, reindexes, and returns a mutation result

### Requirement: PPTX text shape addition tool
The system SHALL expose a `pptx_add_text_shape` escape hatch tool that adds a new text box shape to a slide at specified position and dimensions.

#### Scenario: Agent adds a text box
- **WHEN** an MCP client calls `pptx_add_text_shape` with a valid slide locator, text content, and position/size parameters
- **THEN** the server adds the text shape to the slide, writes the output, reindexes, and returns a mutation result with the new shape's locator
