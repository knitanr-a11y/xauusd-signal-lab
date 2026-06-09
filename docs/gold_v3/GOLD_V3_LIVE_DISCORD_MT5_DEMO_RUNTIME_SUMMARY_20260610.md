# GOLD V3 Live Discord / MT5 Demo Runtime Summary

Created: 2026-06-10 JST  
Repository: `knitanr-a11y/xauusd-signal-lab`

## 0. Current policy

GOLD V3 was moved from pure audit-only candidate review into a controlled live-runtime preparation path.

Important policy decisions:

- GOLD V3 ranked candidates are the active source for the live notification path.
- GOLD V2 / old GOLD / DISC8 remain quarantined and are not used.
- Discord notification is for signal detection.
- MT5 is demo-only.
- MT5 execution results are not posted to Discord.
- MT5 execution results are stored to files for later verification.
- Discord loop and MT5 demo executor loop are separate BATs.
- NO_SIGNAL is not posted to Discord.
- Same signal must not be notified or executed every minute.
- Both Discord and MT5 loops use post-minute lag to avoid reading incomplete candle/snapshot data.

## 1. Ranked candidates fixed by Stage36

Stage36 created the final ranked naming/contract packet from Stage35 outputs.

Ranking basis:

1. `profit_factor_final` descending
2. `win_rate_final` descending
3. `sum_result_usd_final` descending

Ranked candidate order:

| rank | packet | candidate |
|---:|---:|---|
| R01 | 7 | `R01_P7_R1_ONLY_CD60_PRUNE_015` |
| R02 | 8 | `R02_P8_R1_ONLY_CD60_PRUNE_015` |
| R03 | 1 | `R03_P1_R1_ONLY_CD60_PRUNE_111` |
| R04 | 4 | `R04_P4_R1_ONLY_CD60_PRUNE_115` |
| R05 | 9 | `R05_P9_MAIN_R1_R2_CD90_PRUNE_133` |
| R06 | 11 | `R06_P11_MAIN_R1_R2_CD90_PRUNE_132` |
| R07 | 13 | `R07_P13_MAIN_R1_R2_CD120_PRUNE_122` |

Stage36 output location:

```text
FX_OUTPUTS/gold_v3/36_final_ranked_candidate_contract_audit_only/
```

Important Stage36 files:

```text
gold_v3_36_ranked_candidate_contract.csv
gold_v3_36_final_filter_contract.csv
gold_v3_36_summary.json
GOLD_V3_36_FINAL_RANKED_CANDIDATE_CONTRACT_AUDIT_ONLY_REPORT.md
```

## 2. Discord notification format

User-specified signal notification format:

```text
Title:
GOLD BUY
or
GOLD SELL

Body order:
rank
entry time (JST)
entry price
TP/SL
```

Example:

```text
GOLD SELL

rank: 1 R01_P7_R1_ONLY_CD60_PRUNE_015
entry time (JST): 2026-06-10 01:15:00 JST
entry price: 2345.120
TP/SL: 2335.120 / 2350.120
```

MT5 result notifications must not be sent to Discord. Only signal detection and fatal/error conditions are posted.

## 3. Stage37: ranked live Discord notifier

Script:

```text
scripts/gold_v3_runtime/gold_v3_37_ranked_live_discord_notify.py
```

Purpose:

- Read Stage36 ranked candidate contract.
- Read Stage36 final filter contract.
- Read latest live candidate/feature snapshot.
- Select matching ranked GOLD V3 candidate signals.
- Apply final exclusion filters such as Saturday exclusion and selected band cuts.
- Send Discord signal notification if a signal is selected.
- Do not notify NO_SIGNAL.
- Do not call MT5 directly.
- Write selected/latest signal for MT5 executor.

Important behavior:

- Same candle/direction is ranked, and by default only the highest-ranked candidate is selected.
- `--notify-all-hits` is intentionally not used in the normal BAT.
- Duplicate signals are suppressed with `dedupe_key`.
- `latest_signal.json` is updated under `live_runtime/current`.

Dedupe key:

```text
entry_time_utc + direction + packet_row
```

Stage37 main outputs:

```text
FX_OUTPUTS/gold_v3/37_ranked_live_discord_notify/gold_v3_37_summary.json
FX_OUTPUTS/gold_v3/37_ranked_live_discord_notify/gold_v3_37_signal_dispatch_log.csv
FX_OUTPUTS/gold_v3/37_ranked_live_discord_notify/gold_v3_37_event_log.csv
FX_OUTPUTS/gold_v3/live_runtime/current/latest_signal.json
FX_OUTPUTS/gold_v3/live_runtime/logs/signal_events_YYYYMMDD.csv
```

## 4. Stage38: minute loop for Discord notification

Script:

```text
scripts/gold_v3_runtime/gold_v3_38_live_minute_loop.py
```

BAT:

```text
scripts/gold_v3_runtime/bat/GOLD_V3_38_LIVE_MINUTE_LOOP_DISCORD.bat
```

Purpose:

