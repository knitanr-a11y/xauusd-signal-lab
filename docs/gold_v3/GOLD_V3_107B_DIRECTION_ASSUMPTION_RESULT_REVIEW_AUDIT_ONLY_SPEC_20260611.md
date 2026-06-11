# GOLD V3 Stage107B Spec — DIRECTION_ASSUMPTION_RESULT_REVIEW_AUDIT_ONLY

Created JST: `2026-06-11`

Repo: `knitanr-a11y/xauusd-signal-lab`

Stage:

```text
GOLD_V3_107B_DIRECTION_ASSUMPTION_RESULT_REVIEW_AUDIT_ONLY
```

## Purpose

Stage107B reviews Stage107 results on the same trading-decision surfaces used by Stage45:

1. raw all opportunities
2. rank dedup no HV
3. rank dedup plus HV siblings
4. strict rolling health gate no HV
5. strict rolling health gate plus HV siblings

Each surface must be compared for LONG proxy and SHORT proxy, including monthly and high-volatility segmentation.

This stage exists because Stage107 `paste_me.txt` reports raw all-opportunity side metrics, while the user had been looking mainly at strict rolling health gate plus HV siblings style metrics. Those are different populations and must not be mixed.

## Guardrails

GOLD V3 remains audit-only.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 as a trading source.

Do not mutate source CSVs, CSV contract, candidate pool, Stage45 runtime behavior, Stage69 runtime behavior, live evaluator, final signal, Discord, MT5 execution, or AI API.

CSV contract:

```text
open/in-progress candles are not written to CSV
CSV latest row is contractually closed
open/as-of treatment is forbidden
```

Pool policy:

```text
poolから外さない。rolling health gateに判断させる。
```

## Inputs

Stage107B reads only Stage107 outputs under the MT5 Files output tree:

```text
FX_OUTPUTS/gold_v3/107c/gold_v3_107_long_short_proxy_ledger.csv
FX_OUTPUTS/gold_v3/107c/gold_v3_107_rebuilt_stage45_69_opportunities.csv
FX_OUTPUTS/gold_v3/107c/gold_v3_107_direction_assumption_summary.json
```

The primary input is `gold_v3_107_long_short_proxy_ledger.csv`.

Stage107B does not rebuild candidates and does not re-read broad MQL5/Files contents.

## Method

Replicate Stage45 decision surfaces from the Stage107 proxy ledger.

For each proxy side independently:

- raw all opportunities: all evaluated rows for the side;
- rank dedup no HV: exclude `hv_sibling=True`, then choose first row per `entry_dt` sorted by `entry_dt`, `priority`, `candidate_label`;
- rank dedup plus HV siblings: include all rows, then choose first row per `entry_dt` sorted by `entry_dt`, `priority`, `candidate_label`;
- strict rolling health gate no HV: exclude `hv_sibling=True`, then mirror Stage45 rolling health gate;
- strict rolling health gate plus HV siblings: include all rows and mirror Stage45 rolling health gate.

Default health gate parameters:

```text
window = 30
min_history = 20
pf_threshold = 1.10
loss_streak_lt = 3
```

The health gate must update candidate history from all candidate rows at each entry time, matching Stage45 behavior, not only from the selected row.

## Required review cuts

Stage107B must produce at least:

- comparable LONG vs SHORT strategy-surface summary;
- monthly summary by surface and side;
- high-volatility segmentation by `is_high_vol` where available;
- HV-named vs normal segmentation by `hv_sibling`;
- recent month focus, especially 2026-05 and 2026-06;
- a finding explaining whether the 65% style result was a health-gated selected-surface result rather than raw opportunity strength.

## Outputs

Implementation paths:

```text
docs/gold_v3/GOLD_V3_107B_DIRECTION_ASSUMPTION_RESULT_REVIEW_AUDIT_ONLY_SPEC_20260611.md
scripts/gold_v3_runtime/gold_v3_107b_direction_assumption_result_review_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_107b_direction_assumption_result_review.bat
```

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107bc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107bc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107b_surface_side_summary.csv
gold_v3_107b_surface_monthly_summary.csv
gold_v3_107b_surface_hv_segmentation.csv
gold_v3_107b_surface_selected_trade_ledger.csv
gold_v3_107b_blocker_matrix.csv
gold_v3_107b_validation_matrix.csv
gold_v3_107b_direction_result_review_summary.json
GOLD_V3_107B_DIRECTION_ASSUMPTION_RESULT_REVIEW_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107B_DIRECTION_ASSUMPTION_RESULT_REVIEW_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107B_DIRECTION_ASSUMPTION_RESULT_REVIEW_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```

Even when BLOCKED, Stage107B must write `FX_OUTPUTS/gold_v3/107bc/paste_me.txt`.
