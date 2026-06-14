"""Preflight readiness check. Run before any session to confirm the system is in a safe,
correct state. Paper mode needs only a valid config; live mode additionally needs all
secrets present AND the explicit arm flag.

CLI:  python -m lowcap_short_system.live.preflight [paper|live]
Exit code 0 = ready, 1 = not ready."""
from __future__ import annotations
from dataclasses import dataclass

from lowcap_short_system.security.secrets import missing_secrets
from lowcap_short_system.microstructure.config import load_config, MicroConfig
from lowcap_short_system.live.safety import is_armed


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class PreflightResult:
    mode: str
    ready: bool
    checks: tuple[Check, ...]


def preflight(mode: str = "paper", config_path: str = "config/microstructure.yaml") -> PreflightResult:
    cfg = load_config(config_path)
    miss = missing_secrets()
    armed = is_armed()
    checks = (
        Check("config", isinstance(cfg, MicroConfig), f"loaded ({config_path})"),
        Check("secrets", not miss, "all present" if not miss else "missing: " + ", ".join(miss)),
        Check("live_armed", armed, "ARMED" if armed else "not armed (dry-run safe)"),
    )
    by = {c.name: c.ok for c in checks}
    ready = by["config"] if mode == "paper" else all(by.values())
    return PreflightResult(mode, ready, checks)


def main() -> int:
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "paper"
    res = preflight(mode)
    print(f"=== preflight ({res.mode}) ===")
    for c in res.checks:
        print(f"  [{'OK' if c.ok else 'XX'}] {c.name}: {c.detail}")
    print(f"READY: {res.ready}")
    return 0 if res.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
