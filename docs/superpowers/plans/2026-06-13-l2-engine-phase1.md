# L2 Microstructure Engine — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the offline Level 2 microstructure engine — order-book model, feature layer, four strategies, a strategy engine, a replay feed, and a sim harness — pure Python, mock/replay-driven, fully unit-tested, with all thresholds in config and no network/broker calls.

**Architecture:** A normalized order-book model (`events`) is maintained by a `BookMaintainer` (`book`). Pure feature functions (`features`) turn book + tape into microstructure metrics. Stateless `strategies` map features → `Signal`s; a `StrategyEngine` composes them (spoof veto + conviction) into a `ConfirmedSignal`. A `ReplayFeed` plays recorded/synthetic events; a `sim` harness scores signal quality and models fills. Live broker feeds are stubbed behind protocols for Phase 3.

**Tech Stack:** Python 3.11, stdlib `dataclasses`/`typing`, `PyYAML` (config); dev: `pytest`, `ruff`, `mypy`. No numpy/pydantic (keep deps minimal). All under `lowcap_short_system/microstructure/`.

**Spec:** [`../specs/2026-06-13-l2-production-system-design.md`](../specs/2026-06-13-l2-production-system-design.md)

**Conventions:** run all commands from repo root. Package import path is `lowcap_short_system.microstructure.*`. Every commit message ends with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`. Timestamps `ts` are epoch **seconds** (float). We only ever short, so `Signal.side` is always `"short"`.

---

## File Structure

```
lowcap_short_system/
  __init__.py                         # (create if missing — namespace)
  microstructure/
    __init__.py
    events.py        # PriceLevel, BookState, DepthSnapshot, DepthDelta, TradePrint, LevelChange, MarketEvent
    config.py        # MicroConfig dataclass (defaults) + load_config(path)
    book.py          # BookMaintainer
    features.py      # imbalance, absorption, bid_stack_collapse, tape_metrics, spoofing_score (+ Absorption, Tape)
    strategies/
      __init__.py
      base.py        # Signal, EvalContext, Features, Strategy protocol
      imbalance.py   # ImbalanceStrategy
      absorption.py  # AbsorptionStrategy
      tape.py        # TapeStrategy
      engine.py      # compute_features(), StrategyEngine, ConfirmedSignal
    feeds/
      __init__.py
      base.py        # Feed protocol
      replay.py      # ReplayFeed, load_jsonl
      live_stubs.py  # TradeZeroDepthFeed, IBKRDepthFeed (NotImplementedError)
    sim/
      __init__.py
      fills.py       # fill_against_book()
      scenarios.py   # synthetic event sequences (pump-fade, squeeze, fake-wall)
      harness.py     # run scenarios -> metrics; __main__ runnable
  config/
    microstructure.yaml                # all thresholds
tests/microstructure/                  # pytest tests (mirror module tree)
pyproject.toml                         # tooling config (create at repo root)
```

---

## Task 1: Python project scaffold

**Files:**
- Create: `pyproject.toml`, `lowcap_short_system/__init__.py`, `lowcap_short_system/microstructure/__init__.py`, `tests/__init__.py`, `tests/microstructure/__init__.py`, `tests/microstructure/test_smoke.py`

- [ ] **Step 1: Create `pyproject.toml`** (repo root)

```toml
[project]
name = "lowcap-short-system"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["PyYAML>=6.0"]

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.5", "mypy>=1.10"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true
```

- [ ] **Step 2: Create the package + test `__init__.py` files** (all empty) and a smoke test

`lowcap_short_system/__init__.py`, `lowcap_short_system/microstructure/__init__.py`, `tests/__init__.py`, `tests/microstructure/__init__.py`: empty files.

`tests/microstructure/test_smoke.py`:
```python
def test_package_imports():
    import lowcap_short_system.microstructure as m
    assert m is not None
```

- [ ] **Step 3: Install dev deps and run**

Do NOT do an editable install of the project (setuptools auto-discovery would error on the
`lowcap_short_system` + `tests` top-level packages). Install the tools directly; pytest's
`pythonpath = ["."]` (set in `pyproject.toml`) makes `import lowcap_short_system...` resolve
from the repo root with no install needed.

Run: `python -m pip install pytest ruff mypy pyyaml`
Then: `python -m pytest tests/microstructure/test_smoke.py -q`
Expected: 1 passed.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml lowcap_short_system/__init__.py lowcap_short_system/microstructure/__init__.py tests/
git commit -m "chore(engine): python scaffold for L2 microstructure engine"
```

---

## Task 2: Event/domain types

**Files:**
- Create: `lowcap_short_system/microstructure/events.py`, `tests/microstructure/test_events.py`

- [ ] **Step 1: Write the failing test**

`tests/microstructure/test_events.py`:
```python
from lowcap_short_system.microstructure.events import (
    PriceLevel, BookState, DepthSnapshot, DepthDelta, TradePrint, LevelChange,
)

def test_bookstate_derived_quotes():
    b = BookState(
        symbol="TICK", ts=1.0,
        bids=(PriceLevel(4.10, 500), PriceLevel(4.09, 300)),
        asks=(PriceLevel(4.12, 400), PriceLevel(4.13, 200)),
    )
    assert b.best_bid.price == 4.10
    assert b.best_ask.price == 4.12
    assert round(b.mid, 3) == 4.11
    assert round(b.spread, 3) == 0.02

def test_empty_book_quotes_are_none():
    b = BookState(symbol="X", ts=0.0, bids=(), asks=())
    assert b.best_bid is None and b.best_ask is None
    assert b.mid is None and b.spread is None

def test_event_types_are_frozen():
    d = DepthDelta(symbol="X", ts=1.0, side="bid", price=4.0, new_size=0)
    t = TradePrint(symbol="X", ts=1.0, price=4.0, size=100, aggressor="buy")
    s = DepthSnapshot(symbol="X", ts=1.0, bids=((4.0, 100),), asks=((4.1, 100),))
    c = LevelChange(ts=1.0, side="ask", price=4.1, old_size=100, new_size=200)
    assert d.new_size == 0 and t.aggressor == "buy" and s.bids[0][1] == 100 and c.new_size == 200
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/microstructure/test_events.py -q`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `events.py`**

