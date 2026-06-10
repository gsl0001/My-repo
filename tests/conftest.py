from datetime import datetime, timezone

import pytest

from lowcap_short_system.config import SystemConfig
from lowcap_short_system.data.models import BorrowInfo, SymbolSnapshot


@pytest.fixture
def cfg() -> SystemConfig:
    return SystemConfig()


@pytest.fixture
def good_snapshot() -> SymbolSnapshot:
    """A pumping low-cap that passes the universe filter and trigger gate."""
    return SymbolSnapshot(
        symbol="PUMP",
        price=5.20,
        prev_close=4.00,  # +30% intraday
        market_cap=80_000_000,
        exchange="NASDAQ",
        adv_shares_20d=2_000_000,
        adv_dollar_20d=8_000_000,
        float_shares=30_000_000,
        day_volume=8_000_000,  # 4x RVOL
        timestamp=datetime(2026, 6, 10, 14, 30, tzinfo=timezone.utc),
    )


@pytest.fixture
def good_borrow() -> BorrowInfo:
    return BorrowInfo(symbol="PUMP", shares_available=500_000, fee_rate_pct=40.0)
