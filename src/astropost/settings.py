"""User settings for the sender and an always-CC address.

Read from the environment or ~/.config/astropost/.env:
  ASTROPOST_FROM       default From header, e.g. "Ada Lovelace <ada@example.org>"
  ASTROPOST_ALWAYS_CC  comma-separated addresses added to Cc on every message
"""

import os
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path.home() / ".config" / "astropost" / ".env"


def _load() -> None:
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH, override=False)


def default_from() -> str | None:
    _load()
    value = os.environ.get("ASTROPOST_FROM", "").strip()
    return value or None


def always_cc() -> list[str]:
    _load()
    raw = os.environ.get("ASTROPOST_ALWAYS_CC", "")
    return [a.strip() for a in raw.split(",") if a.strip()]


def with_always_cc(cc: list[str] | None) -> list[str]:
    final = list(cc) if cc else []
    for addr in always_cc():
        if addr not in final:
            final.append(addr)
    return final