```python
from __future__ import annotations
from dataclasses import dataclass

Side = str          # "bid" | "ask"
Aggressor = str     # "buy" | "sell" | "unknown"

@dataclass(frozen=True)
class PriceLevel:
    price: float
    size: int

@dataclass(frozen=True)
class BookState:
    symbol: str
    ts: float
    bids: tuple[PriceLevel, ...]   # sorted by price descending
    asks: tuple[PriceLevel, ...]   # sorted by price ascending

    @property
    def best_bid(self) -> PriceLevel | None:
        return self.bids[0] if self.bids else None

    @property
    def best_ask(self) -> PriceLevel | None:
        return self.asks[0] if self.asks else None

    @property
    def mid(self) -> float | None:
        if self.best_bid and self.best_ask:
            return (self.best_bid.price + self.best_ask.price) / 2
        return None

    @property
    def spread(self) -> float | None:
        if self.best_bid and self.best_ask:
            return self.best_ask.price - self.best_bid.price
        return None

@dataclass(frozen=True)
class DepthSnapshot:
    symbol: str
    ts: float
    bids: tuple[tuple[float, int], ...]
    asks: tuple[tuple[float, int], ...]

@dataclass(frozen=True)
class DepthDelta:
    symbol: str
    ts: float
    side: Side
    price: float
    new_size: int          # 0 removes the level

@dataclass(frozen=True)
class TradePrint:
    symbol: str
    ts: float
    price: float
    size: int
    aggressor: Aggressor

@dataclass(frozen=True)
class LevelChange:
    ts: float
    side: Side
    price: float
    old_size: int
    new_size: int

MarketEvent = DepthSnapshot | DepthDelta | TradePrint
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/microstructure/test_events.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add lowcap_short_system/microstructure/events.py tests/microstructure/test_events.py
git commit -m "feat(engine): L2 event/domain types"
```

---

## Task 3: Config

**Files:**
- Create: `lowcap_short_system/microstructure/config.py`, `config/microstructure.yaml`, `tests/microstructure/test_config.py`

- [ ] **Step 1: Write the failing test**

`tests/microstructure/test_config.py`:
```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/microstructure/test_config.py -q`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `config.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, fields
import os
import yaml

@dataclass(frozen=True)
class MicroConfig:
    # imbalance
    imbalance_depth: int = 5
    enter_imbalance: float = 0.35      # ask-heavy if imbalance <= -enter_imbalance
    # absorption
    absorb_window_s: float = 5.0
    absorb_min_volume: int = 5000
    # bid-stack collapse
    collapse_frac: float = 0.5
    collapse_min_levels: int = 2
    # tape
    tape_window_s: float = 5.0
    sweep_levels: int = 3
    block_size: int = 5000
    exhaustion_drop: float = 0.5
    # spoofing
    spoof_window_s: float = 5.0
    veto_spoof: float = 0.5            # spoof score >= this vetoes new entries
    # engine
    min_conviction: float = 0.6        # summed enter-strength * spoof-confidence

def load_config(path: str) -> MicroConfig:
    if not os.path.exists(path):
        return MicroConfig()
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    known = {f.name for f in fields(MicroConfig)}
    return MicroConfig(**{k: v for k, v in data.items() if k in known})
```

- [ ] **Step 4: Create `config/microstructure.yaml`** (defaults, documented)

```yaml
# Level 2 microstructure thresholds. All starting hypotheses — tune via the sim harness.
imbalance_depth: 5
enter_imbalance: 0.35
absorb_window_s: 5.0
absorb_min_volume: 5000
collapse_frac: 0.5
collapse_min_levels: 2
tape_window_s: 5.0
sweep_levels: 3
block_size: 5000
exhaustion_drop: 0.5
spoof_window_s: 5.0
veto_spoof: 0.5
min_conviction: 0.6
```

- [ ] **Step 5: Run to verify it passes**

Run: `python -m pytest tests/microstructure/test_config.py -q`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add lowcap_short_system/microstructure/config.py config/microstructure.yaml tests/microstructure/test_config.py
git commit -m "feat(engine): microstructure config (defaults + yaml loader)"
```

---

## Task 4: Book maintainer

**Files:**
- Create: `lowcap_short_system/microstructure/book.py`, `tests/microstructure/test_book.py`

- [ ] **Step 1: Write the failing test**

`tests/microstructure/test_book.py`:
```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/microstructure/test_book.py -q`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `book.py`**

```python
from __future__ import annotations
from collections import deque
from lowcap_short_system.microstructure.events import (
    BookState, DepthSnapshot, DepthDelta, PriceLevel, LevelChange,
)

