# GOLD V3 Stage109 Spec — BASE_POLICY_SELECTION_REVIEW_PACKET_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_109_BASE_POLICY_SELECTION_REVIEW_PACKET_AUDIT_ONLY
```

## Why this stage exists

Stage108B completed and recommended base preference:

```text
status: GOLD_V3_108B_HEALTH_GATE_DELTA_REVIEW_READY_AUDIT_ONLY
decision: HEALTH_GATE_DELTA_REVIEW_READY_BASE_PREFERRED
```

Reason:

```text
skipped_trades: 280
skipped_win_rate: 58.2143%
skipped_profit_factor: 2.1331
skipped_sum_result_usd: +503.1308
```

The 107S health gate improved WR/PF slightly, but it skipped net-positive trades and reduced total sum_result_usd.

Therefore Stage109 fixes the review candidate as the 107Q base / 107S pass-through resolved ledger, not the health-gated ledger.

## Purpose

Stage109 produces the final audit-only review packet for the selected base policy.

It must:

1. Read the 107R6 resolved 107Q best-family ledger.
2. Read 107S/108/108B summaries.
3. Select `KEEP_107Q_BASE` as the review candidate.
4. Write a selected policy ledger and decision packet.
5. Keep `live_ready=false`.

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/107r6c/gold_v3_107r6_resolved_107q_best_family_ledger.csv
FX_OUTPUTS/gold_v3/107sc/gold_v3_107s_summary.json
FX_OUTPUTS/gold_v3/108c/gold_v3_108_summary.json
FX_OUTPUTS/gold_v3/108bc/gold_v3_108b_summary.json
```

Optional:

```text
FX_OUTPUTS/gold_v3/108bc/gold_v3_108b_monthly_delta.csv
FX_OUTPUTS/gold_v3/108bc/gold_v3_108b_candidate_delta_top.csv
```

## Selected candidate

```text
selected_option: KEEP_107Q_BASE
selected_policy_key: 107Q_BASE_RESOLVED_PASS_THROUGH
health_gate_adopted: false
reason: Health gate skipped net-positive trades; total sum_result_usd was higher in base.
```

## Outputs

```text
FX_OUTPUTS/gold_v3/109c/gold_v3_109_selected_base_policy_ledger.csv
FX_OUTPUTS/gold_v3/109c/gold_v3_109_selected_policy_summary.csv
FX_OUTPUTS/gold_v3/109c/gold_v3_109_base_policy_monthly_metrics.csv
FX_OUTPUTS/gold_v3/109c/gold_v3_109_base_policy_regime_metrics.csv
FX_OUTPUTS/gold_v3/109c/gold_v3_109_selection_reason_matrix.csv
FX_OUTPUTS/gold_v3/109c/gold_v3_109_quality_gate_matrix.csv
FX_OUTPUTS/gold_v3/109c/gold_v3_109_blocker_matrix.csv
FX_OUTPUTS/gold_v3/109c/gold_v3_109_validation_matrix.csv
FX_OUTPUTS/gold_v3/109c/gold_v3_109_summary.json
FX_OUTPUTS/gold_v3/109c/GOLD_V3_109_BASE_POLICY_SELECTION_REVIEW_PACKET_AUDIT_ONLY_REPORT.md
FX_OUTPUTS/gold_v3/109c/paste_me.txt
```

## Decision

Allowed decisions:

```text
BASE_POLICY_SELECTION_READY_FOR_STAGE110_AUDIT_MONITORING_DESIGN
BASE_POLICY_SELECTION_BLOCKED_INPUT_INCOMPLETE
```

## What this stage does not approve

Stage109 does not approve:

- live signal
- MT5 execution
- Discord alerts
- AI API
- live hook
- final signal
- candidate pool removal

## Guardrails

GOLD V3 remains audit-only.

Do not mutate source CSVs, CSV contract, candidate pool, Stage45 runtime, Stage69 runtime, live evaluator, live hook, final signal, Discord, MT5, or AI API.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 feature-only snapshot as a trading source.
