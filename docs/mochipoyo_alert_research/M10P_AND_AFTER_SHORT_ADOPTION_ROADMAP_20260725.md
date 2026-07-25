# M10P and After — SHORT Adoption Roadmap

Status: FROZEN PLANNING / AUDIT-ONLY
Date: 2026-07-25
Repo: knitanr-a11y/xauusd-signal-lab
Branch: feature/mochipoyo-alert-research

## Current position

M10P is the fresh prospective audit-only shadow for the deterministically reproduced C056 + G013 SHORT candidate.

Frozen candidate:
- Seed: M10L_H240_C056
- H1 MACD histogram >= 3.637199446 bps
- H1 MACD line <= -7.667425443 bps
- Regime gate M10N_G013:
  - H1 3-bar return >= 18.70087437 bps
  - D1 MACD histogram >= -14.25480242 bps
- Direction: SHORT
- Holding horizon: 240 minutes
- One-position: true
- M10P immutable prospective start: 2026.07.24 23:56:00 MT5 server time

Historical reference, for context only:
- 2023-2024: n=29, PF=3.0026538036
- 2025: n=33, PF=2.3505277277
- 2026 through 2026-06-19: n=22, PF=2.5802661606
- all: n=84, PF=2.5407153517
- fixed $0.20 spread all PF=2.5384760734

M10O deterministic reproduction passed from frozen raw data with maximum metric absolute difference 4.440892098500626e-16.

## Non-negotiable rules during M10P

- Never rerun M10P BAT01.
- Never change C056 or G013 thresholds from prospective outcomes.
- No historical backfill.
- No nearest-M1 fallback.
- MT5 server time only.
- Latest CSV row remains CLOSED by contract.
- Exact M1 entry and exact M1 exit only.
- Permanent CSV downtime gaps remain unobserved; never reconstruct them later.
- Discord send OFF.
- MT5 order OFF.
- live_ready OFF.
- final_signal OFF.
- automatic promotion OFF.
- Keep collector / M7C / M8C / M9V / M9Y / M10B / M10E unchanged.

## Stage M10Q — Operational fresh review at 5 resolved

Purpose: runtime/data health review only, not an efficacy claim.

Required checks:
- immutable start unchanged
- prefix integrity unchanged
- no pre-start candidates
- entry_data_gap and exit_data_gap explicitly reported
- exact M1 entry/exit parity maintained
- C056/G013 thresholds unchanged
- accepted/resolved/open/overlap accounting coherent
- actual-spread and fixed-$0.20 metrics both reported

Performance metrics may be displayed, but 5 resolved is too small for a PF2 claim.

## Stage M10R — Interim fresh review at 10 resolved

Purpose: early descriptive performance review without any threshold tuning.

Report:
- n, WR, PF, net bps, average win/loss, payoff, DD, max losing streak
- fixed-$0.20 PF
- gap counts and overlap skips
- comparison with historical reference as descriptive context only
- feature values of accepted trades for parity inspection, not for refitting

No promotion decision from 10 trades alone.

## Stage M10S — First formal fresh review at 20 resolved

This is the first point at which a fresh PF2 replication statement may be made.

Predeclared interpretation bands for actual-spread PF:
- PF >= 2.0: EARLY_FORMAL_PF2_REPLICATION_SUPPORT
- 1.5 <= PF < 2.0: STRONG_POSITIVE_FRESH_SUPPORT_BELOW_PF2
- 1.0 < PF < 1.5: POSITIVE_FRESH_SUPPORT_BELOW_TARGET
- PF <= 1.0: FRESH_EDGE_NOT_SUPPORTED_AT_20

Additional requirements for any positive interpretation:
- positive net bps
- fixed-$0.20 PF > 1.0
- no unresolved integrity violation
- no threshold changes

These bands are interpretation labels only. They do not authorize live trading or automatic promotion.

## Stage M10T — Stability expansion at 40 resolved

Purpose: determine whether the 20-trade conclusion survives a materially larger fresh sample.

Review:
- cumulative metrics
- first 20 versus next 20
- rolling loss streak / DD behavior
- payoff stability
- actual-spread versus fixed-$0.20 sensitivity
- candidate density and long inactive periods
- time-of-day / regime distributions descriptively only; no refitting

