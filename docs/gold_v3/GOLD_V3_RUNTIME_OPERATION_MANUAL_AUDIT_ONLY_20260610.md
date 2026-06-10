# GOLD V3 Runtime Operation Manual — Audit-Only

Created JST: `2026-06-10`

Current runtime entry point:

`scripts/gold_v3_runtime/bat/run_gold_v3_80_immutable_runtime_monitor_audit.bat`

This document is the human-facing operation manual. Keep it updated whenever runtime behavior, troubleshooting files, output folders, or BAT names change.

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

---

## 6. Folder map

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
```

---

## 7. What not to upload first

Do not upload these first unless specifically requested:

- full `gold_v3_80_event_log.csv`,
- full `gold_v3_80_timing_log.csv`,
- full `gold_v3_76_monitor_event_log.csv`,
- full `gold_v3_76_runtime_timing_log.csv`,
- full immutable run folder,
- large CSVs from candle data.

Use Stage81 `upload_first.txt` first.

---

## 8. How to stop the monitor

For Stage80 BAT window:

- press `Ctrl+C`, or
- close the BAT window.

Stopping the monitor does not send orders or notifications. It only stops audit-only monitoring.

---

## 9. Current known-good runtime confirmation

Latest known-good check as of this manual creation:

```text
Stage80 READY
latest_m15_time: 2026-06-10 17:15:00
last_seen_m15_time: 2026-06-10 17:15:00
last_stage76_returncode: 0
last_stage79_returncode: 0
auto_support_bundle_enabled: True
blocker_count: 0
```

---

## 10. Documentation maintenance rule

Whenever runtime behavior changes, update this manual in the same chat/task.

Update this manual when changing:

- main runtime BAT,
- output folder names,
- error support bundle behavior,
- paste/upload file names,
- safety flags,
- timing/log policy,
- immutable evidence policy,
- live release gate behavior.

Do not rely only on stage specs. This manual is the human-facing operation guide.
