# GOLD V3 Live Discord / MT5 Demo Runtime Summary

Created: 2026-06-10 JST  
Last reviewed: 2026-06-10 JST  
Repository: `knitanr-a11y/xauusd-signal-lab`

## 0. New chat handoff: read this first

This document is the current handoff for the GOLD V3 live Discord / MT5 demo runtime path.

Continue from these facts:

- GOLD V3 ranked candidates from Stage36 are the only active source for the current live notification path.
- GOLD V2 / old GOLD / DISC8 remain quarantined and must not be used as fallback.
- Discord notification is for signal detection only.
- MT5 execution is demo-only.
- MT5 execution results must not be posted to Discord.
- MT5 execution results are saved to files for later verification.
- Discord loop and MT5 demo executor loop are separate BATs.
- NO_SIGNAL must not notify Discord.
- Same signal must not be notified or executed every minute.
- Both loops use post-minute delay: Discord at 5 seconds, MT5 at 7 seconds.
- Error/stop conditions in either loop should notify Discord.

Current runtime files and BATs:

```text
scripts/gold_v3_runtime/gold_v3_37_ranked_live_discord_notify.py
scripts/gold_v3_runtime/gold_v3_38_live_minute_loop.py
scripts/gold_v3_runtime/gold_v3_39_live_runtime_layout.py
scripts/gold_v3_runtime/gold_v3_40_mt5_demo_executor_loop.py

scripts/gold_v3_runtime/bat/GOLD_V3_38_LIVE_MINUTE_LOOP_DISCORD.bat
scripts/gold_v3_runtime/bat/GOLD_V3_39_LIVE_RUNTIME_LAYOUT.bat
scripts/gold_v3_runtime/bat/GOLD_V3_40_MT5_DEMO_EXECUTOR_LOOP.bat
```

Minimum run order:

```text
1. Run GOLD_V3_39_LIVE_RUNTIME_LAYOUT.bat once.
2. Confirm Stage36 outputs exist.
3. Prepare a small live snapshot CSV.
4. Start GOLD_V3_38_LIVE_MINUTE_LOOP_DISCORD.bat.
5. Confirm live_runtime/current/latest_signal.json updates.
6. Start GOLD_V3_40_MT5_DEMO_EXECUTOR_LOOP.bat only after demo MT5 terminal is ready.
```

Do not treat the current setup as fully unattended-ready until the unverified list in section 13 is checked.

## 1. Current policy

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
- Error/stop conditions in either loop should notify Discord.

## 2. Review result after implementation check

The document was reviewed against the current Stage37/38/39/40 files.

Verified as implemented:

- Stage37 writes a selected signal into `live_runtime/current/latest_signal.json` for Stage40.
- Stage38 runs Stage37 every minute with a default 5 second post-minute delay.
- Stage38 has rolling loop-log retention using `--max-log-rows 10080` by default.
- Stage38 sends Discord error notifications for Stage37 failure, timeout, loop exception, and stop handling.
- Stage39 initializes the live runtime directory layout.
- Stage40 runs separately with a default 7 second post-minute delay.
- Stage40 BAT enables demo MT5 order execution with `--enable-mt5-demo-order`.
- Stage40 blocks non-demo account mode before order execution.
- Stage40 logs MT5 results and does not send normal MT5 results to Discord.
- Stage40 sends Discord notifications for MT5 loop/execution errors.

Important caveats discovered during review:

1. `live_runtime/current/latest_discord_dispatch.csv` is intended to be a latest/current file. It should remain small. If it grows during testing, change Stage37 to overwrite that file instead of appending.
2. The broader `discord_events_YYYYMMDD.csv`, `mt5_events_YYYYMMDD.csv`, and `loop_runs_YYYYMMDD.csv` paths are part of the desired live-runtime layout. The currently implemented daily append logs are primarily `signal_events_YYYYMMDD.csv` and `mt5_results_YYYYMMDD.csv`; Stage38 still keeps compact loop logs under the Stage38 output folder.
3. Stage40 should only execute from a valid, current, intentionally selected signal. Before unattended use, verify that a failed Discord signal notification does not cause MT5 execution. The safest rule is: MT5 execution should require a latest signal with successful signal dispatch metadata.
4. The actual live snapshot producer is not implemented here. These stages consume the snapshot only.
5. Multiple-process lock enforcement is still a known hardening item. Do not start duplicate BAT instances.

## 3. Ranked candidates fixed by Stage36

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

## 4. Discord notification format

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

