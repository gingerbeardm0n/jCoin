import datetime as dt

import pytest

from jcoin.research import splits

UTC = dt.timezone.utc


def test_slices_cover_dev_period_without_gaps():
    s = splits.DEV_SLICES
    assert s[0][1] == splits.DEV_START and s[-1][2] == splits.SEALED_START
    for (_, _, end), (_, start, _) in zip(s, s[1:]):
        assert end == start


def test_guard_blocks_sealed_window():
    with pytest.raises(splits.SealedWindowError):
        splits.check_window(splits.DEV_START, dt.datetime(2026, 7, 1, tzinfo=UTC))
    splits.check_window(*splits.dev_window())  # dev window is fine
    splits.check_window(splits.SEALED_START, dt.datetime(2026, 10, 1, tzinfo=UTC),
                        allow_sealed=True)  # explicit opt-in is allowed
