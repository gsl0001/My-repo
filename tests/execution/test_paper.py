from lowcap_short_system.execution.paper import PaperBroker


def test_place_short_creates_position():
    b = PaperBroker()
    pos = b.place_short("TICK", 1000, 4.20, 4.55)
    assert pos.qty == 1000 and pos.avg_price == 4.20 and b.positions["TICK"].stop_price == 4.55


def test_add_tops_up_with_weighted_avg():
    b = PaperBroker()
    b.place_short("TICK", 1000, 4.00, 4.40)
    pos = b.place_short("TICK", 1000, 4.20, 4.50)
    assert pos.qty == 2000 and pos.avg_price == 4.10


def test_cover_books_realized_profit_when_price_falls():
    b = PaperBroker()
    b.place_short("TICK", 1000, 4.20, 4.55)
    pnl = b.cover("TICK", 4.00)
    assert round(pnl, 2) == 200.0 and b.realized == pnl and "TICK" not in b.positions


def test_cover_unknown_symbol_is_noop():
    assert PaperBroker().cover("NONE", 1.0) == 0.0


def test_gross_short_uses_marks():
    b = PaperBroker()
    b.place_short("TICK", 1000, 4.20, 4.55)
    assert b.gross_short({"TICK": 4.00}) == 4000.0
