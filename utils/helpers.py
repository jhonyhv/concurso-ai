from __future__ import annotations

from datetime import date, datetime

MONTHS_PT = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def format_date_pt(value: date | datetime | str) -> str:
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            try:
                parsed = datetime.strptime(value[:10], "%Y-%m-%d")
            except ValueError:
                return value
    elif isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.combine(value, datetime.min.time())
    return f"{parsed.day:02d} de {MONTHS_PT[parsed.month - 1]} de {parsed.year}"


def format_duration(minutes: int) -> str:
    minutes = max(0, int(minutes))
    hours, remaining = divmod(minutes, 60)
    if hours and remaining:
        return f"{hours}h {remaining:02d}m"
    if hours:
        return f"{hours}h"
    return f"{remaining}m"


def safe_percent(part: float, whole: float) -> float:
    return 0.0 if not whole else max(0.0, min(100.0, 100.0 * part / whole))
