# NEXT CHAT HANDOFF — GOLD V3 117N DONE / 118 NEXT DEMO ALERT-ONLY RESTART REVIEW

Created JST: `2026-06-15`

## Current status

```text
GOLD_V3_117N_LIVE_VALID_JUNE_EXCEPTION_FEASIBILITY_READY
NEXT: GOLD_V3_118_DEMO_ALERT_ONLY_RESTART_REVIEW_AUDIT_ONLY
```

GOLD V3 remains audit-only overall.

Stage115/116 demo Discord alert-only loop is authorized. MT5 order execution, real account routing, final signal promotion, live order path, and automatic trade execution are still prohibited.

## Absolute prohibitions

Do not read, use, reference, fallback to, or compare against:

```text
GOLD V2
old GOLD
DISC8
Stage41 feature-only snapshot as a trading source
```

Do not mutate source CSV contracts. CSV latest row is contractually closed. Do not use open/as-of rows. Do not remove the candidate pool.

NO_SIGNAL must not notify Discord.

## Important current operational BAT

Demo alert-only loop BAT:

```text
scripts/gold_v3_runtime/bat/run_gold_v3_116_115_full_loop.bat
```

This is alert-only. It is not an order loop.

Recommended restart path for next chat:

1. Stop any old running BAT.
2. Pull latest repo.
3. Confirm no MT5 order path is enabled.
4. Start the 116/115 full loop only if the user wants demo Discord alert-only monitoring.

## BAT progress rule

From now on, BAT files should include progress display. Minimum pattern:

```text
[1/4] Working directory set
[2/4] Starting Python audit script
[3/4] Python script finished
[4/4] Output location
```

117N BAT was updated to follow this style:

```text
scripts/gold_v3_runtime/bat/run_gold_v3_117n_live_valid_june_exception_feasibility.bat
commit: 4a477d95c49d1cbdbc2d1fdc352034d3a18d517e
```

## Completed Stage117 chain summary

### 117F — 109C generator lineage

Decision:

```text
DIRECT_109C_WRITER_REFERENCE_FOUND
```

109C selected ledger inventory:

```text
FX_OUTPUTS/gold_v3/109c/gold_v3_109_selected_base_policy_ledger.csv
rows: 5571
min_entry_dt: 2025-08-12 09:00:00
max_entry_dt: 2026-05-29 16:00:00
```

Direct writer:

```text
scripts/gold_v3_runtime/gold_v3_109_base_policy_selection_review_packet_audit.py
```

109C does not search. It copies/tags the 107R6 best family ledger.

### 117G — 107R6 base ledger coverage

Decision:

```text
107R6_BASE_LEDGER_STOPS_BEFORE_JUNE_REGENERATE_107R6_REQUIRED
```

Input ledger:

```text
FX_OUTPUTS/gold_v3/107r6c/gold_v3_107r6_resolved_107q_best_family_ledger.csv
rows: 5571
max_entry_dt: 2026-05-29 16:00:00
june_rows: 0
```

### 117H — 107Q best family input coverage

Decision:

```text
107Q_BEST_FAMILY_STOPS_BEFORE_JUNE_REGENERATE_107Q_REQUIRED
```

Input ledger:

```text
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_best_family_trade_ledger.csv
rows: 5571
max_entry_dt: 2026-05-29 16:00:00
june_rows: 0
```

OHLC did have June coverage:

```text
M15 june rows: 919
M5 june rows: 2759
```

### 117I — 107Q generator input feasibility

Decision:

```text
107Q_INPUTS_HAVE_JUNE_RERUN_107Q_READY
```

107Q generator inputs:

```text
FX_OUTPUTS/gold_v3/107lc/gold_v3_107l_rehydrated_best_policy_ledger.csv
rows: 8565
max_entry_dt: 2026-06-05 15:15:00
june_rows: 8

FX_OUTPUTS/gold_v3/107mc/gold_v3_107m_loss_trim_frontier.csv
rows: 571
```

