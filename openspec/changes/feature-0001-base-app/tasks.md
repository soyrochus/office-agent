## 1. Package Foundation

- [x] 1.1 Add `pyproject.toml` metadata for the `offagent` package, core dependencies, and the `office-agent` console script
- [x] 1.2 Create the initial `src/offagent/` package layout with `config.py`, `domain/models.py`, `domain/locators.py`, `indexing/store.py`, `app/services.py`, and `interfaces/cli.py`
- [x] 1.3 Implement shared domain models for `DocumentRef`, `ItemRef`, `SearchHit`, and `PatchOperation`
- [x] 1.4 Add locator parsing stubs that expose placeholder parsing behavior without full resolution logic

## 2. Index Store

- [x] 2.1 Implement SQLite connection management in `indexing/store.py`
- [x] 2.2 Add first-run schema creation for `documents`, `items`, and `items_fts`
- [x] 2.3 Add explicit FTS5 capability checks so the runtime can report unsupported SQLite builds

## 3. Configuration And Discovery

- [x] 3.1 Implement configuration defaults plus optional file-based loading
- [x] 3.2 Add environment variable overrides with deterministic precedence over file settings
- [x] 3.3 Implement Office document discovery for `.docx`, `.pptx`, and `.xlsx` files under configured roots
- [x] 3.4 Ensure discovery returns path and modification metadata while excluding unsupported files

## 4. CLI And Diagnostics

- [x] 4.1 Wire the Typer CLI entrypoint to the shared application services
- [x] 4.2 Implement the `office-agent doctor` command to check required library imports
- [x] 4.3 Extend `office-agent doctor` to verify SQLite availability, index path writability, and document root readability
- [x] 4.4 Ensure the diagnostic flow can validate schema bootstrap on a new writable database path

## 5. Testing And Verification

- [x] 5.1 Add unit tests for configuration loading and environment override precedence
- [x] 5.2 Add unit tests for SQLite schema creation and FTS5 capability reporting
- [x] 5.3 Add unit tests for Office file discovery in mixed directories
- [x] 5.4 Add unit tests for locator parsing stubs
- [x] 5.5 Run the relevant test suite and confirm `office-agent doctor` behavior matches the specifications
