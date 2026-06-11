# GOLD V3 Stage107 Spec — NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_ONLY

Created JST: `2026-06-11`

Repo: `knitanr-a11y/xauusd-signal-lab`

Stage:

```text
GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_ONLY
```

## Guardrails

GOLD V3 remains audit-only.

Absolute prohibitions:

- Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 feature-only snapshot as a trading source.
- Do not enable Discord, MT5 execution, AI API, live hook, live evaluator, or final signal.
- Do not mutate source CSVs, CSV contract, candidate pool, Stage45 runtime behavior, or Stage69 runtime behavior.
- Do not remove or demote candidates from the candidate pool.
- Do not promote proxy results into runtime.
- Do not treat the CSV latest row as open/as-of.

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

## Source-of-truth contract

Stage107 candidate source-of-truth is not Stage99-106 CSV output.

Stage107 must rebuild candidates audit-only from GOLD V3 code:

```text
scripts/gold_v3_runtime/gold_v3_45_high_vol_sibling_strict_gate_walkforward_audit.py
scripts/gold_v3_runtime/gold_v3_69_live_csv_condition_detector_audit.py
```

Stage45 provides:

```text
prepare(cdir, "closed", 60, 0.70)
base_candidates()
add_hv_siblings(base_candidates())
source_rows(m15)
opportunities(m15, candidates)
```

Stage69 provides the q70 alignment contract and candidate key logic:

```text
merge Stage50 m15_time_jst to m15.time
set m15_atr28_q = atr28_q70
set is_high_vol = high_vol_pass
horizon_m5_bars = horizon_m15 * 3
```

Stage99-106 outputs are recap/evidence only, not Stage107 candidate source-of-truth.

## Exact input files

Read exact live candle CSV names only from the user's MT5 Files directory:

```text
goldsharp_m5.csv
goldsharp_m15.csv
goldsharp_h4.csv
```

Do not broadly scan the MT5 Files directory.

Read exact GOLD V3 audit artifacts only as required by Stage69/Stage107:

```text
FX_OUTPUTS/gold_v3/50_h4_closed_readiness_and_prior_60d_q70_state_builder_audit_only/gold_v3_50_rolling_prior_60d_q70_state.csv
FX_OUTPUTS/gold_v3/68_rank_dedup_selection_repro_audit_only/gold_v3_68_rank_dedup_selection_repro_summary.json
FX_OUTPUTS/gold_v3/51_full_candidate_virtual_opportunity_ledger_builder_audit_only/gold_v3_51_virtual_opportunity_ledger.csv
```

## Entry and profile fields

Use Stage45 opportunity columns:

```text
entry_dt
entry_price
tp_usd
sl_usd
horizon_m15
profile_id
```

Do not reinterpret `TP180` as `18.0`. Current GOLD V3 code uses:

```text
tp_usd = 180.0
sl_usd = 70.0
```

`H128` means 128 M15 bars. M5 horizon is:

```text
horizon_m5_bars = horizon_m15 * 3
```

## Direction audit

Current Stage45 evaluation is LONG-style:

```text
TP = entry + tp_usd
SL = entry - sl_usd
```

Stage107 must compare that with SHORT proxy:

```text
TP = entry - tp_usd
SL = entry + sl_usd
```

If TP and SL hit in the same M5 bar, SL wins.

Scan for any side/direction-like column. If absent, report critical directionless LONG-style evaluation finding.

## Implementation/output protocol

Use only these implementation paths:

```text
docs/gold_v3/GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_ONLY_SPEC_20260611.md
scripts/gold_v3_runtime/gold_v3_107_normal_and_hv_direction_assumption_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_107_normal_and_hv_direction_assumption.bat
```

Runtime outputs must be generated under:

```text
FX_OUTPUTS/gold_v3/107c/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107c/paste_me.txt
```

User should paste back only `paste_me.txt` for ordinary continuation.

Detailed CSV/JSON/report artifacts may be created in the same `107c` directory, but they are not the continuation interface.

## Expected detailed outputs

```text
paste_me.txt
gold_v3_107_rebuilt_stage45_69_opportunities.csv
gold_v3_107_long_short_proxy_ledger.csv
gold_v3_107_per_candidate_long_short_metrics.csv
gold_v3_107_side_summary.csv
gold_v3_107_segment_jst_hour_metrics.csv
gold_v3_107_segment_jst_weekday_metrics.csv
gold_v3_107_segment_h4_bucket_metrics.csv
gold_v3_107_blocker_matrix.csv
gold_v3_107_validation_matrix.csv
gold_v3_107_direction_assumption_summary.json
GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_ONLY_REPORT.md
```

`paste_me.txt` must include at minimum:

```text
status
ready boolean
live_ready: false
source_csv_mutated: false
contract_mutated: false
manual_candidate_demotion_or_removal: false
open_asof_allowed: false
csv_contract
csv_open_bar_exclusion_required: false
safety flags
pool_policy
key metrics
blocker_count
BLOCKERS section
VALIDATION section
OUTPUTS section
```

## Success condition

Ready status:

```text
GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_READY_AUDIT_ONLY
```

## Blocked condition

Official Stage107 blocked status:

```text
GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```

Do not use the old ambiguous blocked status:

```text
BLOCKED_INPUT_INCOMPLETE_AUDIT_ARTIFACTS_WRITTEN
```

Even when BLOCKED, Stage107 must always write:

```text
FX_OUTPUTS/gold_v3/107c/paste_me.txt
```

## Explicit non-goals

Stage107 does not:

- change runtime logic;
- change Stage45 or Stage69 behavior;
- remove or demote any candidate;
- select a new production side;
- approve HV sibling repair;
- resolve the JST-vs-MT5/CSV basis issue;
- enable live evaluator or final signal.
