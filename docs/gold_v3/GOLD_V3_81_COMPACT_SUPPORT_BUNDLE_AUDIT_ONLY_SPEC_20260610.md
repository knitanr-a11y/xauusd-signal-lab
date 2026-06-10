# GOLD V3 Stage81 — Compact Support Bundle Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_81_COMPACT_SUPPORT_BUNDLE_AUDIT_ONLY`

Expected READY status:

`GOLD_V3_81_COMPACT_SUPPORT_BUNDLE_READY_AUDIT_ONLY`

Blocked status:

`GOLD_V3_81_COMPACT_SUPPORT_BUNDLE_BLOCKED_AUDIT_ONLY`

## 1. Purpose

Stage81 creates a compact, upload-friendly support bundle so the human does not need to search through large runtime folders or upload huge logs.

Human concern:

- error-time folders must not be confusing,
- the required file to upload must be obvious,
- log files must not become too large to review.

Stage81 therefore creates one small primary upload file:

`upload_first.txt`

This file is the first file to paste/upload when an error happens.

## 2. Non-negotiable constraints

- GOLD V3 only.
- GOLD V2, old GOLD, and DISC8 remain quarantined.
- Do not read, use, reference, compare against, or fallback to GOLD V2, old GOLD, or DISC8.
- Do not use Stage41 feature-only snapshot as a trading source.
- Do not send Discord notifications.
- Do not place MT5 orders.
- Do not call AI APIs.
- Do not enable live hook, live evaluator, or final signal.
- Do not manually remove or demote candidates/profiles.
- Required pool policy:

`poolから外さない。rolling health gateに判断させる。`

## 3. CSV closed-row contract

Preserve:

- `csv_contract: open/in-progress candles are not written to CSV`
- `csv_open_bar_exclusion_required: false`

## 4. Output model

Short immutable support bundle directory:

`Files/FX_OUTPUTS/gold_v3/81c/YYYYMMDD/HHMMSS_bundle/`

Primary upload file:

`upload_first.txt`

No existing bundle file may be overwritten. If the directory exists, a retry suffix is added.

## 5. Compactness rules

Stage81 must not copy full large logs by default.

Instead it writes:

- status summary from Stage80, Stage76, and latest Stage79 if present,
- file index with sizes and recommended action,
- small tails of important logs,
- path of the latest immutable evidence run,
- blocker/validation summaries.

Default tail caps:

- event log tail: 80 lines,
- timing log tail: 80 lines,
- max inline file bytes: 64 KiB per source.

## 6. READY conditions

Stage81 is READY if:

- bundle directory was newly created,
- `upload_first.txt` was written,
- `file_index.csv` was written,
- Stage80 summary exists or the absence is explicitly recorded,
- live/external flags remain false,
- no oversized source file was copied in full,
- blocker_count is zero.

READY does not approve live release.

## 7. Outputs

Inside the Stage81 bundle directory:

- `upload_first.txt`
- `file_index.csv`
- `bundle_summary.json`
- `blockers.csv`
- `validation.csv`
- `report.md`

The BAT prints the exact `upload_first.txt` path.

## 8. Runner and BAT

Script:

`scripts/gold_v3_runtime/gold_v3_81_compact_support_bundle_audit.py`

BAT:

`scripts/gold_v3_runtime/bat/run_gold_v3_81_compact_support_bundle_audit.bat`
