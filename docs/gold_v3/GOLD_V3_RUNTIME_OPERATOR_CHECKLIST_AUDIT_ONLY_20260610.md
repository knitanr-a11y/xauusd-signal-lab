# GOLD V3 Runtime Operator Checklist — Audit-Only

Created JST: `2026-06-10`

This is the short human checklist. For details, read:

`docs/gold_v3/GOLD_V3_RUNTIME_OPERATION_MANUAL_AUDIT_ONLY_20260610.md`

---

## 1. Start monitoring

Run:

```bat
scripts\gold_v3_runtime\bat\run_gold_v3_80_immutable_runtime_monitor_audit.bat
```

Expected behavior:

- every minute at second 05,
- new closed M15 row only,
- Stage76 -> Stage79,
- immutable snapshot under `79i`,
- no Discord,
- no MT5,
- no AI API,
- no final signal.

---

## 2. Normal check

Open/check:

```text
Files\FX_OUTPUTS\gold_v3\80_immutable_runtime_monitor_audit_only\gold_v3_80_PASTE_ME_IMMUTABLE_RUNTIME_MONITOR_SUMMARY.txt
```

Good state:

```text
status: GOLD_V3_80_IMMUTABLE_RUNTIME_MONITOR_READY_AUDIT_ONLY
last_stage76_returncode: 0
last_stage79_returncode: 0
auto_support_bundle_enabled: True
blocker_count: 0
```

If `blocker_count: 0`, no troubleshooting upload is needed.

---

## 3. When there is an error

First upload/paste only this file:

```text
Files\FX_OUTPUTS\gold_v3\81c\YYYYMMDD\HHMMSS_bundle\upload_first.txt
```

Stage80 should create it automatically when BLOCKED.

If it was not created, run:

```bat
scripts\gold_v3_runtime\bat\run_gold_v3_81_compact_support_bundle_audit.bat
```

Then paste the printed `upload_first.txt` path/file.

---

## 4. Do not upload these first

Do not upload these first unless requested:

```text
gold_v3_80_event_log.csv
gold_v3_80_timing_log.csv
gold_v3_76_monitor_event_log.csv
gold_v3_76_runtime_timing_log.csv
full 79i run folder
full candle CSVs
```

Use `upload_first.txt` first. It already includes short log tails and important paths.

---

## 5. Where immutable evidence is

After each processed new M15 row:

```text
Files\FX_OUTPUTS\gold_v3\79i\YYYYMMDD\RUN_ID\paste_me.txt
```

The current path is shown in Stage80 summary as:

```text
last_stage79_paste_path: ...\79i\YYYYMMDD\RUN_ID\paste_me.txt
```

---

## 6. Stop monitoring

To stop Stage80:

- press `Ctrl+C`, or
- close the BAT window.

Stopping monitor does not send orders or notifications.

---

## 7. Things not to touch without approval

Do not enable:

- Discord live notifications,
- MT5 orders,
- AI API calls,
- final signal,
- live hook,
- live evaluator.

GOLD V3 remains audit-only.

---

## 8. Documentation rule

If runtime behavior changes, update both:

```text
docs/gold_v3/GOLD_V3_RUNTIME_OPERATION_MANUAL_AUDIT_ONLY_20260610.md
docs/gold_v3/GOLD_V3_RUNTIME_OPERATOR_CHECKLIST_AUDIT_ONLY_20260610.md
```
