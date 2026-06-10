from pathlib import Path

import pytest

from lowcap_short_system.config import SystemConfig

DEFAULT_YAML = Path(__file__).resolve().parents[1] / "lowcap_short_system/config/default.yaml"


def test_default_yaml_loads_and_matches_design_values():
    cfg = SystemConfig.from_yaml(DEFAULT_YAML)
    assert cfg.universe.min_market_cap == 10_000_000
    assert cfg.universe.max_market_cap == 500_000_000
    assert cfg.universe.price_floor == 1.00
    assert cfg.universe.price_ceiling == 25.00
    assert cfg.universe.allowed_exchanges == ("NASDAQ", "NYSE", "AMEX")
    assert cfg.squeeze.abort_borrow_fee_pct == 300
    assert cfg.risk.daily_drawdown_limit_pct == 4
    assert cfg.locate.max_locate_cost_fraction_of_edge == 0.20
    assert cfg.session.flatten_by == "15:50"


def test_unknown_config_key_rejected():
    with pytest.raises(ValueError, match="Unknown keys"):
        SystemConfig.from_dict({"universe": {"not_a_knob": 1}})


def test_defaults_used_for_missing_sections():
    cfg = SystemConfig.from_dict({"risk": {"max_concurrent_positions": 2}})
    assert cfg.risk.max_concurrent_positions == 2
    assert cfg.universe.price_floor == 1.00