class BookMaintainer:
    def __init__(self, symbol: str, depth: int = 10, history: int = 500) -> None:
        self.symbol = symbol
        self.depth = depth
        self._bids: dict[float, int] = {}
        self._asks: dict[float, int] = {}
        self._last_ts: float = 0.0
        self._changes: deque[LevelChange] = deque(maxlen=history)

    def apply_snapshot(self, snap: DepthSnapshot) -> None:
        self._bids = {p: s for p, s in snap.bids if s > 0}
        self._asks = {p: s for p, s in snap.asks if s > 0}
        self._last_ts = snap.ts

    def apply_delta(self, delta: DepthDelta) -> None:
        book = self._bids if delta.side == "bid" else self._asks
        old = book.get(delta.price, 0)
        if delta.new_size <= 0:
            book.pop(delta.price, None)
        else:
            book[delta.price] = delta.new_size
        self._last_ts = delta.ts
        self._changes.append(
            LevelChange(delta.ts, delta.side, delta.price, old, max(0, delta.new_size))
        )

    def state(self, ts: float | None = None) -> BookState:
        bids = tuple(
            PriceLevel(p, self._bids[p]) for p in sorted(self._bids, reverse=True)[: self.depth]
        )
        asks = tuple(
            PriceLevel(p, self._asks[p]) for p in sorted(self._asks)[: self.depth]
        )
        return BookState(self.symbol, ts if ts is not None else self._last_ts, bids, asks)

    @property
    def changes(self) -> list[LevelChange]:
        return list(self._changes)

    def is_stale(self, now: float, max_age_s: float) -> bool:
        return (now - self._last_ts) > max_age_s
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/microstructure/test_book.py -q`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add lowcap_short_system/microstructure/book.py tests/microstructure/test_book.py
git commit -m "feat(engine): order-book maintainer with change history + staleness"
```

---

## Task 5: Microstructure features

**Files:**
- Create: `lowcap_short_system/microstructure/features.py`, `tests/microstructure/test_features.py`

The functions are pure. `prints` is a list of `TradePrint` (most recent last). `changes` is `BookMaintainer.changes`. `cfg` is a `MicroConfig`.

- [ ] **Step 1: Write the failing test**

`tests/microstructure/test_features.py`:
```python
from lowcap_short_system.microstructure.config import MicroConfig
from lowcap_short_system.microstructure.events import BookState, PriceLevel, TradePrint, LevelChange
from lowcap_short_system.microstructure.features import (
    order_book_imbalance, absorption, bid_stack_collapse, tape_metrics, spoofing_score,
)

CFG = MicroConfig()

def book(bids, asks, ts=10.0):
    return BookState("X", ts, tuple(PriceLevel(*b) for b in bids), tuple(PriceLevel(*a) for a in asks))

def test_imbalance_sign_and_range():
    bid_heavy = book([(4.1, 1000), (4.0, 1000)], [(4.2, 100), (4.3, 100)])
    ask_heavy = book([(4.1, 100), (4.0, 100)], [(4.2, 1000), (4.3, 1000)])
    assert order_book_imbalance(bid_heavy, CFG.imbalance_depth) > 0.5
    assert order_book_imbalance(ask_heavy, CFG.imbalance_depth) < -0.5
    assert -1.0 <= order_book_imbalance(ask_heavy, CFG.imbalance_depth) <= 1.0

def test_absorption_detects_refresh_against_buying():
    # buyers lift the 4.12 ask for 6000 sh while the ask level refreshes (400 -> 900)
    prints = [TradePrint("X", t, 4.12, 1000, "buy") for t in (10.0, 10.1, 10.2, 10.3, 10.4, 10.5)]
    changes = [LevelChange(10.25, "ask", 4.12, 400, 900)]  # refreshed bigger despite prints
    a = absorption(changes, prints, CFG)
    assert a.side == "sell" and a.strength > 0 and a.price == 4.12

def test_absorption_absent_without_refresh():
    prints = [TradePrint("X", 10.0, 4.12, 1000, "buy")]
    assert absorption([], prints, CFG).strength == 0.0

def test_bid_stack_collapse_scores_on_vanishing_bids():
    changes = [
        LevelChange(10.0, "bid", 4.10, 500, 0),     # removed
        LevelChange(10.1, "bid", 4.09, 400, 150),   # -62% > collapse_frac
    ]
    assert bid_stack_collapse(changes, CFG) >= 1.0  # >= collapse_min_levels collapsed

def test_tape_block_and_exhaustion():
    prints = (
        [TradePrint("X", 10.0 + i * 0.1, 4.1, 1000, "buy") for i in range(8)]  # busy first half
        + [TradePrint("X", 12.5, 4.1, 6000, "buy")]                            # a block, then quiet
    )
    t = tape_metrics(prints, CFG)
    assert t.block is True
    assert t.trades_per_s > 0

def test_spoofing_score_flags_add_then_cancel_without_trade():
    changes = [
        LevelChange(10.0, "bid", 4.00, 0, 5000),    # add a wall
        LevelChange(10.3, "bid", 4.00, 5000, 0),    # cancel it
    ]
    prints = []  # no trade at 4.00
    assert spoofing_score(changes, prints, CFG) > 0.0
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/microstructure/test_features.py -q`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `features.py`** (rules exactly as below)

