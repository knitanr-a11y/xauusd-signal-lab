# NEXT CHAT HANDOFF: GOLD V2 25C37 DONE -> 25C38 NEXT

Date: 2026-06-07
Repo: `knitanr-a11y/xauusd-signal-lab`
Current mode: **audit-only**

## Absolute safety / scope rules

- GOLD V2 is still **audit-only**.
- Old GOLD / DISC8 remain quarantined due to suspected HTF open-time inconsistency.
- `REQUEST_MORE_AUDIT` is **not** source recovery approval.
- Do not perform source recovery, source mutation, live evaluator unblock, final signal, MT5 order, Discord notification, AI API, live hook, or live evaluator execution unless the user gives explicit approval.
- `NO_SIGNAL` must not send Discord.
- Do not approximate or reimplement source-of-truth behavior.
- Prefer audited source-of-truth artifacts and explicit output files.
- Continue using integrated audit-only scripts instead of fragmented meta-audit stages.

## Current latest step

Latest completed step:

```text
25C37_COREB_G1_ADJUSTED_NARROWING_DRY_RUN_AUDIT_ONLY
```

Status:

```text
COREB_G1_ADJUSTED_NARROWING_DRY_RUN_COMPLETED_AUDIT_ONLY_RESULT_REVIEW_REQUIRED
```

Next recommended step:

```text
25C38_COREB_G1_ADJUSTED_NARROWING_RESULT_REVIEW_AUDIT_ONLY
```

25C37 summary flags:

```json
{
  "audit_only": true,
  "dry_run_executed": true,
  "condition_changed": false,
  "full_coreb_parity": false,
  "variant_count": 4,
  "best_variant": "A003_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8_PAIR",
  "best_left_only": 225,
  "best_right_only": 200,
  "best_both": 46,
  "any_exact_match": false,
  "source_recovery_executed": false,
  "source_mutation_executed": false,
  "coreb_live_evaluator_unblocked": false,
  "next_recommended_step": "25C38_COREB_G1_ADJUSTED_NARROWING_RESULT_REVIEW_AUDIT_ONLY",
  "total_stop_rows": 0
}
```

## 25C37 variant result recap

Baseline:

| variant | replay_g1_rows | both | left_only | right_only | exact_match |
|---|---:|---:|---:|---:|---|
| BASELINE_CURRENT | 981 | 168 | 813 | 78 | False |

Adjusted bundle results:

| variant | replay_g1_rows | both | left_only | right_only | exact_match |
|---|---:|---:|---:|---:|---|
| A001_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8 | 437 | 68 | 369 | 178 | False |
| A002_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8U | 644 | 99 | 545 | 147 | False |
| A003_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8_PAIR | 271 | 46 | 225 | 200 | False |
| A004_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC10_PAIR | 644 | 99 | 545 | 147 | False |

Delta from baseline:

| variant | left_only_delta | right_only_delta | both_delta | replay_g1_rows_delta |
|---|---:|---:|---:|---:|
| A001 | -444 | +100 | -100 | -544 |
| A002 | -268 | +69 | -69 | -337 |
| A003 | -588 | +122 | -122 | -710 |
| A004 | -268 | +69 | -69 | -337 |

Interpretation:

- A003 has the strongest net left_only reduction among adjusted candidates, but still over-narrows: right_only rises to 200 and both falls to 46.
- A002 and A004 are equivalent in the 25C37 output: both 99, left_only 545, right_only 147.
- No exact match was achieved.
- CoreB live evaluator remains blocked.

## Path / artifact context

25C37 generated local output directory expected by scripts:

```text
FX_OUTPUTS/gold_v2_25c37_coreb_g1_adjusted_narrowing_dry_run_audit_only/
```

Important 25C37 outputs:

```text
01_25c37_GOLD_V2_COREB_G1_ADJUSTED_NARROWING_DRY_RUN_AUDIT_ONLY_REPORT.md
02_25c37_coreb_g1_adjusted_narrowing_dry_run_summary.json
04_25c37_variant_filter_contract.csv
05_25c37_variant_compare_matrix.csv
06_25c37_variant_delta_matrix.csv
07_25c37_variant_by_dataset_policy.csv
08_25c37_best_variant_left_only_samples.csv
09_25c37_acceptance_gate_matrix.csv
10_25c37_next_step_plan.csv
```

The user uploaded these files in the previous chat, but a new chat will not automatically have them. If needed, ask the user to paste the 25C37 outputs again, or design 25C38 to read them from local `FX_OUTPUTS`.

## Relevant recent implementation commits

25C34:

```text
be13344f27a40db05faedfa5c599258b54adde2a  docs spec
3d67a2951521cc6d54f6bdbd006ee1285ab57bd3  audit script
081892ac397c52d8feb90be7f6cc0684e1ebb858  BAT
```

25C35:

```text
986319fa439abdb603b8c531a9be8231a3c66faf  docs spec
f3fed4ba9fa1d6ddf1602f99f78f53adf0930592  audit script
4bc7be6461f0ecdfe78fabe1f1b7811be1d84b0a  BAT
```

25C36:

```text
738a66a5e367b135d0fa7c101f01d49b71ef9eb0  docs spec
9dd6c3453e07ac770c8e2a0496307963e8137cc8  audit script
0b48758930771ac2eb9b1cb28413b01fd694771a  BAT
```

