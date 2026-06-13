"""Append-only audit log (Blueprint §11 recordkeeping). Every signal, locate, and order
is recorded as a JSONL line stamped with time + the live config version, for compliance
and post-trade review. Append-only by construction (open mode 'a')."""
from __future__ import annotations
import json
import os
import time
from typing import Any


class AuditLog:
    def __init__(self, path: str, config_version: str = "dev", clock=time.time) -> None:
        self.path = path
        self.config_version = config_version
        self._clock = clock

    def record(self, kind: str, **fields: Any) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "ts": self._clock(),
            "kind": kind,
            "config_version": self.config_version,
            **fields,
        }
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
        return entry

    def read(self) -> list[dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]
