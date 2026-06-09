# GOLD V3 19 final audit shortlist human decision template audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_19_FINAL_AUDIT_SHORTLIST_HUMAN_DECISION_TEMPLATE_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 19 converts Stage 18 monthly stability results into a human decision template for the final-audit shortlist.

This stage does not approve final candidates and does not enable live behavior. It only prepares review material.

## Required upstream

```text
GOLD_V3_18_MONTHLY_STABILITY_FINAL_AUDIT_SHORTLIST_READY_AUDIT_ONLY
```

## Required inputs

```text
Files/FX_OUTPUTS/gold_v3/18_monthly_stability_final_audit_shortlist_audit_only/gold_v3_18_summary.json
Files/FX_OUTPUTS/gold_v3/18_monthly_stability_final_audit_shortlist_audit_only/gold_v3_18_scenario_stability_summary.csv
Files/FX_OUTPUTS/gold_v3/18_monthly_stability_final_audit_shortlist_audit_only/gold_v3_18_shortlist_recommendation.csv
Files/FX_OUTPUTS/gold_v3/18_monthly_stability_final_audit_shortlist_audit_only/gold_v3_18_rank_retention_review.csv
```

## Decision rows

The template includes all Stage 18 shortlist rows:

```text
TIER_1_FINAL_AUDIT_SHORTLIST
TIER_2_AUXILIARY_SHORTLIST
TIER_3_DIAGNOSTIC_ONLY
TIER_4_DROP_OR_FILTER_RESCUE_ONLY
```

Rank 7 and rank 8 must remain visible as weak diagnostic/drop-bias items.

## Allowed human decisions

```text
APPROVE_FOR_NEXT_AUDIT_ONLY_FINAL_VALIDATION
APPROVE_AS_AUXILIARY_COMPARISON_ONLY
KEEP_DIAGNOSTIC_ONLY
REQUEST_MORE_AUDIT
REQUEST_FILTER_RESCUE_AUDIT
REJECT_FROM_FINAL_AUDIT_SHORTLIST
```

`APPROVE_FOR_NEXT_AUDIT_ONLY_FINAL_VALIDATION` is still not final/live approval.

## Outputs

Output directory:

```text
Files/FX_OUTPUTS/gold_v3/19_final_audit_shortlist_human_decision_template_audit_only/
```

Required output files:

```text
gold_v3_19_summary.json
gold_v3_19_input_inventory.csv
gold_v3_19_final_audit_shortlist_packet.csv
gold_v3_19_human_decision_template.csv
gold_v3_19_decision_matrix.csv
gold_v3_19_blocker_matrix.csv
GOLD_V3_19_FINAL_AUDIT_SHORTLIST_HUMAN_DECISION_TEMPLATE_AUDIT_ONLY_REPORT.md
```

Exception runs may additionally write:

```text
gold_v3_19_exception.txt
```

ZIP output remains disabled.

## Ready status

```text
GOLD_V3_19_FINAL_AUDIT_SHORTLIST_HUMAN_DECISION_TEMPLATE_READY_AUDIT_ONLY
```

## Safety

These remain false:

```text
auto_approval
final_candidate_approval
threshold_finalization
model_training
signals_generated
zip_output_created
ai_api_called
discord_enabled
mt5_enabled
live_hook_enabled
live_evaluator_enabled
final_signal_enabled
gold_v2_live_sot_used
quarantined_legacy_artifacts_read
```

## Guardrails

- GOLD V3 only.
- No GOLD V2, old GOLD, DISC8, or quarantined legacy artifacts.
- No final candidate approval.
- No threshold finalization.
- No model training.
- No signal generation.
- No ZIP output.
- Discord, MT5, AI API, live hook, live evaluator, and final signal remain OFF.

## BAT

```text
scripts/gold_v3_runtime/bat/GOLD_V3_19_FINAL_AUDIT_SHORTLIST_HUMAN_DECISION_TEMPLATE_AUDIT_ONLY.bat
```
