# NEXT CHAT HANDOFF — GOLD V3 Stage107 implementation ready / local run next

Created JST: `2026-06-11`

Repo: `knitanr-a11y/xauusd-signal-lab`

## Current status

```text
GOLD_V3_107_IMPLEMENTATION_READY_LOCAL_RUN_NEXT_AUDIT_ONLY
```

## Absolute guardrails

GOLD V3 remains audit-only.

Do not read/use/reference/fallback to:

- GOLD V2
- old GOLD
- DISC8
- Stage41 feature-only snapshot as trading source

Do not enable:

- Discord notification
- MT5 execution
- AI API
- live hook
- live evaluator
- final signal

Do not mutate:

- source CSVs
- CSV contract
- candidate pool
- Stage45 runtime behavior
- Stage69 runtime behavior

CSV contract:

```text
open/in-progress candles are not written to CSV
CSV latest row is contractually closed
open/as-of treatment is forbidden
```

Candidate pool policy:

```text
poolから外さない。rolling health gateに判断させる。
```

## What was created

### Spec

```text
docs/gold_v3/GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_ONLY_SPEC_20260611.md
```

### Script

```text
scripts/gold_v3_stage107_normal_and_hv_direction_assumption_audit_only.py
```

### BAT runner

```text
run_gold_v3_stage107_normal_and_hv_direction_assumption_audit_only.bat
```

## Stage107 objective

```text
GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_ONLY
```

Purpose:

- audit normal Stage45/69 candidates as current LONG-style proxy
- audit the same candidates as SHORT-reversed proxy
- produce per-candidate LONG vs SHORT metrics
- scan candidate schema for side/direction metadata
- compare current HV-named sibling semantics with corrected true-HV semantics when `is_high_vol`-like columns exist
- recap Stage105/106 independent true-HV LONG vs SHORT proxy findings
- segment by H4 bucket, JST weekday, and JST hour
- flag critical risk if candidates are directionless but evaluated LONG-fixed

No runtime logic may be changed.

## Expected local command

Run from repo root on Windows:

```bat
run_gold_v3_stage107_normal_and_hv_direction_assumption_audit_only.bat
```

Optional explicit inputs if auto-discovery cannot find safe files:

```bat
python scripts\gold_v3_stage107_normal_and_hv_direction_assumption_audit_only.py ^
  --candidate-file "<candidate artifact path>" ^
  --m5-csv "<M5 OHLC path>" ^
  --out-dir "reports\gold_v3\stage107"
```

## Expected output directory

```text
reports/gold_v3/stage107/
```

Expected artifacts:

```text
gold_v3_107_trade_level_long_short_proxy.csv
gold_v3_107_per_candidate_long_short_metrics.csv
gold_v3_107_segment_h4_bucket_metrics.csv
gold_v3_107_segment_jst_hour_metrics.csv
gold_v3_107_segment_jst_weekday_metrics.csv
gold_v3_107_direction_assumption_summary.json
GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_ONLY_REPORT.md
```

If candidate/M5 inputs are missing or schema is insufficient, the script writes:

```text
BLOCKED_INPUT_INCOMPLETE_AUDIT_ARTIFACTS_WRITTEN
```

This is acceptable. Do not guess or use forbidden sources.

## Important interpretation notes

Stage107 is audit-only/proxy-only.

A SHORT proxy win does not approve runtime direction reversal.

A LONG proxy loss does not approve candidate removal.

HV sibling polarity repair is not approved by Stage107.

The JST vs MT5/CSV time basis issue is not resolved by Stage107.

## Next after local Stage107 run

If Stage107 outputs READY artifacts, review:

```text
reports/gold_v3/stage107/GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_ONLY_REPORT.md
reports/gold_v3/stage107/gold_v3_107_direction_assumption_summary.json
```

Then create a Stage107 result-review handoff and only after that proceed to:

```text
GOLD_V3_108_JST_VS_MT5_TIME_BASIS_DIFFERENTIAL_AUDIT_ONLY
```

## Next chat start prompt

```text
repo: knitanr-a11y/xauusd-signal-lab

まず以下を読んで、続きからお願いします。

docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_107_IMPLEMENTATION_READY_LOCAL_RUN_NEXT_AUDIT_ONLY_20260611.md

GOLD V3は現在もaudit-onlyです。
GOLD V2 / 旧GOLD / DISC8 は隔離中です。
読まない・使わない・参照しない・fallbackにしないでください。
Stage41 feature-only snapshotもtrading sourceにしないでください。

CSV最新行は契約上closedです。open/as-of扱いは禁止です。
candidate poolから外さないでください。

現在status:
GOLD_V3_107_IMPLEMENTATION_READY_LOCAL_RUN_NEXT_AUDIT_ONLY

次はローカルでStage107 BATを実行し、reports/gold_v3/stage107/ のsummary/reportを確認してください。
Stage108はStage107結果レビュー後にしてください。
```
