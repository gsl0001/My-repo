from lowcap_short_system.microstructure.config import MicroConfig, load_config

def test_defaults_present():
    c = MicroConfig()
    assert c.enter_imbalance == 0.35
    assert c.min_conviction == 0.6
    assert c.veto_spoof == 0.5

def test_load_from_yaml_overrides(tmp_path):
    p = tmp_path / "m.yaml"
    p.write_text("enter_imbalance: 0.5\nmin_conviction: 0.9\n")
    c = load_config(str(p))
    assert c.enter_imbalance == 0.5
    assert c.min_conviction == 0.9
    assert c.veto_spoof == 0.5  # untouched default

def test_load_missing_file_returns_defaults():
    assert load_config("does-not-exist.yaml") == MicroConfig()
