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
- Do not remove candidates from the candidate pool.
- Do not promote proxy results into runtime.

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

## Starting status

```text
GOLD_V3_106_INDEPENDENT_HIGH_VOL_SHORT_PROXY_READY_AUDIT_ONLY
```

## Why Stage107 exists

Stage99-106 showed that recent NO_SIGNAL was not caused by a runtime blocker. It was `CONDITION_NOT_MET` with zero latest condition candidate rows.

Key unresolved risk:

- Stage69 detector is not dead historically, but recent conditions have not appeared since `2026-06-02 15:00:00`.
- Stage45 R2 has an ATR upper-bound issue in the recent high-ATR regime.
- Current HV siblings are semantically wrong because Stage45 `cat()` is an exclusion filter; the current HV construction excludes `is_high_vol=True` rows instead of requiring them.
- Independent true high-vol proxy showed LONG profiles losing all evaluated trades and SHORT profiles winning all evaluated trades in the recent window.
- Visible Stage45 evaluation appears LONG-style: TP above entry / SL below entry.
- The candidate schema observed so far does not clearly carry a side/direction field.

Therefore Stage107 must audit whether the candidate set is directionless while being evaluated as LONG-fixed, and whether normal Stage45/69 candidates also reverse materially under SHORT proxy evaluation.

## Inputs

Primary inputs are read-only and may be passed explicitly:

```text
--candidate-file <CSV/JSON/JSONL/Parquet candidate-row artifact>
--m5-csv <M5 OHLC CSV/Parquet>
--m15-csv <optional M15 OHLC CSV/Parquet for entry close enrichment>
--handoff-doc docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_99_106_DONE_107_NEXT_DIRECTION_AND_TIME_AUDIT_20260611.md
```

The script has safe auto-discovery, but it must skip forbidden paths containing:

```text
gold_v2
old_gold
legacy_gold
disc8
stage41
gold_specialist_8
```

Auto-discovery is convenience only. If candidate/M5 inputs cannot be found safely, the script writes BLOCKED audit artifacts rather than guessing.

## Required audit checks

Stage107 must perform these checks:

1. Scan candidate artifact columns for explicit side/direction metadata.
2. Classify candidates into normal candidates and current HV-named siblings.
3. Evaluate candidate rows as current LONG-style proxy:
   - LONG TP = entry + TP distance
   - LONG SL = entry - SL distance
4. Evaluate the same candidate rows as SHORT-reversed proxy:
   - SHORT TP = entry - TP distance
   - SHORT SL = entry + SL distance
5. Produce per-candidate LONG vs SHORT metrics.
6. Produce segmentation by H4 bucket, JST weekday, and JST hour.
7. Audit current HV sibling semantics vs corrected true-HV semantics using `is_high_vol` / equivalent columns when present.
8. Recap independent true-HV LONG vs SHORT proxy findings from the Stage99-106 handoff.
9. Flag critical direction-assumption risk if there is no explicit side/direction metadata and bidirectional LONG/SHORT proxy metrics can be produced.

## TP/SL and horizon handling

Priority order:

1. Use explicit TP/SL/horizon columns when present.
2. If absent, parse profile names like `TP180_SL70_H128`.

Default profile scale:

```text
--profile-scale 0.1
```

This means `TP180` becomes `18.0`, `SL70` becomes `7.0`. The scale is written to the summary report. This is audit/proxy-only and is not runtime authorization.

## M5 adjudication

Default proxy adjudication:

```text
--same-bar-priority SL
--entry-mode after_entry_time
```

Meaning:

- M5 first-touch is used.
- If TP and SL touch in the same M5 bar, SL wins.
- M5 bars after entry time are scanned by default for conservative closed-bar proxy behavior.

No M15 fallback is used for official trade metrics. If M5 OHLC is unavailable, the script blocks trade metrics and still writes metadata/HV scan artifacts.

## Time basis

Stage107 only segments by current JST-style basis:

- existing `jst_hour` / `jst_weekday` columns when available;
- otherwise derived as `time + 9h` for segmentation only.

Stage107 must not decide the JST-vs-MT5/CSV-time issue. That is Stage108:

```text
GOLD_V3_108_JST_VS_MT5_TIME_BASIS_DIFFERENTIAL_AUDIT_ONLY
```

## Outputs

Default output directory:

```text
reports/gold_v3/stage107/
```

Expected files:

```text
gold_v3_107_trade_level_long_short_proxy.csv
gold_v3_107_per_candidate_long_short_metrics.csv
gold_v3_107_segment_h4_bucket_metrics.csv
gold_v3_107_segment_jst_hour_metrics.csv
gold_v3_107_segment_jst_weekday_metrics.csv
gold_v3_107_direction_assumption_summary.json
GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_ONLY_REPORT.md
```

## Success condition

Success status:

```text
GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_READY_AUDIT_ONLY
```

This means Stage107 audit artifacts were produced without missing required inputs for proxy trade metrics.

## Blocked condition

Blocked status:

```text
BLOCKED_INPUT_INCOMPLETE_AUDIT_ARTIFACTS_WRITTEN
```

This is acceptable if candidate/M5 artifacts cannot be safely discovered. The script must still write a summary/report explaining the missing inputs.

## Explicit non-goals

Stage107 does not:

- change runtime logic;
- change Stage45 or Stage69 behavior;
- remove any candidate;
- select a new production side;
- approve HV sibling repair;
- resolve the JST-vs-MT5/CSV basis issue;
- enable live evaluator or final signal.
