# NEXT CHAT HANDOFF — BTC BCR12 B3 contract frozen, BCR13 authorization pending

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- verified at: `2026-07-30T21:57:00+09:00`
- status: `BTC_REDESIGN_BCR12_B3_BREAKOUT_RETEST_REACCELERATION_CONTRACT_FROZEN_BCR13_AUTHORIZATION_PENDING`
- next stage: `BCR13_B3_OUTCOME_BLIND_DENSITY_AND_STATE_MACHINE_AUDIT`
- BCR13 authorization: `PENDING_EXPLICIT_USER_AUTHORIZATION`

## 1. What changed in BCR12

The user explicitly authorized continuation after the BCR11 restart review. BCR12 froze a materially new Track B mechanism contract only.

Frozen family:

`B3_BREAKOUT_RETEST_REACCELERATION`

Authoritative contract files:

1. `docs/btc_ml_v1/BTC_BCR12_MATERIALLY_NEW_OUTCOME_BLIND_TRACK_B_MECHANISM_DESIGN_CONTRACT_20260730.md`
2. `configs/btc_ml_v1/btc_bcr12_materially_new_outcome_blind_track_b_mechanism_design_contract_20260730.json`

Contract commits:

- Markdown: `b9ab8decdbb9be3e09822d92ce1c270a86a39918`
- JSON: `0232261adfddfaa4bc7e79c748838387374aabf2`

No B3 return, win/loss, PF, MFE, MAE or future-exit outcome was opened. No implementation, BAT, package or runtime was created.

## 2. Exact B3 family

The economic mechanism is:

1. a fully closed M15 bar breaks a prior exact structural range;
2. price later retests the frozen broken level without closing through the invalidation zone;
3. a later fully closed bar re-accelerates beyond the post-retest local extreme;
4. entry is scheduled only for the next exact M15 open.

The finite grammar is exactly:

- lookback `L ∈ {32, 64}`;
- breakout displacement `D ∈ {0.25, 0.50}` frozen pre-break ATR;
- first-retest deadline `W ∈ {4, 8}` theoretical M15 bars;
- fixed retest, invalidation and re-acceleration constants;
- eight machines total;
- LONG and SHORT evaluated symmetrically inside every machine.

No ninth machine, side deletion, threshold rescue or result-driven parameter may be added.

## 3. Causal and live-reproduction boundary

At decision boundary `t`, B3 may use only the exact fully closed M15 bar at `t-15m` and earlier exact closed bars. The current bar high, low and close are forbidden. The current exact open may be used only as an execution observation after the signal has already been fixed from closed history.

- latest CSV row remains contractually closed;
- no future bar or future exit result;
- no nearest, next, interpolation or synthetic fallback;
- a gap between breakout and entry cancels the setup;
- no H1/H4/D1 data in BCR12;
- no source labels or M7C state in B3 trading logic;
- all machines initialize `IDLE` and hold at most one position.

## 4. Exposure classification

B3 formulas are frozen before any B3 outcome is opened, so the B3 mechanism is outcome-unopened at contract time.

However, the broader BTC history has been exposed through earlier Track A/B1/B4 work. Therefore any later B3 historical value result must be described as retrospective and not independent OOS evidence.

BCR09-BCR11 outcomes were not used to add an hour, weekday, ATR, direction, regime, holding-time or rollover filter to B3.

## 5. BCR11 decision remains unchanged

- accepted BCR11 package SHA256: `6e10e296e57f2ba9359f29e83711acd9069944f31f9cca78ec65d6587c1299d8`
- trials: `36`
- non-baseline C0 positive / PF>=1: `0 / 0`
- non-baseline C2 positive / PF>=1: `0 / 0`
- advanced overlays: `0`
- deployable candidates: `0`
- Track A and B4 active rescue paths: closed
- B1: rejected
- B2: blocked without threshold rescue
- portfolio, prospective start and shadow: none

BCR12 is not a rescue continuation of those families.

## 6. Recommended next stage

Recommended next stage:

`BCR13_B3_OUTCOME_BLIND_DENSITY_AND_STATE_MACHINE_AUDIT`

BCR13 may inspect only label-free capability facts:

- breakout/retest/re-acceleration and transition counts;
- closed episodes and direction counts;
- months, concentration, holding and occupancy;
- gaps, missing exact entries and state integrity;
- timestamp overlap without PnL;
- deterministic repeat SHA.

The capability thresholds reuse BCR07 unchanged:

- at least 50 closed episodes total;
- at least 20 per direction;
- at least six entry months;
- no month above 35%;
- p90 holding at most 384 bars;
- maximum holding at most 1500 bars;
- at most one endpoint-open episode;
- no fallback or state-integrity failure.

All eight machines must be reported. Failed machines may not be rescued by loosening the grammar.

## 7. Authorization boundary

BCR13 is not yet authorized.

The current user authorization completed BCR12 contract creation. It does not automatically authorize:

- BCR13 code, tests or density run;
- BCR14 PnL/value evaluation;
- historical result filters or portfolio selection;
- prospective start or shadow;
- Discord, MT5 order, final signal or live-ready status.

Wait for an explicit instruction to proceed with BCR13.

## 8. Runtime protection

Collector, M7C, M8C, M9 and M10 remain running and unchanged.

Do not stop, restart, reset or modify them. Do not write BTC research output into GOLD/MOCHIPOYO paths.

## 9. Startup instructions

Read the exact files listed by `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`, in order, with the ref explicitly set to:

`feature/btc-fresh-forward-research`

Before completing that order, do not perform repo-wide search, code search, old-handoff search or broad MOCHIPOYO exploration.

Do not use `main`, the default branch, `AGENTS.md`, GOLD documents, old BTC stacking/YouTube handoffs, FF05 recovery V3-V11 or unreferenced old state/action/handoff as restart authority.

## 10. Current formal decision

`FREEZE_BCR12_B3_BREAKOUT_RETEST_REACCELERATION_FAMILY_NO_OUTCOME_OPENED_NO_IMPLEMENTATION`

No candidate is promoted. The next action is to await explicit user authorization for BCR13.