from datetime import datetime

from git_chronos.analyzer import analyze_commits
from git_chronos.git_parser import Commit


def make_commit(hour, minute, subject="Update", day=13):
    return Commit(
        sha=f"{day:02d}{hour:02d}{minute:02d}",
        timestamp=datetime(2026, 11, day, hour, minute),
        subject=subject,
    )


def test_analyze_commits_with_empty_input():
    result = analyze_commits(
        commits=[],
        session_gap_hours=2,
        buffer_mins=30,
        hourly_rate=50.0,
        currency="USD",
    )

    assert result.days == []
    assert result.total_hours == 0
    assert result.total_amount == 0
    assert result.task_hours == {}


def test_splits_sessions_when_gap_exceeds_threshold():
    commits = [
        make_commit(13, 0),
        make_commit(9, 30),
        make_commit(9, 0),
    ]

    result = analyze_commits(
        commits=commits,
        session_gap_hours=2,
        buffer_mins=0,
        hourly_rate=50.0,
        currency="USD",
    )

    sessions = result.days[0].sessions

    assert len(sessions) == 2
    assert len(sessions[0].commits) == 2
    assert len(sessions[1].commits) == 1
    assert sessions[0].start == datetime(2026, 11, 13, 9, 0)
    assert sessions[0].end == datetime(2026, 11, 13, 9, 30)
    assert sessions[1].start == datetime(2026, 11, 13, 13, 0)


def test_commits_at_exact_session_gap_stay_in_same_session():
    commits = [
        make_commit(9, 0),
        make_commit(11, 0),
    ]

    result = analyze_commits(
        commits=commits,
        session_gap_hours=2,
        buffer_mins=0,
        hourly_rate=50.0,
        currency="USD",
    )

    sessions = result.days[0].sessions

    assert len(sessions) == 1
    assert len(sessions[0].commits) == 2


def test_applies_buffer_before_first_commit():
    commits = [
        make_commit(9, 0),
        make_commit(9, 30),
    ]

    result = analyze_commits(
        commits=commits,
        session_gap_hours=2,
        buffer_mins=30,
        hourly_rate=50.0,
        currency="USD",
    )

    session = result.days[0].sessions[0]

    assert session.start == datetime(2026, 11, 13, 8, 30)
    assert session.end == datetime(2026, 11, 13, 9, 30)
    assert session.minutes == 60


def test_applies_buffer_to_every_session():
    commits = [
        make_commit(9, 0),
        make_commit(9, 30),
        make_commit(13, 0),
        make_commit(13, 30),
    ]

    result = analyze_commits(
        commits=commits,
        session_gap_hours=2,
        buffer_mins=30,
        hourly_rate=50.0,
        currency="USD",
    )

    sessions = result.days[0].sessions

    assert len(sessions) == 2
    assert sessions[0].start == datetime(2026, 11, 13, 8, 30)
    assert sessions[1].start == datetime(2026, 11, 13, 12, 30)
    assert sessions[0].minutes == 60
    assert sessions[1].minutes == 60


def test_detects_ticket_prefix_from_commit_subject():
    commits = [
        make_commit(9, 0, "PROJ-123: Add login"),
        make_commit(9, 30, "Update login validation"),
    ]

    result = analyze_commits(
        commits=commits,
        session_gap_hours=2,
        buffer_mins=0,
        hourly_rate=50.0,
        currency="USD",
    )

    assert result.days[0].sessions[0].task == "PROJ-123"
    assert result.task_hours == {"PROJ-123": 0.5}


def test_detects_plain_task_prefix():
    commits = [
        make_commit(9, 0, "Backend: Add authentication"),
        make_commit(9, 30, "Backend: Fix validation"),
    ]

    result = analyze_commits(
        commits=commits,
        session_gap_hours=2,
        buffer_mins=0,
        hourly_rate=50.0,
        currency="USD",
    )

    assert result.days[0].sessions[0].task == "Backend"
    assert result.task_hours == {"Backend": 0.5}


def test_uses_general_when_no_task_prefix_exists():
    commits = [
        make_commit(9, 0, "Add authentication"),
        make_commit(9, 30, "Fix validation"),
    ]

    result = analyze_commits(
        commits=commits,
        session_gap_hours=2,
        buffer_mins=0,
        hourly_rate=50.0,
        currency="USD",
    )

    assert result.days[0].sessions[0].task == "General"
    assert result.task_hours == {"General": 0.5}


def test_detects_prefix_from_later_commit_in_session():
    commits = [
        make_commit(9, 0, "Add authentication"),
        make_commit(9, 30, "PROJ-456: Fix login validation"),
    ]

    result = analyze_commits(
        commits=commits,
        session_gap_hours=2,
        buffer_mins=0,
        hourly_rate=50.0,
        currency="USD",
    )

    assert result.days[0].sessions[0].task == "PROJ-456"
    assert result.task_hours == {"PROJ-456": 0.5}


def test_groups_commits_by_different_days():
    commits = [
        make_commit(9, 0, "Backend: Add authentication", day=13),
        make_commit(9, 30, "Backend: Fix validation", day=13),
        make_commit(10, 0, "Frontend: Add dashboard", day=14),
        make_commit(10, 30, "Frontend: Fix dashboard", day=14),
    ]

    result = analyze_commits(
        commits=commits,
        session_gap_hours=2,
        buffer_mins=0,
        hourly_rate=50.0,
        currency="USD",
    )

    assert len(result.days) == 2
    assert result.days[0].day == datetime(2026, 11, 13).date()
    assert result.days[1].day == datetime(2026, 11, 14).date()

    assert len(result.days[0].sessions) == 1
    assert len(result.days[1].sessions) == 1

    assert result.total_hours == 1.0
    assert result.task_hours == {
        "Backend": 0.5,
        "Frontend": 0.5,
    }


def test_calculates_total_hours_and_amount():
    commits = [
        make_commit(9, 0),
        make_commit(9, 30),
        make_commit(13, 0),
        make_commit(13, 30),
    ]

    result = analyze_commits(
        commits=commits,
        session_gap_hours=2,
        buffer_mins=0,
        hourly_rate=100.0,
        currency="USD",
    )

    assert result.total_hours == 1.0
    assert result.total_amount == 100.0
    assert result.hourly_rate == 100.0
    assert result.currency == "USD"


def test_aggregates_hours_for_same_task_across_sessions():
    commits = [
        make_commit(9, 0, "Backend: Add authentication"),
        make_commit(9, 30, "Fix authentication"),
        make_commit(13, 0, "Backend: Add authorization"),
        make_commit(13, 30, "Fix authorization"),
    ]

    result = analyze_commits(
        commits=commits,
        session_gap_hours=2,
        buffer_mins=0,
        hourly_rate=50.0,
        currency="USD",
    )

    assert len(result.days[0].sessions) == 2
    assert result.task_hours == {"Backend": 1.0}
    assert result.total_hours == 1.0
    assert result.total_amount == 50.0