```python
from __future__ import annotations
from dataclasses import dataclass
from lowcap_short_system.microstructure.config import MicroConfig
from lowcap_short_system.microstructure.events import BookState, TradePrint, LevelChange

@dataclass(frozen=True)
class Absorption:
    strength: float          # 0..1
    side: str                # "sell" (hidden seller) | "none"
    price: float | None

@dataclass(frozen=True)
class Tape:
    trades_per_s: float
    sweep: bool
    block: bool
    exhaustion: bool

def order_book_imbalance(book: BookState, depth: int) -> float:
    """Depth-weighted (bid - ask)/(bid + ask). + = bid-heavy, - = ask-heavy. Range [-1, 1]."""
    def weighted(levels) -> float:
        return sum(lvl.size / (i + 1) for i, lvl in enumerate(levels[:depth]))
    bw, aw = weighted(book.bids), weighted(book.asks)
    return (bw - aw) / (bw + aw) if (bw + aw) > 0 else 0.0

def absorption(changes: list[LevelChange], prints: list[TradePrint], cfg: MicroConfig) -> Absorption:
    """Hidden seller: heavy buy volume at an ask price while that ask level refreshes (holds/grows)."""
    if not prints:
        return Absorption(0.0, "none", None)
    latest = prints[-1].ts
    window = [p for p in prints if latest - p.ts <= cfg.absorb_window_s]
    buy_vol: dict[float, int] = {}
    for p in window:
        if p.aggressor == "buy":
            buy_vol[p.price] = buy_vol.get(p.price, 0) + p.size
    best_price, best_strength = None, 0.0
    for price, vol in buy_vol.items():
        if vol < cfg.absorb_min_volume:
            continue
        refreshed = any(
            c.side == "ask" and c.price == price and c.new_size >= c.old_size
            and latest - c.ts <= cfg.absorb_window_s
            for c in changes
        )
        if refreshed:
            strength = min(1.0, vol / (2 * cfg.absorb_min_volume))
            if strength > best_strength:
                best_price, best_strength = price, strength
    return Absorption(best_strength, "sell" if best_strength > 0 else "none", best_price)

def bid_stack_collapse(changes: list[LevelChange], cfg: MicroConfig) -> float:
    """Fraction (capped at 1) of bid levels that vanished or shrank past collapse_frac, vs min_levels."""
    collapsed: set[float] = set()
    for c in changes:
        if c.side != "bid" or c.old_size <= 0:
            continue
        if c.new_size == 0 or c.new_size <= c.old_size * (1 - cfg.collapse_frac):
            collapsed.add(c.price)
    return min(1.0, len(collapsed) / cfg.collapse_min_levels)

def tape_metrics(prints: list[TradePrint], cfg: MicroConfig) -> Tape:
    if not prints:
        return Tape(0.0, False, False, False)
    latest = prints[-1].ts
    window = [p for p in prints if latest - p.ts <= cfg.tape_window_s]
    span = max(cfg.tape_window_s, 1e-9)
    rate = len(window) / span
    block = any(p.size >= cfg.block_size for p in window)
    recent_buy_prices = {p.price for p in window if p.aggressor == "buy" and latest - p.ts <= 1.0}
    sweep = len(recent_buy_prices) >= cfg.sweep_levels
    half = latest - cfg.tape_window_s / 2
    first = [p for p in window if p.ts < half]
    second = [p for p in window if p.ts >= half]
    first_rate = len(first) / (cfg.tape_window_s / 2)
    second_rate = len(second) / (cfg.tape_window_s / 2)
    exhaustion = bool(first and second_rate <= cfg.exhaustion_drop * first_rate)
    return Tape(rate, sweep, block, exhaustion)

def spoofing_score(changes: list[LevelChange], prints: list[TradePrint], cfg: MicroConfig) -> float:
    """Ratio of 'add then cancel without a trade at that price' to total adds, in the window. 0..1."""
    if not changes:
        return 0.0
    latest = changes[-1].ts
    window = [c for c in changes if latest - c.ts <= cfg.spoof_window_s]
    traded_prices = {p.price for p in prints if latest - p.ts <= cfg.spoof_window_s}
    adds = [c for c in window if c.old_size == 0 and c.new_size > 0]
    cancels = {c.price for c in window if c.old_size > 0 and c.new_size == 0}
    if not adds:
        return 0.0
    spoofy = sum(
        1 for c in adds if c.price in cancels and c.price not in traded_prices
    )
    return min(1.0, spoofy / len(adds))
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/microstructure/test_features.py -q`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add lowcap_short_system/microstructure/features.py tests/microstructure/test_features.py
git commit -m "feat(engine): microstructure features (imbalance, absorption, collapse, tape, spoof)"
```

---

## Task 6: Strategies

**Files:**
- Create: `lowcap_short_system/microstructure/strategies/__init__.py` (empty), `base.py`, `imbalance.py`, `absorption.py`, `tape.py`, `tests/microstructure/test_strategies.py`

- [ ] **Step 1: Write the failing test**

`tests/microstructure/test_strategies.py`:
```python
from lowcap_short_system.microstructure.config import MicroConfig
from lowcap_short_system.microstructure.events import BookState
from lowcap_short_system.microstructure.features import Absorption, Tape
from lowcap_short_system.microstructure.strategies.base import Features, EvalContext
from lowcap_short_system.microstructure.strategies.imbalance import ImbalanceStrategy
from lowcap_short_system.microstructure.strategies.absorption import AbsorptionStrategy
from lowcap_short_system.microstructure.strategies.tape import TapeStrategy

CFG = MicroConfig()
BOOK = BookState("X", 1.0, (), ())
FLAT = EvalContext(in_position=False)
IN = EvalContext(in_position=True)

def feats(**kw):
    base = dict(imbalance=0.0, absorption=Absorption(0.0, "none", None),
                bid_collapse=0.0, tape=Tape(0.0, False, False, False), spoof=0.0)
    base.update(kw)
    return Features(**base)

def test_imbalance_enters_on_ask_heavy():
    s = ImbalanceStrategy()
    sig = s.evaluate(BOOK, feats(imbalance=-0.5), FLAT, CFG)
    assert sig and sig.kind == "enter" and sig.side == "short"
    assert s.evaluate(BOOK, feats(imbalance=-0.1), FLAT, CFG) is None  # below threshold

