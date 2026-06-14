# Promotion Gates — backtest → paper → tiny-live → scale

> No stage advances until the prior stage's exit criteria are met and signed off. This is the
> safety ladder between code and real capital. Tie-in: Blueprint §14 (validation) and §11–§12
> (compliance & circuit breakers). Every stage snapshots the exact `config/` version used.

## Stage 0 — Engineering gate (every change)
- [ ] `python -m pytest tests -q` green; `ruff` + `mypy` clean (CI enforces — `.github/workflows/ci.yml`).
- [ ] UI: `npm run test` + `npm run build` green.
- [ ] No secrets in the repo; `.env` is gitignored; required secrets resolve via `security/secrets.py`.

## Stage 1 — Backtest
**Goal:** prove the edge survives realistic frictions before any wiring.
- [ ] L2 sim harness + price/borrow backtester run on a survivorship-bias-free universe.
- [ ] Slippage modeled as a function of size/ADV (not flat bps); borrow-cost + non-refundable
      locate fees accrued; SSR/LULD mechanics modeled.
- **Exit criteria:** positive expectancy net of all modeled costs across the sample; max drawdown
  within the §12 daily limit; locate efficiency (traded/paid) above target. Snapshot config.

## Stage 2 — Paper (order logic)
**Goal:** prove the *plumbing* — signal → sizing → locate gate → order → stop → exit → reconcile —
end to end, with no real capital. (Offline `PaperBroker` + `MockLocateProvider` today; broker
paper account when wired.)
- [ ] Reg SHO fail-closed verified: no order ever transmits without a confirmed locate.
- [ ] Attached programmatic stop on every fill; reconnection-to-flat verified on simulated feed loss.
- [ ] Circuit breakers + kill switch flatten-and-halt verified; audit log captures every event.
- **Exit criteria:** zero naked-risk paths in a fault-injection run; books reconcile to zero EOD.

## Stage 3 — Tiny live  ⚠️ requires the operator
**Goal:** validate against real fills/borrow/latency at trivial size.  **Operator-gated:**
needs live broker credentials, a funded account (≥ $25k PDT), and explicit authorization to
trade real money. The agent does not cross this line autonomously.
- [ ] Live locate quote→accept→credit-back proven; real fills vs modeled slippage compared.
- [ ] Daily drawdown / per-position / gross caps enforced live; kill switch tested at market open.
- **Exit criteria:** N sessions with realized slippage and locate-efficiency within backtest
  tolerance; no breaker or compliance incident.

## Stage 4 — Scale
**Goal:** grow size within risk policy.
- [ ] Size up per a written capital/drawdown policy; re-tune `config/` from live data only after
      a stable sample; monitoring + paging in place for breaker trips and feed loss.
- **Exit criteria:** stable expectancy at each size step before the next; documented rollback.
