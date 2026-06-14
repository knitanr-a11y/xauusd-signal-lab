# GOLD V3 Stage117H Spec — 107Q_BEST_FAMILY_INPUT_COVERAGE_AUDIT

Created JST: `2026-06-15`

## Purpose

Stage117G proved that the Stage109 direct input ledger stops before June:

```text
FX_OUTPUTS/gold_v3/107r6c/gold_v3_107r6_resolved_107q_best_family_ledger.csv
```

Stage117H checks the upstream input used by the 107R6 builder:

```text
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_best_family_trade_ledger.csv
```

If 107Q best family already has June rows, then 107R6 can be regenerated from 107Q + current OHLC.

If 107Q also stops before June, the regeneration point moves further upstream to Stage107Q.

## Outputs

```text
FX_OUTPUTS/gold_v3/117h/gold_v3_117h_107q_best_family_coverage.csv
FX_OUTPUTS/gold_v3/117h/gold_v3_117h_monthly_metrics.csv
FX_OUTPUTS/gold_v3/117h/gold_v3_117h_ohlc_coverage.csv
FX_OUTPUTS/gold_v3/117h/gold_v3_117h_decision.csv
FX_OUTPUTS/gold_v3/117h/gold_v3_117h_summary.json
FX_OUTPUTS/gold_v3/117h/paste_me.txt
```

## Guardrails

This stage does not regenerate or overwrite 107Q/107R6/109c.

```text
source_csv_mutated: false
contract_mutated: false
open_asof_allowed: false
approximate_reconstruction: false
```
