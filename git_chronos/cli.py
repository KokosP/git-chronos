# Copyright (c) sbgid.com
"""Git-Chronos command-line interface built on Typer."""

from __future__ import annotations

import enum
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from . import __version__, config as config_module
from .analyzer import analyze_commits
from .config import Config, ConfigError
from .exporters.excel import export_excel
from .exporters.terminal import render_terminal, safe_symbol
from .git_parser import RepositoryError, get_commits

app = typer.Typer(
    name="git-chronos",
    help="Automatic time tracking and earnings calculation from local Git history.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


class Period(str, enum.Enum):
    week = "week"
    month = "month"
    custom = "custom"


class Export(str, enum.Enum):
    terminal = "terminal"
    excel = "excel"
    both = "both"


def _load_or_fail() -> tuple[Config, bool]:
    try:
        return config_module.load_config()
    except ConfigError as exc:
        console.print(f"[bold red]Config error:[/] {exc}")
        raise typer.Exit(code=1) from exc


def _parse_day(value: str, option: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        console.print(
            f"[bold red]Invalid date for {option}:[/] {value} (expected YYYY-MM-DD)"
        )
        raise typer.Exit(code=2)


def _resolve_period(
    period: Period, since: Optional[str], until: Optional[str]
) -> tuple[date | None, date | None, str]:
    today = date.today()
    if period is Period.week:
        return today - timedelta(days=7), today, "Last 7 days"
    if period is Period.month:
        return today - timedelta(days=30), today, "Last 30 days"
    if since is None:
        console.print(
            "[bold red]--period custom requires --since YYYY-MM-DD[/] "
            "(--until is optional, defaults to today)"
        )
        raise typer.Exit(code=2)
    since_d = _parse_day(since, "--since")
    until_d = _parse_day(until, "--until") if until else today
    if until_d < since_d:
        console.print("[bold red]--until must not be earlier than --since[/]")
        raise typer.Exit(code=2)
    return since_d, until_d, f"{since_d.isoformat()} — {until_d.isoformat()}"


@app.command()
def init(
    force: bool = typer.Option(
        False, "--force", help="Overwrite the existing config with defaults."
    ),
) -> None:
    """Create the default ~/.git-chronos.toml configuration file."""
    path = config_module.config_path()
    existed = path.exists()
    if existed and not force:
        console.print(f"[yellow]Config already exists:[/] {path}")
        console.print("Use [bold]--force[/] to overwrite it with defaults.")
        raise typer.Exit(code=0)
    config_module.init_config(overwrite=force)
    console.print(f"[green]Config written to[/] {path}")
    console.print("Edit [bold]developer.email[/] to match your Git author email.")


@app.command()
def status() -> None:
    """Validate the configuration file and show current settings."""
    cfg, created = _load_or_fail()
    if created:
        console.print(
            f"[yellow]No config found — created default:[/] {cfg.path}\n"
            "Edit [bold]developer.email[/] to match your Git author email.\n"
        )

    table = Table(title=f"Git-Chronos v{__version__} — config OK", box=None)
    table.add_column("Setting", style="bold cyan")
    table.add_column("Value")
    table.add_row("Config file", str(cfg.path))
    table.add_row("Developer", f"{cfg.developer_name} <{cfg.developer_email}>")
    table.add_row(
        "Rate",
        f"{safe_symbol(console, cfg.currency_symbol, cfg.currency)}"
        f"{cfg.hourly_rate:.2f}/h ({cfg.currency})",
    )
    table.add_row("Session gap", f"{cfg.session_gap_hours:g} h")
    table.add_row("Start buffer", f"{cfg.first_commit_buffer_mins} min")
    table.add_row("Company", cfg.company_name)
    table.add_row("Client", cfg.client_name)
    console.print(table)


@app.command()
def analyze(
    path: Path = typer.Argument(
        Path("."), help="Path to the Git repository to analyze."
    ),
    period: Period = typer.Option(
        Period.month, "--period", "-p", help="Reporting period."
    ),
    export: Export = typer.Option(
        Export.terminal, "--export", "-e", help="Output format."
    ),
    since: Optional[str] = typer.Option(
        None, "--since", help="Start date YYYY-MM-DD (custom period)."
    ),
    until: Optional[str] = typer.Option(
        None, "--until", help="End date YYYY-MM-DD (custom period, default: today)."
    ),
    currency: Optional[str] = typer.Option(
        None, "--currency", "-c", help="Override currency, e.g. USD, EUR, GBP."
    ),
    rate: Optional[float] = typer.Option(
        None, "--rate", "-r", help="Override hourly rate from the config."
    ),
) -> None:
    """Analyze a repository and report billable time."""
    cfg, created = _load_or_fail()
    if currency:
        cfg = replace(cfg, currency=currency.strip().upper())
    if rate is not None:
        cfg = replace(cfg, hourly_rate=rate)
    if created:
        console.print(
            f"[yellow]No config found — created default:[/] {cfg.path}\n"
            "Set [bold]developer.email[/] to your Git author email and re-run.\n"
        )

    since_d, until_d, period_label = _resolve_period(period, since, until)

    try:
        commits = get_commits(path, cfg.developer_email, since_d, until_d)
    except RepositoryError as exc:
        console.print(f"[bold red]Repository error:[/] {exc}")
        raise typer.Exit(code=1) from exc

    if not commits:
        console.print(
            f"[yellow]No commits by[/] {cfg.developer_email} "
            f"[yellow]in {path.resolve()} for the selected period.[/]"
        )
        console.print("Check [bold]developer.email[/] in the config or widen the period.")
        raise typer.Exit(code=0)

    result = analyze_commits(
        commits,
        session_gap_hours=cfg.session_gap_hours,
        buffer_mins=cfg.first_commit_buffer_mins,
        hourly_rate=cfg.hourly_rate,
        currency=cfg.currency,
    )
    repo_label = str(Path(path).resolve())

    if export in (Export.terminal, Export.both):
        render_terminal(result, cfg, repo_label, period_label, console)

    if export in (Export.excel, Export.both):
        out_path = export_excel(result, cfg, Path.cwd(), period_label)
        console.print(f"[green]Excel invoice saved:[/] {out_path}")
