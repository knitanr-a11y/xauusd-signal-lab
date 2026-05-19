# GOLD Strict 7 Signals

This folder is the isolated research area for the new GOLD strict seven-signal candidate set.

It is intentionally separated from old Mochipoyo, old GOLD multi-strategy, Discord, MT5 auto-trade, and AI review runtime files.

## Current purpose

The purpose of this folder is to regenerate and validate the seven current GOLD candidates under a strict no-future contract.

This folder does **not** send Discord notifications.
This folder does **not** place MT5 orders.
This folder does **not** mutate live runtime ledgers.
This folder does **not** call OpenAI.

## Strict no-future contract

All scripts in this folder must obey:

```text
- Trigger timeframe: M5 or lower.
- M5 trigger candle must be closed.
- H1/H4/D1 context is allowed only when context_close_time <= trigger_close_time.
- Forming H1/H4/D1 candles are not allowed in backtests.
- M1 first-touch is the preferred outcome adjudication.
- Same M1 bar TP/SL conflict defaults to SL first.
- GOLD pip convention here: 1 pip = 0.10 price.
- Minimum TP size is 20 pips.
```

## The seven current candidates

```text
1. SELL_KC_CCI150_LONDON_TP100_SL10
2. BUY_SWEEP_RECLAIM_RSI_TP150_SL10
3. BUY_STOCH_BB_KTURN_NY_TP150_SL10
4. SELL_DONCHIAN48_MACD_RANGE_NY_TP30_SL7P5
5. SELL_DONCHIAN96_MACD_RANGE_ALL_TP150_SL37P5_CD120
6. SELL_DONCHIAN96_MACD_RANGE_ALL_TP150_SL37P5_CD60
7. BUY_BB_RSI30_REJECTION65_NY_TP30_SL7P5
```

The source-of-truth strategy list is in:

```text
scripts/gold_strict_7_signals/gold_strict_7_signal_specs.py
```

The source-of-truth project document is:

```text
docs/GOLD_STRICT_7_SIGNAL_CANDIDATES_CURRENT_SCOPE.md
```

## Intended outputs

Default output directory:

```text
data/research_results/gold_strict_7_signal_candidates/
```

Main files:

```text
gold_strict_7_candidates_trades.csv
gold_strict_7_candidates_summary.csv
gold_strict_7_candidates_monthly.csv
gold_strict_7_candidates_overlap.csv
gold_strict_7_candidates_portfolio_summary.json
```

## Typical command

```bat
python scripts/gold_strict_7_signals/run_gold_strict_7_backtest_from_csv.py ^
  --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"
```

Explicit files can also be passed:

```bat
python scripts/gold_strict_7_signals/run_gold_strict_7_backtest_from_csv.py ^
  --gold-m1-csv "C:\...\goldsharp_m1.csv" ^
  --gold-m5-csv "C:\...\goldsharp_m5.csv" ^
  --gold-h1-csv "C:\...\goldsharp_h1.csv" ^
  --gold-h4-csv "C:\...\goldsharp_h4.csv" ^
  --gold-d1-csv "C:\...\goldsharp_d1.csv"
```

## Important warning

The code in this folder is research validation code.

Do not import it directly into live send loops or guarded demo send loops.
A separate adapter layer must be designed and approved before any Discord/autotrade integration.
