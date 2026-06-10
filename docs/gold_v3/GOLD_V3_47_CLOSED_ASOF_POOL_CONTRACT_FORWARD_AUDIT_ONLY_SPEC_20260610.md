# GOLD V3 47 closed-asof pool contract forward audit-only spec

Created JST: `2026-06-10`
Status: `GOLD_V3_47_CLOSED_ASOF_POOL_CONTRACT_FORWARD_AUDIT_SPEC_READY_AUDIT_ONLY`

## Purpose

Run a local forward audit using the frozen Stage46 contract without changing the candidate pool or gate.

Stage47 replays the current Files candle CSVs with the Stage45 closed-asof full-pool strict rolling health gate, then compares the latest replay result against the Stage46 frozen baseline.

## Non-negotiable constraints

- Do not change candidate pool.
- Do not demote or remove any high-volatility sibling profile.
- Do not use OPEN HTF asof.
- Do not use GOLD V2 / old GOLD / DISC8.
- Do not use Stage41 feature-only snapshot as trading source.
- Do not enable MT5, Discord, AI API, live hook, or final signal.
- Stage47 is audit-only monitoring, not deployment.

## Required upstream

Stage46 must be ready:

`GOLD_V3_46_CLOSED_ASOF_STAGE45_POOL_CONTRACT_FREEZE_READY_AUDIT_ONLY`

The Stage46 contract must state:

- `htf_asof = closed`
- `open_asof_allowed = false`
- full Stage45 base + HV sibling pool retained
- no manual demotion/removal
- rolling health gate:
  - window 30
  - min_history 20
  - pf_threshold 1.1
  - loss_streak_lt 3
  - virtual_monitoring true

## Stage47 behavior

1. Locate the MT5 Files directory.
2. Locate Stage46 frozen contract output.
3. Validate Stage46 contract.
4. Re-run the Stage45 closed-asof audit using the exact frozen gate parameters.
5. Write outputs into a Stage47 folder, not the Stage45 folder.
6. Compare current metrics against the Stage46 baseline.
7. Write compact PASTE_ME summary.

## Outputs

Default output folder:

`Files\FX_OUTPUTS\gold_v3\47_closed_asof_pool_contract_forward_audit_only`

Files:

- `stage47_replay/` full Stage45-style replay outputs for current Files candles
- `gold_v3_47_validation_matrix.csv`
- `gold_v3_47_metric_delta_vs_stage46_baseline.csv`
- `gold_v3_47_forward_audit_summary.json`
- `gold_v3_47_PASTE_ME_FORWARD_AUDIT_SUMMARY.txt`
- `GOLD_V3_47_CLOSED_ASOF_POOL_CONTRACT_FORWARD_AUDIT_ONLY_REPORT.md`

## PASTE_ME workflow

If upload limits are reached, paste only:

`gold_v3_47_PASTE_ME_FORWARD_AUDIT_SUMMARY.txt`

## Stop conditions

Stage47 must stop or block if:

- Stage46 contract is missing or not READY
- Stage46 allows OPEN asof
- Stage46 contract does not retain all HV profiles
- Any live/MT5/Discord/final signal flag is enabled
- Stage45 replay output is missing the strict gate experiment row
- The replay is not closed asof

## Interpretation

A PASS means the frozen contract was re-run successfully on the current local Files candles.
It does not mean live trading is approved.
