"""One shared definition of research time windows.

Before 2026-10-14 the train/valid/test boundaries were copy-pasted into ~8 research
scripts (optimize.py, validate_best.py, validate_coins*.py, ...). New research uses
this module instead. See VALIDATION_RULES.md §1 and §5.

SEALED window: 2026-06-01 onward. No selection may use it. The single allowed
confirmation look (VALIDATION_RULES.md §5) must pass allow_sealed=True AND be logged
in the Looks Log.
"""

from __future__ import annotations

import datetime as dt

UTC = dt.timezone.utc

DEV_START = dt.datetime(2021, 1, 1, tzinfo=UTC)
SEALED_START = dt.datetime(2026, 6, 1, tzinfo=UTC)

# Six dev slices for consistency checks (half-open [start, end)).
DEV_SLICES: list[tuple[str, dt.datetime, dt.datetime]] = [
    ("2021", dt.datetime(2021, 1, 1, tzinfo=UTC), dt.datetime(2022, 1, 1, tzinfo=UTC)),
    ("2022", dt.datetime(2022, 1, 1, tzinfo=UTC), dt.datetime(2023, 1, 1, tzinfo=UTC)),
    ("2023", dt.datetime(2023, 1, 1, tzinfo=UTC), dt.datetime(2024, 1, 1, tzinfo=UTC)),
    ("2024", dt.datetime(2024, 1, 1, tzinfo=UTC), dt.datetime(2025, 1, 1, tzinfo=UTC)),
    ("2025", dt.datetime(2025, 1, 1, tzinfo=UTC), dt.datetime(2026, 1, 1, tzinfo=UTC)),
    ("2026H1", dt.datetime(2026, 1, 1, tzinfo=UTC), SEALED_START),
]


class SealedWindowError(RuntimeError):
    """Raised when research code reaches into the sealed window without opting in."""


def check_window(start: dt.datetime, end: dt.datetime, allow_sealed: bool = False) -> None:
    """Raise unless [start, end) stays before SEALED_START (or the caller opted in)."""
    if end > SEALED_START and not allow_sealed:
        raise SealedWindowError(
            f"window ends {end.isoformat()} which is past SEALED_START "
            f"{SEALED_START.date()}; pass allow_sealed=True only for the single logged "
            f"confirmation look (VALIDATION_RULES.md §5)")


def dev_window() -> tuple[dt.datetime, dt.datetime]:
    """The full development period: everything selection is allowed to see."""
    return DEV_START, SEALED_START


def in_window(ts: dt.datetime, start: dt.datetime, end: dt.datetime) -> bool:
    return start <= ts < end