### 117J — shadow 107Q rerun

Decision:

```text
SHADOW_107Q_RERUN_NO_JUNE_ROWS_REVIEW_REQUIRED
```

Best family remained:

```text
family_id: F002
feature: score
op: <=
lookback_active_days: 20
target_active_days: 5
rows: 5571
max_entry_dt: 2026-05-29
june_rows: 0
```

The 107Q rerun worked. June rows were not retained by the selected F002 family.

### 117L — June removed 8 detail review

Decision:

```text
ALL_JUNE_107L_ROWS_REMOVED_BY_F002_SCORE_FILTER
```

Details:

```text
june_rows: 8
f002_threshold: 1715.7012987012986
removed_rows: 8
kept_rows: 0
june_win_rate: 0.5
june_profit_factor: 2.0
june_sum_result_usd: 37.5
```

The 8 June rows were all removed by:

```text
score <= 1715.701299
```

### 117M — June restore policy comparison

Decision:

```text
RESTORE_ALL_8_IS_POSITIVE_BUT_REVIEW_ONLY_NOT_AUTO_ADOPTED
```

Policy comparison:

```text
KEEP_F002_EXCLUSION:
trades: 5571
wins: 3550
losses: 2019
WR: 0.637229
PF: 3.129035
sum_result_usd: 18065.748438

RESTORE_ALL_8_JUNE_REVIEW_ONLY:
trades: 5579
wins: 3554
losses: 2023
WR: 0.637032
PF: 3.124068
sum_result_usd: 18103.248438
june_trades: 8
june_wr: 0.5
june_pf: 2.0
june_sum_result_usd: 37.5
```

Restoring all 8 increases total PnL by +37.5 but slightly lowers WR/PF. It is review-only, not auto-adopted.

### 117N — live-valid June exception feasibility

Decision:

```text
NO_PRETRADE_EXCEPTION_REVIEW_GATE_PASS_KEEP_F002_EXCLUSION
```

Candidate rows:

```text
candidate_rows: 4
review_gate_count: 0
```

No pre-trade-feature-only exception rule passed review gate. Therefore keep F002 exclusion.

## Current selected policy conclusion

Current best policy remains:

```text
KEEP_F002_EXCLUSION
F002 / score <= / lookback 20 / target 5
```

June 2026 produced 8 upstream 107L rows, but all are removed by F002. Review-only restoration is positive in raw PnL but not auto-adoptable, and no valid pre-trade exception gate passed.

## 2026 performance summary

Using current selected F002 exclusion.

Japanese fiscal year 2026 so far, `2026-04` onward:

```text
trades: 166
wins: 111
losses: 55
WR: 66.87%
PF: 3.615
sum_result_usd: +654.94
```

Calendar-year 2026 so far, `2026-01` onward:

```text
trades: 2102
wins: 1329
losses: 773
WR: 63.23%
PF: 2.937
sum_result_usd: +6972.79
```

## Live/demo restart guidance

Only demo Discord alert-only loop may be resumed.

Recommended next stage:

```text
GOLD_V3_118_DEMO_ALERT_ONLY_RESTART_REVIEW_AUDIT_ONLY
```

Suggested checks:

1. Confirm repo latest includes Stage116/115 full loop and 117N BAT progress update.
2. Confirm no MT5 order scripts are enabled.
3. Confirm Discord webhook env is set only for alert-only sending.
4. Run the full loop BAT only if user approves demo alert-only restart.
5. Expect NO_SIGNAL if latest closed candle is not in selected 109C/107Q ledger. This is currently normal.

## Next chat should not do

Do not implement order execution.
Do not promote review-only 8 June restore into live policy.
Do not bypass F002 exclusion.
Do not notify Discord for NO_SIGNAL.
Do not overwrite 109c/107qc/107r6c unless a new stage explicitly authorizes a shadow-to-source promotion review, and even then keep audit-only.
