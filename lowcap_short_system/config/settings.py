"""Tunable configuration.

Every numeric threshold from design sections 8-9 is a config knob here, not a
hardcoded constant. Defaults mirror the design doc's starting values, which are
hypotheses to be tuned against a backtest — not validated live parameters.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

import yaml


@dataclass
class UniverseConfig:
    """Static universe filter (design section 8)."""

    min_market_cap: float = 10_000_000.0
    max_market_cap: float = 500_000_000.0
    price_floor: float = 1.00
    price_ceiling: float = 25.00
    min_adv_dollar_20d: float = 3_000_000.0
    min_adv_shares_20d: float = 500_000.0
    low_float_flag_shares: float = 20_000_000.0  # flag (size down), not exclude
    soft_max_borrow_fee_pct: float = 100.0
    hard_max_borrow_fee_pct: float = 300.0
    allowed_exchanges: tuple[str, ...] = ("NASDAQ", "NYSE", "AMEX")
    # intraday trigger gates on top of the static universe
    min_trigger_rvol: float = 3.0
    min_trigger_move_pct: float = 10.0  # gap or intraday move needed to fade


@dataclass
class SqueezeGuardConfig:
    """Squeeze-guard thresholds (design section 9)."""

    # entry: caution (reduce size)
    caution_gain_pct: float = 50.0
    caution_rvol: float = 5.0
    caution_borrow_fee_pct: float = 100.0
    caution_float_shares: float = 20_000_000.0
    # entry: abort / no-entry
    abort_gain_pct: float = 100.0  # only when still accelerating
    abort_rvol: float = 10.0
    abort_borrow_fee_pct: float = 300.0
    abort_float_shares: float = 5_000_000.0
    # in-position: force exit
    force_exit_adverse_pct: float = 15.0
    force_exit_rvol: float = 10.0
    # sizing haircut applied on a caution verdict
    caution_size_factor: float = 0.5


@dataclass
class RiskConfig:
    """Sizing and account-level circuit breakers (design sections 4.3, 9)."""

    max_pct_of_adv: float = 1.0  # position cap as % of 20-day ADV shares
    max_position_dollars: float = 25_000.0
    target_risk_dollars: float = 1_000.0  # vol-based sizing budget per trade
    stop_distance_pct: float = 15.0  # initial stop above entry
    target_reversion_pct: float = 15.0  # profit target below entry
    per_position_max_loss_pct: float = 20.0
    daily_drawdown_limit_pct: float = 4.0  # flatten + halt for the day
    max_concurrent_positions: int = 5
    max_gross_short_exposure: float = 100_000.0


@dataclass
class LocateConfig:
    """Locate orchestration (design section 10)."""

    max_locate_cost_fraction_of_edge: float = 0.20  # step 3 cost gate
    locate_retry_budget: int = 2
    locate_timeout_seconds: float = 10.0
    expected_win_prob: float = 0.55  # used in expected-edge estimate
    expected_fade_pct: float = 10.0  # expected reversion captured, percent


@dataclass
class SessionConfig:
    """Trading session boundaries (US/Eastern wall-clock, HH:MM)."""

    market_open: str = "09:30"
    market_close: str = "16:00"
    flatten_by: str = "15:50"  # intraday mandate: flat before the close


@dataclass
class SystemConfig:
    universe: UniverseConfig = field(default_factory=UniverseConfig)
    squeeze: SqueezeGuardConfig = field(default_factory=SqueezeGuardConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    locate: LocateConfig = field(default_factory=LocateConfig)
    session: SessionConfig = field(default_factory=SessionConfig)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SystemConfig":
        cfg = cls()
        for f in fields(cls):
            section = raw.get(f.name)
            if section is None:
                continue
            sub = getattr(cfg, f.name)
            valid = {sf.name for sf in fields(sub)}
            unknown = set(section) - valid
            if unknown:
                raise ValueError(f"Unknown keys in config section '{f.name}': {sorted(unknown)}")
            for key, value in section.items():
                if isinstance(value, list):
                    value = tuple(value)
                setattr(sub, key, value)
        return cfg

    @classmethod
    def from_yaml(cls, path: str | Path) -> "SystemConfig":
        raw = yaml.safe_load(Path(path).read_text()) or {}
        return cls.from_dict(raw)
