from __future__ import annotations

from pathlib import Path
from typing import Annotated

from offagent.app.services import AppServices, format_doctor_report
from offagent.config import load_config

try:
    import typer
except ModuleNotFoundError:  # pragma: no cover - covered indirectly by doctor
    typer = None


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
        config: Annotated[
            Path | None,
            typer.Option(
                "--config",
                help="Optional path to an office-agent TOML configuration file.",
                dir_okay=False,
                resolve_path=False,
            ),
        ] = None,
    ) -> None:
        settings = load_config(config)
        report = AppServices(settings).run_doctor()
        typer.echo(format_doctor_report(report))
        raise typer.Exit(code=0 if report.ok else 1)

    return app
