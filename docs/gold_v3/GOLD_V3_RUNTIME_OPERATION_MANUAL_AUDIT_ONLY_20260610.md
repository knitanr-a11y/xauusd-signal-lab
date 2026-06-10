# GOLD V3 Runtime Operation Manual — Audit-Only

Created JST: `2026-06-10`

Current runtime entry point:

`scripts/gold_v3_runtime/bat/run_gold_v3_80_immutable_runtime_monitor_audit.bat`

This document is the human-facing operation manual. Keep it updated whenever runtime behavior, troubleshooting files, output folders, trade review policy, candidate catalog, or BAT names change.

---

## 0. Current safety state

GOLD V3 remains audit-only.

Hard safety flags:

- `live_ready=false`
- `live_allowed=false`
- `mt5=false`
- `discord=false`
- `ai_api=false`
- `final_signal=false`

Do not enable any of the following without explicit human approval:

- Discord live notification,
- MT5 order execution,
- AI API call,
- live hook,
- live evaluator,
- final signal.

NO_SIGNAL must not notify Discord.

---

## 1. What to start for normal monitoring

Start this BAT:

```bat
scripts\gold_v3_runtime\bat\run_gold_v3_80_immutable_runtime_monitor_audit.bat
```

Stage80 does the runtime audit-only monitoring.

Behavior:

1. Every minute at second `05`, read only the latest row timestamp from `goldsharp_m15.csv`.
2. If the latest closed M15 timestamp has not changed, write a heartbeat only.
3. If a new closed M15 row is detected, run Stage76 once.
4. After Stage76 completes, run Stage79 to create an immutable evidence snapshot.
5. If Stage80 becomes BLOCKED, automatically run Stage81 to create a compact support bundle.

The CSV contract is:

`open/in-progress candles are not written to CSV`

Therefore:

`csv_open_bar_exclusion_required=false`

The latest CSV row is treated as the latest closed M15 row.

---

## 2. Which file to check first

For normal status checking, look at:

```text
Files\FX_OUTPUTS\gold_v3\80_immutable_runtime_monitor_audit_only\gold_v3_80_PASTE_ME_IMMUTABLE_RUNTIME_MONITOR_SUMMARY.txt
```

READY example fields:

```text
status: GOLD_V3_80_IMMUTABLE_RUNTIME_MONITOR_READY_AUDIT_ONLY
immutable_runtime_monitor_ready: true
latest_m15_time: <latest closed M15 time>
last_seen_m15_time: <last processed M15 time>
last_stage76_returncode: 0
last_stage79_returncode: 0
last_stage79_paste_path: <immutable snapshot paste file>
auto_support_bundle_enabled: True
blocker_count: 0
```

If `blocker_count: 0`, the audit monitor itself is healthy.

---

## 3. What to upload/paste when an error happens

Do not search the whole folder manually.

Do not upload huge CSV logs first.

First paste this file:

```text
Files\FX_OUTPUTS\gold_v3\81c\YYYYMMDD\HHMMSS_bundle\upload_first.txt
```

Stage80 automatically creates this file when it becomes BLOCKED.

If Stage80 did not create it, run this BAT manually:

```bat
scripts\gold_v3_runtime\bat\run_gold_v3_81_compact_support_bundle_audit.bat
```

Then paste the printed path:

```text
...\81c\YYYYMMDD\HHMMSS_bundle\upload_first.txt
```

`upload_first.txt` is intentionally small. It includes:

- current Stage80 status,
- current Stage76 status,
- latest Stage79 immutable run path,
- important file paths and sizes,
- tail of Stage80 event/timing logs,
- tail of Stage76 event/timing logs,
- live/external flags.

Only paste additional files if asked.

---

## 4. Where immutable evidence is stored

Each processed M15 run creates a short immutable snapshot folder:

```text
Files\FX_OUTPUTS\gold_v3\79i\YYYYMMDD\RUN_ID\
```

Example:

```text
Files\FX_OUTPUTS\gold_v3\79i\20260610\144110_1715_NO_SIGNAL\
```

Inside this folder, the main paste file is:

```text
paste_me.txt
```

Stage80 shows this path as:

