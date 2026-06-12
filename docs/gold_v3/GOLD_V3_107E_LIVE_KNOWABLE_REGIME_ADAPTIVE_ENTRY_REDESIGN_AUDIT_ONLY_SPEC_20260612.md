# GOLD V3 Stage107E Spec — LIVE_KNOWABLE_REGIME_ADAPTIVE_ENTRY_REDESIGN_AUDIT_ONLY

Created JST: `2026-06-12`

Repo: `knitanr-a11y/xauusd-signal-lab`

Stage:

```text
GOLD_V3_107E_LIVE_KNOWABLE_REGIME_ADAPTIVE_ENTRY_REDESIGN_AUDIT_ONLY
```

## Purpose

Stage107E starts the transition from a single static signal condition plus health gate toward a regime-adaptive signal design.

The goal is not to create a 2025-only rule or a 2026-only rule. The goal is to audit whether live-knowable market regime information can choose among:

```text
LONG
SHORT
NO_TRADE
```

so that the system can adapt to multiple market states without using future information.

This stage is motivated by Stage107C/107D findings:

- Stage45-style health gate performance was materially optimistic versus resolved-only live rehydration.
- Resolved-only health gate optimization did not recover the old 65% / PF3-style performance.
- Entry/regime redesign is now required, but runtime must not be changed yet.

## Guardrails

GOLD V3 remains audit-only.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 as a trading source.

Do not mutate source CSVs, CSV contract, candidate pool, Stage45 runtime behavior, Stage69 runtime behavior, live evaluator, final signal, Discord, MT5 execution, or AI API.

CSV contract:

```text
open/in-progress candles are not written to CSV
CSV latest row is contractually closed
open/as-of treatment is forbidden
```

Pool policy:

```text
poolから外さない。rolling health gateに判断させる。
```

## Inputs

Primary input:

```text
FX_OUTPUTS/gold_v3/107c/gold_v3_107_long_short_proxy_ledger.csv
```

Optional references:

```text
FX_OUTPUTS/gold_v3/107c/gold_v3_107_direction_assumption_summary.json
FX_OUTPUTS/gold_v3/107dc/gold_v3_107d_top_resolved_only_configs.csv
```

Stage107E must report year coverage. If the input ledger does not include 2025 and 2026, it must explicitly state that cross-year adaptation cannot yet be fully judged from the available ledger.

## Live-knowable regime features

Stage107E may use only entry-time features already present in the Stage107 ledger, such as:

```text
is_high_vol
m15_atr28
m15_atr28_q
m15_atr28 >= m15_atr28_q
h4_ret4 sign
jst_hour
jst_weekday
hv_sibling
source_rank
profile_id
```

Stage107E must not use future TP/SL/exit outcome to define the regime or the entry rule. Outcome columns are allowed only for post-hoc scoring.

## Adaptive policy audit

For each current `entry_dt`, Stage107E may use only histories whose `exit_dt <= current entry_dt`.

Audit policy class:

```text
regime_side_switcher
```

For a given live-knowable regime key, maintain resolved-only historical performance for LONG and SHORT. At decision time:

```text
choose LONG if resolved LONG performance passes threshold and is sufficiently better than SHORT
choose SHORT if resolved SHORT performance passes threshold and is sufficiently better than LONG
otherwise choose NO_TRADE
```

Candidate selection within the chosen side is still proxy-only and audit-only; default to the first row by `priority`, `candidate_label`.

## Search dimensions

Regime keys:

```text
h4_dir
hv_state
atr_q70_state
session_bucket
h4_dir+hv_state
h4_dir+atr_q70_state
h4_dir+hv_state+session_bucket
h4_dir+hv_state+atr_q70_state
h4_dir+hv_state+jst_weekday
```

Policy parameters:

```text
history_window: 20, 30, 50
min_side_history: 10, 20, 30
side_pf_threshold: 1.00, 1.15, 1.30
side_margin: 1.00, 1.15, 1.30
```

Metrics:

```text
trades
no_trade_events
long_trades
short_trades
win_rate
profit_factor
sum_result_usd
negative_month_count
year_count
recent_2026_03_plus_profit_factor
recent_2026_05_06_profit_factor
```

## Required outputs

Implementation paths:

```text
docs/gold_v3/GOLD_V3_107E_LIVE_KNOWABLE_REGIME_ADAPTIVE_ENTRY_REDESIGN_AUDIT_ONLY_SPEC_20260612.md
scripts/gold_v3_runtime/gold_v3_107e_live_knowable_regime_adaptive_entry_redesign_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_107e_live_knowable_regime_adaptive_entry_redesign.bat
```

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107ec/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107ec/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107e_year_coverage.csv
gold_v3_107e_regime_raw_side_matrix.csv
gold_v3_107e_regime_policy_grid_summary.csv
gold_v3_107e_top_regime_policy_configs.csv
gold_v3_107e_top_policy_selected_trade_ledger.csv
gold_v3_107e_blocker_matrix.csv
gold_v3_107e_validation_matrix.csv
gold_v3_107e_summary.json
GOLD_V3_107E_LIVE_KNOWABLE_REGIME_ADAPTIVE_ENTRY_REDESIGN_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107E_LIVE_KNOWABLE_REGIME_ADAPTIVE_ENTRY_REDESIGN_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107E_LIVE_KNOWABLE_REGIME_ADAPTIVE_ENTRY_REDESIGN_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```

Even when BLOCKED, Stage107E must write `FX_OUTPUTS/gold_v3/107ec/paste_me.txt`.

## Non-goals

Stage107E does not:

- approve live trading;
- change runtime signal conditions;
- remove candidates from the pool;
- rewrite Stage45/69;
- repair HV sibling polarity;
- enable live evaluator or final signal.
