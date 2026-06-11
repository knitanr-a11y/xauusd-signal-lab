# NEXT CHAT HANDOFF — GOLD V3 99-106 DONE / 107 NEXT

Created JST: `2026-06-11`

Repo: `knitanr-a11y/xauusd-signal-lab`

## Guardrails

GOLD V3 remains audit-only.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 feature-only snapshot as a trading source.

Do not enable Discord, MT5 execution, AI API, live hook, live evaluator, or final signal.

Do not mutate source CSVs, CSV contract, candidate pool, Stage45, or Stage69 runtime behavior.

CSV contract:

```text
open/in-progress candles are not written to CSV
CSV latest row is contractually closed
```

Pool policy:

```text
poolから外さない。rolling health gateに判断させる。
```

Current status:

```text
GOLD_V3_106_INDEPENDENT_HIGH_VOL_SHORT_PROXY_READY_AUDIT_ONLY
```

## What happened in this chat

### Stage99

`GOLD_V3_99_RECENT_CLOSED_CANDLE_SIGNAL_REPLAY_READY_AUDIT_ONLY`

128 recent closed M15 bars replayed. All were NO_SIGNAL. No blockers.

### Stage100

`GOLD_V3_100_NO_SIGNAL_REASON_BREAKDOWN_READY_AUDIT_ONLY`

All 128 replay bars were `CONDITION_NOT_MET`. Latest condition candidate rows were zero.

### Stage101

`GOLD_V3_101_STAGE69_DETECTION_COVERAGE_READY_AUDIT_ONLY`

Stage69 detector itself was active historically:

```text
max_detected_condition_rows_before_asof: 7346
max_latest_closed_condition_candidate_rows: 0
last_detected_condition_time: 2026-06-02 15:00:00
```

The recent replay window was about 173.5 to 207.25 hours after the last detected condition.

### Stage102

`GOLD_V3_102_POST_LAST_DETECTION_GATE_ATTRITION_READY_AUDIT_ONLY`

Post-last-detection window:

```text
2026-06-02 15:00:00 to 2026-06-11 09:45:00
source_rank_max_base_rows: 36
candidate_max_rows_after_filters_before_cooldown: 4
candidate_count_with_rows_after_filters: 8
```

Important finding:

- Recent `m15_atr28` was roughly 5.13 to 18.01.
- Stage45 R2 source condition still has an upper ATR bound near 4.29321, so R2 does not cover the recent high-vol regime.
- R1 rows were sparse and disappeared after early June.

### Stage103

`GOLD_V3_103_HIGH_VOL_REACHABILITY_READY_AUDIT_ONLY`

```text
high_vol_m15_rows: 59
max_high_vol_source_rows_for_ranks: 0
reachable_high_vol_sibling_count: 6
max_hv_after_original_filters_plus_high_vol: 4
```

This revealed a contradiction: true high-vol rows existed, but none satisfied inherited source gates, while some HV siblings were still reachable.

### Stage104

`GOLD_V3_104_HIGH_VOL_POLARITY_AND_PROXY_READY_AUDIT_ONLY`

```text
current_stage45_hv_total_rows: 24
current_stage45_hv_true_rows: 0
current_stage45_hv_false_rows: 24
intended_require_high_vol_total_rows: 0
polarity_mismatch_candidate_count: 6
```

Critical finding:

Stage45 `cat()` is an exclusion filter. Current HV siblings append a cat filter on `is_high_vol=True`, so the current HV siblings exclude true high-vol rows instead of requiring them.

Therefore current `HV_...` candidates are name-only high-vol siblings in this audit window.

Also, simply correcting polarity while still inheriting original source gates would still produce zero true-HV rows in the recent window.

### Stage105

`GOLD_V3_105_INDEPENDENT_HIGH_VOL_PROXY_READY_AUDIT_ONLY`

Independent true-HV LONG proxy:

```text
independent_high_vol_m15_rows: 59
proxy_opportunity_rows: 177
evaluated_trade_rows: 90
```

All evaluated LONG proxy profiles lost every trade in the recent window.

### Stage106

`GOLD_V3_106_INDEPENDENT_HIGH_VOL_SHORT_PROXY_READY_AUDIT_ONLY`

Independent true-HV SHORT proxy:

```text
independent_high_vol_m15_rows: 59
proxy_opportunity_rows: 177
evaluated_trade_rows: 90
```

All evaluated SHORT proxy profiles won every trade in the recent window:

```text
HV_SHORT_TP180_SL70_H128: 30 wins / 0 losses
HV_SHORT_TP200_SL80_H128: 30 wins / 0 losses
HV_SHORT_TP220_SL90_H128: 30 wins / 0 losses
```

This is still proxy-only and recent-window-only. Do not promote to runtime.

## Critical unresolved issues

1. Direction assumption is now the main risk.
2. Stage45 visible evaluation is LONG-style: TP above entry, SL below entry.
3. Candidate schema seen so far does not carry a clear side/direction field.
4. Normal Stage45/69 candidates may also be affected by direction-fixed evaluation.
5. Current HV siblings are semantically wrong for true high-vol selection.
6. True high-vol in the recent window was down-directional: LONG proxy failed, SHORT proxy succeeded.
7. Time basis issue remains open: Stage45 derives `jst_hour` and `jst_weekday` from `time + 9h`. User prefers checking MT5/CSV-time basis for clean Saturday cutoffs, but this must be audited before any change.

## Next stage

Create Stage107:

```text
GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_ONLY
```

Stage107 must be audit-only/proxy-only.

Required checks:

- normal Stage45/69 candidates evaluated as current LONG
- same normal candidates evaluated as SHORT-reversed
- per-candidate LONG vs SHORT metrics
- explicit scan for side/direction metadata
- current HV sibling semantics vs corrected true-HV semantics
- independent true-HV LONG vs SHORT recap
- segmentation by H4 bucket, JST weekday, and JST hour
- critical finding if candidates are directionless but evaluated LONG-fixed

Do not alter runtime logic.

## After Stage107

Create Stage108 only after Stage107:

```text
GOLD_V3_108_JST_VS_MT5_TIME_BASIS_DIFFERENTIAL_AUDIT_ONLY
```

Purpose:

- compare current JST weekday/hour filters with raw CSV/MT5 time weekday/hour
- quantify Friday/Saturday/hour-boundary differences
- do not change runtime behavior

## Next chat start prompt

```text
repo: knitanr-a11y/xauusd-signal-lab

まず以下を読んで、続きからお願いします。

docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_99_106_DONE_107_NEXT_DIRECTION_AND_TIME_AUDIT_20260611.md

GOLD V3は現在もaudit-onlyです。
GOLD V2 / 旧GOLD / DISC8 は隔離中です。
読まない・使わない・参照しない・fallbackにしないでください。
Stage41 feature-only snapshotもtrading sourceにしないでください。

現在status:
GOLD_V3_106_INDEPENDENT_HIGH_VOL_SHORT_PROXY_READY_AUDIT_ONLY

次はStage107:
GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_ONLY

最優先:
通常候補とHV候補の方向仮定をaudit-onlyで検証してください。
Stage108のJST vs MT5/CSV時刻基準auditはStage107の後にしてください。
```
