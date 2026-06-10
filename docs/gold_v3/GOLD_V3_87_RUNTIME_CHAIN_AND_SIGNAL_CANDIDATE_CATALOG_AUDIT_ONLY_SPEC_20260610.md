# GOLD V3 Stage87 — Runtime Chain and Signal Candidate Catalog Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_87_RUNTIME_CHAIN_AND_SIGNAL_CANDIDATE_CATALOG_AUDIT_ONLY`

Expected READY status:

`GOLD_V3_87_RUNTIME_CHAIN_AND_SIGNAL_CANDIDATE_CATALOG_READY_AUDIT_ONLY`

Blocked status:

`GOLD_V3_87_RUNTIME_CHAIN_AND_SIGNAL_CANDIDATE_CATALOG_BLOCKED_AUDIT_ONLY`

## 1. Purpose

Stage87 has two goals:

1. Audit the intended runtime chain around Stage80 -> Stage76 -> Stage79 -> Stage85 -> Stage86.
2. Generate a human-readable signal candidate catalog from Stage69 candidate condition outputs so the operation manual can list each signal candidate name and condition in bullet form.

The human requested:

`トリセツには各シグナル候補の名前とその条件も箇条書きにしておいてください`

Stage87 does not invent candidate conditions. It reads current GOLD V3 audit artifacts and writes a catalog. If exact condition text is not present in a summary, Stage87 uses the Stage69 condition CSVs as source.

## 2. Non-negotiable constraints

- GOLD V3 only.
- GOLD V2, old GOLD, and DISC8 remain quarantined.
- Do not read, use, reference, compare against, or fallback to GOLD V2, old GOLD, or DISC8.
- Do not use Stage41 feature-only snapshot as a trading source.
- GOLD V3 remains audit-only.
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

## 4. Candidate catalog source priority

Stage87 reads candidate catalog data in this priority order:

1. `gold_v3_69_candidate_condition_summary.csv`
2. `gold_v3_69_detected_candidate_conditions.csv`
3. `gold_v3_68_candidate_selection_summary.csv`
4. Stage68/69 summaries as fallback metadata only

If candidate names exist but exact condition text is incomplete, Stage87 must state `condition_detail_source_missing_or_column_unknown` instead of guessing.

## 5. Runtime chain policy

Stage87 audits that the intended chain is documented as:

- Stage80 monitor checks latest closed M15 row.
- New closed M15 row runs Stage76.
- Stage76 result is frozen into Stage79 immutable evidence.
- Stage85 may create a trade review row preview only for SIGNAL.
- Stage86 guards durable ledger append.
- NO_SIGNAL is suppressed from trade review ledger.

Stage87 does not patch Stage80 to auto-run Stage85/86 yet unless a later stage explicitly implements that integration.

## 6. Outputs

Output folder:

`Files/FX_OUTPUTS/gold_v3/87_runtime_chain_and_signal_candidate_catalog_audit_only/`

Outputs:

- `gold_v3_87_signal_candidate_catalog.csv`
- `gold_v3_87_signal_candidate_catalog.md`
- `gold_v3_87_manual_candidate_bullets.md`
- `gold_v3_87_runtime_chain_matrix.csv`
- `gold_v3_87_blocker_matrix.csv`
- `gold_v3_87_validation_matrix.csv`
- `gold_v3_87_runtime_chain_and_signal_candidate_catalog_summary.json`
- `gold_v3_87_PASTE_ME_RUNTIME_CHAIN_AND_SIGNAL_CANDIDATE_CATALOG_SUMMARY.txt`
- `GOLD_V3_87_REPORT.md`

## 7. READY conditions

Stage87 is READY if:

- Stage69 condition summary or detected condition CSV exists,
- candidate catalog is written,
- manual bullet markdown is written,
- runtime chain matrix is written,
- candidate key order is documented exactly,
- no live/external flags are enabled,
- blocker_count is zero.

If no candidate source CSV exists, Stage87 is BLOCKED because candidate names/conditions cannot be listed safely.

## 8. Runner and BAT

Script:

`scripts/gold_v3_runtime/gold_v3_87_runtime_chain_and_signal_candidate_catalog_audit.py`

BAT:

`scripts/gold_v3_runtime/bat/run_gold_v3_87_runtime_chain_and_signal_candidate_catalog_audit.bat`
