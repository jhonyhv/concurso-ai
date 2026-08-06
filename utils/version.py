from __future__ import annotations

from pathlib import Path

VERSION_FILE = Path(__file__).resolve().parents[1] / "VERSION"


def get_version(default: str = "0.9.0") -> str:
    if not VERSION_FILE.exists():
        return default
    value = VERSION_FILE.read_text(encoding="utf-8").strip()
    return value or default


def get_version_badge() -> str:
    return f"v{get_version()}"


def get_version_label() -> str:
    return get_version().replace("-", " ")
