"""Real HTTP transport for live adapters (stdlib only — no extra deps). The operator wires
this into TradeZeroClient(dry_run=False, transport=HttpTransport(...)) for live use. It only
ever performs IO when explicitly constructed and called by an ARMED live client; in dry-run it
is never touched. Verify the broker's exact base URL/auth in onboarding before live use."""
from __future__ import annotations
import json
import urllib.request
from typing import Any


class HttpTransport:
    def __init__(self, *, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def request(
        self, method: str, url: str, headers: dict[str, str], payload: dict[str, Any] | None
    ) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            url, data=data, method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json", **headers},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 (operator-controlled URL)
            body = resp.read().decode("utf-8")
        return json.loads(body) if body else {}
