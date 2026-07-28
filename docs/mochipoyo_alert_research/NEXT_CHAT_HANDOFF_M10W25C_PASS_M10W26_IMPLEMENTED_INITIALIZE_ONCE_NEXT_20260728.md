# MOCHIPOYO Alert Research handoff — M10W25C PASS / M10W26 implemented / initialize-once next

repo: `knitanr-a11y/xauusd-signal-lab`  
branch: `feature/mochipoyo-alert-research`

## Current formal state

`M10W25C_PASS_M10W26_PRESTART_IMPLEMENTATION_READY_INITIALIZE_ONCE_NEXT_AUDIT_ONLY`

The existing seven bounded-CSV V4 private-snapshot loops remain healthy and must stay running unchanged:

- M9V
- M9Y
- M10B
- M10E
- M10P
- M10P2
- M10W19

Collector, M7C and M8C also remain running unchanged.

## M10W25C result

Formal result:

`config/mochipoyo_alert_research/m10w25c_independent_reproduction_result_20260728.json`

The exact frozen M10W23 formulas were re-evaluated on the M10W25B prefix-causal `coverage_class=NEITHER` cohort:

- historical NEITHER rows: 5,917
- causal NEITHER rows: 5,913
- removed by causal audit: 4
- newly accepted rows without frozen outcomes: 0

MMO1 remains `STRONG_CANDIDATE` without any formula, threshold or horizon change:

- candidate count: 1,359
- accepted count: 437
- resolved count: 399
- train PF: 1.5140710842
- validation PF: 1.5477690866
- 2026 test: n=31, PF=2.5573099358
- all PF: 1.6157633609
- all net: +2706.4878973 bps
- all +2bps PF: 1.4008203483

Exact MMO1 formula:

- `m1_ret5_bps > 0.0`
- `m1_up_close_count5 >= 3`
- `m1_close_location >= 0.60`

Historical support is not fresh support. An independent fresh prospective shadow is required.

## M10W26 frozen design

Contract:

`config/mochipoyo_alert_research/m10w26_mmo1_causal_neither_fresh_prospective_shadow_contract_20260728.json`

Implementation audit:

`config/mochipoyo_alert_research/m10w26_prestart_implementation_audit_20260728.json`

M10W26 is a new independent audit-only shadow. It does not modify M10W19 or any existing runtime/start.

Frozen scope:

- GOLD/XAUUSD only
- MT5 server time
- closed-row contract
- M15 decision boundaries represented by exact M1 timestamps
- target regime:
  - D1 EMA20 > EMA30 > EMA40
  - H4 EMA20 > EMA30
  - H1 TORYS MACD line(6,13) > 0
  - H1 Wilder ATR14 trailing-100 percentile >= 0.67
- prefix-causal coverage class must equal `NEITHER`
- exact six M10W25 coverage families
- exact MMO1 three-condition formula
- LONG
- exact M1 entry ask
- exact M1 +240-minute exit bid
- one position
- no nearest-M1 fallback
- no pre-start candidate eligibility
- no historical backfill

## M10W26 implementation

Runtime and private-snapshot operator:

- `scripts/mochipoyo_alert_research/m10w26/python/m10w26_runtime.py`
- `scripts/mochipoyo_alert_research/m10w26/python/m10w26_runtime_v2.py`
- `scripts/mochipoyo_alert_research/m10w26/python/run_m10w26_private_snapshot.py`
- `scripts/mochipoyo_alert_research/m10w26/python/run_m10w26_private_snapshot_v2.py`

V2 performs these checks before writing the new start:

1. reviewed bounded-adapter migration remains PASS;
2. all six shared journals verify;
3. a M10W26-only private snapshot is copied under the adapter update lock;
4. all six frozen M10W25 causal coverage families run successfully;
5. short-family causal source-timing violations equal zero;
6. long families use no future exit reference and require no completed pair;
7. provisional start dry-run contains no post-start rows or candidates;
8. all required implementation SHA256 values are frozen into the runtime;
9. runtime/state/start-receipt creation is transactional;
10. an incomplete newly created M10W26 runtime self-rolls back without touching existing loops.

## Required user-local operation

Read first:

`scripts/mochipoyo_alert_research/m10w26/bat/00_READ_ME_FIRST.txt`

### 1. Fetch/Pull

Confirm branch `feature/mochipoyo-alert-research`, then Fetch/Pull.

### 2. Initialize exactly once

Run:

`scripts/mochipoyo_alert_research/m10w26/bat/01_initialize_fresh_start_once.bat`

Required output:

- `[M10W26 PRESTART ENGINE PASS] six causal coverage families verified before start freeze`
- `[M10W26 INIT PASS] fresh start=<MT5 server time>`

After INIT PASS, BAT01 is permanently forbidden.

### 3. Start persistent shadow

Run and keep open:

`scripts/mochipoyo_alert_research/m10w26/bat/03_run_shadow_forever.bat`

Wait for:

`[M10W26 PASS] CANDIDATES=<n> ACCEPTED=<n> RESOLVED=<n> OPEN=<n>`

### 4. Initial health audit

While M10W26 remains running, run:

`scripts/mochipoyo_alert_research/m10w26/bat/05_audit_initial_health.bat`

Upload only:

`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10W26_INITIAL_HEALTH\LATEST\99_UPLOAD_PACKAGE.zip`

### 5. Normal stop only when needed

Use only:

`scripts/mochipoyo_alert_research/m10w26/bat/04_stop_shadow_forever.bat`

Restart after initialization only with BAT03.

## Review gates

- operational: 20 resolved
- interim: 60 resolved
- formal: 120 resolved

No operational or interim result can automatically promote the candidate. Formal review is review-only.

## Absolute prohibitions

- Do not rerun BAT01/initializer for M9V, M9Y, M10B, M10E, M10P, M10P2 or M10W19.
- Do not run M10W26 BAT03 before INIT PASS.
- Do not run M10W26 BAT01 more than once after INIT PASS.
- Do not stop/restart the healthy seven V4 loops without a new incident.
- Do not taskkill or force-close loops.
- Do not manually edit/delete runtime, state, prestart audit, lock, STOP file, adapter snapshot or journal.
- Do not reset any prospective start.
- Do not backfill pre-start candidates.
- Do not send Discord messages.
- Do not place MT5 orders.
- Do not enable live-ready, final-signal or automatic promotion.
- M10V remains forbidden until M10P and M10P2 each have at least 20 resolved plus integrity PASS.

If any M10W26 BAT reports BLOCKED/REVIEW, preserve the full screen and all files. Do not clean up or retry blindly.
