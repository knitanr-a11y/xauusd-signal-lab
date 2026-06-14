# GOLD V3 Stage108 Spec — RESOLVED_ONLY_STAGE_REVIEW_PACKET_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_108_RESOLVED_ONLY_STAGE_REVIEW_PACKET_AUDIT_ONLY
```

## Why this stage exists

Stage107S completed a strict resolved-only health gate replay on the 107Q best-family ledger.

Key 107S result:

```text
status: GOLD_V3_107S_RESOLVED_ONLY_HEALTH_GATE_REPLAY_READY_AUDIT_ONLY
decision: RESOLVED_ONLY_HEALTH_GATE_PRIMARY_READY_FOR_STAGE108_REVIEW
resolved_only_strict: true
exit_dt_used_as_entry_feature: false
best_policy_key: candidate_pf_gate||W50||N5||PF1.5
base_rows: 5571
best_health_trades: 5291
best_retention: 94.97%
base WR: 63.7229%
best WR: 64.0144%
base PF: 3.1290
best PF: 3.1840
base sum_result_usd: 18065.7484
best sum_result_usd: 17562.6176
```

107S passes primary because WR/PF improved with high retention and zero negative months. However, the improvement is small and total sum_result_usd decreased because 280 trades were skipped.

Therefore Stage108 is a review packet, not live approval.

## Purpose

Stage108 prepares a human-readable audit-only decision packet comparing:

1. 107Q / 107S pass-through baseline
2. 107S best resolved-only health gate

It should make the tradeoff explicit:

```text
Health gate improves WR/PF slightly.
Health gate reduces trade count and total sum_result_usd.
Health gate is strict resolved-only.
No live readiness is granted.
```

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/107sc/gold_v3_107s_summary.json
FX_OUTPUTS/gold_v3/107sc/gold_v3_107s_health_policy_summary.csv
FX_OUTPUTS/gold_v3/107sc/gold_v3_107s_base_monthly_metrics.csv
FX_OUTPUTS/gold_v3/107sc/gold_v3_107s_best_monthly_metrics.csv
FX_OUTPUTS/gold_v3/107sc/gold_v3_107s_best_regime_metrics.csv
```

Optional:

```text
FX_OUTPUTS/gold_v3/107r6c/gold_v3_107r6_join_coverage_matrix.csv
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_summary.json
```

## Outputs

```text
FX_OUTPUTS/gold_v3/108c/gold_v3_108_decision_review_summary.csv
FX_OUTPUTS/gold_v3/108c/gold_v3_108_adoption_options.csv
FX_OUTPUTS/gold_v3/108c/gold_v3_108_monthly_diff.csv
FX_OUTPUTS/gold_v3/108c/gold_v3_108_regime_review.csv
FX_OUTPUTS/gold_v3/108c/gold_v3_108_human_decision_template.md
FX_OUTPUTS/gold_v3/108c/gold_v3_108_quality_gate_matrix.csv
FX_OUTPUTS/gold_v3/108c/gold_v3_108_blocker_matrix.csv
FX_OUTPUTS/gold_v3/108c/gold_v3_108_validation_matrix.csv
FX_OUTPUTS/gold_v3/108c/gold_v3_108_summary.json
FX_OUTPUTS/gold_v3/108c/GOLD_V3_108_RESOLVED_ONLY_STAGE_REVIEW_PACKET_AUDIT_ONLY_REPORT.md
FX_OUTPUTS/gold_v3/108c/paste_me.txt
```

## Review questions

Stage108 must answer:

1. Did resolved-only health gate improve WR/PF?
2. Did it retain enough trades?
3. Did it keep min regime WR above 60%?
4. Did it avoid negative months?
5. How much sum_result_usd was sacrificed?
6. Should the next stage test health-gated candidate or keep base candidate?

## Allowed decisions

```text
STAGE108_REVIEW_PACKET_READY_HEALTH_GATE_CANDIDATE
STAGE108_REVIEW_PACKET_READY_BASE_107Q_CANDIDATE
STAGE108_REVIEW_PACKET_READY_HUMAN_DECISION_REQUIRED
STAGE108_BLOCKED_INPUT_INCOMPLETE
```

## Stage108 recommendation rule

If health gate passes primary but sum_result_usd decreases, Stage108 should not auto-approve it.

It should output:

```text
STAGE108_REVIEW_PACKET_READY_HUMAN_DECISION_REQUIRED
```

unless a later explicit rule prioritizes WR/PF over total sum.

## Guardrails

GOLD V3 remains audit-only.

Do not mutate source CSVs, CSV contract, candidate pool, Stage45 runtime, Stage69 runtime, live evaluator, live hook, final signal, Discord, MT5, or AI API.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 feature-only snapshot as a trading source.
