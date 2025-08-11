from __future__ import annotations

import sys
import json
import pathlib
from typing import Optional
from enum import Enum

import typer
import structlog
from rich.console import Console

from .config import load_config, CloakConfig
from .engine.pipeline import Pipeline, ScanResult

console = Console()
log = structlog.get_logger()
app = typer.Typer(add_completion=False, no_args_is_help=True, help="cloak — privacy-first PII scrubber")

class Mode(str, Enum):
    mask = "mask"
    hash = "hash"
    pseudonymize = "pseudonymize"


def version_callback(value: bool):
    if value:
        from . import __version__
        console.print(f"cloak {__version__}")
        raise typer.Exit()


@app.callback()
def common(
    ctx: typer.Context,
    config: Optional[pathlib.Path] = typer.Option(None, "--config", help="Path to .cloak.yaml"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logs"),
    version: Optional[bool] = typer.Option(None, "--version", callback=version_callback, is_eager=True),
):
    """Global options (config, verbosity)."""
    structlog.configure(processors=[structlog.processors.JSONRenderer()])
    ctx.obj = {"config": load_config(config) if config else CloakConfig()}
    if verbose:
        log.info("verbose_enabled")


@app.command()
def scan(
    src: pathlib.Path = typer.Argument(..., help="File or directory to scan"),
    report: Optional[pathlib.Path] = typer.Option(None, "--report", help="Write HTML report to this path"),
):
    """Detect PII without modifying files."""
    cfg: CloakConfig = typer.get_app_dir  # type: ignore
    cfg = typer.get_current_context().obj["config"]
    pipeline = Pipeline(cfg)
    result: ScanResult = pipeline.scan_path(src)
    console.print(f"Scanned {result.files} files, {result.entities} entities found")
    if report:
        from .reporting.html import write_report
        write_report(result, report)
        console.print(f"[green]Report written:[/green] {report}")


@app.command()
def scrub(
    src: pathlib.Path = typer.Argument(..., help="File or directory to scrub"),
    out: pathlib.Path = typer.Option(..., "--out", help="Destination directory for sanitized output"),
    mode: Mode = typer.Option(
    Mode.pseudonymize, "--mode",
    help="Action to apply to entities",
    case_sensitive=False
),
):
    """Write a sanitized mirror of the source to OUT."""
    cfg: CloakConfig = typer.get_current_context().obj["config"]
    pipeline = Pipeline(cfg, mode=mode)
    pipeline.scrub_path(src, out)
    console.print(f"[green]Scrub complete[/green] → {out}")


@app.command()
def review(review_file: pathlib.Path = typer.Argument(..., help="review.jsonl to triage")):
    """Open the (stub) TUI to accept/fix low-confidence items."""
    try:
        from .tui.review_app import launch
    except Exception as e:  # pragma: no cover
        console.print(f"[red]TUI dependencies missing or error: {e}[/red]")
        raise typer.Exit(code=1)
    launch(review_file)


@app.command()
def hook(cmd: str = typer.Argument(..., help="install|uninstall")):
    """Manage the pre-commit hook (writes .pre-commit-config.yaml)."""
    if cmd == "install":
        console.print("Add the provided .pre-commit-config.yaml to your repo and run: pre-commit install")
    elif cmd == "uninstall":
        console.print("Run: pre-commit uninstall")
    else:
        raise typer.BadParameter("cmd must be 'install' or 'uninstall'")