## 5. Stage37: ranked live Discord notifier

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
FX_OUTPUTS/gold_v3/live_runtime/current/latest_status.json
FX_OUTPUTS/gold_v3/live_runtime/logs/signal_events_YYYYMMDD.csv
```

## 6. Stage38: minute loop for Discord notification

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

## 7. Stage39: live runtime layout

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
    latest_mt5_result.json        # Stage40 writes this
    latest_mt5_result.csv         # legacy/current placeholder from Stage39 initialization if present

  logs/
    signal_events_YYYYMMDD.csv    # implemented
    mt5_results_YYYYMMDD.csv      # implemented
    discord_events_YYYYMMDD.csv   # reserved / future hardening
    mt5_events_YYYYMMDD.csv       # reserved / future hardening
    loop_runs_YYYYMMDD.csv        # reserved / future hardening

  state/
    dedupe_state.json
    live_loop.lock                # policy placeholder; strict lock enforcement still needs hardening

  archive/
```

Policy:

- `current/` files are intended as latest/current state.
- `logs/` files are daily append files used for later verification.
- NO_SIGNAL detail is not appended every minute; counters are enough.
- MT5 result Discord notification is disabled.
- Notification BAT and MT5 demo executor BAT are separated.

## 8. Stage40: MT5 demo executor loop

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

## 9. Execution order

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

## 10. Required live snapshot

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

## 11. Logging policy

Do not create a new folder every minute.

Keep current state in latest/current files:

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

## 12. Known remaining concerns

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
13. Before unattended use, verify that MT5 direct execution does not proceed from a signal whose Discord signal notification failed.
14. `latest_discord_dispatch.csv` should be monitored during test runs to ensure it does not grow unexpectedly; if it grows, Stage37 should be changed to overwrite that current file.

## 13. Unverified / not yet tested locally

The following items are not confirmed by this chat and must be checked on the user's Windows/MT5 environment:

1. Stage39 BAT actually creates `FX_OUTPUTS/gold_v3/live_runtime/` in the expected location on the user's machine.
2. The live snapshot CSV exists at one of the Stage37 default paths, or Stage38 is launched with `--live-snapshot` pointing to the real file.
3. The live snapshot producer writes a complete row after candle close and before Stage38's 5 second read.
4. The live snapshot is written atomically enough to avoid partial reads.
5. Stage37 can match live rows to Stage36 candidates using `packet_row`, `source_scenario_key`, or `variant_key`.
6. Stage37 has all feature columns needed by `gold_v3_36_final_filter_contract.csv`.
7. Stage37 Discord signal notification succeeds with the real `GOLD_V3_DISCORD_WEBHOOK_URL`.
8. Stage37 NO_SIGNAL remains silent.
9. Stage37 duplicate suppression prevents repeated notification for the same signal over multiple minutes.
10. Stage37's `latest_signal.json` contains the intended latest selected signal and a suitable `discord_status`.
11. Stage40 does not execute if `latest_signal.json` is NO_SIGNAL or stale.
12. Stage40 does not execute if the previous Discord signal notification failed.
13. Stage40 imports Python `MetaTrader5` successfully in the same Python environment used by the BAT.
14. MT5 terminal is open, logged in, and connected to the intended demo account.
15. Stage40 correctly detects and blocks non-demo accounts on the user's terminal.
16. Broker symbol name is exactly `XAUUSD`, or the BAT/script is adjusted to the broker symbol.
17. Default lot size `0.01` is acceptable for the user's demo test.
18. TP/SL prices are accepted by the broker and not rejected due to stops level, freeze level, digits, or filling mode.
19. `ORDER_FILLING_IOC` is accepted by the broker; if rejected, filling mode needs adjustment.
20. Stage40 duplicate execution guard prevents repeated order sends across repeated minute loops.
21. Error Discord notifications are actually received for Stage38 and Stage40 failures/stops.
22. Multiple BAT instances are not running simultaneously; strict lock enforcement is not fully implemented yet.
23. Daily/result logs remain small enough for long operation.
24. `latest_discord_dispatch.csv` does not grow unexpectedly.

## 14. Key commits

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
- Summary document review correction: `c16f7f2be5d314a5049159aa2fc1e93292912e33`

## 15. Next recommended checks

Before leaving this running unattended:

1. Run Stage39 BAT once.
2. Confirm `live_runtime/current/latest_status.json` exists.
3. Prepare a small live snapshot CSV.
4. Run Stage38 once with `--run-once --enable-discord` if testing manually.
5. Confirm Discord receives only `GOLD BUY` or `GOLD SELL` signal messages.
6. Confirm NO_SIGNAL is silent.
7. Confirm duplicate signal does not repeat every minute.
8. Confirm `latest_signal.json` has the expected selected signal and `discord_status`.
9. Run Stage40 once with demo MT5 terminal open and logged into demo.
10. Confirm non-demo account is blocked if accidentally connected.
11. Confirm `mt5_results_YYYYMMDD.csv` contains the result and no Discord MT5-result notification is sent.
12. Confirm MT5 errors/stops notify Discord.
13. Confirm Stage37/Stage40 do not execute duplicate signals across repeated minute loops.