25C37:

```text
1f4de76b1fedade57798f793037a2682a6ae452d  docs spec
928d0b3e1ab8739e149a07575e52111eb7d7a8d2  audit script
b0edfe990b17101a67d58c83d1fd88b9e24338b0  BAT
```

## Condensed history of this phase

### 25C28

- Built retention candidate plan from G1 filter narrowing.
- Primary review candidates were `same_count>=2/3/4/5 & unique_origins>=2`.
- Dry-run was blocked pending approval.

### 25C29

- Human accepted candidate review gate.
- Primary candidates: 4.
- Diagnostic candidates: 4.
- Proceeded to 25C30 after explicit human acceptance.

### 25C30

- Simulated removing the 4 primary candidates.
- Result: no G1 count effect.
- Baseline and narrowed both stayed `both=168`, `left_only=813`, `right_only=78`.

### 25C31

- Reviewed no-effect result.
- Found primary-filter G1 keys retained by other filters: `772/772`.
- Next focus shifted to retaining filters.

### 25C32

- Identified retaining filter drivers.
- `unique_origins>=2` retained all 772 primary G1 keys.
- Family summary: `unique_origins_only` was top retaining family.

### 25C33

- Built retention-aware bundle plan.
- Bundles:
  - B001: primary + `unique_origins>=2`
  - B002: primary + top 5 retainers
  - B003: unique_origins retainers only
- Dry-run blocked pending acceptance.

### 25C34

- Human accepted retention-aware dry-run.
- Results:
  - B001: left_only 545, right_only 147, both 99
  - B002: left_only 78, right_only 225, both 21
  - B003: no effect
- B002 improved left_only but over-narrowed heavily.

### 25C35

- Reviewed 25C34 over-narrowing.
- B002 not usable as-is.
- Required less destructive adjustment plan.

### 25C36

- Planned adjusted bundles:
  - A001: primary + `unique_origins>=2` + `same_count>=8`
  - A002: primary + `unique_origins>=2` + `same_count>=8&unique_origins>=2`
  - A003: primary + `unique_origins>=2` + `same_count>=8` + `same_count>=8&unique_origins>=2`
  - A004: primary + `unique_origins>=2` + `same_count>=10` + `same_count>=10&unique_origins>=2`
- Dry-run blocked pending acceptance.

### 25C37

- Human accepted adjusted dry-run.
- Results:
  - A001: left_only 369, right_only 178, both 68
  - A002: left_only 545, right_only 147, both 99
  - A003: left_only 225, right_only 200, both 46
  - A004: left_only 545, right_only 147, both 99
- No exact match. A003 best by left_only reduction, but still over-narrows materially.

## Next step: 25C38

Recommended next step:

```text
25C38_COREB_G1_ADJUSTED_NARROWING_RESULT_REVIEW_AUDIT_ONLY
```

Purpose:

- Review 25C37 adjusted bundle results.
- Compare A001/A002/A003/A004 trade-offs.
- Decide whether the path should continue with:
  - a less destructive threshold plan,
  - a separate right_only recovery review,
  - a hybrid variant plan,
  - or stop adjusted narrowing as insufficient.

Suggested status:

```text
COREB_G1_ADJUSTED_NARROWING_RESULT_REVIEW_COMPLETED_AUDIT_ONLY_NEXT_PLAN_REQUIRED
```

25C38 should remain audit-only result review. It must not run a new dry-run unless a later explicit acceptance gate is created and approved.

Suggested 25C38 outputs:

```text
00_不要_25c38_file_request_list.csv
01_25c38_GOLD_V2_COREB_G1_ADJUSTED_NARROWING_RESULT_REVIEW_AUDIT_ONLY_REPORT.md
02_25c38_coreb_g1_adjusted_narrowing_result_review_summary.json
03_25c38_input_audit.csv
04_25c38_adjusted_variant_tradeoff_matrix.csv
05_25c38_best_variant_review_matrix.csv
06_25c38_remaining_mismatch_decision_matrix.csv
07_25c38_next_step_plan.csv
```

Possible 25C38 conclusions to test:

- A003 best left_only reduction but too destructive.
- A001 may be the less destructive compromise compared with A003, but still raises right_only materially.
- A002/A004 are equivalent and less destructive but only moderate left_only improvement.
- No variant is CoreB-live ready.

## Suggested prompt for the next chat

```text
repo: knitanr-a11y/xauusd-signal-lab

まず以下を読んで続きからお願いします。

docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_25C37_DONE_25C38_NEXT_AUDIT_ONLY_20260607.md

GOLD V2は現在もaudit-onlyです。
REQUEST_MORE_AUDITはsource recovery承認ではありません。
旧GOLD/DISC8はHTF open-time不整合疑いで隔離済みです。
近似再実装は禁止です。
source-of-truthの監査済みartifactを優先してください。
Discord通知・MT5発注・AI API・live hook・live evaluator・final signalは明示許可までOFFです。
NO_SIGNAL時はDiscord通知しません。

25C37まで完了しました。
次は25C38_COREB_G1_ADJUSTED_NARROWING_RESULT_REVIEW_AUDIT_ONLYです。
25C38は結果レビューのみで、dry-run再実行や条件変更はしないでください。
```
