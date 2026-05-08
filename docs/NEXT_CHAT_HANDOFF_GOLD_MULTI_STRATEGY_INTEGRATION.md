# NEXT CHAT HANDOFF - GOLD Multi-Strategy Integration Planning

Use this handoff when continuing the H1 down / SELL signal work or when preparing later integration with the existing BUY-side C_ENV 72h setup.

## Repository

```text
knitanr-a11y/xauusd-signal-lab
```

## Read this first

```text
docs/GOLD_SIGNAL_INTEGRATION_ROADMAP_BUY_C_ENV_AND_H1_SELL.md
```

For the BUY-side details, also read:

```text
docs/GOLD_C_ENV_RR2_72H_SIGNAL_DESIGN.md
docs/NEXT_CHAT_HANDOFF_GOLD_C_ENV_RR2_72H.md
```

## Current decision

The BUY-side C_ENV RR2 72h setup has reached an isolated dry-run base, but it should not yet be connected to demo autotrade or mixed into the existing Mochipoyo live/demo/autotrade flow.

The next priority is to complete the separate H1 down / SELL signal first, using the same isolated lifecycle.

Recommended order:

```text
1. Freeze BUY-side C_ENV 72h as isolated dry-run PASS.
2. Build H1 SELL signal separately.
3. Validate H1 SELL with research/backtest and M5 first-touch.
4. Add H1 SELL notification preview and order-intent preview.
5. Add H1 SELL live scan once.
6. Add H1 SELL position monitor once.
7. Add H1 SELL dry-run cycle runner.
8. Only after both BUY and SELL pass, build a multi-strategy router.
9. Only after router pass, consider demo autotrade dry-run integration.
```

## BUY-side current condition ID

```text
GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H
```

## BUY-side current status

```text
Research/backtest: PASS as a sparse candidate
Notification preview: PASS
Order intent preview: PASS
Live scan once: PASS
Position monitor once: PASS
Combined dry-run cycle runner: PASS
No-signal / no-position path: PASS
Existing Mochipoyo integration: NOT CONNECTED
Demo autotrade order placement: NOT CONNECTED
Discord real send: NOT CONNECTED
```

## BUY-side latest dry-run cycle result

The latest combined dry-run cycle had:

```text
cycle_ok: true
live_scan_returncode: 0
position_monitor_returncode: 0
```

Live scan:

```text
candidate_count: 24
latest_candidate_entry_time: 2026-04-17 07:45:00
latest_m15_close_time: 2026-05-08 13:00:00
signal_found: false
reason: NO_SIGNAL_ON_LATEST_CONFIRMED_M15
```

Position monitor:

```text
signals_monitored: 0
close_intent_created: 0
reason: NO_DRY_RUN_SIGNAL_CREATED_ROWS
```

Interpretation:

```text
The dry-run framework works correctly.
There was no new BUY signal on the latest confirmed M15 bar.
No position existed to monitor.
```

## BUY-side scripts currently available

```text
scripts/run_gold_c_env_rr2_72h_live_scan_once.py
scripts/run_gold_c_env_rr2_72h_position_monitor_once.py
scripts/run_gold_c_env_rr2_72h_dry_run_cycle.py
```

Single BUY-side dry-run cycle command:

```cmd
python scripts\run_gold_c_env_rr2_72h_dry_run_cycle.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\research_results\gold_c_env_rr2_72h_live_scan
```

Repeated 15-minute BUY-side dry-run command:

```cmd
python scripts\run_gold_c_env_rr2_72h_dry_run_cycle.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --out-dir data\research_results\gold_c_env_rr2_72h_live_scan --cycles 0 --sleep-seconds 900
```

`--cycles 0` is an infinite loop. Stop it with Ctrl+C.

## BUY-side dry-run output directory

```text
data/research_results/gold_c_env_rr2_72h_live_scan/
```

Main result files:

