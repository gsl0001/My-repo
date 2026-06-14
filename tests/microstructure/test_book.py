from lowcap_short_system.microstructure.book import BookMaintainer
from lowcap_short_system.microstructure.events import DepthSnapshot, DepthDelta

def snap():
    return DepthSnapshot(symbol="TICK", ts=1.0,
                         bids=((4.10, 500), (4.09, 300)),
                         asks=((4.12, 400), (4.13, 200)))

def test_snapshot_builds_sorted_book():
    bm = BookMaintainer("TICK")
    bm.apply_snapshot(snap())
    st = bm.state()
    assert st.best_bid.price == 4.10 and st.best_ask.price == 4.12
    assert st.bids[0].size == 500

def test_delta_updates_and_removes_levels():
    bm = BookMaintainer("TICK")
    bm.apply_snapshot(snap())
    bm.apply_delta(DepthDelta("TICK", 2.0, "ask", 4.12, 100))  # shrink best ask
    assert bm.state().best_ask.size == 100
    bm.apply_delta(DepthDelta("TICK", 3.0, "ask", 4.12, 0))    # remove best ask
    assert bm.state().best_ask.price == 4.13

def test_changes_history_records_old_and_new():
    bm = BookMaintainer("TICK")
    bm.apply_snapshot(snap())
    bm.apply_delta(DepthDelta("TICK", 2.0, "ask", 4.12, 900))
    last = bm.changes[-1]
    assert last.side == "ask" and last.price == 4.12
    assert last.old_size == 400 and last.new_size == 900

def test_staleness():
    bm = BookMaintainer("TICK")
    bm.apply_snapshot(snap())            # last update ts = 1.0
    assert bm.is_stale(now=1.5, max_age_s=1.0) is False
    assert bm.is_stale(now=3.0, max_age_s=1.0) is True
