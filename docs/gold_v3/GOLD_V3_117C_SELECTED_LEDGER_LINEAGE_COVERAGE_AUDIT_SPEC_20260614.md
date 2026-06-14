# GOLD V3 Stage117C Spec — SELECTED_LEDGER_LINEAGE_COVERAGE_AUDIT

Created JST: `2026-06-14`

## Purpose

Stage117B showed that the selected ledger ends before June while M15 OHLC contains June data.

Stage117C scans GOLD V3 output CSVs and identifies whether any upstream GOLD V3 ledger has June rows.

It does not reconstruct any detector.

## Scope

Only `FX_OUTPUTS/gold_v3` is scanned.

Files are treated as candidate trade ledgers only when they contain an `entry_dt`-like column.

## Key questions

```text
1. Does 109c selected ledger stop at 2026-05-29?
2. Do upstream GOLD V3 ledgers contain June rows?
3. If upstream June rows exist, which files contain them?
4. If no upstream June rows exist, source trade ledger rehydration is required before live signal bridge can emit June signals.
```

## Outputs

```text
FX_OUTPUTS/gold_v3/117c/gold_v3_117c_all_entrydt_csv_coverage.csv
FX_OUTPUTS/gold_v3/117c/gold_v3_117c_june_capable_sources.csv
FX_OUTPUTS/gold_v3/117c/gold_v3_117c_selected_key_overlap.csv
FX_OUTPUTS/gold_v3/117c/gold_v3_117c_decision.csv
FX_OUTPUTS/gold_v3/117c/gold_v3_117c_summary.json
FX_OUTPUTS/gold_v3/117c/paste_me.txt
```

## Guardrails

```text
source_csv_mutated: false
contract_mutated: false
open_asof_allowed: false
approximate_reconstruction: false
```
