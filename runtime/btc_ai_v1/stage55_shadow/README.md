# BTC Stage55 observation-only Shadow launcher

This directory contains the Windows launchers and local configuration example.

## Supported CSV input

Stage55 uses the continuously updated live H4/M15/M5/M1 CSV files.

The reader automatically supports both:

- live exporter comma-delimited files such as `btcusdsharp_h4.csv`
- research exporter semicolon-delimited files such as `BTCUSD#_H4_....csv`

Required columns are `time, open, high, low, close`. Additional volume/spread columns are allowed and ignored by candidate logic.

## Shadow runtime

1. Run `01_INSTALL.bat`.
2. Run `02_BOOTSTRAP_ACTIVATE.bat` once to create `local_config.json`.
3. Edit the exact continuously updated H4/M15/M5/M1 CSV paths.
4. Run `02_BOOTSTRAP_ACTIVATE.bat` again and confirm `READY_NO_BACKFILL_ACTIVATED`.
5. Keep `03_RUN_LOOP.bat` open.
6. Check `04_STATUS.bat`.

Every launcher window title and banner starts with `BTC Stage55 Shadow` or `[BTC_STAGE55_SHADOW]`, so it can be distinguished from GOLD and other runtimes.

## Discord entry notification

7. Run `05_CONFIGURE_DISCORD.bat` and set `discord.enabled=true` plus the Webhook URL in local `local_config.json`.
8. Run `06_TEST_DISCORD.bat` and confirm the Japanese connection test in Discord.
9. Keep `07_RUN_DISCORD_ALERTS.bat` open beside `03_RUN_LOOP.bat`.
10. Check notifier state with `08_DISCORD_STATUS.bat`.

Only newly accepted M1/M5 reverse-SHORT entries are delivered. Existing entries at notifier activation, recovery replay, stale entries, NO_SIGNAL and exits are not sent.

Candidate logic is unchanged. Notification delivery does not affect selection or performance. This remains observation-only; MT5 orders, live trading and automatic promotion are disabled.
