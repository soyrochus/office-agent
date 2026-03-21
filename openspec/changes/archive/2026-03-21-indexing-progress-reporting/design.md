## Context

Indexing currently runs through `AppServices.index_path()` and `AppServices.index_document()`, with the CLI in `src/offagent/interfaces/cli.py` invoking those services and then rendering a final summary. When `--with-embeddings` is enabled, `LocalEmbeddingProvider.embed_texts()` delegates to either the fastembed-backed iterator or the hashing fallback, but neither path emits incremental progress. As a result, long embedding runs appear stalled even though work is advancing.

This change crosses the service layer, embedding adapter layer, and CLI interface layer, and it introduces a new direct dependency on `rich`. The design therefore needs to keep terminal concerns out of application services while still giving the interface layer enough lifecycle events to render useful progress.

## Goals / Non-Goals

**Goals:**
- Make `office-agent index` and `office-agent reindex` visibly report progress during long-running work.
- Keep the service layer UI-agnostic by reporting progress through a small protocol instead of importing `rich` directly.
- Support both file-level progress and embedding-item progress when embeddings are enabled.
- Preserve existing output-mode guarantees by suppressing progress in `--quiet`, `--json`, and non-TTY stderr scenarios.
- Keep the hashing embedding backend behavior aligned with the fastembed path so tests and fallback behavior share one progress contract.

**Non-Goals:**
- Redesign the final success summary emitted after indexing completes.
- Add progress reporting to commands other than `index` and `reindex`.
- Introduce concurrent embedding generation or parallel file indexing.
- Persist progress state outside the lifetime of a single CLI invocation.

## Decisions

### 1. Add a service-layer `ProgressReporter` protocol with a no-op default

`src/offagent/app/progress.py` will define a `ProgressReporter` protocol plus `NullProgressReporter`. `AppServices.index_path()`, `index_document()`, `reindex_path()`, and `refresh_document()` will accept an optional reporter and normalize `None` to the null implementation.

This keeps the service layer responsible only for reporting lifecycle events it already knows about: overall index start, per-file start, embedding start, per-item embedding progress, file completion, and overall completion.

Why this approach:
- It preserves clean layering. Services report state; interfaces decide whether and how to render it.
- It keeps tests simple because a fake reporter can capture event sequences without needing terminal rendering.

Alternative considered:
- Import `rich` directly inside `AppServices` and render progress there. Rejected because it couples business logic to one UI implementation and makes quiet/JSON behavior harder to enforce consistently.

### 2. Thread embedding progress through the provider boundary as an optional callback

`EmbeddingProvider.embed_texts()` will gain `on_progress: Callable[[int, int], None] | None = None`. `LocalEmbeddingProvider` will pass that callback into the selected backend. Both `_FastEmbedBackend.embed()` and `_HashingBackend.embed()` will move from list-comprehension style collection to explicit loops so they can call the callback after each item is produced.

Why this approach:
- The embedding layer is the only place that knows when each vector is actually complete.
- The callback keeps the protocol minimal and avoids introducing service-level knowledge of backend internals.

Alternative considered:
- Estimate progress at the service layer before and after one bulk embedding call. Rejected because it would only show a start/end jump and would not solve the silent-terminal problem during long vector generation.

### 3. Render progress in the CLI layer with a single Rich progress context on `stderr`

`src/offagent/interfaces/cli_progress.py` will provide `RichProgressReporter`, responsible for mapping reporter events to one persistent `rich.progress.Progress` instance. The reporter will maintain:
- One file task covering total files discovered for the indexing request
- One embedding sub-task that is created or updated only when embeddings are active for the current file

Rendering will go to `stderr` so JSON and human-readable summaries on `stdout` remain unchanged. The reporter will be used as a context manager from `index_command()` and `reindex_command()`.

Why this approach:
- A single progress context avoids flicker and inconsistent terminal state across files.
- `stderr` is the standard place for transient progress UI that should not pollute redirected `stdout`.

Alternative considered:
- Print ad hoc status lines with `typer.echo()`. Rejected because it cannot provide an updating progress bar/spinner experience and would either spam the terminal or require custom cursor control.

### 4. Gate progress reporter construction at the CLI boundary

The CLI will construct `RichProgressReporter` only when `not (quiet or as_json)` and `sys.stderr.isatty()` is true. Otherwise it will pass `NullProgressReporter` into the service layer. This ensures progress suppression is decided once, near the interface, rather than via scattered checks in service code.

Why this approach:
- It makes output-mode behavior explicit and easy to test.
- It preserves the existing contract that `--json` writes only structured payloads to `stdout`, while `--quiet` suppresses informational success output entirely.

Alternative considered:
- Always construct the reporter and let it internally decide whether to render. Rejected because it obscures command behavior and complicates tests that should assert the CLI passes a no-op reporter in suppressed modes.

### 5. Keep indexing transactional behavior unchanged

Progress events will reflect work as it proceeds, but they will not alter the existing transaction boundaries in `index_document()`. The document upsert, item replacement, and embedding replacement will still commit only after the file finishes successfully.

Why this approach:
- The change is about observability, not persistence semantics.
- Avoiding transactional changes reduces regression risk in indexing correctness.

Alternative considered:
- Commit incrementally during embedding generation to match progress updates. Rejected because it creates partial-write states and materially changes failure semantics.

## Risks / Trade-offs

- `[Callback overhead during embedding]` -> Progress callbacks fire once per item, which adds minor overhead for large batches. Mitigation: keep the callback signature minimal and do constant-time updates only.
- `[Terminal rendering inconsistencies across environments]` -> Some CI or redirected sessions may not handle live progress well. Mitigation: gate on `sys.stderr.isatty()` and fall back to `NullProgressReporter`.
- `[Progress reflects work in flight, not committed state]` -> A file may show full embedding progress and then fail before commit. Mitigation: treat progress as operational feedback only; final success remains the existing post-command summary.
- `[Extra dependency surface from Rich]` -> A new direct dependency increases install and compatibility surface. Mitigation: isolate usage to one CLI module and keep the service layer independent of the library.

## Migration Plan

No data migration is required. Rollout is code-only:

1. Add the progress protocol and callback plumbing.
2. Add the Rich-based CLI reporter and dependency.
3. Wire `index` and `reindex` to construct the appropriate reporter.
4. Add tests for reporter event flow, output-mode suppression, and embedding callback behavior.

Rollback is straightforward: remove reporter wiring from the CLI and service signatures, and indexing behavior returns to the current silent execution model.

## Open Questions

- Whether the file task should report only indexable Office files or all scanned filesystem candidates. The current service summary tracks both scanned and indexed counts, and the spec should make the user-visible progress denominator explicit.
- Whether the embedding task should remain visible for zero-item files or be omitted entirely. The current proposal implies it should appear only when embeddings are active and there is work to show.
