## 1. Progress plumbing

- [x] 1.1 Add `src/offagent/app/progress.py` with the `ProgressReporter` protocol and `NullProgressReporter` implementation.
- [x] 1.2 Update `AppServices.index_path()`, `reindex_path()`, `refresh_document()`, and `index_document()` to accept an optional reporter and emit the required lifecycle events without changing commit behavior.

## 2. Embedding callback support

- [x] 2.1 Extend `src/offagent/adapters/embedding_provider.py` so `EmbeddingProvider.embed_texts()` accepts an optional `on_progress` callback and `LocalEmbeddingProvider` passes it through to the backend.
- [x] 2.2 Refactor the fastembed and hashing backends to report item-by-item embedding completion while preserving existing vector output semantics.

## 3. CLI progress rendering

- [x] 3.1 Add `rich` as a direct dependency and implement `src/offagent/interfaces/cli_progress.py` with a stderr-based `RichProgressReporter` for file and embedding progress.
- [x] 3.2 Update `src/offagent/interfaces/cli.py` so `index` and `reindex` construct the rich reporter only for interactive stderr sessions and fall back to `NullProgressReporter` for `--quiet`, `--json`, or non-TTY stderr.

## 4. Verification

- [x] 4.1 Add service and embedding-provider tests covering reporter event ordering, null-reporter behavior, and item-level embedding callbacks.
- [x] 4.2 Add CLI tests covering progress suppression for `--quiet`, `--json`, and non-interactive stderr, plus visible progress behavior for interactive indexing runs.