```text
latest_scan_result.json
latest_position_monitor_result.json
latest_dry_run_cycle_result.json
dry_run_cycle_log.csv
signal_ledger.csv
close_intent_log.csv
```

## H1 SELL work should align with this output shape

The H1 SELL side should not reuse the BUY-side output directory. Create a dedicated directory such as:

```text
data/research_results/gold_h1_sell_<short_name>_live_scan/
```

The H1 SELL side should eventually create its own scripts such as:

```text
scripts/run_gold_h1_sell_<short_name>_live_scan_once.py
scripts/run_gold_h1_sell_<short_name>_position_monitor_once.py
scripts/run_gold_h1_sell_<short_name>_dry_run_cycle.py
```

## H1 SELL direction-specific warnings

SELL is not just BUY with labels flipped. Be careful with these differences:

```text
Entry direction: SELL
TP is below entry
SL is above entry
TP touch: M5 low <= tp_price
SL touch: M5 high >= sl_price
Same M5 conflict: conservative priority should be defined explicitly
R calculation: (entry_price - exit_price) / risk_price
close_side for close intent: BUY
```

## Required H1 SELL dry-run lifecycle

Use this sequence:

```text
1. Research/backtest script
2. Signal review export
3. Notification preview and order-intent preview
4. Live scan once
5. Position monitor once
6. Combined dry-run cycle runner
7. Multi-strategy router only after PASS
```

## Later router target

After BUY-side C_ENV 72h and H1 SELL both pass isolated dry-run, create a router such as:

```text
scripts/run_gold_multi_strategy_dry_run_cycle.py
```

Initial router responsibilities:

```text
- Run each strategy dry-run cycle once
- Collect latest_dry_run_cycle_result.json from each strategy
- Normalize status fields
- Write combined result JSON and CSV
- Keep order/close intents dry-run only
- Do not connect to existing Mochipoyo yet
- Do not send Discord yet
- Do not place MT5 orders yet
```

Possible router output directory:

```text
data/research_results/gold_multi_strategy_dry_run/
```

Possible router outputs:

```text
latest_multi_strategy_cycle_result.json
multi_strategy_cycle_log.csv
strategy_status_latest.csv
combined_order_intent_dry_run.jsonl
combined_close_intent_dry_run.jsonl
```

## Integration guardrails

Do not do the following yet:

```text
- Do not write to existing Mochipoyo trigger state
- Do not write to existing Mochipoyo notification ledger
- Do not send Discord messages
- Do not place MT5 orders
- Do not write to existing autotrade order-intent files
- Do not mix BUY and SELL ledgers before each is validated separately
```

Before any demo autotrade integration, confirm:

```text
- Each strategy has unique condition_id and strategy_id
- Each strategy has its own signal_key format
- Signal duplicate filtering works
- Close intent duplicate filtering works
- M5 NO_M5_PATH behavior is preserved
- Forming candle policy is explicit
- BUY/SELL R calculations are correct
- Time exit logic is correct for both directions
```

## Suggested next prompt for H1 SELL chat

```text
GitHubリポジトリ knitanr-a11y/xauusd-signal-lab の以下を最初に読んで、H1下落シグナルの続きから進めてください。

docs/GOLD_SIGNAL_INTEGRATION_ROADMAP_BUY_C_ENV_AND_H1_SELL.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_INTEGRATION.md

現在、BUY側の GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H は isolated dry-run 基盤までPASSしています。
ただし既存もちぽよ live/demo/autotrade にはまだ接続していません。

次はH1下落/SELLシグナルを、BUY側と同じ粒度で専用research/backtest、notification preview、order intent preview、live scan once、position monitor once、dry-run cycle runnerまで作りたいです。

重要:
- BUY側とはまだ混ぜない
- 既存もちぽよ系にはまだ書かない
- SELL専用のdry-run output directoryを使う
- SELLなのでTP/SL判定、R計算、close_sideをBUY側と逆向きに正しく実装する
- 最終的にはBUY側とSELL側をmulti-strategy routerで統合する予定です
```
