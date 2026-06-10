"""Parser for IBKR short-availability ("shortable stock") files.

IBKR publishes pipe-delimited availability files (usa.txt) daily on its FTP
server (ftp3.interactivebrokers.com, user 'shortstock'). Format:

    #BOF|<timestamp>|...
    #SYM|CUR|NAME|CON|ISIN|REBATERATE|FEERATE|AVAILABLE
    AAPL|USD|APPLE INC|265598|US0378331005|4.83|0.25|>10000000
    ...
    #EOF

AVAILABLE may be an integer or ">N" when inventory exceeds the reporting cap.
This data is a *pre-filter* only; TradeZero confirms the real locate.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

from .models import BorrowInfo

# Column order in the IBKR file header (#SYM|CUR|...)
_COL_SYMBOL = 0
_COL_CURRENCY = 1
_COL_REBATE = 5
_COL_FEE = 6
_COL_AVAILABLE = 7


def _parse_available(raw: str) -> int:
    raw = raw.strip()
    if not raw:
        return 0
    if raw.startswith(">"):
        raw = raw[1:]
    try:
        return int(float(raw))
    except ValueError:
        return 0


def _parse_rate(raw: str) -> float | None:
    raw = raw.strip()
    if not raw or raw.upper() == "NA":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def parse_borrow_lines(
    lines: Iterable[str], as_of: datetime | None = None
) -> dict[str, BorrowInfo]:
    """Parse IBKR availability lines into {symbol: BorrowInfo}."""
    out: dict[str, BorrowInfo] = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) <= _COL_AVAILABLE:
            continue
        symbol = parts[_COL_SYMBOL].strip().upper()
        if not symbol or parts[_COL_CURRENCY].strip().upper() != "USD":
            continue
        fee = _parse_rate(parts[_COL_FEE])
        out[symbol] = BorrowInfo(
            symbol=symbol,
            shares_available=_parse_available(parts[_COL_AVAILABLE]),
            fee_rate_pct=fee if fee is not None else 0.0,
            rebate_rate_pct=_parse_rate(parts[_COL_REBATE]),
            as_of=as_of,
        )
    return out


def parse_borrow_file(path: str | Path, as_of: datetime | None = None) -> dict[str, BorrowInfo]:
    text = Path(path).read_text(errors="replace")
    return parse_borrow_lines(text.splitlines(), as_of=as_of)
