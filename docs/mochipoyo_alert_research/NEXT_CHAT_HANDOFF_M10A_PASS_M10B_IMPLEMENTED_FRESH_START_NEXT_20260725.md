# NEXT CHAT HANDOFF — M10A USER-LOCAL PASS / M10B IMPLEMENTED / FRESH START NEXT

Date: 2026-07-25  
Repo: `knitanr-a11y/xauusd-signal-lab`  
Branch: `feature/mochipoyo-alert-research`

## 1. Authoritative current state

M10A deterministic historical reproduction has passed on the user's local machine.

M10B is implemented and its design is frozen, but its independent fresh prospective start has NOT yet been created.

Current status:

`M10A_USER_LOCAL_REPRODUCTION_PASS_M10B_IMPLEMENTED_FRESH_START_PENDING_AUDIT_ONLY`

Everything remains audit-only.

All remain OFF/FALSE:

- Discord send
- MT5 orders
- live_ready
- final_signal
- real entry gate
- automatic live promotion

## 2. Existing forward monitors — DO NOT CHANGE

Keep running unchanged:

1. genuine source collector
2. M7C
3. M8C
4. M9V
5. M9Y

Immutable starts:

- M7C valid prospective start UTC: `2026-07-20T14:54:15Z`
- M9V start MT5 server time: `2026.07.24 11:04:00`
- M9Y start MT5 server time: `2026.07.24 12:45:00`

Never reset, re-freeze, backfill, or rerun their frozen initializers.

## 3. M10A user-local deterministic reproduction PASS

Formal record:

`config/mochipoyo_alert_research/m10a_gold_multitimeframe_payoff_user_local_reproduction_result_20260725.json`

Submitted package SHA256:

`c5e575b479dfbf38de87697f4afec0b2f4a02a09d57b13b4463a76dcd814600a`

Exact reproduced references:

| Reference | Count | PF | Payoff |
|---|---:|---:|---:|
| M5 entry | 842 | 1.537338444576352 | 0.7741597167 |
| M5 runner75 one-position | 837 | 1.6651962763806494 | 0.9795272214 |
| H1 entry | 171 | 2.814130403928734 | 1.0981972308 |
| H1 runner50 one-position | 159 | 2.8303858342555084 | 1.3365710884 |
| H4 entry native | 57 | 4.668798744063922 | 1.5200740097 |

Raw frozen branch reproduction also matched:

- M5 S1 = 1256
- M15 S2 = 1495
- H1 S3 = 191
- H4 S4 = 70

M10A audit confirms:

- `future_outcome_used_in_entry_gate=false`
- `historical_backfill=false`
- M9V unchanged
- M9Y unchanged
- Discord/MT5/live_ready/final_signal all false

Historical results remain research-exposed and are NOT forward validation.

## 4. M10B fresh prospective contract

Stage:

`M10B_GOLD_MULTI_TIMEFRAME_PAYOFF_FRESH_PROSPECTIVE_SHADOW`

Contract:

`config/mochipoyo_alert_research/m10b_gold_multitimeframe_payoff_fresh_prospective_shadow_contract_20260725.json`

Resolved-only clarification:

`config/mochipoyo_alert_research/m10b_resolved_only_materialization_addendum_20260725.json`

Pre-start review:

`config/mochipoyo_alert_research/m10b_implementation_prestart_review_20260725.json`

Runtime:

`scripts/mochipoyo_alert_research/m10b/python/m10b_runtime.py`

M10B reads the existing M9V v2 branch candidate ledger READ-ONLY.

Eligible upstream branches only:

- S1_M5
- S3_H1
- S4_H4

M10B does NOT use M9Y outputs as an upstream signal source.

Strict fresh eligibility:

`proxy_primary_time > M10B prospective_start_server_time`

A first-turn after M10B start belonging to a PRIMARY that occurred at/before M10B start is forbidden.

M10B start is independent and must be strictly later than both M9V and M9Y starts.

## 5. Frozen M10B payoff arms

### B0 M5 entry native

- frozen M9V S1_M5 upstream
- M5-specific reclaim: original PRIMARY - `0.15 * latest fully closed M5 Wilder ATR14`
- maximum 6 fully closed M1 bars
- actual entry at exact causal M1 open ask
- native M5 EXIT

### B1 M5 runner75

Same entry as B0.

At native M5 EXIT:

- latest fully closed M15 MACD(6,13) rising versus previous fully closed M15
- 75% runner when eligible
- runner exits on first causal M5 RCI9 turn-down decision at/after native EXIT
- one-position accounting

### B2 H1 entry native