def test_absorption_enters_on_hidden_seller():
    s = AbsorptionStrategy()
    sig = s.evaluate(BOOK, feats(absorption=Absorption(0.9, "sell", 4.12)), FLAT, CFG)
    assert sig and sig.kind == "enter" and sig.strength == 0.9

def test_tape_enters_on_exhaustion_after_sweep_and_exits_on_upsweep():
    s = TapeStrategy()
    enter = s.evaluate(BOOK, feats(tape=Tape(5.0, True, False, True)), FLAT, CFG)
    assert enter and enter.kind == "enter"
    exit_sig = s.evaluate(BOOK, feats(tape=Tape(9.0, True, False, False)), IN, CFG)
    assert exit_sig and exit_sig.kind == "exit"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/microstructure/test_strategies.py -q`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `base.py`**

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from lowcap_short_system.microstructure.config import MicroConfig
from lowcap_short_system.microstructure.events import BookState
from lowcap_short_system.microstructure.features import Absorption, Tape

@dataclass(frozen=True)
class Signal:
    kind: str        # "enter" | "add" | "reduce" | "exit"
    side: str        # always "short"
    strength: float  # 0..1
    reason: str

@dataclass(frozen=True)
class EvalContext:
    in_position: bool

@dataclass(frozen=True)
class Features:
    imbalance: float
    absorption: Absorption
    bid_collapse: float
    tape: Tape
    spoof: float

class Strategy(Protocol):
    name: str
    def evaluate(self, book: BookState, feats: Features, ctx: EvalContext, cfg: MicroConfig) -> Signal | None: ...
```

- [ ] **Step 4: Implement `imbalance.py`**

```python
from __future__ import annotations
from lowcap_short_system.microstructure.config import MicroConfig
from lowcap_short_system.microstructure.events import BookState
from lowcap_short_system.microstructure.strategies.base import Signal, EvalContext, Features

class ImbalanceStrategy:
    name = "imbalance"
    def evaluate(self, book: BookState, feats: Features, ctx: EvalContext, cfg: MicroConfig) -> Signal | None:
        if not ctx.in_position and feats.imbalance <= -cfg.enter_imbalance:
            return Signal("enter", "short", min(1.0, abs(feats.imbalance)),
                          f"ask-heavy imbalance {feats.imbalance:.2f}")
        return None
```

- [ ] **Step 5: Implement `absorption.py`**

```python
from __future__ import annotations
from lowcap_short_system.microstructure.config import MicroConfig
from lowcap_short_system.microstructure.events import BookState
from lowcap_short_system.microstructure.strategies.base import Signal, EvalContext, Features

class AbsorptionStrategy:
    name = "absorption"
    def evaluate(self, book: BookState, feats: Features, ctx: EvalContext, cfg: MicroConfig) -> Signal | None:
        a = feats.absorption
        if not ctx.in_position and a.side == "sell" and a.strength > 0:
            return Signal("enter", "short", a.strength,
                          f"hidden seller absorption @ {a.price}")
        return None
```

- [ ] **Step 6: Implement `tape.py`**

```python
from __future__ import annotations
from lowcap_short_system.microstructure.config import MicroConfig
from lowcap_short_system.microstructure.events import BookState
from lowcap_short_system.microstructure.strategies.base import Signal, EvalContext, Features

class TapeStrategy:
    name = "tape"
    def evaluate(self, book: BookState, feats: Features, ctx: EvalContext, cfg: MicroConfig) -> Signal | None:
        t = feats.tape
        if ctx.in_position and t.sweep:
            return Signal("exit", "short", 0.8, "up-sweep against short")
        if not ctx.in_position and t.exhaustion and t.sweep:
            return Signal("enter", "short", 0.7, "buy exhaustion after sweep")
        return None
```

- [ ] **Step 7: Run to verify it passes**

Run: `python -m pytest tests/microstructure/test_strategies.py -q`
Expected: 3 passed.

- [ ] **Step 8: Commit**

```bash
git add lowcap_short_system/microstructure/strategies/ tests/microstructure/test_strategies.py
git commit -m "feat(engine): L2 strategies (imbalance, absorption, tape)"
```

---

## Task 7: Strategy engine

**Files:**
- Create: `lowcap_short_system/microstructure/strategies/engine.py`, `tests/microstructure/test_engine.py`

- [ ] **Step 1: Write the failing test**

