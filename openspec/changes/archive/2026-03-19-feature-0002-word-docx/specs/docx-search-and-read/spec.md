## ADDED Requirements

### Requirement: DOCX item indexing
The system SHALL persist extracted DOCX paragraph items in the local index so search, locate, and read workflows operate on indexed item metadata rather than scanning files at query time.

#### Scenario: Indexed DOCX paragraphs are stored for later query
- **WHEN** a user runs `office-agent index` on a `.docx` file or directory containing `.docx` files
- **THEN** the system stores document metadata and paragraph items for those files in the local index

### Requirement: DOCX paragraph search
The system SHALL support searching indexed DOCX paragraph content and return matching paragraph hits with score, locator, preview, and document context.

#### Scenario: Search returns the matching paragraph
- **WHEN** a user runs `office-agent search` with a phrase contained in an indexed DOCX paragraph
- **THEN** the system returns the corresponding paragraph hit with its paragraph locator and preview text

### Requirement: Direct DOCX paragraph location
The system SHALL resolve `office-agent locate --doc <file> --paragraph <n>` to the paragraph `ItemRef` for the requested DOCX paragraph index.

#### Scenario: Locate resolves a paragraph reference
- **WHEN** a user requests paragraph `3` from an indexed DOCX file through the locate command
- **THEN** the system returns the `ItemRef` for `para:3` from that document

### Requirement: DOCX paragraph read
The system SHALL read the current paragraph text from the source DOCX file for a resolved paragraph item.

#### Scenario: Read returns source paragraph text
- **WHEN** a user runs `office-agent read --doc <file> --item <item-id>` for an existing DOCX paragraph item
- **THEN** the system returns the current paragraph text from the source document

### Requirement: Forced DOCX reindex
The system SHALL support reindexing a specific DOCX file to refresh stored paragraph items after the document changes.

#### Scenario: Reindex refreshes stored paragraph content
- **WHEN** a user runs `office-agent reindex <path>` for a changed `.docx` file
- **THEN** the system replaces the stored paragraph items for that document with the newly extracted set