- frozen M9V S3_H1 upstream
- original PRIMARY - `0.05 * latest fully closed H1 Wilder ATR14`
- fully closed M5 confirmation
- maximum 30 minutes
- native H1 EXIT

### B3 H1 runner50

Same entry as B2.

At native H1 EXIT:

- BOTH latest fully closed H4 MACD(6,13) and D1 MACD(6,13) rising versus their previous fully closed values
- 50% runner
- runner exits on first causal H1 RCI9 turn-down decision at/after native EXIT
- one-position accounting

### B4 H4 entry native

- frozen M9V S4_H4 upstream
- original PRIMARY price reclaim, no ATR offset
- fully closed M15 confirmation
- maximum 60 minutes
- native H4 EXIT only
- no runner

## 6. Resolved-only implementation contract

M10B does not insert unresolved native outcomes early into performance history.

Native base materialization is:

`RESOLVED_ONLY`

An upstream post-M10B-start candidate is materialized after its native branch EXIT resolves.

At that time, entry acceptance is deterministically reconstructed using ONLY bars/features that were fully closed and knowable at the original entry/reclaim decision.

The native EXIT result/value is NEVER used to decide entry eligibility.

For runner arms:

- native EXIT may be resolved while runner remains open
- open runner return is not included in resolved PF/WR
- the open runner blocks later same-arm entries under one-position accounting

This preserves the user's required resolved-only live-repro history rule without future leakage into entry logic.

## 7. M10B review gates

M5:

- operational 20 accepted
- interim 60
- formal 120

H1:

- operational 5 accepted
- interim 10
- formal 20

H4:

- descriptive checkpoint 5
- no formal claim before 20

All checkpoints are manual review only. Never auto-promote.

## 8. Forced reboot recovery now includes M10B

Recovery BAT remains:

`scripts/mochipoyo_alert_research/recovery/bat/01_recover_after_forced_reboot.bat`

It now protects stale locks for:

- collector
- M7C
- M9V
- M9Y
- M10B

It first verifies that NONE of these protected loop processes are running. If any are running, recovery blocks and touches no lock.

After a genuine forced reboot/power loss and successful recovery, restart order is:

1. MT5 / CSV exporter
2. collector
3. M7C
4. M8C
5. M9V
6. M9Y
7. M10B

Never rerun M10B BAT01 after its first successful initialization.

If MT5 raw CSVs permanently miss the PC-off interval, that interval is unobserved forward time for M9V/M9Y/M10B and must not be backfilled or reconstructed using future outcomes.

## 9. Exact user action now

First Fetch/Pull the latest `feature/mochipoyo-alert-research` branch.

Keep collector / M7C / M8C / M9V / M9Y running unchanged.

Go to:

`scripts/mochipoyo_alert_research/m10b/bat/`

Run exactly:

### Step 1 — ONE TIME ONLY

`01_initialize_fresh_runtime_once.bat`

Success display:

`[M10B INIT PASS] fresh start=YYYY.MM.DD HH:MM:SS`

That timestamp becomes the immutable M10B fresh prospective start in MT5 server time.

After INIT PASS, NEVER run BAT01 again.

If blocked, do not delete/reset anything; submit the full console output.

### Step 2 — ONE TIME bootstrap check

`02_run_shadow_once.bat`

Success display starts with:

`[M10B PASS]`

Then run:

`05_open_latest_results.bat`

Submit only:

`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10B\LATEST\99_UPLOAD_PACKAGE.zip`

Do NOT run BAT03 yet.

Review that first M10B package for:

- frozen start receipt
- prefix integrity
- post-start-only candidate eligibility
- resolved-only materialization
- zero/preliminary arm counts
- one-position behavior
- safety flags

Only after that bootstrap review should BAT03 persistent M10B collection be allowed.

## 10. Next chat restart point

Read first:

1. `docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M10A_PASS_M10B_IMPLEMENTED_FRESH_START_NEXT_20260725.md`
2. `config/mochipoyo_alert_research/current_state_20260725.json`
3. `config/mochipoyo_alert_research/next_action_20260725.json`
4. `config/mochipoyo_alert_research/m10a_gold_multitimeframe_payoff_user_local_reproduction_result_20260725.json`
5. `config/mochipoyo_alert_research/m10b_gold_multitimeframe_payoff_fresh_prospective_shadow_contract_20260725.json`
6. `config/mochipoyo_alert_research/m10b_resolved_only_materialization_addendum_20260725.json`
7. `config/mochipoyo_alert_research/m10b_implementation_prestart_review_20260725.json`
8. `config/mochipoyo_alert_research/forced_reboot_recovery_contract_20260724.json`

Current next state:

`M10B_FRESH_START_BOOTSTRAP_NEXT`
