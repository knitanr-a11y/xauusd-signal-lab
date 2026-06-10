# GOLD V3 45 high-vol sibling + rolling health gate local run spec audit-only

Created JST: `2026-06-10`
Status: `GOLD_V3_45_HIGH_VOL_SIBLING_ROLLING_HEALTH_GATE_LOCAL_RUN_SPEC_READY_AUDIT_ONLY`

## Scope

This stage prepares a local audit-only runner for the current GOLD V3 honmei set:

1. `R01_P7_R1_ONLY_CD60_PRUNE_015`
2. `R02_P8_R1_ONLY_CD60_PRUNE_015`
3. `R03_P1_R1_ONLY_CD60_PRUNE_111`
4. `R04_P4_R1_ONLY_CD60_PRUNE_115`
5. `R05_P9_MAIN_R1_R2_CD90_PRUNE_133`
6. `R06_P11_MAIN_R1_R2_CD90_PRUNE_132`
7. `R07_P13_MAIN_R1_R2_CD120_PRUNE_122`
8. `R1_ONLY_CD90_PRUNE_050__R1_ONLY_CD90_PRUNE_050_S030__R1_ONLY_CD90_PRUNE_050_S024`

It adds exploratory high-volatility sibling candidates and applies a strict per-candidate rolling health gate.

This is not a live approval stage.

## Safety

- No MT5 order is sent.
- No Discord notification is sent.
- No AI API call is made.
- No live hook is enabled.
- No final signal behavior is enabled.
- GOLD V2 / old GOLD / DISC8 are not used.
- Stage41 feature-only snapshot is not used as a trading source.
- The BAT file is a local Python launcher only. It is not an MT5 execution BAT.

## Input files

The local runner expects these candle CSVs in the MT5 `Files` directory, or in a directory passed to the BAT/script:

- `goldsharp_m5.csv`
- `goldsharp_m15.csv`
- `goldsharp_h4.csv`

Optional files such as `goldsharp_m1.csv`, `goldsharp_h1.csv`, and `goldsharp_d1.csv` may exist but are not required for this Stage45 audit runner.

Required candle columns:

- `time`
- `open`
- `high`
- `low`
- `close`

The current implementation treats `time` as the same timestamp basis used by the exported Files candle CSVs.

## Feature definitions

### M15 ATR28

`m15_atr28` is calculated from M15 candles using a simple rolling mean of True Range over 28 M15 candles.

### H4 ret4

`h4_ret4 = h4_close / h4_close.shift(4) - 1`

The script supports two H4 feature availability modes:

- `closed`: H4 feature becomes available after the H4 candle closes. This is safer for live usage.
- `open`: H4 feature is asof-merged at the H4 candle open timestamp. This is useful for parity comparison if older Stage05 artifacts used open-time HTF merge semantics.

Default BAT mode is `closed`.

## Base entry families

### Source rank 1

- group: `GROUP_H4_RET4_MOMENTUM`
- side: `LONG` / `BUY` if later live-approved
- rule: `h4_ret4 >= 0.00751699`
- profile: `USDPRICE_TP150_SL60_H128`

### Source rank 2

- group: `GROUP_M15_ATR28_MID_VOL_RANGE`
- side: `LONG` / `BUY` if later live-approved
- rule: `3.59086 <= m15_atr28 <= 4.29321`
- profile: `USDPRICE_TP80_SL30_H64`

`MAIN_R1_R2` candidates are treated as a union of source-rank 1 and source-rank 2 events. Rank-scoped filters apply only to their matching source rank.

## High-volatility sibling rule

Each Stage43 honmei candidate receives three exploratory high-volatility sibling candidates.

High-vol condition:

`m15_atr28 >= rolling prior 60D q70 of m15_atr28`

Default profiles:

- `HV_TP180_SL70_H128`
- `HV_TP200_SL80_H128`
- `HV_TP220_SL90_H128`

The sibling keeps the original candidate filter chain and adds the high-vol condition. These siblings are not Stage36 source candidates. They are exploratory audit-only candidates.

## Strict rolling health gate

The strict gate runs per candidate label.

Default parameters:

- rolling virtual history window: `30` candidate opportunities
- minimum history before enforcement: `20` opportunities
- required rolling PF: `>= 1.10`
- required current virtual losing streak: `< 3`

Candidates that are not selected are still virtually monitored. This allows recovery instead of permanent stopping.

## Backtest result semantics

For a long entry:

- entry price: M15 close at entry timestamp
- judge timeframe: M5 future candles
- same M5 bar TP/SL collision: SL priority
- timeout result: final M5 close at horizon minus entry price
- complete horizon only: enabled by default

This is a local live-candle audit replay. Stage05 parity remains a separate review item if exact historical SOT parity is required.

## Local BAT usage

Default run from repo root or by double-clicking the BAT:

```bat
scripts\gold_v3_runtime\run_gold_v3_45_high_vol_sibling_strict_gate_walkforward_audit.bat
```

Explicit candle directory:

```bat
scripts\gold_v3_runtime\run_gold_v3_45_high_vol_sibling_strict_gate_walkforward_audit.bat "C:\path\to\MQL5\Files"
```

Explicit candle directory and H4 asof mode:

```bat
scripts\gold_v3_runtime\run_gold_v3_45_high_vol_sibling_strict_gate_walkforward_audit.bat "C:\path\to\MQL5\Files" closed
scripts\gold_v3_runtime\run_gold_v3_45_high_vol_sibling_strict_gate_walkforward_audit.bat "C:\path\to\MQL5\Files" open
```

## Output directory

By default outputs are written under:

`<candle_dir>\FX_OUTPUTS\gold_v3\45_high_vol_sibling_strict_gate_walkforward_audit_only`

## Output files

- `gold_v3_45_hv_sibling_candidate_definitions.csv`
- `gold_v3_45_all_candidate_opportunity_ledger.csv`
- `gold_v3_45_hv_sibling_all_candidate_summary.csv`
- `gold_v3_45_hv_sibling_best_candidates.csv`
- `gold_v3_45_hv_sibling_gate_experiment_summary.csv`
- `gold_v3_45_hv_sibling_strict_gate_trade_ledger.csv`
- `gold_v3_45_hv_sibling_strict_gate_candidate_summary.csv`
- `gold_v3_45_hv_sibling_strict_gate_monthly_summary.csv`
- `gold_v3_45_hv_sibling_rolling_walkforward_monthly_summary.csv`
- `gold_v3_45_hv_sibling_strict_gate_summary.json`
- `GOLD_V3_45_HIGH_VOL_SIBLING_STRICT_GATE_AUDIT_ONLY_REPORT.md`

## Local validation plan

1. Run the BAT in `closed` mode first.
2. Review `gold_v3_45_hv_sibling_gate_experiment_summary.csv`.
3. Review `gold_v3_45_hv_sibling_rolling_walkforward_monthly_summary.csv`.
4. If needed, run a second audit in `open` mode to compare HTF asof parity risk.
5. Do not connect the result to live notification or MT5 execution until a follow-up review explicitly approves the next audit-only stage.

## Stop conditions

Stop and inspect if any of these occur:

- Required candle files are missing.
- Output opportunity rows are zero.
- H4 asof mode materially changes conclusions.
- High-vol siblings improve only in the same sample but fail rolling monthly walk-forward.
- The gate reduces trades below the user-required operational minimum.

## Next stage

After the local run, compare local outputs against this chat's exploratory outputs and decide whether to freeze Stage45 gate parameters for a stricter walk-forward validation stage.
