from lowcap_short_system.data.ibkr_borrow import parse_borrow_lines


SAMPLE = """\
#BOF|2026.06.10|02:15:03
#SYM|CUR|NAME|CON|ISIN|REBATERATE|FEERATE|AVAILABLE
AAPL|USD|APPLE INC|265598|US0378331005|4.83|0.25|>10000000
PUMP|USD|PUMPCO HOLDINGS|111111|US1111111111|-35.0|42.5|350000
NOBRW|USD|NOBORROW CORP|222222|US2222222222|NA|NA|0
EURX|EUR|EURO LISTING|333333|DE3333333333|1.0|1.0|5000
BAD|USD|TOO|FEW
#EOF
"""


def test_parses_symbols_fees_and_availability():
    out = parse_borrow_lines(SAMPLE.splitlines())
    assert out["PUMP"].shares_available == 350_000
    assert out["PUMP"].fee_rate_pct == 42.5
    assert out["PUMP"].rebate_rate_pct == -35.0
    assert out["PUMP"].borrowable


def test_gt_capped_availability_parsed():
    out = parse_borrow_lines(SAMPLE.splitlines())
    assert out["AAPL"].shares_available == 10_000_000


def test_zero_availability_not_borrowable():
    out = parse_borrow_lines(SAMPLE.splitlines())
    assert not out["NOBRW"].borrowable


def test_non_usd_and_malformed_rows_skipped():
    out = parse_borrow_lines(SAMPLE.splitlines())
    assert "EURX" not in out
    assert "BAD" not in out
