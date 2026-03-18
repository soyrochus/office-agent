## 1. Package Foundation

- [ ] 1.1 Add `pyproject.toml` metadata for the `offagent` package, core dependencies, and the `office-agent` console script
- [ ] 1.2 Create the initial `src/offagent/` package layout with `config.py`, `domain/models.py`, `domain/locators.py`, `indexing/store.py`, `app/services.py`, and `interfaces/cli.py`
- [ ] 1.3 Implement shared domain models for `DocumentRef`, `ItemRef`, `SearchHit`, and `PatchOperation`
- [ ] 1.4 Add locator parsing stubs that expose placeholder parsing behavior without full resolution logic

## 2. Index Store

- [ ] 2.1 Implement SQLite connection management in `indexing/store.py`
- [ ] 2.2 Add first-run schema creation for `documents`, `items`, and `items_fts`
- [ ] 2.3 Add explicit FTS5 capability checks so the runtime can report unsupported SQLite builds

## 3. Configuration And Discovery

- [ ] 3.1 Implement configuration defaults plus optional file-based loading
- [ ] 3.2 Add environment variable overrides with deterministic precedence over file settings
- [ ] 3.3 Implement Office document discovery for `.docx`, `.pptx`, and `.xlsx` files under configured roots
- [ ] 3.4 Ensure discovery returns path and modification metadata while excluding unsupported files

## 4. CLI And Diagnostics

- [ ] 4.1 Wire the Typer CLI entrypoint to the shared application services
- [ ] 4.2 Implement the `office-agent doctor` command to check required library imports
- [ ] 4.3 Extend `office-agent doctor` to verify SQLite availability, index path writability, and document root readability
- [ ] 4.4 Ensure the diagnostic flow can validate schema bootstrap on a new writable database path

## 5. Testing And Verification

- [ ] 5.1 Add unit tests for configuration loading and environment override precedence
- [ ] 5.2 Add unit tests for SQLite schema creation and FTS5 capability reporting
- [ ] 5.3 Add unit tests for Office file discovery in mixed directories
- [ ] 5.4 Add unit tests for locator parsing stubs
- [ ] 5.5 Run the relevant test suite and confirm `office-agent doctor` behavior matches the specifications
