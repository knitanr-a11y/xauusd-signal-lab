# GOLD SCALP DAILY / SESSION LEVEL GEOMETRY V1 — Audit

Date: 2026-08-02
Formal status: **`AUDIT_COMPLETE_NO_FORMAL_PROMOTION`**

## Causal contract

- MT5 broker-server naive timestamps; no JST conversion.
- Uploaded latest CSV rows are treated as closed.
- Signals use only completed previous-day levels and closed M5 bars.
- Entry is the next exact M1 open after confirmation.
- Standard spread is 0.30 USD once; initial SL <= 5 USD; first TP >= 5 USD.
- Candidate selection uses only older history and the immediately prior coverage-qualified block.
- Health/promotion history includes only outcomes with `exit_dt <= current entry_dt`.
- No live-ready, final signal, Shadow, Discord, MT5 order, or deployment action.

## Reproduction correction

The research was rerun against the current uploaded candle files before finalization.

- The authoritative canonical M1 union is 1,239,131 rows, not the 1,167,591-row earlier snapshot.
- The authoritative canonical M5 union is 253,557 rows.
- The report generator previously hard-coded that 2024H1 and 2024H2 were excluded. The actual coverage table excludes only 2024H1; report wording was changed to derive exclusions dynamically.
- The final research decision is unchanged: no formal candidate.

## Data audit

- Canonical M1 union: 1,239,131 rows, 2023-01-03 01:00:00 to 2026-07-31 23:56:00.
- Canonical M5 union: 253,557 rows, 2023-01-03 01:00:00 to 2026-07-31 23:50:00.
- `gold_v3` M1 had 1 appended-chunk reversal, 0 conflicting duplicate timestamps, and 1 invalid bridge row.
- Later appended M1 chunk was preferred deterministically; `goldsharp` overlap (114,032 rows) matched exactly.
- Blocks below the >=99% exact-M1 coverage gate are excluded dynamically; `m1_exact_coverage_by_block.csv` records 2024H1 as the only excluded block.
- M5 all-history results are descriptive sensitivity only, never a replacement for exact M1.

## Preregistered families

1. Previous-day high/low sweep and close-back.
2. Fixed server-hour opening-range expansion and first retest.
3. Daily reopen gap hold and continuation (not gap-fill/reclaim).

## V19 / Challenger independence

The research does not read or calculate V19 E40 scores, P90 ranks, `IMPULSE_EARLY`, V19 episodes, Challenger C1 `IMPULSE_LATE` / `CORRECTION_EARLY`, `chosen_rank`, V19 priority, or preemption. It uses fixed daily/session price levels and closed-M5 confirmations only.

## Separated exact-M1 stages

- CATALOG — RAW_SELECTED_EXACT_M1: n=10, WR=30.00% PF=0.5357 Net=-13.00 DD=13.75
- CATALOG — GLOBAL_DEDUP_EXACT_M1: n=10, WR=30.00% PF=0.5357 Net=-13.00 DD=13.75
- CATALOG — HEALTH_GATE_1_PRIOR_POSITIVE_BLOCK: n=0
- CATALOG — HEALTH_GATE_2_PRIOR_POSITIVE_BLOCKS: n=0
- CATALOG — RESOLVED_ONLY_LIVE_REPLAY_1BLOCK: n=0
- BALANCED — RAW_SELECTED_EXACT_M1: n=0
- BALANCED — GLOBAL_DEDUP_EXACT_M1: n=0
- BALANCED — HEALTH_GATE_1_PRIOR_POSITIVE_BLOCK: n=0
- BALANCED — HEALTH_GATE_2_PRIOR_POSITIVE_BLOCKS: n=0
- BALANCED — RESOLVED_ONLY_LIVE_REPLAY_1BLOCK: n=0

The only selected target engine was `OR01_ORH_E1_T0.25_R0.25_STRONG` with `P50_TP5_TP7P5_SL4_H180` for 2026H1. It lost in the frozen target block.

## Observation decision

- No engine + fixed exit policy achieved two positive pseudo-forward target blocks with positive aggregate exact-M1 performance.

## Post-result sparse trace

The strongest row found only after all engine tables were inspected was `GAP_HOLD_CONT_G1_H0.5_UP_BASE` with `P67_TP5_TP10_SL5_H240`.

- exact M1: 21 trades, WR 80.95%, PF 3.8948, net +57.90 USD, DD 5.00 USD;
- conservative M5: 22 trades, WR 81.82%, PF 3.7282, net +54.56 USD;
- 13 of 21 exact trades occurred in 2026H1;
- LONG only and median zero trades per month;
- never selected by the strict pseudo-forward gate.

It is retained only as `POST_RESULT_DESCRIPTIVE_TRACE_NOT_RETAINED` and is not a candidate.

## Decision

- No formal portfolio or deployment authorization.
- No historical hour/month/volatility deletion was used.
- V19, Challenger C1, P75 State Survival Shadow, the unified registry, Discord, and MT5 remain unchanged.
- No result from this research may be promoted by deleting the losing side, month, session, hour, or volatility band.
