from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.domain.clock import FixedClock, SystemClock


def test_clock_system_clock_is_utc() -> None:
    assert SystemClock().now().utcoffset() == timedelta(0)


def test_clock_fixed_clock_advances() -> None:
    clock = FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
    clock.advance(timedelta(days=90))
    assert clock.now() == datetime(2026, 4, 1, tzinfo=UTC)


def test_clock_rejects_non_utc() -> None:
    with pytest.raises(ValueError):
        FixedClock(datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=2))))
    with pytest.raises(ValueError):
        FixedClock(datetime(2026, 1, 1))