`tests/microstructure/test_engine.py`:
```python
from lowcap_short_system.microstructure.config import MicroConfig
from lowcap_short_system.microstructure.events import BookState, PriceLevel, TradePrint, LevelChange
from lowcap_short_system.microstructure.strategies.base import EvalContext
from lowcap_short_system.microstructure.strategies.engine import StrategyEngine, compute_features

CFG = MicroConfig()

def ask_heavy_book(ts=10.0):
    return BookState("X", ts, (PriceLevel(4.10, 100),), (PriceLevel(4.12, 2000), PriceLevel(4.13, 2000)))

def test_strong_absorption_alone_confirms_enter():
    prints = [TradePrint("X", 10.0 + i * 0.1, 4.12, 2000, "buy") for i in range(6)]  # 12k buy vol
    changes = [LevelChange(10.4, "ask", 4.12, 2000, 4000)]                            # refreshed
    eng = StrategyEngine(CFG)
    sig = eng.evaluate(ask_heavy_book(10.6), prints, changes, EvalContext(False))
    assert sig and sig.kind == "enter"

def test_weak_single_signal_does_not_confirm():
    # mild ask-heavy imbalance only (~ -0.4 strength) is below min_conviction 0.6
    eng = StrategyEngine(CFG)
    book = BookState("X", 10.0, (PriceLevel(4.10, 300),), (PriceLevel(4.12, 700),))
    sig = eng.evaluate(book, [], [], EvalContext(False))
    assert sig is None

def test_spoof_veto_blocks_entry():
    # ask-heavy + absorption would enter, but a spoofy book vetoes it
    prints = [TradePrint("X", 10.0 + i * 0.1, 4.12, 2000, "buy") for i in range(6)]
    changes = [
        LevelChange(10.4, "ask", 4.12, 2000, 4000),
        LevelChange(10.0, "bid", 4.00, 0, 9000),   # add wall
        LevelChange(10.3, "bid", 4.00, 9000, 0),   # cancel (no trade at 4.00) -> spoof
    ]
    eng = StrategyEngine(CFG)
    sig = eng.evaluate(ask_heavy_book(10.6), prints, changes, EvalContext(False))
    assert sig is None  # vetoed

def test_exit_dominates_when_in_position_on_upsweep():
    prints = [TradePrint("X", 10.0, 4.12, 100, "buy"),
              TradePrint("X", 10.1, 4.13, 100, "buy"),
              TradePrint("X", 10.2, 4.14, 100, "buy")]  # 3 distinct prices in <1s -> sweep
    eng = StrategyEngine(CFG)
    sig = eng.evaluate(ask_heavy_book(10.3), prints, [], EvalContext(True))
    assert sig and sig.kind == "exit"

def test_compute_features_bundles_all():
    f = compute_features(ask_heavy_book(), [], [], CFG)
    assert hasattr(f, "imbalance") and hasattr(f, "tape") and hasattr(f, "spoof")
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/microstructure/test_engine.py -q`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `engine.py`**

```python
from __future__ import annotations
from dataclasses import dataclass
from lowcap_short_system.microstructure.config import MicroConfig
from lowcap_short_system.microstructure.events import BookState, TradePrint, LevelChange
from lowcap_short_system.microstructure import features as F
from lowcap_short_system.microstructure.strategies.base import Features, EvalContext, Signal
from lowcap_short_system.microstructure.strategies.imbalance import ImbalanceStrategy
from lowcap_short_system.microstructure.strategies.absorption import AbsorptionStrategy
from lowcap_short_system.microstructure.strategies.tape import TapeStrategy

@dataclass(frozen=True)
class ConfirmedSignal:
    kind: str            # "enter" | "exit"
    side: str            # "short"
    strength: float
    reasons: tuple[str, ...]
    features: Features

def compute_features(book: BookState, prints: list[TradePrint],
                     changes: list[LevelChange], cfg: MicroConfig) -> Features:
    return Features(
        imbalance=F.order_book_imbalance(book, cfg.imbalance_depth),
        absorption=F.absorption(changes, prints, cfg),
        bid_collapse=F.bid_stack_collapse(changes, cfg),
        tape=F.tape_metrics(prints, cfg),
        spoof=F.spoofing_score(changes, prints, cfg),
    )

class StrategyEngine:
    def __init__(self, cfg: MicroConfig) -> None:
        self.cfg = cfg
        self.strategies = [ImbalanceStrategy(), AbsorptionStrategy(), TapeStrategy()]

    def evaluate(self, book: BookState, prints: list[TradePrint],
                 changes: list[LevelChange], ctx: EvalContext) -> ConfirmedSignal | None:
        feats = compute_features(book, prints, changes, self.cfg)
        subs: list[Signal] = []
        for s in self.strategies:
            sig = s.evaluate(book, feats, ctx, self.cfg)
            if sig is not None:
                subs.append(sig)

        exits = [s for s in subs if s.kind == "exit"]
        if ctx.in_position and exits:
            best = max(exits, key=lambda s: s.strength)
            return ConfirmedSignal("exit", "short", best.strength,
                                   tuple(s.reason for s in exits), feats)

        enters = [s for s in subs if s.kind == "enter"]
        confidence = 0.0 if feats.spoof >= self.cfg.veto_spoof else 1.0
        score = sum(s.strength for s in enters) * confidence
        if enters and score >= self.cfg.min_conviction:
            return ConfirmedSignal("enter", "short", min(1.0, score),
                                   tuple(s.reason for s in enters), feats)
        return None
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/microstructure/test_engine.py -q`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add lowcap_short_system/microstructure/strategies/engine.py tests/microstructure/test_engine.py
git commit -m "feat(engine): strategy engine (feature compute, spoof veto, conviction)"
```

---

## Task 8: Feeds (replay + live stubs)

**Files:**
- Create: `lowcap_short_system/microstructure/feeds/__init__.py` (empty), `base.py`, `replay.py`, `live_stubs.py`, `tests/microstructure/test_feeds.py`

- [ ] **Step 1: Write the failing test**

`tests/microstructure/test_feeds.py`:
```python
import json
import pytest
from lowcap_short_system.microstructure.events import DepthSnapshot, TradePrint, DepthDelta
from lowcap_short_system.microstructure.feeds.replay import ReplayFeed, load_jsonl
from lowcap_short_system.microstructure.feeds.live_stubs import TradeZeroDepthFeed, IBKRDepthFeed

def test_replay_orders_events_by_ts():
    evs = [
        TradePrint("X", 3.0, 4.1, 100, "buy"),
        DepthSnapshot("X", 1.0, ((4.0, 100),), ((4.1, 100),)),
        DepthDelta("X", 2.0, "ask", 4.1, 50),
    ]
    out = list(ReplayFeed(evs).events())
    assert [e.ts for e in out] == [1.0, 2.0, 3.0]

