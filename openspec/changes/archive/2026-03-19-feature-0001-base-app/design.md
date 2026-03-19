## Context

This change establishes the first usable slice of the local-first Office agent. No production package structure, configuration contract, persistent index store, or runtime diagnostics exist yet, but every later indexing, search, and patch feature depends on those foundations. The design needs to keep CLI and future MCP work pointed at the same application core, while keeping the MVP narrow enough to validate packaging, storage, discovery, and environment setup early.

Constraints:
- The initial implementation is Python-based and should rely on a small dependency set.
- Search infrastructure must start with a local SQLite database and FTS5 support.
- The first feature must not pull in format-specific extraction logic yet.
- Later capabilities will need stable domain models and service boundaries for CLI and MCP adapters.

## Goals / Non-Goals

**Goals:**
- Create the `offagent` package skeleton and CLI entrypoint needed for a shared application core.
- Define stable domain model stubs for documents, items, search hits, and patch operations.
- Establish a SQLite-backed local store with schema initialization on first run.
- Provide configuration loading with deterministic precedence between file settings and environment overrides.
- Provide Office file discovery under configured roots for `.docx`, `.pptx`, and `.xlsx`.
- Add a `doctor` command that validates runtime dependencies, SQLite availability, index path writability, and configured root readability.

**Non-Goals:**
- Format-specific extraction, indexing, or write-back behavior for DOCX, PPTX, or XLSX.
- MCP transport, server startup, or tool exposure.
- Search query execution, patch application, or versioned output writing.
- Rich locator parsing beyond basic stub behavior needed for tests and future extension.

## Decisions

### 1. Use a layered package structure from the first commit

Decision:
Create `config.py`, `domain/`, `indexing/`, `interfaces/`, and `app/` modules under `src/offagent/`, with Typer in `interfaces/cli.py` and service orchestration in `app/services.py`.

Rationale:
The first feature is already cross-cutting. Creating clean layer boundaries now avoids binding CLI behavior directly to storage code and reduces refactoring pressure when MCP is introduced.

Alternatives considered:
- Put all MVP code in a single CLI module for speed.
  Rejected because it would mix transport concerns, configuration, and persistence in a way that later features would need to unwind.
- Build the MCP interface first and adapt CLI later.
  Rejected because the MVP must be locally testable and operationally debuggable before agent-facing integration.

### 2. Keep the foundational domain model format-neutral

Decision:
Add `DocumentRef`, `ItemRef`, `SearchHit`, and `PatchOperation` as shared models in `domain/models.py`, plus locator parsing stubs in `domain/locators.py`.

Rationale:
Later document adapters and interfaces need a common contract. A small neutral model keeps search, read, and write workflows aligned before format-specific details arrive.

Alternatives considered:
- Use ad hoc dictionaries until extraction features are implemented.
  Rejected because it weakens type guarantees and makes later service signatures unstable.
- Model DOCX, PPTX, and XLSX entities separately immediately.
  Rejected because the current feature does not yet implement format adapters and would introduce premature complexity.

### 3. Initialize SQLite schema eagerly through a dedicated store module

Decision:
Implement connection management and schema creation in `indexing/store.py`, with first-run creation of `documents`, `items`, and `items_fts` tables.

Rationale:
The local index is a core architectural dependency, not an optional optimization. Centralizing schema creation in one module keeps persistence setup deterministic and makes `doctor` able to verify storage behavior directly.

Alternatives considered:
- Delay schema creation until the first indexing feature.
  Rejected because this base feature explicitly needs to validate that the environment can support the index layer.
- Use a heavier ORM or migration framework from the start.
  Rejected because the schema is small, SQLite-specific, and better served by explicit SQL for the MVP.

### 4. Use explicit configuration precedence: defaults, file, then environment

Decision:
Load configuration from code defaults, overlay an optional config file, and then override with environment variables.

Rationale:
This matches common operational expectations and supports both local developer use and automation without making the runtime behavior ambiguous.

Alternatives considered:
- Environment variables only.
  Rejected because document roots and index paths benefit from a durable local config file.
- Config file only.
  Rejected because deployment and CI use cases need override support without mutating checked-in files.

### 5. Limit file discovery to metadata collection for supported Office extensions

Decision:
Implement recursive discovery that records path and modified time for `.docx`, `.pptx`, and `.xlsx` files only.

Rationale:
This satisfies the base feature while keeping extraction concerns out of scope. It also establishes the traversal logic later indexing features will reuse.

Alternatives considered:
- Parse document content during discovery.
  Rejected because extraction belongs to later capabilities and would violate the MVP boundary.
- Support all files and let downstream filtering decide.
  Rejected because the base feature should validate only supported inputs and keep discovery predictable.

### 6. Make `doctor` the first operational integration point

Decision:
Expose `office-agent doctor` as the command that exercises configuration loading, dependency imports, SQLite availability, index path setup, and root readability.

Rationale:
This creates a fast feedback loop for developers and operators before search and indexing exist. It also validates that the foundational modules work together through a single user-facing path.

Alternatives considered:
- Wait to add diagnostics until indexing is implemented.
  Rejected because setup failures would otherwise surface later and be harder to isolate.
- Add multiple setup commands instead of one diagnostic command.
  Rejected because the first release benefits from one obvious entrypoint for environment validation.

## Risks / Trade-offs

- [The initial package boundaries may still shift once format adapters arrive] -> Keep service and domain interfaces small so later refactors stay local.
- [SQLite FTS5 availability can vary across Python and OS builds] -> Have `doctor` explicitly verify SQLite capabilities and report a clear failure mode.
- [Discovery rules may be too narrow for future formats or hidden-file policies] -> Keep extension filtering and root traversal configurable rather than hard-coded into CLI commands.
- [Locator parsing stubs can create a false sense of completeness] -> Keep the stub scope explicit in tests and document that full locator resolution is deferred.

## Migration Plan

1. Add packaging, module skeletons, and configuration primitives.
2. Add the SQLite store and schema initialization path.
3. Add Office file discovery and wire it through the application layer.
4. Add the `doctor` CLI flow that exercises all foundational checks.
5. Land unit tests covering config precedence, schema creation, discovery, and locator stub parsing.

Rollback:
Because this is foundational code with no existing production interface, rollback is simply reverting the package and schema initialization changes before downstream features depend on them.

## Open Questions

- Should the default config file live under the repo root for development or under a user config directory for local installs?
- Should `doctor` fail fast on the first error or always report a full checklist of pass/fail results?
- Should document discovery ignore temporary Office files such as `~$` lock files in the base capability or in a later refinement?
