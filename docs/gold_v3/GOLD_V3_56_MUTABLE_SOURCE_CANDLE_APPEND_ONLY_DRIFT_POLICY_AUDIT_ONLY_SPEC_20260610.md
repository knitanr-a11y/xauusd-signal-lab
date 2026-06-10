# GOLD V3 56 mutable source candle append-only drift policy audit-only spec

Created JST: `2026-06-10`
Status: `GOLD_V3_56_MUTABLE_SOURCE_CANDLE_APPEND_ONLY_DRIFT_POLICY_SPEC_READY_AUDIT_ONLY`

## Purpose

Classify Stage55 checkpoint dry-run BLOCKED causes into:

1. mutable source candle drift
2. immutable state artifact drift
3. source rewrite/truncation blockers

Stage56 is a policy classification layer only. It does **not** mark Stage55 strict replay as READY, does **not** refresh checkpoints, and does **not** enable live trading.

## Background

Stage55 intentionally performs strict hash/row-count checking against Stage54 checkpoint artifacts. Source candle files such as `goldsharp_m5.csv`, `goldsharp_m15.csv`, and `goldsharp_h4.csv` are mutable because MT5 continues appending new rows. Therefore, a later Stage55 run may correctly BLOCK if a source candle gained rows after checkpoint creation.

Stage56 records whether the BLOCK is caused only by a mutable source candle row increase, while all immutable state artifacts remain stable.

## Required upstream artifacts

- Stage55 replay dry-run summary
- Stage55 hash recheck CSV
- Stage55 hash mismatch details CSV
- Stage55 validation matrix

## Non-negotiable safety boundaries

- GOLD V3 remains audit-only.
- No MT5 orders.
- No MT5 execution BAT.
- No Discord live notification.
- No AI API call.
- No live hook.
- No final signal.
- No candidate pool mutation.
- No high-vol profile demotion/removal.
- No GOLD V2 / old GOLD / DISC8.
- No Stage41 feature-only trading source.

## Policy rules

Artifact roles:

- `mutable_source_candle`
  - `m5_csv`
  - `m15_csv`
  - `h4_csv`
- `immutable_state_artifact`
  - all Stage49-55 output artifacts

Classification:

- `STABLE_OK`: hash and row count match.
- `MUTABLE_SOURCE_ADVANCED_APPEND_LIKELY`: mutable source candle row count increased and hash changed.
- `MUTABLE_SOURCE_REWRITE_BLOCKER`: mutable source candle row count unchanged but hash changed.
- `MUTABLE_SOURCE_TRUNCATION_BLOCKER`: mutable source candle row count decreased.
- `IMMUTABLE_STATE_DRIFT_BLOCKER`: immutable state artifact hash or row count changed.
- `MISSING_ARTIFACT_BLOCKER`: expected artifact no longer exists.

Important: `MUTABLE_SOURCE_ADVANCED_APPEND_LIKELY` is not proof of byte-level append-only because Stage54 did not store prefix hashes. It only means row-count movement is consistent with source-candle advancement and not with state artifact corruption.

## Outputs

Default output folder:

`Files\\FX_OUTPUTS\\gold_v3\\56_mutable_source_candle_append_only_drift_policy_audit_only`

Files:

- `gold_v3_56_drift_policy_matrix.csv`
- `gold_v3_56_validation_matrix.csv`
- `gold_v3_56_policy_summary.json`
- `gold_v3_56_PASTE_ME_DRIFT_POLICY_SUMMARY.txt`
- `GOLD_V3_56_REPORT.md`

## Success condition

Stage56 READY means:

- Stage55 BLOCKED cause is classified.
- No immutable state artifact drift exists.
- No source candle rewrite/truncation blocker exists.
- Any mutable source candle mismatch is row-count-increase only.
- Strict Stage55 replay remains not-ready until checkpoint refresh or a replay range freeze is explicitly performed.

## Next stage

Stage57 should perform a bounded replay-window or checkpoint-refresh decision template, still audit-only and without enabling live trading.
