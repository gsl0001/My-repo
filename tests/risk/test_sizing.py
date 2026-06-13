from lowcap_short_system.risk.sizing import SizeInputs, size_short


def base(**kw) -> SizeInputs:
    d = dict(account_equity=100_000, risk_per_trade_pct=0.5, entry_price=5.0, stop_price=5.5,
             adv_shares=1_000_000, max_adv_pct=2.0, hard_dollar_cap=20_000, located_shares=100_000)
    d.update(kw)
    return SizeInputs(**d)


def test_returns_minimum_of_caps_floored_to_lot():
    # vol: 500$/0.5 = 1000; adv: 20000; hard$: 4000; located: 100000 -> min 1000
    assert size_short(base()) == 1000


def test_located_shares_caps_size():
    assert size_short(base(located_shares=300)) == 300


def test_hard_dollar_cap_binds():
    # hard$ 2000 / entry 5 = 400 -> 400 (below vol 1000)
    assert size_short(base(hard_dollar_cap=2000)) == 400


def test_zero_when_nothing_located():
    assert size_short(base(located_shares=0)) == 0


def test_rounds_down_to_round_lot():
    # adv cap = 1_000_000 * 0.0157% -> 157 -> floored to 100
    assert size_short(base(max_adv_pct=0.0157)) == 100
