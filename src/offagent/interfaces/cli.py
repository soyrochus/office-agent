from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

from offagent.app.progress import NullProgressReporter
from offagent.app.services import (
    AppServices,
)
from offagent.config import load_config
from offagent.errors import (
    InvalidArgumentsError,
    PolicyRefusedError,
    StaleLocatorError,
    TargetNotEditableError,
    TargetNotFoundError,
)
from offagent.interfaces.cli_output import (
    emit_output,
    render_doctor_report,
    render_document,
    render_documents,
    render_index_summary,
    render_item,
    render_items,
    render_patch_result,
    render_search_hits,
    render_text_result,
)

try:
    import typer
except ModuleNotFoundError:  # pragma: no cover - covered indirectly by doctor
    typer = None

if typer is not None:
    CONFIG_OPTION = typer.Option(
        "--config",
        help="Optional path to an office-agent TOML configuration file.",
        dir_okay=False,
        resolve_path=False,
    )
else:  # pragma: no cover - exercised only when typer is unavailable
    CONFIG_OPTION = None

if typer is not None:
    JSON_OPTION = typer.Option(
        "--json",
        help="Emit machine-readable JSON with no extra text.",
    )
    QUIET_OPTION = typer.Option(
        "--quiet",
        help="Suppress successful command output.",
    )
else:  # pragma: no cover - exercised only when typer is unavailable
    JSON_OPTION = None
    QUIET_OPTION = None


def main() -> None:
    if typer is None:
        raise SystemExit(
            "Typer is required to run the office-agent CLI. Install project dependencies first."
        )

    app = build_app()
    app()