```text
last_stage79_paste_path: ...\79i\YYYYMMDD\RUN_ID\paste_me.txt
```

Stage79 uses short names to avoid Windows/MetaQuotes path-length failures.

The immutable snapshot policy is:

- do not overwrite existing run evidence,
- create a new run_id folder for each processed M15 run,
- if a duplicate happens, use retry suffix,
- include SHA256 manifest files.

---

## 5. What the main stages mean

### Stage76

Full audit monitor with payload preview.

Role:

- reads latest closed M15 row,
- runs guarded audit pipeline,
- builds payload preview only,
- records timing values,
- keeps all external side effects OFF.

Main file:

```text
Files\FX_OUTPUTS\gold_v3\76_full_audit_monitor_with_payload_preview_audit_only\gold_v3_76_PASTE_ME_FULL_AUDIT_MONITOR_WITH_PAYLOAD_PREVIEW_SUMMARY.txt
```

### Stage79

Immutable runtime output policy.

Role:

- copies Stage76 evidence into a run_id folder,
- does not overwrite existing evidence,
- writes manifest and hashes,
- uses short paths under `79i`.

Main file:

```text
Files\FX_OUTPUTS\gold_v3\79i\YYYYMMDD\RUN_ID\paste_me.txt
```

### Stage80

Immutable runtime monitor.

Role:

- operational monitor wrapper,
- every minute at second 05,
- new M15: Stage76 -> Stage79,
- BLOCKED: auto Stage81 support bundle.

Main file:

```text
Files\FX_OUTPUTS\gold_v3\80_immutable_runtime_monitor_audit_only\gold_v3_80_PASTE_ME_IMMUTABLE_RUNTIME_MONITOR_SUMMARY.txt
```

### Stage81

Compact support bundle.

Role:

- creates one small file to paste first,
- includes log tails only,
- avoids uploading huge logs unless requested.

Main file:

```text
Files\FX_OUTPUTS\gold_v3\81c\YYYYMMDD\HHMMSS_bundle\upload_first.txt
```

### Stage84

Trade review ledger policy.

Role:

- defines the long-term trade review ledger schema,
- shifts long-term retention priority from operational logs to trade history,
- creates templates for post-trade review.

Main folder:

```text
Files\FX_OUTPUTS\gold_v3\trade_review_ledger\
```

Important files:

```text
trade_review_ledger_schema.csv
trade_review_current_template.csv
trade_review_manual_outcome_template.csv
trade_review_retention_policy_matrix.csv
README_TRADE_REVIEW_LEDGER.md
```

### Stage85

Trade review ledger entry preview.

Role:

- if current decision is `NO_SIGNAL`, suppress ledger row creation,
- if current decision is a real SIGNAL, create one preview row only,
- does not append to the durable ledger.

NO_SIGNAL suppression reason:

```text
NO_SIGNAL_NOT_A_TRADE_REVIEW_LEDGER_ROW
```

### Stage86

Trade review ledger append guard.

Role:

- prevents NO_SIGNAL, heartbeat, notification errors, and incomplete/unconfirmed records from entering the durable trade ledger,
- holds SIGNAL preview rows until execution or explicit human review intent is confirmed,
- does not append to the durable ledger.

Expected NO_SIGNAL guard decision:

```text
NO_APPEND_SUPPRESSED_NO_SIGNAL
```

Expected unconfirmed SIGNAL guard decision:

```text
HOLD_NOT_APPEND_UNTIL_EXECUTION_OR_HUMAN_REVIEW_CONFIRMED
```

### Stage88

Signal candidate normalization and condition coverage.

Role:

- normalizes 44 expanded candidate rows into 8 base signal candidates,
- identifies high-volatility TP/SL/horizon expansions,
- measures whether exact candidate conditions can be recovered from current GOLD V3 artifacts,
- uses short output folder `88c` to avoid Windows path-length failures.

Main file:

```text
Files\FX_OUTPUTS\gold_v3\88c\paste_me.txt
```

Manual candidate section source:

```text
Files\FX_OUTPUTS\gold_v3\88c\manual_candidates.md
```

---

## 6. Trade review ledger policy

The most important long-term artifact is not old notification logs. It is trade history.

Keep long-term:

