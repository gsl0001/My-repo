"""Global kill switch (design sections 5 and 9): one control that flattens
everything and blocks new orders. Latches until explicitly reset by a human."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class KillSwitch:
    def __init__(self):
        self._engaged = threading.Event()
        self.reason: str | None = None
        self.engaged_at: datetime | None = None

    @property
    def engaged(self) -> bool:
        return self._engaged.is_set()

    def engage(self, reason: str) -> None:
        if self.engaged:
            return
        self.reason = reason
        self.engaged_at = datetime.now(timezone.utc)
        self._engaged.set()
        logger.critical("KILL SWITCH ENGAGED: %s", reason)

    def reset(self) -> None:
        """Manual, deliberate reset only — never called from automated paths."""
        logger.warning("Kill switch reset (was: %s)", self.reason)
        self._engaged.clear()
        self.reason = None
        self.engaged_at = None

    def assert_trading_allowed(self) -> None:
        if self.engaged:
            raise TradingHalted(f"kill switch engaged: {self.reason}")


class TradingHalted(RuntimeError):
    pass
