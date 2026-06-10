"""Component scores for the signal engine (design section 4.2).

Each score is normalized to [0, 1]. The composite favors names where the
pump-fade and dilution theses align and borrow conditions are clean. Weights
and shapes here are starting hypotheses for backtest tuning.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..data.models import BorrowInfo, Filing, SymbolSnapshot

# Form types weighted by how directly they imply near-term supply.
_FORM_WEIGHTS = {
    "424B5": 1.0,  # prospectus supplement — offering is live
    "424B3": 0.8,
    "S-1": 0.9,
    "F-1": 0.9,
    "S-3": 0.7,  # shelf — supply is enabled, not necessarily active
    "F-3": 0.7,
    "8-K": 0.5,  # only relevant when offering-related; treated generically
}


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def pump_fade_score(snap: SymbolSnapshot) -> float:
    """Parabolic move + volume spike (+ optional social-mention spike).

    Peaks for a large-but-fadeable spike; an unbroken parabolic with no
    pullback is squeeze-guard territory, not a better signal.
    """
    gain = snap.intraday_gain_pct
    if gain <= 0:
        return 0.0
    move = _clamp(gain / 100.0)  # saturates at +100%
    volume = _clamp(snap.rvol / 10.0)  # saturates at 10x RVOL
    social = _clamp(snap.social_volume_zscore / 4.0)  # 0 when no social data
    score = 0.5 * move + 0.35 * volume + 0.15 * social
    if not snap.pulled_back:
        score *= 0.7  # still accelerating: discount, the guard may abort anyway
    return _clamp(score)


def dilution_score(filings: list[Filing], now: datetime | None = None) -> float:
    """Recency-weighted dilution pressure from EDGAR filings."""
    if not filings:
        return 0.0
    now = now or datetime.now(timezone.utc)
    score = 0.0
    for f in filings:
        weight = _FORM_WEIGHTS.get(f.form_type.upper(), 0.3)
        age_days = max(0.0, (now - f.filed_at).total_seconds() / 86400.0)
        recency = max(0.0, 1.0 - age_days / 30.0)  # linear decay over 30 days
        score += weight * recency
    return _clamp(score)


def borrow_score(borrow: BorrowInfo | None, soft_max_fee_pct: float = 100.0) -> float:
    """Availability and cost of borrow. Higher fee = more crowded = more
    squeeze risk and less edge after costs, so the score decays with fee."""
    if borrow is None or not borrow.borrowable:
        return 0.0
    availability = _clamp(borrow.shares_available / 1_000_000.0)
    fee_penalty = _clamp(borrow.fee_rate_pct / soft_max_fee_pct)
    return _clamp(availability * (1.0 - 0.7 * fee_penalty))


def composite_score(pump: float, dilution: float, borrow: float) -> float:
    """score = pump-fade + dilution + borrow-availability (section 3),
    weighted; borrow acts mostly as a feasibility multiplier."""
    thesis = 0.6 * pump + 0.4 * dilution
    return _clamp(thesis * (0.5 + 0.5 * borrow))