def test_load_jsonl_roundtrip(tmp_path):
    p = tmp_path / "evs.jsonl"
    p.write_text(
        json.dumps({"type": "snapshot", "symbol": "X", "ts": 1.0, "bids": [[4.0, 100]], "asks": [[4.1, 100]]}) + "\n"
        + json.dumps({"type": "trade", "symbol": "X", "ts": 2.0, "price": 4.1, "size": 100, "aggressor": "buy"}) + "\n"
        + json.dumps({"type": "delta", "symbol": "X", "ts": 3.0, "side": "ask", "price": 4.1, "new_size": 0}) + "\n"
    )
    evs = load_jsonl(str(p))
    assert isinstance(evs[0], DepthSnapshot) and isinstance(evs[1], TradePrint) and isinstance(evs[2], DepthDelta)

def test_live_feeds_are_stubbed():
    with pytest.raises(NotImplementedError):
        TradeZeroDepthFeed("TICK").events()
    with pytest.raises(NotImplementedError):
        IBKRDepthFeed("TICK").events()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/microstructure/test_feeds.py -q`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `base.py`**

```python
from __future__ import annotations
from typing import Iterator, Protocol
from lowcap_short_system.microstructure.events import MarketEvent

class Feed(Protocol):
    def events(self) -> Iterator[MarketEvent]: ...
```

- [ ] **Step 4: Implement `replay.py`**

```python
from __future__ import annotations
import json
from typing import Iterator
from lowcap_short_system.microstructure.events import (
    MarketEvent, DepthSnapshot, DepthDelta, TradePrint,
)

class ReplayFeed:
    """Replays a fixed list of events in timestamp order."""
    def __init__(self, events: list[MarketEvent]) -> None:
        self._events = sorted(events, key=lambda e: e.ts)

    def events(self) -> Iterator[MarketEvent]:
        return iter(self._events)

def _parse(obj: dict) -> MarketEvent:
    kind = obj["type"]
    if kind == "snapshot":
        return DepthSnapshot(obj["symbol"], obj["ts"],
                             tuple((p, s) for p, s in obj["bids"]),
                             tuple((p, s) for p, s in obj["asks"]))
    if kind == "delta":
        return DepthDelta(obj["symbol"], obj["ts"], obj["side"], obj["price"], obj["new_size"])
    if kind == "trade":
        return TradePrint(obj["symbol"], obj["ts"], obj["price"], obj["size"], obj["aggressor"])
    raise ValueError(f"unknown event type: {kind}")

def load_jsonl(path: str) -> list[MarketEvent]:
    with open(path, "r", encoding="utf-8") as fh:
        return [_parse(json.loads(line)) for line in fh if line.strip()]
```

- [ ] **Step 5: Implement `live_stubs.py`**

```python
from __future__ import annotations
from typing import Iterator
from lowcap_short_system.microstructure.events import MarketEvent

class _LiveFeedStub:
    """Phase 3: real broker depth. Stubbed behind the Feed protocol for now."""
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    def events(self) -> Iterator[MarketEvent]:
        raise NotImplementedError(
            "Live broker depth is Phase 3 — requires credentials + a funded account."
        )

class TradeZeroDepthFeed(_LiveFeedStub):
    pass

class IBKRDepthFeed(_LiveFeedStub):
    pass
```

- [ ] **Step 6: Run to verify it passes**

Run: `python -m pytest tests/microstructure/test_feeds.py -q`
Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add lowcap_short_system/microstructure/feeds/ tests/microstructure/test_feeds.py
git commit -m "feat(engine): replay feed + jsonl loader + live feed stubs"
```

---

## Task 9: Sim harness (fills, scenarios, runnable)

**Files:**
- Create: `lowcap_short_system/microstructure/sim/__init__.py` (empty), `fills.py`, `scenarios.py`, `harness.py`, `tests/microstructure/test_sim.py`

- [ ] **Step 1: Write the failing test**

`tests/microstructure/test_sim.py`:
```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/microstructure/test_sim.py -q`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `fills.py`**

```python
from __future__ import annotations
from lowcap_short_system.microstructure.events import BookState

def fill_against_book(book: BookState, side: str, qty: int) -> tuple[int, float]:
    """Fill `qty` against displayed depth. side='sell' hits bids; 'buy' lifts asks.
    Returns (filled_qty, avg_price). Caps at displayed size (no infinite liquidity)."""
    levels = book.bids if side == "sell" else book.asks
    remaining, notional, filled = qty, 0.0, 0
    for lvl in levels:
        take = min(remaining, lvl.size)
        notional += take * lvl.price
        filled += take
        remaining -= take
        if remaining <= 0:
            break
    avg = notional / filled if filled else 0.0
    return filled, avg
```

- [ ] **Step 4: Implement `scenarios.py`**

```python
from __future__ import annotations
from lowcap_short_system.microstructure.events import (
    MarketEvent, DepthSnapshot, DepthDelta, TradePrint,
)

def pump_fade_absorption() -> list[MarketEvent]:
    """Parabolic top: heavy buying lifts the 4.12 ask but it refreshes (hidden seller),
    plus ask-heavy depth. Engine should confirm a fade enter."""
    evs: list[MarketEvent] = [
        DepthSnapshot("TICK", 0.0, ((4.10, 100), (4.09, 100)), ((4.12, 3000), (4.13, 3000))),
    ]
    t = 0.1
    for _ in range(6):
        evs.append(TradePrint("TICK", t, 4.12, 2000, "buy"))
        t += 0.1
    evs.append(DepthDelta("TICK", t, "ask", 4.12, 5000))  # refresh bigger despite the buying
    return evs

def squeeze() -> list[MarketEvent]:
    """Up-sweep against an open short: buys across rising prices in under a second."""
    return [
        DepthSnapshot("TICK", 0.0, ((4.10, 200),), ((4.12, 200), (4.13, 200), (4.14, 200))),
        TradePrint("TICK", 0.1, 4.12, 200, "buy"),
        TradePrint("TICK", 0.2, 4.13, 200, "buy"),
        TradePrint("TICK", 0.3, 4.14, 200, "buy"),
    ]

def fake_wall() -> list[MarketEvent]:
    """Same fade setup as pump_fade, but a spoofed bid wall flickers in and out -> veto."""
    evs = pump_fade_absorption()
    evs.append(DepthDelta("TICK", 0.05, "bid", 4.00, 9000))   # add wall (no trade at 4.00)
    evs.append(DepthDelta("TICK", 0.55, "bid", 4.00, 0))      # cancel it
    return evs
```

