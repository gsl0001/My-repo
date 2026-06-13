from lowcap_short_system.microstructure.events import BookState, PriceLevel
from lowcap_short_system.microstructure.sim.fills import fill_against_book
from lowcap_short_system.microstructure.sim import scenarios
from lowcap_short_system.microstructure.sim.harness import run_scenario

def test_fill_against_book_caps_at_displayed_size():
    book = BookState("X", 1.0, (PriceLevel(4.10, 300), PriceLevel(4.09, 300)), ())
    # selling short into the bid: want 1000, only 600 displayed across two levels
    filled, avg = fill_against_book(book, side="sell", qty=1000)
    assert filled == 600
    assert round(avg, 4) == round((300 * 4.10 + 300 * 4.09) / 600, 4)

def test_pump_fade_scenario_emits_enter():
    res = run_scenario(scenarios.pump_fade_absorption())
    assert any(s.kind == "enter" for s in res.signals)

def test_squeeze_scenario_emits_exit():
    res = run_scenario(scenarios.squeeze(), start_in_position=True)
    assert any(s.kind == "exit" for s in res.signals)

def test_fake_wall_scenario_is_vetoed():
    res = run_scenario(scenarios.fake_wall())
    assert all(s.kind != "enter" for s in res.signals)
