# NEXT CHAT HANDOFF — BTC BCR11 final verified, BCR12 authorization pending

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- verified at: `2026-07-30T21:46:00+09:00`
- status: `BTC_REDESIGN_BCR11_COMPLETE_NO_CAUSAL_HOLDING_OVERLAY_ADVANCES_NEW_TRACK_B_FAMILY_NEXT`
- next stage: `BCR12_MATERIALLY_NEW_OUTCOME_BLIND_TRACK_B_MECHANISM_DESIGN`
- BCR12 authorization: `PENDING_EXPLICIT_USER_AUTHORIZATION`

## 1. Final handoff verification

The following handoff layers were checked together and found consistent:

1. `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. this latest dated handoff
3. `configs/btc_ml_v1/btc_candidate_research_current_state_20260730.json`
4. `configs/btc_ml_v1/btc_candidate_research_next_action_20260730.json`
5. `configs/btc_ml_v1/btc_candidate_research_handoff_policy_20260730.json`
6. `docs/btc_ml_v1/BTC_BCR11_FINITE_CAUSAL_HOLDING_OVERLAY_DEVELOPMENT_RESULT_20260730.md`
7. `configs/btc_ml_v1/btc_bcr11_finite_causal_holding_overlay_result_20260730.json`

Read-order maintenance correction:

- `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md` omitted two companion JSON files that were already present in the frozen handoff-policy read order.
- The stable entry was corrected on the authoritative branch by commit `5aa938cee2655edcb67faca7f46c8092d2c3442e`.
- The restored files are `configs/btc_ml_v1/btc_bcr11_finite_causal_holding_overlay_development_contract_20260730.json` and `configs/btc_ml_v1/btc_bcr10_holding_rollover_path_diagnostic_result_20260730.json`.
- The complete 17-file required read order was then read in order on the authoritative branch.
- This was a handoff-maintenance correction only. No BCR11 fact, status, decision, Track decision or BCR12 authorization boundary changed.

Verified facts:

- required branch is exactly `feature/btc-fresh-forward-research`;
- `main`, default branch and similar-file fallback are forbidden;
- accepted BCR11 package SHA256 is `6e10e296e57f2ba9359f29e83711acd9069944f31f9cca78ec65d6587c1299d8`;
- BCR11 contains `36` trials from six unchanged machines and six frozen overlays;
- all six baseline episode ledgers reproduce BCR09 exactly;
- non-baseline positive/PF>=1 trials are `0/0` under C0 and `0/0` under C2;
- overlay proposals advanced: `0`;
- deployable candidates: `0`;
- portfolio, prospective start and shadow: none;
- Track A and current B4 active rescue paths are closed;
- B1 remains rejected and B2 remains blocked without threshold rescue;
- BCR12 has not been contracted or implemented.

No factual correction to the BCR11 result was required. This document replaces the previous dated handoff as restart authority. Older handoffs remain `AUDIT_HISTORY_ONLY`.

## 2. Mandatory startup boundary

Read only the files listed by `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`, in the exact order and with the branch explicitly set to:

`feature/btc-fresh-forward-research`

Before completing that read order, do not perform repo-wide search, old-handoff search, code search or broad MOCHIPOYO exploration.

Do not start from:

- `main` or the default branch;
- `AGENTS.md`;
- GOLD V3, GOLD_ML_V1, GOLD V2, old GOLD, DISC8 or Stage41;
- old BTC stacking/YouTube handoffs;
- FF05 recovery V3–V11;
- any old state/action/handoff not referenced by the stable entry.

## 3. Runtime protection

Collector, M7C, M8C, M9 and M10 remain running and unchanged.

Do not stop, restart, reset, overwrite or modify them. Do not write BTC research output into GOLD/MOCHIPOYO paths. No Discord notification or MT5 order is authorized.

## 4. Frozen market and execution evidence

- BTC M15 origin: `C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_m15.csv`
- frozen BTC M15 SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- frozen rows: `30,661`
- exact symbol: `BTCUSD#`
- BID bars
- point/tick size: `0.01`
- contract size: `1.0`
- historical spread: `2250/3000` points = USD `22.50/30.00`
- KIWAMI commission: zero
- historical swap: not included; rollover results remain `PRE_SWAP_ONLY`

BCR09 C0/C2 execution and cost formulas remain authoritative.

## 5. BCR09–BCR11 result chain

### BCR09

- accepted package SHA256: `92b989ce7b0b76acab0bb6205c1d8e5cfdd9d2f86c42e74781e38177c79c45fa`
- supported: `0`
- promising: `0`
- cost-sensitive HOLD: `1`
- rejected: `7`

### BCR10

- accepted package SHA256: `99ebfeba9a83ff6eedadec35bf37cfe63e4b8dee116436d4be04c672b567d5e0`
- diagnostic only, fully outcome-exposed
- actual base exits within 16 bars were descriptive winners, not a validated max-hold rule

### BCR11

- accepted package SHA256: `6e10e296e57f2ba9359f29e83711acd9069944f31f9cca78ec65d6587c1299d8`
- tests: `4 passed`
- deterministic repeat SHA: matched
- trials: `36`
- non-baseline C0 positive / PF>=1: `0 / 0`
- non-baseline C2 positive / PF>=1: `0 / 0`
- best row remained B4 E0 baseline:
  - C0 PF `1.000623`, net `+108.97 USD / 1 lot`
  - C2 PF `0.949662`, net `-8,951.03 USD / 1 lot`

Max-hold 16 changed the state path: `24.25%–38.02%` of base episodes changed/disappeared and `108–553` new entries appeared per machine. Exact 23:45 flat also failed to create positive value. No holding/day-flat overlay advances.

## 6. Current formal decision

Preserve all completed work as audit evidence, but do not continue rescue work on the exposed Track A, B1, B2 or B4 families.

Forbidden rescue actions include:

- another max-hold threshold or server-flat time;
- TP/SL or trailing-stop search;
- entry-hour, weekday, ATR, direction or regime filters for the old families;
- threshold/formula retuning;
- portfolio selection from the exposed results.

## 7. Recommended next stage

Recommended next stage:

`BCR12_MATERIALLY_NEW_OUTCOME_BLIND_TRACK_B_MECHANISM_DESIGN`

BCR12 must be a materially new economic mechanism, not a parameter or exit variation of Track A, B1, B2 or B4. Potential design classes are:

- breakout → retest → re-acceleration;
- causal fully closed higher-timeframe regime plus M15 execution;
- directionally asymmetric LONG/SHORT mechanisms with separate economic rationale.

Before any outcome access, BCR12 must freeze:

- causal data and bar-availability boundary;
- finite grammar inventory;
- gap behavior;
- state-machine semantics;
- trial-count and multiple-testing controls;
- advancement and rejection gates.

BCR12 contract creation and implementation require explicit user authorization. Do not infer authorization merely because a new chat was opened.

## 8. User action at restart

No BAT, ZIP upload, runtime stop, prospective start or shadow action is currently required.

After completing the required read order, report:

1. the formal current status;
2. the BCR11 decision;
3. the exact next-stage authorization boundary;
4. any genuine ambiguity or conflict.

Do not begin BCR12 until the user explicitly says to proceed.
