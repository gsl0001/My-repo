"""Market data provider interface and Polygon.io implementation.

The rest of the system depends only on `MarketDataProvider`, so the Polygon
client can be swapped for a replay/backtest provider without touching signal,
risk, or execution code.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import date, datetime, timezone

import requests

from .models import Bar, SymbolSnapshot

POLYGON_BASE_URL = "https://api.polygon.io"


class MarketDataProvider(ABC):
    @abstractmethod
    def snapshots(self, symbols: list[str] | None = None) -> list[SymbolSnapshot]:
        """Current snapshots for the given symbols (or full universe if None)."""

    @abstractmethod
    def daily_bars(self, symbol: str, start: date, end: date) -> list[Bar]:
        """Historical daily bars, inclusive of both endpoints."""

    @abstractmethod
    def minute_bars(self, symbol: str, day: date) -> list[Bar]:
        """Intraday minute bars for one session."""


class PolygonMarketData(MarketDataProvider):
    """Thin Polygon.io REST client.

    Requires POLYGON_API_KEY (or an explicit api_key). Full-universe real-time
    snapshots need a paid plan tier — confirm the tier before relying on this
    for live scanning (design doc section 6 open question).
    """

    def __init__(self, api_key: str | None = None, session: requests.Session | None = None):
        self.api_key = api_key or os.environ.get("POLYGON_API_KEY", "")
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY is not set")
        self.http = session or requests.Session()

    def _get(self, path: str, **params) -> dict:
        params["apiKey"] = self.api_key
        resp = self.http.get(f"{POLYGON_BASE_URL}{path}", params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def snapshots(self, symbols: list[str] | None = None) -> list[SymbolSnapshot]:
        params = {}
        if symbols:
            params["tickers"] = ",".join(symbols)
        data = self._get("/v2/snapshot/locale/us/markets/stocks/tickers", **params)
        out = []
        for t in data.get("tickers", []):
            day = t.get("day") or {}
            prev = t.get("prevDay") or {}
            price = (t.get("lastTrade") or {}).get("p") or day.get("c") or 0.0
            out.append(
                SymbolSnapshot(
                    symbol=t.get("ticker", ""),
                    price=float(price),
                    prev_close=float(prev.get("c") or 0.0),
                    # reference data (market cap, float, exchange, ADV) is
                    # enriched separately via enrich_reference()
                    market_cap=0.0,
                    exchange="",
                    adv_shares_20d=0.0,
                    adv_dollar_20d=0.0,
                    day_volume=int(day.get("v") or 0),
                    vwap=day.get("vw"),
                    timestamp=datetime.now(timezone.utc),
                )
            )
        return out

    def enrich_reference(self, snapshot: SymbolSnapshot) -> SymbolSnapshot:
        """Fill market cap / float / exchange from Polygon ticker details, and
        20-day ADV from daily bars."""
        details = self._get(f"/v3/reference/tickers/{snapshot.symbol}").get("results", {})
        snapshot.market_cap = float(details.get("market_cap") or 0.0)
        snapshot.exchange = _normalize_exchange(details.get("primary_exchange", ""))
        share_class = details.get("weighted_shares_outstanding")
        if share_class:
            snapshot.float_shares = float(share_class)

        today = datetime.now(timezone.utc).date()
        bars = self.daily_bars(snapshot.symbol, _n_trading_days_back(today, 30), today)
        recent = bars[-20:]
        if recent:
            snapshot.adv_shares_20d = sum(b.volume for b in recent) / len(recent)
            snapshot.adv_dollar_20d = sum(b.volume * b.close for b in recent) / len(recent)
        return snapshot

    def daily_bars(self, symbol: str, start: date, end: date) -> list[Bar]:
        data = self._get(
            f"/v2/aggs/ticker/{symbol}/range/1/day/{start.isoformat()}/{end.isoformat()}",
            adjusted="true",
            sort="asc",
            limit=50000,
        )
        return [_agg_to_bar(symbol, r) for r in data.get("results") or []]

    def minute_bars(self, symbol: str, day: date) -> list[Bar]:
        data = self._get(
            f"/v2/aggs/ticker/{symbol}/range/1/minute/{day.isoformat()}/{day.isoformat()}",
            adjusted="true",
            sort="asc",
            limit=50000,
        )
        return [_agg_to_bar(symbol, r) for r in data.get("results") or []]


def _agg_to_bar(symbol: str, r: dict) -> Bar:
    return Bar(
        symbol=symbol,
        timestamp=datetime.fromtimestamp(r["t"] / 1000.0, tz=timezone.utc),
        open=float(r["o"]),
        high=float(r["h"]),
        low=float(r["l"]),
        close=float(r["c"]),
        volume=int(r["v"]),
    )


def _normalize_exchange(mic: str) -> str:
    return {
        "XNAS": "NASDAQ",
        "XNYS": "NYSE",
        "XASE": "AMEX",
        "ARCX": "NYSEARCA",
    }.get(mic, mic)


def _n_trading_days_back(today: date, n: int) -> date:
    # calendar approximation is fine: we fetch extra and slice the last 20 bars
    from datetime import timedelta

    return today - timedelta(days=int(n * 1.5) + 5)
