# Copyright (c) sbgid.com
"""Colored terminal dashboard rendered with Rich."""

from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..analyzer import AnalysisResult
from ..config import Config

BAR_WIDTH = 24


def _meta_table(config: Config, repo_label: str, period_label: str) -> Table:
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold cyan", justify="right")
    grid.add_column(style="white")
    grid.add_row("Developer", f"{config.developer_name} <{config.developer_email}>")
    grid.add_row("Client", config.client_name)
    grid.add_row("Company", config.company_name)
    grid.add_row("Repository", repo_label)
    grid.add_row("Period", period_label)
    grid.add_row("Rate", f"{config.currency_symbol}{config.hourly_rate:.2f}/h")
    return grid


def _days_table(result: AnalysisResult, symbol: str) -> Table:
    table = Table(box=None, pad_edge=False, show_edge=False)
    table.add_column("Date", style="bold")
    table.add_column("Sessions", justify="right")
    table.add_column("Hours", justify="right")
    table.add_column("Activity")
    table.add_column("Amount", justify="right", style="green")
    table.add_column("Tasks", style="dim")

    max_hours = max((d.hours for d in result.days), default=1) or 1
    for day in result.days:
        bar_len = round(day.hours / max_hours * BAR_WIDTH)
        bar = Text("█" * bar_len + "░" * (BAR_WIDTH - bar_len), style="green")
        table.add_row(
            day.day.isoformat(),
            str(len(day.sessions)),
            f"{day.hours:.1f}",
            bar,
            f"{symbol}{day.hours * result.hourly_rate:,.2f}",
            ", ".join(day.tasks),
        )
    return table


def _tasks_table(result: AnalysisResult, symbol: str) -> Table:
    table = Table(box=None, pad_edge=False, show_edge=False)
    table.add_column("Task", style="bold")
    table.add_column("Hours", justify="right")
    table.add_column("Amount", justify="right", style="green")
    for task, hours in sorted(result.task_hours.items(), key=lambda kv: -kv[1]):
        table.add_row(task, f"{hours:.1f}", f"{symbol}{hours * result.hourly_rate:,.2f}")
    return table


def render_terminal(
    result: AnalysisResult,
    config: Config,
    repo_label: str,
    period_label: str,
    console: Console | None = None,
) -> None:
    console = console or Console()
    symbol = config.currency_symbol

    parts: list = [_meta_table(config, repo_label, period_label), ""]

    if result.days:
        parts.append(Text("Daily breakdown", style="bold underline"))
        parts.append(_days_table(result, symbol))
        parts.append("")

    if result.task_hours and (
        len(result.task_hours) > 1 or "General" not in result.task_hours
    ):
        parts.append(Text("Per-task breakdown", style="bold underline"))
        parts.append(_tasks_table(result, symbol))
        parts.append("")

    total = Text(
        f"Total due: {result.total_hours:.1f} h × "
        f"{symbol}{config.hourly_rate:.2f} = {symbol}{result.total_amount:,.2f}",
        style="bold green",
    )
    parts.append(total)

    console.print(
        Panel(
            Group(*parts),
            title="[bold cyan]GIT-CHRONOS[/]",
            subtitle="[dim]local time tracking[/]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
