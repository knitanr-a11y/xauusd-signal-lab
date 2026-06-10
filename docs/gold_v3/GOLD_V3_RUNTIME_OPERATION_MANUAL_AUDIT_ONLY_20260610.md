# GOLD V3 Runtime Operation Manual — Audit-Only

Created JST: `2026-06-10`

Current normal runtime entry point:

```bat
scripts\gold_v3_runtime\bat\run_gold_v3_80_immutable_runtime_monitor_audit.bat
```

Optional sidecar dry-run test entry point:

```bat
scripts\gold_v3_runtime\bat\run_gold_v3_91_stage80_ledger_sidecar_dry_run_patch_audit.bat
```

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
- `durable_ledger_append_enabled=false`

Do not enable any of the following without explicit human approval:

- Discord live notification,
- MT5 order execution,
- AI API call,
- live hook,
- live evaluator,
- final signal,
- durable trade ledger append.

NO_SIGNAL must not notify Discord.

---

## 1. What to start for normal monitoring

Start this BAT for normal monitoring:

```bat
scripts\gold_v3_runtime\bat\run_gold_v3_80_immutable_runtime_monitor_audit.bat
```

Normal Stage80 behavior:

```text
Stage80 -> Stage76 -> Stage79
```

Ledger sidecar is OFF by default in normal monitoring.

Normal mode must show:

```text
ledger_sidecar_enabled: False
durable_ledger_append_enabled: False
```

Stage92 confirmed this default regression check:

```text
stage80_default_no_sidecar_regression_ready: true
stage80_returncode: 0
stage80_status: GOLD_V3_80_IMMUTABLE_RUNTIME_MONITOR_READY_AUDIT_ONLY
ledger_sidecar_enabled: False
durable_ledger_append_enabled: False
blocker_count: 0
```

---

## 2. Optional ledger sidecar dry-run test

Use this only when explicitly testing Stage85/86 sidecar wiring:

```bat
scripts\gold_v3_runtime\bat\run_gold_v3_91_stage80_ledger_sidecar_dry_run_patch_audit.bat
```

This BAT runs Stage80 once with:

```text
--enable-ledger-sidecar-dry-run
```

Sidecar test chain:

```text
Stage80 -> Stage76 -> Stage79 -> Stage85 -> Stage86
```

Stage91 confirmed:

```text
status: GOLD_V3_80_IMMUTABLE_RUNTIME_MONITOR_READY_AUDIT_ONLY
ledger_sidecar_enabled: True
last_stage85_returncode: 0
last_stage86_returncode: 0
last_stage85_paste_path: nonempty
last_stage86_paste_path: nonempty
durable_ledger_append_enabled: False
blocker_count: 0
```

This is still audit-only. It does not append the durable trade ledger.

---

## 3. CSV closed-row contract

The CSV contract is:

```text
open/in-progress candles are not written to CSV
```

Therefore:

```text
csv_open_bar_exclusion_required=false
```

The latest CSV row is treated as the latest closed M15 row.

---

## 4. Which file to check first

For normal Stage80 status:

```text
Files\FX_OUTPUTS\gold_v3\80_immutable_runtime_monitor_audit_only\gold_v3_80_PASTE_ME_IMMUTABLE_RUNTIME_MONITOR_SUMMARY.txt
```

For sidecar test output, the same Stage80 summary file is used:

```text
Files\FX_OUTPUTS\gold_v3\80_immutable_runtime_monitor_audit_only\gold_v3_80_PASTE_ME_IMMUTABLE_RUNTIME_MONITOR_SUMMARY.txt
```

For support-bundle troubleshooting, paste this first:

```text
Files\FX_OUTPUTS\gold_v3\81c\YYYYMMDD\HHMMSS_bundle\upload_first.txt
```

---

## 5. What to upload/paste when an error happens

Do not upload huge CSV logs first.

First paste Stage81 support bundle:

```text
Files\FX_OUTPUTS\gold_v3\81c\YYYYMMDD\HHMMSS_bundle\upload_first.txt
```

If Stage80 did not create it, run:

