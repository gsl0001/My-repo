"""HTTP transport seam for live adapters. The operator supplies a real implementation
(e.g. a requests/httpx wrapper) for live use; nothing here ever touches the network."""
from __future__ import annotations
from typing import Any, Protocol


class Transport(Protocol):
    def request(
        self, method: str, url: str, headers: dict[str, str], payload: dict[str, Any] | None
    ) -> dict[str, Any]: ...


class RecordingTransport:
    """Dev/test transport: records calls and returns a canned response. Never networks."""
    def __init__(self, response: dict[str, Any] | None = None) -> None:
        self.calls: list[tuple[str, str]] = []
        self._response = response or {}

    def request(
        self, method: str, url: str, headers: dict[str, str], payload: dict[str, Any] | None
    ) -> dict[str, Any]:
        self.calls.append((method, url))
        return dict(self._response)
