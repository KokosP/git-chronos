# Copyright (c) sbgid.com
"""CSV export of the time report."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from ..analyzer import AnalysisResult
from ..config import Config

HEADERS = ["date", "sessions", "hours", "rate", "amount", "tasks"]

def export_csv(
    result: AnalysisResult,
    config: Config,
    out_dir: Path,
    period_label: str,
) -> Path:
    """Write one row per day to a .csv file and return its path."""
    filename = f"git-chronos-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
    out_path = Path(out_dir) / filename

    # utf-8-sig adds a BOM so Excel detects UTF-8; newline="" is required by csv
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)
        for day in result.days:
            hours = round(day.hours, 2)
            writer.writerow([
                day.day.isoformat(),
                len(day.sessions),
                f"{hours:.2f}",
                f"{result.hourly_rate:.2f}",
                f"{hours * result.hourly_rate:.2f}",
                ", ".join(day.tasks),
            ])
    return out_path