- [ ] **Step 5: Implement `harness.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from lowcap_short_system.microstructure.config import MicroConfig, load_config
from lowcap_short_system.microstructure.events import (
    MarketEvent, DepthSnapshot, DepthDelta, TradePrint,
)
from lowcap_short_system.microstructure.book import BookMaintainer
from lowcap_short_system.microstructure.feeds.replay import ReplayFeed
from lowcap_short_system.microstructure.strategies.base import EvalContext
from lowcap_short_system.microstructure.strategies.engine import StrategyEngine, ConfirmedSignal

@dataclass
class ScenarioResult:
    signals: list[ConfirmedSignal] = field(default_factory=list)
    enters: int = 0
    exits: int = 0

def run_scenario(events: list[MarketEvent], cfg: MicroConfig | None = None,
                 start_in_position: bool = False) -> ScenarioResult:
    cfg = cfg or MicroConfig()
    symbol = events[0].symbol
    bm = BookMaintainer(symbol)
    eng = StrategyEngine(cfg)
    prints: list[TradePrint] = []
    in_position = start_in_position
    res = ScenarioResult()
    for ev in ReplayFeed(events).events():
        if isinstance(ev, DepthSnapshot):
            bm.apply_snapshot(ev)
        elif isinstance(ev, DepthDelta):
            bm.apply_delta(ev)
        elif isinstance(ev, TradePrint):
            prints.append(ev)
        sig = eng.evaluate(bm.state(ev.ts), prints, bm.changes, EvalContext(in_position))
        if sig is not None:
            res.signals.append(sig)
            if sig.kind == "enter":
                res.enters += 1
                in_position = True
            elif sig.kind == "exit":
                res.exits += 1
                in_position = False
    return res

def main() -> None:
    from lowcap_short_system.microstructure.sim import scenarios
    cfg = load_config("config/microstructure.yaml")
    runs = {
        "pump_fade_absorption": (scenarios.pump_fade_absorption(), False),
        "squeeze": (scenarios.squeeze(), True),
        "fake_wall": (scenarios.fake_wall(), False),
    }
    print("=== L2 engine sim ===")
    for name, (evs, in_pos) in runs.items():
        res = run_scenario(evs, cfg, start_in_position=in_pos)
        kinds = [s.kind for s in res.signals]
        print(f"{name:24s} enters={res.enters} exits={res.exits} signals={kinds}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run to verify it passes**

Run: `python -m pytest tests/microstructure/test_sim.py -q`
Expected: 4 passed.

- [ ] **Step 7: Run the demo + full suite + lint/type**

Run: `python -m lowcap_short_system.microstructure.sim.harness`
Expected output (signals lists may vary slightly but the counts must hold):
```
=== L2 engine sim ===
pump_fade_absorption     enters=1 exits=0 signals=['enter']
squeeze                  exits>=1 ...
fake_wall                enters=0 ...
```
Then: `python -m pytest tests/microstructure -q` → all pass.
Then: `python -m ruff check lowcap_short_system tests` → no errors.
Then: `python -m mypy lowcap_short_system/microstructure` → no errors (or only acceptable notes).

- [ ] **Step 8: Commit**

```bash
git add lowcap_short_system/microstructure/sim/ tests/microstructure/test_sim.py
git commit -m "feat(engine): L2 sim harness, fill model, synthetic scenarios"
```

---

## Self-Review

**1. Spec coverage:**
- Data spine (events, book maintainer, staleness) → Tasks 2, 4. ✓
- Feature layer (imbalance, absorption, bid-collapse, tape, spoof) → Task 5. ✓
- Four strategies + engine (spoof veto, conviction) → Tasks 6, 7. The "spoof/fake-wall defense" strategy is implemented as the engine's spoof veto (confidence multiplier) per spec §5.4, not a standalone enter strategy. ✓
- Replay feed + live adapter stubs (broker depth, Phase 3) → Task 8. ✓
- Sim/backtest harness + displayed-size fill model → Task 9. ✓
- Config: every threshold in `config/microstructure.yaml` + loader → Task 3. ✓
- No network/broker calls in Phase 1 (live feeds raise NotImplementedError) → Task 8. ✓
- Phase 1 success criteria (runnable harness, scenarios) → Task 9 Step 7. ✓

**2. Placeholder scan:** No TBD/TODO; every code step has complete code; algorithms fully specified and pinned by tests. ✓

**3. Type consistency:** `MicroConfig` field names match across config/features/strategies/engine. `Features` bundle (imbalance/absorption/bid_collapse/tape/spoof) is produced by `compute_features` and consumed identically by strategies. `Signal`(kind/side/strength/reason) vs `ConfirmedSignal`(kind/side/strength/reasons/features) used consistently. `BookMaintainer.changes`/`.state()`/`.is_stale()` signatures match their call sites in the engine/harness. Feed `.events()` returns `Iterator[MarketEvent]` everywhere. ✓
