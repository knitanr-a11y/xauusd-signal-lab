# GOLD V3 Stage100 — NO_SIGNAL Reason Breakdown Audit-Only Spec

Created JST: `2026-06-11`

Stage name:

`GOLD_V3_100_NO_SIGNAL_REASON_BREAKDOWN_AUDIT_ONLY`

READY status:

`GOLD_V3_100_NO_SIGNAL_REASON_BREAKDOWN_READY_AUDIT_ONLY`

## Purpose

Diagnose why Stage99 recent closed-candle replay produced NO_SIGNAL for every replay point.

This stage does not replay candles again. It reads Stage99 replay artifacts and summarizes:

- whether Stage69 condition candidates were produced,
- whether Stage70 health gate removed all candidates,
- `no_signal_reason`,
- candidate labels seen before health gating,
- health gate reasons.

## Inputs

- `FX_OUTPUTS/gold_v3/99c/summary.json`
- `FX_OUTPUTS/gold_v3/99c/replay_results.csv`
- replay directories referenced by `replay_results.csv`

Each replay directory is expected to contain Stage69/70 outputs under:

- `FX_OUTPUTS/gold_v3/69_live_csv_condition_detector_audit_only/`
- `FX_OUTPUTS/gold_v3/70_live_csv_signal_decision_preview_audit_only/`

## Outputs

Folder:

`FX_OUTPUTS/gold_v3/100c/`

Files:

- `paste_me.txt`
- `summary.json`
- `no_signal_breakdown.csv`
- `candidate_label_counts.csv`
- `health_gate_reason_counts.csv`
- `validation.csv`
- `blockers.csv`
- `report.md`

## Safety

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, final signal, source CSV mutation, or candidate pool mutation.
