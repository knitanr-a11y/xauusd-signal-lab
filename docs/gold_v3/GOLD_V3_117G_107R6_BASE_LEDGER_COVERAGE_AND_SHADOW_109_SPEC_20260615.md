# GOLD V3 Stage117G Spec — 107R6_BASE_LEDGER_COVERAGE_AND_SHADOW_109

Created JST: `2026-06-15`

## Purpose

Stage117F found that Stage109 directly writes 109c from:

```text
FX_OUTPUTS/gold_v3/107r6c/gold_v3_107r6_resolved_107q_best_family_ledger.csv
```

Stage117G checks whether that exact 107R6 base ledger has June coverage.

If it does, Stage117G creates a shadow 109 output under `117g`, not under `109c`.

## Inputs

```text
FX_OUTPUTS/gold_v3/107r6c/gold_v3_107r6_resolved_107q_best_family_ledger.csv
FX_OUTPUTS/gold_v3/107sc/gold_v3_107s_summary.json
FX_OUTPUTS/gold_v3/108c/gold_v3_108_summary.json
FX_OUTPUTS/gold_v3/108bc/gold_v3_108b_summary.json
```

## Outputs

```text
FX_OUTPUTS/gold_v3/117g/gold_v3_117g_107r6_base_ledger_coverage.csv
FX_OUTPUTS/gold_v3/117g/gold_v3_117g_shadow_109_selected_base_policy_ledger.csv
FX_OUTPUTS/gold_v3/117g/gold_v3_117g_monthly_metrics.csv
FX_OUTPUTS/gold_v3/117g/gold_v3_117g_decision.csv
FX_OUTPUTS/gold_v3/117g/gold_v3_117g_summary.json
FX_OUTPUTS/gold_v3/117g/paste_me.txt
```

## Guardrails

This stage does not overwrite `109c`.

```text
source_csv_mutated: false
contract_mutated: false
open_asof_allowed: false
approximate_reconstruction: false
```
