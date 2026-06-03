# GOLD V2 Core/Tier2 audit-only evaluator

Created: 2026-06-03
Status: audit-only / no live integration

## Purpose

Evaluate the currently selected practical GOLD V2 policy without AI, Discord, or MT5 order execution.

```text
Core / HIGH:
  fold4_rules + ABC entry gate + CAP5 sizing

Tier2 / MEDIUM:
  Core REJECT only
  trend_eff96 <= 0.4
  ret96 <= -25
  CAP3 sizing
```

## Added files

```text
scripts/gold_v2_runtime/evaluate_gold_v2_core_tier2_audit_only.py
scripts/gold_v2_runtime/bat/01_RUN_CORE_TIER2_AUDIT_ONLY.bat
```

## Required inputs

The evaluator expects the prior stack-cap validation outputs under:

```text
Files\FX_OUTPUTS\gold_v2_ABC_stack_cap_2025_2026_validation_outputs\
```

Required CSVs:

```text
abc_stack_cap_2025_fold4_cluster_ledger.csv
abc_stack_cap_2026_cluster_ledger.csv
```

These inputs are candidate-cluster ledgers, not raw MT5 candle files.

## Outputs

Default output directory:

```text
Files\FX_OUTPUTS\gold_v2_core_tier2_audit_only\
```

Output files:

```text
core_tier2_portfolio_ledger.csv
core_tier2_aggregate_summary.csv
core_tier2_monthly_summary.csv
core_tier2_signal_breakdown.csv
core_tier2_input_audit.csv
core_tier2_summary.json
GOLD_V2_CORE_TIER2_AUDIT_ONLY_REPORT.md
```

## Important status

This is not runtime approval. It is only a deterministic evaluator for the frozen Core/Tier2 policy.

Before Discord/MT5 integration, run the evaluator and compare:

```text
Core only
Tier2 only
Core + Tier2
monthly performance
HIGH/MEDIUM priority breakdown
```

## Current recommended policy from prior probe

```text
Core:
  fold4_rules + ABC + CAP5
  priority = HIGH

Tier2:
  trend_eff96 <= 0.4 AND ret96 <= -25
  priority = MEDIUM
  sizing = CAP3
```

Unlimited stacking remains rejected.