```bat
scripts\gold_v3_runtime\bat\run_gold_v3_81_compact_support_bundle_audit.bat
```

Only paste additional files if asked.

---

## 6. Where immutable evidence is stored

Each processed M15 run creates a short immutable snapshot folder:

```text
Files\FX_OUTPUTS\gold_v3\79i\YYYYMMDD\RUN_ID\
```

Main paste file:

```text
paste_me.txt
```

Stage80 shows this path as:

```text
last_stage79_paste_path: ...\79i\YYYYMMDD\RUN_ID\paste_me.txt
```

---

## 7. What the main stages mean

### Stage76

Full audit monitor with payload preview.

Role:

- reads latest closed M15 row,
- runs guarded audit pipeline,
- builds payload preview only,
- records timing values,
- keeps all external side effects OFF.

### Stage79

Immutable runtime output policy.

Role:

- copies Stage76 evidence into a run_id folder,
- does not overwrite existing evidence,
- writes manifest and hashes,
- uses short paths under `79i`.

### Stage80

Immutable runtime monitor.

Role:

- operational monitor wrapper,
- every minute at second 05,
- normal new M15: Stage76 -> Stage79,
- optional sidecar dry-run: Stage76 -> Stage79 -> Stage85 -> Stage86,
- BLOCKED: auto Stage81 support bundle.

Default normal monitor keeps:

```text
ledger_sidecar_enabled: False
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
- uses short output folder `88c`.

### Stage91

Stage80 ledger sidecar dry-run patch.

Role:

- adds optional sidecar dry-run mode to Stage80,
- default remains OFF,
- explicit sidecar test runs Stage85/86 after Stage79,
- still no durable ledger append.

### Stage92

Stage80 default no-sidecar regression.

Role:

- verifies normal Stage80 invocation keeps sidecar OFF,
- confirms Stage91 patch did not change normal monitoring behavior.

---

## 8. Trade review ledger policy

The most important long-term artifact is trade history, not old notification logs.

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

## 9. Signal candidate catalog

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

## 10. Folder map

```text
Files\FX_OUTPUTS\gold_v3\
  76_full_audit_monitor_with_payload_preview_audit_only\
  79i\
  80_immutable_runtime_monitor_audit_only\
  81c\
  88c\
  92c\
  trade_review_ledger\
```

Important Stage80 files:

```text
Files\FX_OUTPUTS\gold_v3\80_immutable_runtime_monitor_audit_only\gold_v3_80_PASTE_ME_IMMUTABLE_RUNTIME_MONITOR_SUMMARY.txt
Files\FX_OUTPUTS\gold_v3\80_immutable_runtime_monitor_audit_only\gold_v3_80_state.json
Files\FX_OUTPUTS\gold_v3\80_immutable_runtime_monitor_audit_only\gold_v3_80_event_log.csv
Files\FX_OUTPUTS\gold_v3\80_immutable_runtime_monitor_audit_only\gold_v3_80_timing_log.csv
```

---

## 11. What not to upload first

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

## 12. How to stop the monitor

For Stage80 BAT window:

- press `Ctrl+C`, or
- close the BAT window.

Stopping the monitor does not send orders or notifications. It only stops audit-only monitoring.

---

## 13. Current known-good runtime confirmation

Latest known-good checks as of this manual update:

```text
Stage91 sidecar dry-run READY
ledger_sidecar_enabled: True
last_stage85_returncode: 0
last_stage86_returncode: 0
last_stage85_paste_path: nonempty
last_stage86_paste_path: nonempty
durable_ledger_append_enabled: False
blocker_count: 0

Stage92 default regression READY
stage80_returncode: 0
stage80_status: GOLD_V3_80_IMMUTABLE_RUNTIME_MONITOR_READY_AUDIT_ONLY
ledger_sidecar_enabled: False
durable_ledger_append_enabled: False
blocker_count: 0
```

---

## 14. Documentation maintenance rule

Whenever runtime behavior changes, update this manual in the same task/chat.

Update this manual when changing:

- main runtime BAT,
- optional runtime BAT,
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
