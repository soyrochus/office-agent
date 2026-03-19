## ADDED Requirements

### Requirement: PPTX item indexing
The system SHALL persist extracted PPTX text-shape items in the local index so search, locate, and read workflows operate on indexed shape metadata rather than scanning presentations at query time.

#### Scenario: Indexed PPTX text shapes are stored for query
- **WHEN** a user runs `office-agent index` on a `.pptx` file or directory containing `.pptx` files
- **THEN** the system stores presentation metadata and extracted text-shape items for those files in the local index

### Requirement: PPTX text-shape search
The system SHALL support searching indexed PPTX text-frame content and return matching shape hits with score, locator, preview, and presentation context.

#### Scenario: Search returns the matching text shape
- **WHEN** a user runs `office-agent search "known phrase" --type pptx` for text contained in an indexed PPTX shape
- **THEN** the system returns the corresponding shape hit with its slide-and-shape locator and preview text

### Requirement: Slide-based locate
The system SHALL support `office-agent locate --doc <file> --slide <n> [--shape <id>]` for PPTX presentations.

#### Scenario: Slide-only locate returns editable shapes on the slide
- **WHEN** a user locates a specific slide without a shape id
- **THEN** the system returns the matching `ItemRef` values for editable text-bearing shapes on that slide

#### Scenario: Slide-and-shape locate returns one target
- **WHEN** a user locates a specific slide and shape id for an editable PPTX shape
- **THEN** the system returns the `ItemRef` for that one text-bearing shape

### Requirement: PPTX text-shape read
The system SHALL read the current text-frame content from the source presentation for a resolved PPTX text-bearing shape item.

#### Scenario: Read returns source text-frame content
- **WHEN** a user runs `office-agent read --doc <file> --item <item-id>` for an existing PPTX text-shape item
- **THEN** the system returns the current text-frame content from the source presentation

### Requirement: Non-text targets are not treated as readable items
The system SHALL not index non-text PowerPoint shapes as readable text-shape items.

#### Scenario: Non-text shapes are absent from text-shape results
- **WHEN** a presentation contains charts, tables, images, SmartArt, or other non-text shapes
- **THEN** those shapes do not appear as indexed PPTX text-shape items for search and locate workflows