- Run Stage37 every minute.
- Use post-minute lag so candle/snapshot files have time to settle.
- Default timing is every minute at `00 seconds + 5 seconds`.

Timing:

```text
xx:xx:00 candle/snapshot update window starts
xx:xx:05 Discord detection loop runs
```

Default execution:

```bat
python scripts\gold_v3_runtime\gold_v3_38_live_minute_loop.py --loop --enable-discord
```

Error behavior:

- If Stage37 returns non-zero, times out, or Stage38 itself raises an exception, Discord error notification is sent.
- KeyboardInterrupt/manual stop also attempts to send a Discord stop notification.
- NO_SIGNAL is not an error and is not posted.

Error Discord titles:

```text
GOLD V3 LOOP ERROR
GOLD V3 LOOP EXCEPTION
GOLD V3 LOOP STOPPED
```

Loop log retention:

```text
FX_OUTPUTS/gold_v3/38_live_minute_loop/gold_v3_38_loop_runs.csv
```

Default max retained loop rows:

```text
10080 rows = 60 minutes * 24 hours * 7 days
```

## 5. Stage39: live runtime layout

Script:

```text
scripts/gold_v3_runtime/gold_v3_39_live_runtime_layout.py
```

BAT:

```text
scripts/gold_v3_runtime/bat/GOLD_V3_39_LIVE_RUNTIME_LAYOUT.bat
```

Purpose:

- Initialize live runtime folders.
- Separate live state/log files from stage audit output folders.
- Keep current/latest files small.
- Keep daily append logs for later verification.
- Record the policy that MT5 results are log-only and are not posted to Discord.

Live runtime layout:

```text
FX_OUTPUTS/gold_v3/live_runtime/
  current/
    latest_status.json
    latest_signal.json
    latest_discord_dispatch.csv
    latest_mt5_result.csv

  logs/
    signal_events_YYYYMMDD.csv
    discord_events_YYYYMMDD.csv
    mt5_results_YYYYMMDD.csv
    mt5_events_YYYYMMDD.csv
    loop_runs_YYYYMMDD.csv

  state/
    dedupe_state.json
    live_loop.lock

  archive/
```

Policy:

- `current/` files are overwrite/latest state.
- `logs/` files are daily append files used for later verification.
- NO_SIGNAL detail is not appended every minute; counters are enough.
- MT5 result Discord notification is disabled.
- Notification BAT and MT5 demo executor BAT are separated.

## 6. Stage40: MT5 demo executor loop

Script:

```text
scripts/gold_v3_runtime/gold_v3_40_mt5_demo_executor_loop.py
```

BAT:

```text
scripts/gold_v3_runtime/bat/GOLD_V3_40_MT5_DEMO_EXECUTOR_LOOP.bat
```

Purpose:

- Run separately from Discord notification loop.
- Read `live_runtime/current/latest_signal.json` written by Stage37.
- Use separate post-minute lag.
- Check dedupe state before attempting execution.
- Attempt demo-account MT5 execution when enabled.
- Save MT5 results to log files only.
- Do not send MT5 execution results to Discord.
- Send Discord only for MT5 loop/execution errors.

Timing:

```text
xx:xx:05 Discord signal detection loop runs
xx:xx:07 MT5 demo executor loop reads latest_signal.json
```

BAT currently starts Stage40 with direct demo MT5 enabled:

```bat
python scripts\gold_v3_runtime\gold_v3_40_mt5_demo_executor_loop.py --loop --enable-mt5-demo-order
```

MT5 safety guards:

- Import failure blocks execution.
- MT5 initialize failure blocks execution.
- Account info failure blocks execution.
- Non-demo account blocks execution.
- Symbol select failure blocks execution.
- Tick retrieval failure blocks execution.
- Duplicate dedupe key blocks repeated execution.
- Execution result is logged.
- Execution result is not sent to Discord.
- MT5 errors are sent to Discord.

MT5 results are written here:

```text
FX_OUTPUTS/gold_v3/live_runtime/logs/mt5_results_YYYYMMDD.csv
FX_OUTPUTS/gold_v3/live_runtime/current/latest_mt5_result.json
```

## 7. Execution order

Initial setup, run once:

```bat
scripts\gold_v3_runtime\bat\GOLD_V3_39_LIVE_RUNTIME_LAYOUT.bat
```

Start Discord signal notification loop:

```bat
scripts\gold_v3_runtime\bat\GOLD_V3_38_LIVE_MINUTE_LOOP_DISCORD.bat
```

Start MT5 demo executor loop:

```bat
scripts\gold_v3_runtime\bat\GOLD_V3_40_MT5_DEMO_EXECUTOR_LOOP.bat
```

Recommended runtime order:

1. Confirm Stage36 outputs exist.
2. Run Stage39 layout initialization once.
3. Start Stage38 Discord loop.
4. Confirm `live_runtime/current/latest_signal.json` updates.
5. Start Stage40 MT5 demo executor loop.
6. Verify `mt5_results_YYYYMMDD.csv` and `latest_mt5_result.json`.

