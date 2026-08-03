# Copyright (c) sbgid.com
"""Billable-time engine: groups commits into work sessions per day."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from .git_parser import Commit

DEFAULT_TASK = "General"


@dataclass
class Session:
    start: datetime
    end: datetime
    commits: list[Commit]
    task: str

    @property
    def minutes(self) -> float:
        return max((self.end - self.start).total_seconds() / 60, 0.0)


@dataclass
class DayReport:
    day: date
    sessions: list[Session] = field(default_factory=list)

    @property
    def hours(self) -> float:
        return sum(s.minutes for s in self.sessions) / 60

    @property
    def tasks(self) -> list[str]:
        seen: list[str] = []
        for s in self.sessions:
            if s.task not in seen:
                seen.append(s.task)
        return seen


@dataclass
class AnalysisResult:
    days: list[DayReport]
    hourly_rate: float
    currency: str
    task_hours: dict[str, float]

    @property
    def total_hours(self) -> float:
        return sum(d.hours for d in self.days)

    @property
    def total_amount(self) -> float:
        return self.total_hours * self.hourly_rate


def _detect_task(group: list[Commit]) -> str:
    return DEFAULT_TASK


def analyze_commits(
    commits: list[Commit],
    session_gap_hours: float,
    buffer_mins: int,
    hourly_rate: float,
    currency: str,
) -> AnalysisResult:
    """Group commits into sessions and compute billable hours.

    Rules:
    - commits are sorted chronologically and grouped by calendar day;
    - a gap between consecutive commits larger than ``session_gap_hours``
      closes the current session (the gap itself is unpaid rest);
    - ``buffer_mins`` is added before the first commit of every session,
      since code is written before it is committed.
    """
    by_day: dict[date, list[Commit]] = defaultdict(list)
    for commit in sorted(commits, key=lambda c: c.timestamp):
        by_day[commit.timestamp.date()].append(commit)

    gap = timedelta(hours=session_gap_hours)
    buffer = timedelta(minutes=buffer_mins)
    days: list[DayReport] = []
    task_hours: dict[str, float] = defaultdict(float)

    for day, day_commits in sorted(by_day.items()):
        groups: list[list[Commit]] = [[day_commits[0]]]
        for prev, cur in zip(day_commits, day_commits[1:]):
            if cur.timestamp - prev.timestamp <= gap:
                groups[-1].append(cur)
            else:
                groups.append([cur])

        report = DayReport(day=day)
        for group in groups:
            session = Session(
                start=group[0].timestamp - buffer,
                end=group[-1].timestamp,
                commits=group,
                task=_detect_task(group),
            )
            report.sessions.append(session)
            task_hours[session.task] += session.minutes / 60
        days.append(report)

    return AnalysisResult(
        days=days,
        hourly_rate=hourly_rate,
        currency=currency,
        task_hours=dict(task_hours),
    )
