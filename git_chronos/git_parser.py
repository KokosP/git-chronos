# Copyright (c) sbgid.com
"""Extraction of commit history from a local Git repository via GitPython."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from git import InvalidGitRepositoryError, NoSuchPathError, Repo


class RepositoryError(Exception):
    """Raised when the target path is not a readable Git repository."""


@dataclass(frozen=True)
class Commit:
    sha: str
    timestamp: datetime
    subject: str


def get_commits(
    repo_path: str | Path,
    email: str,
    since: date | None = None,
    until: date | None = None,
) -> list[Commit]:
    """Return commits authored by ``email`` in chronological order.

    ``since`` / ``until`` are inclusive calendar-day bounds; ``None`` removes
    the corresponding bound.
    """
    try:
        repo = Repo(str(Path(repo_path).resolve()))
    except (InvalidGitRepositoryError, NoSuchPathError) as exc:
        raise RepositoryError(f"Not a Git repository: {repo_path}") from exc

    needle = email.strip().lower()
    commits: list[Commit] = []
    try:
        for item in repo.iter_commits():
            author_email = (item.author.email or "").lower()
            if needle and author_email != needle:
                continue
            ts = item.committed_datetime
            if since and ts.date() < since:
                continue
            if until and ts.date() > until:
                continue
            subject = item.message.strip().splitlines()[0] if item.message else ""
            commits.append(Commit(sha=item.hexsha[:8], timestamp=ts, subject=subject))
    except ValueError as exc:
        raise RepositoryError(f"Cannot read history in {repo_path}: {exc}") from exc

    return sorted(commits, key=lambda c: c.timestamp)
