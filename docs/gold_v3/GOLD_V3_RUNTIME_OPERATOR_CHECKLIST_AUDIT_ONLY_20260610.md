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

## 5. Trade review ledger rule

Long-term value is in trade review records, not old heartbeat/notification logs.

Main folder:

```text
Files\FX_OUTPUTS\gold_v3\trade_review_ledger\
```

Keep long-term:

```text
trade review ledger rows
signal decision context
candidate/profile key
TP/SL/horizon
health gate status
Stage79 evidence path
outcome result
why win/loss note
post-trade review note
```

Do not treat these as long-term primary learning records:

```text
old notification errors
heartbeat logs
full timing CSVs
repeated NO_SIGNAL entries
support bundle diagnostics
```

Candidate key order must stay exactly:

```text
candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars
```

---

## 6. Signal / NO_SIGNAL ledger rule

For NO_SIGNAL:

```text
Do not append to trade_review_ledger.
Expected Stage85 reason:
NO_SIGNAL_NOT_A_TRADE_REVIEW_LEDGER_ROW
Expected Stage86 guard:
NO_APPEND_SUPPRESSED_NO_SIGNAL
```

For SIGNAL:

```text
Create preview row only.
Do not append durable ledger yet.
Hold until execution is confirmed or human explicitly chooses to review it.
Outcome starts as PENDING.
manual_review_required=True.
```

If candidate/profile context is missing:

```text
BLOCK; do not append.
```

---

## 7. Where immutable evidence is

After each processed new M15 row:

```text
Files\FX_OUTPUTS\gold_v3\79i\YYYYMMDD\RUN_ID\paste_me.txt
```

The current path is shown in Stage80 summary as:

```text
last_stage79_paste_path: ...\79i\YYYYMMDD\RUN_ID\paste_me.txt
```

For trade review, keep the Stage79 evidence path in the ledger row instead of uploading full folders first.

---

## 8. Stop monitoring

To stop Stage80:

- press `Ctrl+C`, or
- close the BAT window.

Stopping monitor does not send orders or notifications.

---

## 9. Things not to touch without approval

Do not enable:

- Discord live notifications,
- MT5 orders,
- AI API calls,
- final signal,
- live hook,
- live evaluator.

GOLD V3 remains audit-only.

---

## 10. Documentation rule

If runtime behavior changes, update both:

```text
docs/gold_v3/GOLD_V3_RUNTIME_OPERATION_MANUAL_AUDIT_ONLY_20260610.md
docs/gold_v3/GOLD_V3_RUNTIME_OPERATOR_CHECKLIST_AUDIT_ONLY_20260610.md
```

Also update these when trade review ledger or append guard rules change.
