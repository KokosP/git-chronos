# Copyright (c) sbgid.com
"""Loading and creation of the ``.git-chronos.toml`` configuration file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import toml

CONFIG_FILENAME = ".git-chronos.toml"

DEFAULT_CONFIG: dict[str, Any] = {
    "developer": {
        "name": "Your Name",
        "email": "you@example.com",
    },
    "finance": {
        "currency": "USD",
        "hourly_rate": 25.0,
    },
    "algorithm": {
        "session_gap_hours": 2.0,
        "first_commit_buffer_mins": 30,
    },
    "reporting": {
        "company_name": "Freelance Inc.",
        "client_name": "Best Customer LLC",
    },
}

CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "CHF": "CHF ",
    "CAD": "CA$",
    "AUD": "A$",
    "NZD": "NZ$",
    "JPY": "¥",
    "CNY": "¥",
    "KRW": "₩",
    "INR": "₹",
    "BRL": "R$",
    "PLN": "zł",
    "CZK": "Kč",
    "TRY": "₺",
    "AED": "AED ",
    "RUB": "₽",
    "UAH": "₴",
    "KZT": "₸",
    "BYN": "Br",
}

_REQUIRED_KEYS = {
    "developer": ("name", "email"),
    "finance": ("currency", "hourly_rate"),
    "algorithm": ("session_gap_hours", "first_commit_buffer_mins"),
    "reporting": ("company_name", "client_name"),
}


class ConfigError(Exception):
    """Raised when the configuration file is missing or invalid."""


@dataclass(frozen=True)
class Config:
    developer_name: str
    developer_email: str
    currency: str
    hourly_rate: float
    session_gap_hours: float
    first_commit_buffer_mins: int
    company_name: str
    client_name: str
    path: Path

    @property
    def currency_symbol(self) -> str:
        return CURRENCY_SYMBOLS.get(self.currency.upper(), self.currency)


def config_path() -> Path:
    return Path.home() / CONFIG_FILENAME


def init_config(path: Path | None = None, overwrite: bool = False) -> Path:
    path = path or config_path()
    if path.exists() and not overwrite:
        return path
    path.write_text(toml.dumps(DEFAULT_CONFIG), encoding="utf-8")
    return path


def load_config(path: Path | None = None) -> tuple[Config, bool]:
    """Load the configuration, creating the default file if needed.

    Returns a ``(config, created)`` tuple where ``created`` is True when the
    file did not exist and a fresh default one was written.
    """
    path = path or config_path()
    created = not path.exists()
    if created:
        init_config(path)

    try:
        raw = toml.load(path)
    except toml.TomlDecodeError as exc:
        raise ConfigError(f"Cannot parse {path}: {exc}") from exc

    for section, keys in _REQUIRED_KEYS.items():
        if section not in raw:
            raise ConfigError(f"{path}: missing [{section}] section")
        for key in keys:
            if key not in raw[section]:
                raise ConfigError(f"{path}: missing {section}.{key}")

    try:
        cfg = Config(
            developer_name=str(raw["developer"]["name"]),
            developer_email=str(raw["developer"]["email"]),
            currency=str(raw["finance"]["currency"]).upper(),
            hourly_rate=float(raw["finance"]["hourly_rate"]),
            session_gap_hours=float(raw["algorithm"]["session_gap_hours"]),
            first_commit_buffer_mins=int(raw["algorithm"]["first_commit_buffer_mins"]),
            company_name=str(raw["reporting"]["company_name"]),
            client_name=str(raw["reporting"]["client_name"]),
            path=path,
        )
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{path}: invalid value ({exc})") from exc

    if cfg.hourly_rate < 0:
        raise ConfigError(f"{path}: finance.hourly_rate must be >= 0")
    if cfg.session_gap_hours <= 0:
        raise ConfigError(f"{path}: algorithm.session_gap_hours must be > 0")
    if cfg.first_commit_buffer_mins < 0:
        raise ConfigError(f"{path}: algorithm.first_commit_buffer_mins must be >= 0")

    return cfg, created
