# GOLD V3 Stage117D Spec — UPSTREAM_JUNE_REGEN_CANDIDATE_AUDIT

Created JST: `2026-06-15`

## Purpose

Stage117C found upstream GOLD V3 sources with June rows and selected-key overlap.

Stage117D tests whether those upstream sources can reproduce the already-selected 109c ledger during May, then extracts June extension candidates from sources that pass the parity check.

## Method

No detector is reconstructed.

For each June-capable upstream CSV from Stage117C:

```text
1. detect candidate key column
2. filter rows whose key exists in 109c selected ledger keys
3. compare May selected entry_dt coverage against 109c selected May rows
4. write June extension candidate rows only when exact-key filtering is available
```

## Inputs

```text
FX_OUTPUTS/gold_v3/109c/gold_v3_109_selected_base_policy_ledger.csv
FX_OUTPUTS/gold_v3/117c/gold_v3_117c_june_capable_sources.csv
```

## Outputs

```text
FX_OUTPUTS/gold_v3/117d/gold_v3_117d_source_parity_matrix.csv
FX_OUTPUTS/gold_v3/117d/gold_v3_117d_june_extension_candidates.csv
FX_OUTPUTS/gold_v3/117d/gold_v3_117d_decision.csv
FX_OUTPUTS/gold_v3/117d/gold_v3_117d_summary.json
FX_OUTPUTS/gold_v3/117d/paste_me.txt
```

## Guardrails

```text
source_csv_mutated: false
contract_mutated: false
open_asof_allowed: false
approximate_reconstruction: false
```
