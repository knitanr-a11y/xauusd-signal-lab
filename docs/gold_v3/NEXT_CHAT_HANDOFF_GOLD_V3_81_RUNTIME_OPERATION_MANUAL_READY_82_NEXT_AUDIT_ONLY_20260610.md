# NEXT CHAT HANDOFF — GOLD V3 runtime operation manual ready / Stage82 next

Created JST: `2026-06-10`

Current status:

`GOLD_V3_RUNTIME_OPERATION_MANUAL_READY_AUDIT_ONLY`

Latest confirmed runtime stage:

`GOLD_V3_80_IMMUTABLE_RUNTIME_MONITOR_READY_AUDIT_ONLY`

## 1. Absolute constraints

- GOLD V3 only.
- GOLD V2 / old GOLD / DISC8 are quarantined.
- Do not read, use, reference, compare against, or fallback to GOLD V2, old GOLD, or DISC8.
- Do not use Stage41 feature-only snapshot as a trading source.
- GOLD V3 remains audit-only.
- Discord / MT5 / AI API / live hook / live evaluator / final signal remain OFF unless explicitly approved by the human.
- NO_SIGNAL must not notify Discord.
- Keep `manual_candidate_demotion_or_removal=false`.
- Keep pool policy exactly:

`poolから外さない。rolling health gateに判断させる。`

- Preserve CSV contract:

`csv_contract: open/in-progress candles are not written to CSV`

- Preserve:

`csv_open_bar_exclusion_required: false`

## 2. Current operational entry point

Normal monitor BAT:

```bat
scripts\gold_v3_runtime\bat\run_gold_v3_80_immutable_runtime_monitor_audit.bat
```

Stage80 behavior:

- every minute at second 05,
- read only latest CSV row timestamp,
- on new closed M15 row: Stage76 one-shot -> Stage79 immutable snapshot,
- if Stage80 becomes BLOCKED: auto-run Stage81 compact support bundle.

## 3. Latest confirmed Stage80 local result

Uploaded summary confirmed:

```text
status: GOLD_V3_80_IMMUTABLE_RUNTIME_MONITOR_READY_AUDIT_ONLY
immutable_runtime_monitor_ready: true
latest_m15_time: 2026-06-10 17:15:00
last_seen_m15_time: 2026-06-10 17:15:00
last_pipeline_run_time: 2026-06-10T14:41:05Z
last_stage76_returncode: 0
last_stage79_returncode: 0
last_stage76_seconds: 5.36922
last_stage79_seconds: 0.656929
last_total_seconds: 6.028188
latest_check_seconds: 0.0018
last_stage79_paste_path: ...\FX_OUTPUTS\gold_v3\79i\20260610\144110_1715_NO_SIGNAL\paste_me.txt
auto_support_bundle_enabled: True
blocker_count: 0
```

This confirms:

- Stage76 runner exists,
- Stage79 runner exists,
- Stage81 runner exists,
- Stage80 auto support bundle option is enabled,
- Stage76/Stage79 both returned 0,
- immutable snapshot path was produced,
- no blockers.

## 4. Human-facing runtime manual

Created:

```text
docs/gold_v3/GOLD_V3_RUNTIME_OPERATION_MANUAL_AUDIT_ONLY_20260610.md
```

Purpose:

- human operation guide,
- which BAT to start,
- which file to check first,
- error-time upload rule,
- folder map,
- do-not-upload-large-logs guidance,
- documentation maintenance rule.

Important rule going forward:

Whenever runtime behavior changes, update this manual in the same task/chat.

Update it when changing:

- main runtime BAT,
- output folder names,
- error support bundle behavior,
- paste/upload file names,
- safety flags,
- timing/log policy,
- immutable evidence policy,
- live release gate behavior.

## 5. Current important files

Normal status file:

```text
Files\FX_OUTPUTS\gold_v3\80_immutable_runtime_monitor_audit_only\gold_v3_80_PASTE_ME_IMMUTABLE_RUNTIME_MONITOR_SUMMARY.txt
```

Error-first upload file:

```text
Files\FX_OUTPUTS\gold_v3\81c\YYYYMMDD\HHMMSS_bundle\upload_first.txt
```

Latest immutable run evidence:

```text
Files\FX_OUTPUTS\gold_v3\79i\YYYYMMDD\RUN_ID\paste_me.txt
```

Do not ask the human to upload full event/timing CSVs first. Ask for Stage81 `upload_first.txt` first.

## 6. Stage76/79/80/81 summary

Stage76:

- full audit monitor with payload preview,
- records timing,
- payload preview only,
- external side effects OFF.

Stage79:

- immutable evidence snapshot,
- short path root `79i`,
- run_id folder,
- no overwrite,
- SHA256 manifest.

Stage80:

- operational audit-only runtime wrapper,
- every minute + 5 seconds,
- new M15 -> Stage76 -> Stage79,
- BLOCKED -> Stage81 auto support bundle.

Stage81:

- compact support bundle,
- primary file `upload_first.txt`,
- includes status and log tails only,
- avoids giant uploads.

## 7. Suggested Stage82 next

Recommended next stage:

`GOLD_V3_82_RUNTIME_DOC_SYNC_AND_OPERATOR_CHECKLIST_AUDIT_ONLY`

Purpose:

- verify runtime manual references existing files/BATs,
- verify Stage80 summary confirms Stage81 script present and auto support enabled,
- verify `upload_first.txt` rule is documented,
- verify no direct instruction tells user to upload giant logs first,
- optionally create a short operator checklist file:
  - start monitor,
  - check READY,
  - on error upload `upload_first.txt`,
  - stop monitor,
  - what not to touch.

Keep audit-only. Do not enable live release.

## 8. Do not do next unless explicit human approval

Do not enable:

- Discord notification,
- MT5 order execution,
- AI API calls,
- final signal,
- live hook,
- live evaluator,
- actual release.

Stage77 release gate remains blocked pending explicit human approval.
