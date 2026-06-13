"""TradeZero live adapters (Blueprint §7 locates, §8 execution). DRY-RUN by default:
every call is logged to the audit trail and SIMULATED — no network, no orders. The live
path is hard-gated behind `require_armed()`, so it cannot trade by accident. Endpoint paths
follow Blueprint §7.1 and MUST be verified in TradeZero onboarding before live use."""
from __future__ import annotations
from typing import Any

from lowcap_short_system.locate.provider import LocateResult
from lowcap_short_system.execution.paper import PaperPosition
from lowcap_short_system.observability.audit import AuditLog
from lowcap_short_system.live.transport import Transport
from lowcap_short_system.live.safety import require_armed

_BASE = "https://api.tradezero.com"  # placeholder — confirm the real base in onboarding


class TradeZeroClient:
    def __init__(
        self, *, dry_run: bool = True, transport: Transport | None = None, audit: AuditLog | None = None
    ) -> None:
        self.dry_run = dry_run
        self._transport = transport
        self._audit = audit

    def _call(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._audit is not None:
            self._audit.record(
                "DRYRUN_API" if self.dry_run else "LIVE_API", method=method, path=path, payload=payload
            )
        if self.dry_run:
            return {"dryRun": True, "method": method, "path": path, "payload": payload}
        require_armed()  # hard gate: raises unless the operator explicitly armed live trading
        if self._transport is None:
            raise RuntimeError("live mode requires a Transport; none was provided")
        return self._transport.request(method, _BASE + path, {}, payload)


class TradeZeroLocate:
    """Implements the LocateProvider protocol via the §7.1 ETB → quote → accept flow."""
    def __init__(self, client: TradeZeroClient) -> None:
        self._c = client

    def locate(self, symbol: str, requested: int) -> LocateResult:
        self._c._call("GET", f"/locates/is-easy-to-borrow/symbol/{symbol}")
        self._c._call("POST", "/locates/quote", {"symbol": symbol, "shares": requested})
        resp = self._c._call("POST", "/locates/accept", {"symbol": symbol, "shares": requested})
        if self._c.dry_run:
            return LocateResult(symbol, requested, 0.0, True, "dry-run simulated")
        granted = int(resp.get("shares", 0))
        return LocateResult(symbol, granted, float(resp.get("price", 0.0)), ok=granted > 0)


class TradeZeroOrderRouter:
    """Implements the OrderRouter protocol. Builds a marketable-limit short with an attached
    programmatic stop. Dry-run logs the intended order and returns a simulated fill."""
    def __init__(self, client: TradeZeroClient) -> None:
        self._c = client

    def place_short(self, symbol: str, qty: int, limit_price: float, stop_price: float) -> PaperPosition:
        payload = {
            "symbol": symbol,
            "side": "short",
            "type": "limit",
            "qty": qty,
            "limitPrice": limit_price,
            "attachedStop": stop_price,
            # SSR Rule 201: if SSR is active, a short must price above the NBB — enforce pre-send.
        }
        self._c._call("POST", "/orders", payload)  # dry-run: logged & simulated, not transmitted
        return PaperPosition(symbol, qty, limit_price, stop_price)