## 8. Required live snapshot

Stage37 expects a live snapshot CSV from the live side.

Default search order:

```text
FX_OUTPUTS/gold_v3/live/gold_v3_live_candidate_snapshot.csv
FX_OUTPUTS/gold_v3/live/gold_v3_live_feature_snapshot.csv
FX_OUTPUTS/gold_v3/gold_v3_live_candidate_snapshot.csv
FX_OUTPUTS/gold_v3/gold_v3_live_feature_snapshot.csv
```

The snapshot must be small and fast to read. It should contain the latest confirmed bar/candidate rows, not full historical data.

Expected useful columns include:

```text
packet_row or source_scenario_key or variant_key
direction
entry_time_utc or feature_bar_open_utc
entry_price or close/bid/ask
source_rank if packet-specific rank_scope filters apply
features used by final_filter_contract.csv
optional tp_price/sl_price or tp/sl distance fields
```

## 9. Logging policy

Do not create a new folder every minute.

Keep current state in overwrite files:

```text
live_runtime/current/latest_status.json
live_runtime/current/latest_signal.json
live_runtime/current/latest_discord_dispatch.csv
live_runtime/current/latest_mt5_result.json
```

Keep important history in daily append files:

```text
live_runtime/logs/signal_events_YYYYMMDD.csv
live_runtime/logs/mt5_results_YYYYMMDD.csv
```

Do not append full NO_SIGNAL detail every minute. Use counters in `latest_status.json`.

Stage38 compact loop log keeps a rolling cap of 10080 rows by default.

## 10. Known remaining concerns

These items should be verified before trusting the live demo loop for decision-making:

1. Live snapshot generation is not implemented in this stage set.
2. Live snapshot must be atomically written by producer side if possible: write temp then rename.
3. Stage37 assumes rows already represent candidate-level live evaluations or contain enough columns to match ranked candidates and filters.
4. If live snapshot lacks required feature columns, final filters may not behave as intended.
5. Stage40 uses Python `MetaTrader5`; the terminal must be logged into the intended demo account.
6. Stage40 blocks non-demo account, but this guard should be verified locally.
7. Broker symbol naming may differ from `XAUUSD`; override `--symbol` if needed.
8. Lot size default is `0.01`; adjust only deliberately.
9. Stop-loss/take-profit defaults are `TP 10 USD / SL 5 USD` unless live snapshot supplies explicit prices or distances.
10. Multiple BAT instances should not be launched simultaneously; a lock file policy exists conceptually but should still be enforced more strictly if duplicate Windows processes are possible.
11. Discord webhook should be provided by environment variable `GOLD_V3_DISCORD_WEBHOOK_URL`, not hard-coded in BAT.
12. MT5 result Discord notification is intentionally disabled; only MT5 errors/stops notify Discord.

## 11. Key commits

- Stage36 ranked candidate contract script: `7c65ff65824f74cff308b55fb362eb78c990021e`
- Stage36 BAT: `5455650c217a5972e165bd8d4ae28ecf51fb5fb2`
- Stage37 Discord notifier initial add: `331de620988dfb96c06c3484d5006a1bff17664d`
- Stage38 minute loop add: `53ae3675beef88c554ee830f636c04a204951c0f`
- Stage38 loop BAT: `e5a0a2642f9a796f10116441ec593fbe6decf1eb`
- Stage38 log retention: `bc311a99a653a89b4dab91c299a4bdc4b4a34054`
- Stage39 live runtime layout: `65ab3c273820fde6a8b6e74ba34219bba46eaa20`
- Stage39 BAT: `b3128a9b5836b3d2aac77200d351c06ace0c3892`
- Stage40 MT5 demo executor skeleton: `1b4bf1b17f139a469acdf3f088d8b85ddd633125`
- Stage40 BAT initial add: `0589c544e304044f0bd16e79ad74522fe352d174`
- Stage37 latest signal integration: `1bedca0063b5804b1b063b8b1aacb3b27a416e29`
- Stage38 error Discord notifications: `762b0414c4b246c9f53f185ec873fda1c9a1e08a`
- Stage40 MT5 demo direct send + error Discord: `359959fba44394323d00099f56f6bc7f31c7f309`
- Stage40 BAT direct demo flag: `a5e60d17405b8d5571454d5185d3f3ac6c318226`

## 12. Next recommended checks

Before leaving this running unattended:

1. Run Stage39 BAT once.
2. Confirm `live_runtime/current/latest_status.json` exists.
3. Prepare a small live snapshot CSV.
4. Run Stage38 once with `--run-once --enable-discord` if testing manually.
5. Confirm Discord receives only `GOLD BUY` or `GOLD SELL` signal messages.
6. Confirm NO_SIGNAL is silent.
7. Confirm duplicate signal does not repeat every minute.
8. Run Stage40 once with demo MT5 terminal open and logged into demo.
9. Confirm non-demo account is blocked if accidentally connected.
10. Confirm `mt5_results_YYYYMMDD.csv` contains the result and no Discord MT5-result notification is sent.