def build_app():
    if typer is None:
        raise RuntimeError("Typer is unavailable.")

    app = typer.Typer(help="Local-first Office document tooling.")

    @app.callback()
    def main_callback() -> None:
        """Root command group for office-agent."""

    @app.command()
    def doctor(
        config: Annotated[Path | None, CONFIG_OPTION] = None,
        as_json: Annotated[bool, JSON_OPTION] = False,
        quiet: Annotated[bool, QUIET_OPTION] = False,
    ) -> None:
        settings = load_config(config)
        services = AppServices(settings)
        report = _run_command(
            lambda: services.run_doctor(), as_json=as_json, quiet=quiet
        )
        emit_output(
            report,
            as_json=as_json,
            quiet=quiet,
            human_renderer=render_doctor_report,
            echo=typer.echo,
        )
        raise typer.Exit(code=0 if report.ok else 1)

    @app.command("index")
    def index_command(
        path: Path,
        with_embeddings: Annotated[bool, typer.Option("--with-embeddings")] = False,
        config: Annotated[Path | None, CONFIG_OPTION] = None,
        as_json: Annotated[bool, JSON_OPTION] = False,
        quiet: Annotated[bool, QUIET_OPTION] = False,
    ) -> None:
        services = AppServices(load_config(config))

        def runner() -> None:
            with _build_index_reporter(as_json=as_json, quiet=quiet) as reporter:
                summary = services.index_path(
                    path,
                    with_embeddings=with_embeddings,
                    reporter=reporter,
                )
            emit_output(
                {
                    "path": path.resolve(),
                    "summary": summary,
                },
                as_json=as_json,
                quiet=quiet,
                human_renderer=render_index_summary,
                echo=typer.echo,
            )

        _run_command(
            runner,
            as_json=as_json,
            quiet=quiet,
        )

    @app.command("reindex")
    def reindex_command(
        path: Path,
        with_embeddings: Annotated[bool, typer.Option("--with-embeddings")] = False,
        config: Annotated[Path | None, CONFIG_OPTION] = None,
        as_json: Annotated[bool, JSON_OPTION] = False,
        quiet: Annotated[bool, QUIET_OPTION] = False,
    ) -> None:
        services = AppServices(load_config(config))

        def runner() -> None:
            with _build_index_reporter(as_json=as_json, quiet=quiet) as reporter:
                summary = services.reindex_path(
                    path,
                    with_embeddings=with_embeddings,
                    reporter=reporter,
                )
            emit_output(
                {
                    "path": path.resolve(),
                    "summary": summary,
                },
                as_json=as_json,
                quiet=quiet,
                human_renderer=render_index_summary,
                echo=typer.echo,
            )

        _run_command(
            runner,
            as_json=as_json,
            quiet=quiet,
        )

    @app.command()
    def search(
        query: str,
        file_type: Annotated[str | None, typer.Option("--type")] = None,
        doc: Annotated[Path | None, typer.Option("--doc")] = None,
        mode: Annotated[str, typer.Option("--mode")] = "keyword",
        config: Annotated[Path | None, CONFIG_OPTION] = None,
        as_json: Annotated[bool, JSON_OPTION] = False,
        quiet: Annotated[bool, QUIET_OPTION] = False,
    ) -> None:
        services = AppServices(load_config(config))

        def runner() -> None:
            hits = services.search_corpus(
                query,
                file_type=file_type,
                document_path=doc,
                mode=mode,
            )
            emit_output(
                {"hits": hits},
                as_json=as_json,
                quiet=quiet,
                human_renderer=lambda payload: render_search_hits(payload["hits"]),
                echo=typer.echo,
            )

        _run_command(runner, as_json=as_json, quiet=quiet)

    @app.command()
    def locate(
        doc: Annotated[Path, typer.Option("--doc")],
        paragraph: Annotated[int | None, typer.Option("--paragraph")] = None,
        slide: Annotated[int | None, typer.Option("--slide")] = None,
        shape: Annotated[int | None, typer.Option("--shape")] = None,
        sheet: Annotated[str | None, typer.Option("--sheet")] = None,
        cell: Annotated[str | None, typer.Option("--cell")] = None,
        config: Annotated[Path | None, CONFIG_OPTION] = None,
        as_json: Annotated[bool, JSON_OPTION] = False,
        quiet: Annotated[bool, QUIET_OPTION] = False,
    ) -> None:
        services = AppServices(load_config(config))

        def runner() -> None:
            items = services.locate_items(
                doc,
                paragraph_index=paragraph,
                slide_number=slide,
                shape_id=shape,
                sheet_name=sheet,
                cell_coordinate=cell,
            )
            emit_output(
                {"items": items},
                as_json=as_json,
                quiet=quiet,
                human_renderer=lambda payload: render_items(payload["items"]),
                echo=typer.echo,
            )

        _run_command(runner, as_json=as_json, quiet=quiet)

    @app.command()
    def read(
        doc: Annotated[Path, typer.Option("--doc")],
        item: Annotated[str, typer.Option("--item")],
        config: Annotated[Path | None, CONFIG_OPTION] = None,
        as_json: Annotated[bool, JSON_OPTION] = False,
        quiet: Annotated[bool, QUIET_OPTION] = False,
    ) -> None:
        services = AppServices(load_config(config))
        _run_command(
            lambda: emit_output(
                {
                    "document_path": doc.resolve(),
                    "item_id": item,
                    "text": services.read_item(doc, item),
                },
                as_json=as_json,
                quiet=quiet,
                human_renderer=render_text_result,
                echo=typer.echo,
            ),
            as_json=as_json,
            quiet=quiet,
        )

    @app.command()
    def replace(
        doc: Annotated[Path, typer.Option("--doc")],
        item: Annotated[str, typer.Option("--item")],
        text: Annotated[str, typer.Option("--text")],
        output_mode: Annotated[str, typer.Option("--output-mode")] = "versioned",
        config: Annotated[Path | None, CONFIG_OPTION] = None,
        as_json: Annotated[bool, JSON_OPTION] = False,
        quiet: Annotated[bool, QUIET_OPTION] = False,
    ) -> None:
        services = AppServices(load_config(config))
        _run_command(
            lambda: emit_output(
                services.replace_item_text(doc, item, text, output_mode=output_mode),
                as_json=as_json,
                quiet=quiet,
                human_renderer=render_patch_result,
                echo=typer.echo,
            ),
            as_json=as_json,
            quiet=quiet,
        )

    @app.command()
    def append(
        doc: Annotated[Path, typer.Option("--doc")],
        item: Annotated[str, typer.Option("--item")],
        text: Annotated[str, typer.Option("--text")],
        output_mode: Annotated[str, typer.Option("--output-mode")] = "versioned",
        config: Annotated[Path | None, CONFIG_OPTION] = None,
        as_json: Annotated[bool, JSON_OPTION] = False,
        quiet: Annotated[bool, QUIET_OPTION] = False,
    ) -> None:
        services = AppServices(load_config(config))
        _run_command(
            lambda: emit_output(
                services.append_item_text(doc, item, text, output_mode=output_mode),
                as_json=as_json,
                quiet=quiet,
                human_renderer=render_patch_result,
                echo=typer.echo,
            ),
            as_json=as_json,
            quiet=quiet,
        )

    @app.command("write-cell")
    def write_cell(
        doc: Annotated[Path, typer.Option("--doc")],
        sheet: Annotated[str, typer.Option("--sheet")],
        cell: Annotated[str, typer.Option("--cell")],
        value: Annotated[str, typer.Option("--value")],
        output_mode: Annotated[str, typer.Option("--output-mode")] = "versioned",
        config: Annotated[Path | None, CONFIG_OPTION] = None,
        as_json: Annotated[bool, JSON_OPTION] = False,
        quiet: Annotated[bool, QUIET_OPTION] = False,
    ) -> None:
        services = AppServices(load_config(config))
        _run_command(
            lambda: emit_output(
                services.write_cell_value(
                    doc, sheet, cell, value, output_mode=output_mode
                ),
                as_json=as_json,
                quiet=quiet,
                human_renderer=render_patch_result,
                echo=typer.echo,
            ),
            as_json=as_json,
            quiet=quiet,
        )

    @app.command("list")
    def list_command(
        config: Annotated[Path | None, CONFIG_OPTION] = None,
        as_json: Annotated[bool, JSON_OPTION] = False,
        quiet: Annotated[bool, QUIET_OPTION] = False,
    ) -> None:
        services = AppServices(load_config(config))
        _run_command(
            lambda: emit_output(
                {"documents": services.list_documents()},
                as_json=as_json,
                quiet=quiet,
                human_renderer=lambda payload: render_documents(payload["documents"]),
                echo=typer.echo,
            ),
            as_json=as_json,
            quiet=quiet,
        )

    @app.command()
    def show(
        doc: Annotated[Path, typer.Option("--doc")],
        item: Annotated[str | None, typer.Option("--item")] = None,
        config: Annotated[Path | None, CONFIG_OPTION] = None,
        as_json: Annotated[bool, JSON_OPTION] = False,
        quiet: Annotated[bool, QUIET_OPTION] = False,
    ) -> None:
        services = AppServices(load_config(config))

        def runner() -> None:
            if item is None:
                emit_output(
                    services.show_document(doc),
                    as_json=as_json,
                    quiet=quiet,
                    human_renderer=render_document,
                    echo=typer.echo,
                )
                return
            emit_output(
                services.show_item(doc, item),
                as_json=as_json,
                quiet=quiet,
                human_renderer=render_item,
                echo=typer.echo,
            )

        _run_command(runner, as_json=as_json, quiet=quiet)

    @app.command()
    def mcp(
        config: Annotated[Path | None, CONFIG_OPTION] = None,
    ) -> None:
        settings = load_config(config)

        def runner() -> None:
            from offagent.interfaces.mcp import run_mcp_server

            run_mcp_server(settings)

        _run_command(runner)

    return app


def _run_command(callback, *, as_json: bool = False, quiet: bool = False):
    if typer is None:
        raise RuntimeError("Typer is unavailable.")

    try:
        _validate_output_flags(as_json, quiet)
        return callback()
    except InvalidArgumentsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    except (FileNotFoundError, TargetNotFoundError, StaleLocatorError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=3) from exc
    except TargetNotEditableError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=4) from exc
    except PolicyRefusedError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=5) from exc
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


def _validate_output_flags(as_json: bool, quiet: bool) -> None:
    if as_json and quiet:
        raise InvalidArgumentsError("Choose either --json or --quiet, not both.")


def _build_index_reporter(*, as_json: bool, quiet: bool):
    if quiet or as_json or not _stderr_supports_live_progress():
        return NullProgressReporter()
    return _rich_progress_reporter_class()()


def _stderr_supports_live_progress() -> bool:
    return sys.stderr.isatty()


def _rich_progress_reporter_class():
    try:
        from offagent.interfaces.cli_progress import RichProgressReporter
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Rich is required to render indexing progress. Install project dependencies first."
        ) from exc
    return RichProgressReporter
