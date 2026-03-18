from __future__ import annotations

from pathlib import Path
from typing import Annotated

from offagent.app.services import AppServices, IndexSummary, PatchResult, format_doctor_report
from offagent.config import load_config

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


def main() -> None:
    if typer is None:
        raise SystemExit(
            "Typer is required to run the office-agent CLI. Install project dependencies first."
        )

    build_app()(prog_name="office-agent")


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
    ) -> None:
        settings = load_config(config)
        report = AppServices(settings).run_doctor()
        typer.echo(format_doctor_report(report))
        raise typer.Exit(code=0 if report.ok else 1)

    @app.command("index")
    def index_command(
        path: Path,
        config: Annotated[Path | None, CONFIG_OPTION] = None,
    ) -> None:
        services = AppServices(load_config(config))
        _run_command(lambda: _echo_index_summary(services.index_path(path)))

    @app.command("reindex")
    def reindex_command(
        path: Path,
        config: Annotated[Path | None, CONFIG_OPTION] = None,
    ) -> None:
        services = AppServices(load_config(config))
        _run_command(lambda: _echo_index_summary(services.reindex_path(path)))

    @app.command()
    def search(
        query: str,
        file_type: Annotated[str | None, typer.Option("--type")] = None,
        doc: Annotated[Path | None, typer.Option("--doc")] = None,
        config: Annotated[Path | None, CONFIG_OPTION] = None,
    ) -> None:
        services = AppServices(load_config(config))

        def runner() -> None:
            hits = services.search_corpus(query, file_type=file_type, document_path=doc)
            if not hits:
                typer.echo("No matches found.")
                return
            for hit in hits:
                typer.echo(
                    f"{hit.item_id}\tscore={hit.score:.3f}\tdoc={hit.display_name or hit.document_path}"
                )
                typer.echo(hit.preview)

        _run_command(runner)

    @app.command()
    def locate(
        doc: Annotated[Path, typer.Option("--doc")],
        paragraph: Annotated[int | None, typer.Option("--paragraph")] = None,
        slide: Annotated[int | None, typer.Option("--slide")] = None,
        shape: Annotated[int | None, typer.Option("--shape")] = None,
        sheet: Annotated[str | None, typer.Option("--sheet")] = None,
        cell: Annotated[str | None, typer.Option("--cell")] = None,
        config: Annotated[Path | None, CONFIG_OPTION] = None,
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
            for item in items:
                _echo_item(item)

        _run_command(runner)

    @app.command()
    def read(
        doc: Annotated[Path, typer.Option("--doc")],
        item: Annotated[str, typer.Option("--item")],
        config: Annotated[Path | None, CONFIG_OPTION] = None,
    ) -> None:
        services = AppServices(load_config(config))
        _run_command(lambda: typer.echo(services.read_item(doc, item)))

    @app.command()
    def replace(
        doc: Annotated[Path, typer.Option("--doc")],
        item: Annotated[str, typer.Option("--item")],
        text: Annotated[str, typer.Option("--text")],
        config: Annotated[Path | None, CONFIG_OPTION] = None,
    ) -> None:
        services = AppServices(load_config(config))
        _run_command(lambda: _echo_patch_result(services.replace_item_text(doc, item, text)))

    @app.command()
    def append(
        doc: Annotated[Path, typer.Option("--doc")],
        item: Annotated[str, typer.Option("--item")],
        text: Annotated[str, typer.Option("--text")],
        config: Annotated[Path | None, CONFIG_OPTION] = None,
    ) -> None:
        services = AppServices(load_config(config))
        _run_command(lambda: _echo_patch_result(services.append_item_text(doc, item, text)))

    @app.command("write-cell")
    def write_cell(
        doc: Annotated[Path, typer.Option("--doc")],
        sheet: Annotated[str, typer.Option("--sheet")],
        cell: Annotated[str, typer.Option("--cell")],
        value: Annotated[str, typer.Option("--value")],
        config: Annotated[Path | None, CONFIG_OPTION] = None,
    ) -> None:
        services = AppServices(load_config(config))
        _run_command(lambda: _echo_patch_result(services.write_cell_value(doc, sheet, cell, value)))

    return app


def _run_command(callback) -> None:
    if typer is None:
        raise RuntimeError("Typer is unavailable.")

    try:
        callback()
    except (FileNotFoundError, LookupError, RuntimeError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


def _echo_index_summary(summary: IndexSummary) -> None:
    if typer is None:
        raise RuntimeError("Typer is unavailable.")
    typer.echo(
        f"Scanned {summary.files_scanned} file(s); indexed {summary.files_indexed}; skipped {summary.files_skipped}."
    )


def _echo_item(item) -> None:
    if typer is None:
        raise RuntimeError("Typer is unavailable.")
    typer.echo(f"{item.item_id}\t{item.locator}\t{item.preview}")


def _echo_patch_result(result: PatchResult) -> None:
    if typer is None:
        raise RuntimeError("Typer is unavailable.")
    typer.echo(f"{result.item.item_id}\tupdated\t{result.output_path}")