- trade review ledger rows,
- per-trade compact evidence packet,
- signal decision context,
- candidate/profile key,
- TP/SL/horizon,
- health gate status,
- evidence path,
- outcome status,
- realized result when available,
- why the trade won/lost,
- post-trade review notes.

Short-term or summary-only:

- old notification errors,
- heartbeat logs,
- full timing CSVs,
- repeated NO_SIGNAL entries,
- support-bundle diagnostics.

Candidate key order must remain exactly:

```text
candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars
```

NO_SIGNAL must not create durable trade review rows.

A SIGNAL preview row must not be appended to the durable ledger until:

1. execution is confirmed, or
2. the human explicitly chooses to review it as a trade candidate,
3. required candidate/profile context is complete.

---

## 7. Signal candidate catalog

This section is generated from GOLD V3 audit artifacts only. Missing rule conditions are not inferred.

Current Stage88 status:

```text
raw_expansion_row_count: 44
dedup_expansion_row_count: 32
normalized_base_candidate_count: 8
condition_coverage_complete: false
condition_restored_base_count: 0
```

Candidate key order:

```text
candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars
```

Manual warning:

- Current candidate names and high-volatility expansions are restored.
- Exact rule conditions are not restored from current artifacts.
- Do not present `CONDITION_NOT_RESTORED_FROM_CURRENT_ARTIFACTS` as a known trading rule.
- Do not guess rule conditions.

Base signal candidates:

- **R01_P7_R1_ONLY_CD60_PRUNE_015**
  - variants: `4`
  - high-volatility profiles: `HV_TP180_SL70_H128;HV_TP200_SL80_H128;HV_TP220_SL90_H128`
  - condition status: `NOT_RESTORED`
  - condition: `CONDITION_NOT_RESTORED_FROM_CURRENT_ARTIFACTS`
- **R02_P8_R1_ONLY_CD60_PRUNE_015**
  - variants: `4`
  - high-volatility profiles: `HV_TP180_SL70_H128;HV_TP200_SL80_H128;HV_TP220_SL90_H128`
  - condition status: `NOT_RESTORED`
  - condition: `CONDITION_NOT_RESTORED_FROM_CURRENT_ARTIFACTS`
- **R03_P1_R1_ONLY_CD60_PRUNE_111**
  - variants: `4`
  - high-volatility profiles: `HV_TP180_SL70_H128;HV_TP200_SL80_H128;HV_TP220_SL90_H128`
  - condition status: `NOT_RESTORED`
  - condition: `CONDITION_NOT_RESTORED_FROM_CURRENT_ARTIFACTS`
- **R04_P4_R1_ONLY_CD60_PRUNE_115**
  - variants: `4`
  - high-volatility profiles: `HV_TP180_SL70_H128;HV_TP200_SL80_H128;HV_TP220_SL90_H128`
  - condition status: `NOT_RESTORED`
  - condition: `CONDITION_NOT_RESTORED_FROM_CURRENT_ARTIFACTS`
- **R05_P9_MAIN_R1_R2_CD90_PRUNE_133**
  - variants: `4`
  - high-volatility profiles: `HV_TP180_SL70_H128;HV_TP200_SL80_H128;HV_TP220_SL90_H128`
  - condition status: `NOT_RESTORED`
  - condition: `CONDITION_NOT_RESTORED_FROM_CURRENT_ARTIFACTS`
- **R06_P11_MAIN_R1_R2_CD90_PRUNE_132**
  - variants: `4`
  - high-volatility profiles: `HV_TP180_SL70_H128;HV_TP200_SL80_H128;HV_TP220_SL90_H128`
  - condition status: `NOT_RESTORED`
  - condition: `CONDITION_NOT_RESTORED_FROM_CURRENT_ARTIFACTS`
- **R07_P13_MAIN_R1_R2_CD120_PRUNE_122**
  - variants: `4`
  - high-volatility profiles: `HV_TP180_SL70_H128;HV_TP200_SL80_H128;HV_TP220_SL90_H128`
  - condition status: `NOT_RESTORED`
  - condition: `CONDITION_NOT_RESTORED_FROM_CURRENT_ARTIFACTS`
