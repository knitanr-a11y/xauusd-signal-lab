# GOLD V3 Stage107F Spec — NO_REGIME_BASELINE_AND_VOL_TPSL_AUDIT_ONLY

Created JST: `2026-06-12`

Repo: `knitanr-a11y/xauusd-signal-lab`

Stage:

```text
GOLD_V3_107F_NO_REGIME_BASELINE_AND_VOL_TPSL_AUDIT_ONLY
```

## Purpose

Stage107F preserves a backtest path that does **not** use regime arbitration, because regime may be unnecessary or may overfit.

Stage107F also introduces an audit-only volatility-adjusted TP/SL candidate path with a hard minimum profit width requirement:

```text
minimum TP width = 5.0 USD
minimum SL width = 5.0 USD unless explicitly overridden in later audit
```

This stage is audit-only. It must not change live runtime, Stage45, Stage69, candidate pool, Discord, MT5 execution, or final signal.

## Required comparison classes

Stage107F must compare:

```text
1. no_regime_long_only
2. no_regime_short_only
3. no_regime_dual_edge_global
4. regime_arbitration_reference_from_107E, if available
5. optional_vol_adaptive_tpsl, if exact M5 candles are available
```

## No-regime requirement

No-regime tests must not use `h4_dir`, `hv_state`, `session_bucket`, `weekday`, or any other regime key to choose LONG/SHORT.

Allowed no-regime policies:

- LONG-only resolved-only health gate.
- SHORT-only resolved-only health gate.
- GLOBAL dual-edge arbitration using only resolved LONG/SHORT histories across all entries, not regime-specific histories.

All histories must be based only on rows whose:

```text
exit_dt <= current entry_dt
```

## Volatility TP/SL candidate requirement

Volatility TP/SL may only be evaluated when M5 candles are available from an exact source path or known exact filename. No broad scan is allowed.

Candidate formula examples:

```text
TP = max(5.0, m15_atr28 * tp_mult)
SL = max(5.0, m15_atr28 * sl_mult)
```

Candidate multiplier grid:

```text
tp_mult: 0.50, 0.75, 1.00, 1.25
sl_mult: 0.25, 0.35, 0.50, 0.75
```

If M5 candles are not available, Stage107F must write a clear SKIPPED reason and still complete no-regime tests.

## Inputs

Primary input:

```text
FX_OUTPUTS/gold_v3/107c/gold_v3_107_long_short_proxy_ledger.csv
```

Optional reference input:

```text
FX_OUTPUTS/gold_v3/107ec/gold_v3_107e_top_regime_policy_configs.csv
```

Optional M5 sources for vol TP/SL evaluation:

```text
--m5-csv <path>
```

or exact filenames under MQL5/Files only:

```text
M5_backtest.csv
candles_history_M5.csv
candles_history_M5_backtest.csv
```

## Outputs

Implementation paths:

```text
docs/gold_v3/GOLD_V3_107F_NO_REGIME_BASELINE_AND_VOL_TPSL_AUDIT_ONLY_SPEC_20260612.md
scripts/gold_v3_runtime/gold_v3_107f_no_regime_baseline_and_vol_tpsl_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_107f_no_regime_baseline_and_vol_tpsl.bat
```

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107fc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107fc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107f_no_regime_policy_summary.csv
gold_v3_107f_no_regime_monthly_summary.csv
gold_v3_107f_no_regime_selected_trade_ledger.csv
gold_v3_107f_vol_tpsl_candidate_summary.csv
gold_v3_107f_vol_tpsl_selected_trade_ledger.csv
gold_v3_107f_comparison_summary.csv
gold_v3_107f_blocker_matrix.csv
gold_v3_107f_validation_matrix.csv
gold_v3_107f_summary.json
GOLD_V3_107F_NO_REGIME_BASELINE_AND_VOL_TPSL_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107F_NO_REGIME_BASELINE_AND_VOL_TPSL_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107F_NO_REGIME_BASELINE_AND_VOL_TPSL_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```

Even when BLOCKED, Stage107F must write `FX_OUTPUTS/gold_v3/107fc/paste_me.txt`.

## Non-goals

Stage107F does not approve live trading and does not choose the final system design.
