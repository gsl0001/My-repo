# Operations Runbook — paper testing & go-live

> How to run the system for **paper (live) testing** and, when *you* choose, how to take it
> live. Pairs with [`PROMOTION.md`](PROMOTION.md) (the promotion ladder) and the failure-mode
> table in [`MASTER_BLUEPRINT.md`](MASTER_BLUEPRINT.md) §17. **The agent never arms or operates
> live trading — every step in §2–§3 is performed by the human operator.**

## 1. Paper (live) testing — safe, no real money

This exercises the full decision→order pipeline on replay/mock data with the `PaperBroker` and
`MockLocateProvider`. Nothing connects to a broker.

1. Preflight: `python -m lowcap_short_system.live.preflight paper` → expect `READY: True`.
2. Engine sanity: `python -m lowcap_short_system.microstructure.sim.harness` → fade enter /
   squeeze exit / spoof veto.
3. Drive a session from your own replay/mock feed via `run.session.TradingSession` (mode
   `"paper"`) — it logs every signal/order/exit to the audit log. Inspect with `AuditLog.read()`.
4. Cockpit walkthrough: `.\start.ps1` → watch the L2 panel, scanner, kill switch, pause.
5. Exit criteria to advance (see PROMOTION Stage 2): Reg SHO fail-closed verified (no order
   without a locate), a stop attached to every fill, kill switch flattens + halts, books
   reconcile to zero at end of run.

## 2. Go-live preparation — operator only

Do NOT proceed until paper testing's exit criteria pass.

1. **Broker onboarding** — obtain TradeZero (and/or IBKR) API access; **verify the real endpoint
   paths, auth model, and rate limits** (the paths in `live/tradezero.py` follow Blueprint §7.1
   and are marked "verify in onboarding").
2. **Account** — funded live account ≥ $25k (PDT); confirm shortable inventory access.
3. **Secrets** — copy `.env.example` → `.env` (gitignored) and fill in. Never commit secrets.
4. **Transport** — construct `TradeZeroClient(dry_run=False, transport=HttpTransport(...))` with
   the verified base URL/auth.
5. **Preflight (live):** `python -m lowcap_short_system.live.preflight live` — must be `READY:
   True` (config + all secrets + armed). It will report `not armed` until step 6.

## 3. Arming & first live trades — operator only, deliberate

1. **Arm** only when you intend to trade real money:
   `setx LOWCAP_LIVE_ARMED I_UNDERSTAND_REAL_MONEY` (new shell), or set it in `.env`.
2. **Tiny size first** (PROMOTION Stage 3): one name, minimum lot, full supervision.
3. **Watch:** fills vs modeled slippage, locate quote→accept→credit-back, the audit log, and the
   circuit-breaker / kill-switch state.
4. **Scale** only per PROMOTION Stage 4 after a stable sample.

## 4. Abort / emergency

- **Kill switch** — flatten everything and halt new orders. Test it at every session start.
- **Disarm** — unset `LOWCAP_LIVE_ARMED`; the order path immediately reverts to refusing live
  sends (`LiveNotArmed`).
- **Feed/broker loss** — sessions block new entries and resolve toward *flat*; never hold naked
  risk through a blackout (Blueprint §17). When in doubt, kill + flatten manually in the broker
  GUI and investigate before restart.

## 5. Daily cadence (when live)
Cold start (health-check APIs, confirm equity ≥ PDT, arm kill switch) → pre-market build →
locate prep → prime window 09:30–10:30 → manage → power hour → **forced flat by close** →
reconcile (credit-back unused locates, log fills/fees/P&L) → review. Full timeline:
MASTER_BLUEPRINT §2.