- **R1_ONLY_CD90_PRUNE_050__R1_ONLY_CD90_PRUNE_050_S030__R1_ONLY_CD90_PRUNE_050_S024**
  - variants: `4`
  - high-volatility profiles: `HV_TP180_SL70_H128;HV_TP200_SL80_H128;HV_TP220_SL90_H128`
  - condition status: `NOT_RESTORED`
  - condition: `CONDITION_NOT_RESTORED_FROM_CURRENT_ARTIFACTS`

---

## 8. Folder map

```text
Files\FX_OUTPUTS\gold_v3\
  76_full_audit_monitor_with_payload_preview_audit_only\
    gold_v3_76_PASTE_ME_FULL_AUDIT_MONITOR_WITH_PAYLOAD_PREVIEW_SUMMARY.txt
    gold_v3_76_runtime_timing_log.csv
    gold_v3_76_monitor_event_log.csv

  79i\
    YYYYMMDD\
      RUN_ID\
        paste_me.txt
        manifest.json
        manifest.csv
        summary.json
        s76\
          s76_summary.json
          s76_payload.csv
          s76_timing.csv
          ...

  80_immutable_runtime_monitor_audit_only\
    gold_v3_80_PASTE_ME_IMMUTABLE_RUNTIME_MONITOR_SUMMARY.txt
    gold_v3_80_state.json
    gold_v3_80_event_log.csv
    gold_v3_80_timing_log.csv

  81c\
    YYYYMMDD\
      HHMMSS_bundle\
        upload_first.txt
        file_index.csv
        bundle_summary.json
        blockers.csv
        validation.csv
        report.md

  88c\
    paste_me.txt
    manual_candidates.md
    base.csv
    expansion.csv
    condition.csv
    summary.json

  trade_review_ledger\
    trade_review_ledger_schema.csv
    trade_review_current_template.csv
    trade_review_manual_outcome_template.csv
    trade_review_retention_policy_matrix.csv
    README_TRADE_REVIEW_LEDGER.md
```

---

## 9. What not to upload first

Do not upload these first unless specifically requested:

- full `gold_v3_80_event_log.csv`,
- full `gold_v3_80_timing_log.csv`,
- full `gold_v3_76_monitor_event_log.csv`,
- full `gold_v3_76_runtime_timing_log.csv`,
- full immutable run folder,
- large CSVs from candle data.

Use Stage81 `upload_first.txt` first.

For trade review, use the trade ledger files and Stage79 evidence path instead of uploading giant operational logs.

---

## 10. How to stop the monitor

For Stage80 BAT window:

- press `Ctrl+C`, or
- close the BAT window.

Stopping the monitor does not send orders or notifications. It only stops audit-only monitoring.

---

## 11. Current known-good runtime confirmation

Latest known-good checks as of this manual update:

```text
Stage80 READY
latest_m15_time: 2026-06-10 17:15:00
last_seen_m15_time: 2026-06-10 17:15:00
last_stage76_returncode: 0
last_stage79_returncode: 0
auto_support_bundle_enabled: True
blocker_count: 0

Stage85 READY
decision: NO_SIGNAL
ledger_action: SUPPRESS
ledger_suppression_reason: NO_SIGNAL_NOT_A_TRADE_REVIEW_LEDGER_ROW
preview_row_count: 0
blocker_count: 0

Stage86 READY
decision: NO_SIGNAL
append_guard_decision: NO_APPEND_SUPPRESSED_NO_SIGNAL
append_allowed_now: false
blocker_count: 0

Stage88 READY
raw_expansion_row_count: 44
dedup_expansion_row_count: 32
normalized_base_candidate_count: 8
condition_coverage_complete: false
condition_restored_base_count: 0
blocker_count: 0
```

---

## 12. Documentation maintenance rule

Whenever runtime behavior changes, update this manual in the same task/chat.

Update this manual when changing:

- main runtime BAT,
- output folder names,
- error support bundle behavior,
- paste/upload file names,
- safety flags,
- timing/log policy,
- immutable evidence policy,
- trade review ledger policy,
- ledger append guard behavior,
- signal candidate catalog,
- live release gate behavior.

Do not rely only on stage specs. This manual is the human-facing operation guide.
