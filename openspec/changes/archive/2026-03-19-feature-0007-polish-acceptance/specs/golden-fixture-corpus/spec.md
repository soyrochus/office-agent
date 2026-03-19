## ADDED Requirements

### Requirement: Version-controlled golden fixture corpus
The system SHALL include deterministic Office fixture files under `tests/fixtures/` for DOCX, PPTX, and XLSX acceptance coverage.

#### Scenario: Fixture files are present in the repository
- **WHEN** a contributor inspects the test fixture tree
- **THEN** the repository contains version-controlled sample `.docx`, `.pptx`, and `.xlsx` files for acceptance workflows

### Requirement: Fixture corpus content requirements
The system SHALL provide fixture documents with the minimum content coverage defined for Word paragraphs, PowerPoint slides and non-text shapes, and Excel sheets, text cells, numeric cells, and formulas.

#### Scenario: Fixtures satisfy acceptance coverage shape
- **WHEN** the CLI or MCP acceptance suites run against the golden corpus
- **THEN** the sample files contain the required structure needed to exercise the documented workflows

### Requirement: Fixture stability across test runs
The system SHALL treat the golden fixture corpus as deterministic and SHALL not regenerate those files during normal test execution.

#### Scenario: Test runs reuse the same fixture files
- **WHEN** the acceptance suite runs multiple times
- **THEN** it uses the same checked-in fixture files rather than creating new binary documents each run