If 20-trade PF2 disappears by 40, record the degradation; do not rescue it by changing thresholds.

## Stage M10U — Adoption review at 60 resolved

Purpose: decide whether C056+G013 is strong enough to become an operational candidate rather than research-only.

Possible decisions:
- RETAIN_RESEARCH_ONLY
- CONTINUE_FRESH_ACCUMULATION
- APPROVE_DEMO_ALERT_ONLY_DESIGN
- REJECT_AS_OPERATIONAL_SHORT_CANDIDATE

Any Discord/demo alert activation requires explicit user approval and a separate frozen contract. MT5 orders remain prohibited unless explicitly authorized in a later stage.

## Parallel track P1 — Preserve and validate C0212 independently

C0212 remains a separate SHORT family, not a fallback or a rescue filter for C056+G013.

Reference formula:
- H4 EMA20-EMA30 >= 37.61355979 bps
- H1 ATR percentile100 >= 0.80
- M15 decision
- 240-minute fixed horizon historical reference

Evidence already obtained:
- 2023-2024 PF=1.5689385902
- 2025 PF=1.3904778450
- 2026 PF=1.5465266112
- all PF=1.4839437157
- independently rediscovered by M10M

Next work for C0212, while M10P accumulates:
1. deterministic raw-data reproduction of exact C0212
2. freeze a separate fresh prospective start only after reproduction passes
3. run an independent fresh shadow; never reuse M10P start
4. do not merge C0212 and C056+G013 before both are independently characterized

## Parallel track P2 — Continue M7C genuine source collection

M7C remains source-fidelity research only.

Do not use C056+G013 or C0212 to refit M7C.
Do not call proprietary Mochipoyo SHORT weak based on proxy results.
Continue collecting genuine XAUUSD PRIMARY_SHORT source evidence until sample size is adequate for a source-fidelity claim.

## Stage M10V — SHORT family comparison

Only after sufficient fresh evidence exists for C056+G013 and at least deterministic/fresh evidence is available for C0212.

Compare:
- C056+G013 H1 SHORT
- C0212 M15 SHORT
- any retained M5 reference only if independently justified

Measure:
- signal/trade overlap
- P&L correlation
- simultaneous exposure
- disagreement periods
- leave-one-out value
- combined PF/net/DD under raw independent arms
- combined PF/net/DD under deterministic single-capital accounting

No threshold optimization during this comparison.

## Stage M10W — Integrated LONG + SHORT portfolio reconstruction

Use frozen LONG research ledgers/references and frozen SHORT candidates. Do not reopen threshold discovery.

Required portfolio views:
1. raw simultaneous virtual arms
2. deterministic single-capital portfolio
3. opposite-direction conflict accounting
4. candidate density and exposure time
5. PF, net, DD, payoff, WR, yearly breakdown
6. actual spread and fixed-$0.20 stress
7. leave-one-out candidate value
8. P&L correlations

Keep historical portfolio reconstruction separate from prospective M10B/M10E/M10P outcomes.

## Stage M10X — Fresh integrated portfolio shadow

Only after portfolio rules are frozen.

Fresh prospective audit-only portfolio shadow with:
- new immutable start
- no historical backfill
- deterministic conflict policy
- fixed exposure/risk accounting
- no orders
- no Discord unless separately approved

This stage tests whether independently good arms still behave well together.

## Stage M10Y — Operational/demo decision

Possible next operational level, only after explicit user approval:
- alert-only / Discord-only candidate notifications
- no MT5 orders initially
- preserve shadow ledger beside alerts

Later demo order execution, and later still any live order execution, require separate explicit approvals, separate contracts, execution/slippage checks, and risk sizing rules.

## Long-term goal

The target is not merely to obtain one historical PF2 rule. The target is a reproducible portfolio in which:
- entry logic is causal
- historical and live parity is demonstrated
- fresh evidence supports each candidate
- portfolio overlap/conflict is controlled
- execution costs do not destroy the edge
- drawdown and loss tails are acceptable
- no stage is promoted automatically
