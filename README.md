# Git-Chronos

**Git-Chronos** is a standalone command-line utility (CLI) written in Python that automatically tracks working time and calculates earnings based on the commit history of local Git repositories.

The tool is designed for freelancers and contract developers. It runs **100% locally**, guarantees full data privacy, and requires no internet connection or third-party AI services.

---

## Features

- **Automatic time tracking** — derives billable hours from your Git commit history; no manual timers.
- **Earnings calculation** — multiplies tracked hours by your hourly rate and produces a total amount due.
- **Session-aware algorithm** — groups commits into work sessions with configurable gap thresholds and start buffers.
- **Task parsing** — attributes session time to tasks when commit messages follow a pattern like `TASK-123:` or `feature:`.
- **Beautiful terminal reports** — a colored TUI dashboard built with [Rich](https://github.com/Textualize/rich).
- **Corporate-grade Excel invoices** — styled `.xlsx` reports generated with `openpyxl`, including native Excel `SUM` formulas.
- **Private by design** — everything runs locally; no data ever leaves your machine.

---

## Project Structure

```text
git-chronos/
│
├── git_chronos/               # Main source package
│   ├── __init__.py
│   ├── cli.py                 # Command-line interface (Typer)
│   ├── config.py              # config.toml initialization and reading
│   ├── git_parser.py          # Git history module (GitPython)
│   ├── analyzer.py            # Time-calculation engine
│   └── exporters/             # Report exporters
│       ├── __init__.py
│       ├── excel.py           # Designer Excel reports (openpyxl)
│       └── terminal.py        # Colored TUI dashboard (Rich)
│
├── pyproject.toml             # Package dependencies and metadata
├── README.md                  # Repository documentation
└── LICENSE                    # MIT License
```

---

## Installation

Python **3.10+** is required.

```bash
pip install git-chronos
```

Or straight from GitHub:

```bash
pip install git+https://github.com/KokosP/git-chronos
```

Or install from source:

```bash
git clone https://github.com/KokosP/git-chronos
cd git-chronos
pip install .
```

---

## Configuration

On first run, or via the `git-chronos init` command, a `.git-chronos.toml` file is created in the user's home directory.

### Config file structure

```toml
[developer]
name = "Ivan Ivanov"
email = "ivan@developer.dev"       # Filter: only count commits by this author

[finance]
currency = "USD"                   # ISO code: USD, EUR, GBP, RUB, ...
hourly_rate = 25.0                 # Hourly rate (price per 1 hour)

[algorithm]
session_gap_hours = 2.0            # Max. break between commits (in hours)
first_commit_buffer_mins = 30      # "Warm-up" time before the first commit of the day

[reporting]
company_name = "Freelance Inc."
client_name = "Best Customer LLC"
```

---

## CLI Commands

The interface is built on [Typer](https://typer.tiangolo.com/).

| Command | Description |
|---|---|
| `git-chronos init` | Creates the default `.git-chronos.toml` config file |
| `git-chronos status` | Validates the config and prints the current rate |
| `git-chronos analyze [PATH]` | Analyzes the repository at the given path (default: `.`) |

### `analyze` options

- `--period` — reporting period: `week`, `month`, or `custom`
- `--export` — output format: `terminal`, `excel`, or `both`
- `--since` / `--until` — date bounds `YYYY-MM-DD` (required for `--period custom`)
- `--currency` — override the currency for this run (e.g. `USD`, `EUR`, `GBP`)
- `--rate` — override the hourly rate for this run
- `--all` — count commits across all branches and tags, not only the current branch (HEAD)

### Examples

```bash
git-chronos init
git-chronos status
git-chronos analyze .
git-chronos analyze ~/projects/client-app --period month --export both
git-chronos analyze . --currency EUR --rate 40
```

---

## Time-Calculation Algorithm

Commits are extracted from the local `.git` folder via **GitPython** and filtered by `developer.email`.

1. **Grouping** — all commits are sorted chronologically and grouped by day.
2. **Session detection** — if the gap between commit A and commit B is less than `session_gap_hours` (e.g., 2 hours), the interval is treated as continuous work, and `Time(B) - Time(A)` is added to the day's timer.
3. **Breaks** — if the gap exceeds `session_gap_hours`, the current session is closed. The idle interval is treated as rest and is not billable.
4. **Start buffer** — `first_commit_buffer_mins` (e.g., 30 minutes) is added before the first commit of each new session (or the first commit of the day), since code is written before it is committed.
5. **Task parsing** — if a commit message starts with a task pattern (e.g., `TASK-123:` or `feature:`), the session's time is attributed to that task.

---

## Output Design

### Terminal dashboard (`exporters/terminal.py`)

Using **Rich**, the utility renders a formatted report card:

- **Header** — a gradient-framed panel with the utility name and metadata (Developer / Client).
- **Finance block** — a brightly highlighted block (e.g., green for income):
  `Total due: 80.5 h × $25.00 = $2,012.50`
- **Activity charts** — pseudo-graphic bars via `Rich.progress` or `█` characters visualizing load by day or week.

### Excel invoice (`exporters/excel.py`)

The `.xlsx` file is generated via **openpyxl** and follows modern corporate design rules:

- **Color palette** — no default styles. Slate Gray (`#34495E`) table headers with white text; alternating data rows with a light gray tint for readability.
- **Formatting** — date columns use `YYYY-MM-DD`, hour columns use `0.0`, money columns use a strict financial format (e.g., `$#,##0.00`).
- **Formulas** — totals in money and hours are computed with native Excel formulas (`=SUM(...)`), not hardcoded text.

---

## Tech Stack

| Library | Purpose |
|---|---|
| `typer` | Command-line interface (CLI) |
| `gitpython` | Low-level reading of local Git repository history |
| `toml` | Parsing and validating the config file |
| `rich` | Terminal formatting: tables, colors, charts |
| `openpyxl` | Generating and styling Excel reports |

**Constraints:** Python 3.10+. No external APIs or AI models are used.

---

## License

This project is licensed under the [MIT License](LICENSE).

Copyright (c) sbgid.com
