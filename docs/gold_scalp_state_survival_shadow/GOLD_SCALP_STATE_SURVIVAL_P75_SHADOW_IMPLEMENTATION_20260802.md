# GOLD Scalp State Survival P75 — Prospective Shadow Implementation

Date: 2026-08-02

Formal status:

`PROSPECTIVE_SHADOW_IMPLEMENTED_PENDING_USER_PC_ACTIVATION`

## Authorization

The user authorized:

- observation-only prospective Shadow;
- Discord notification for newly accepted pseudo-entries.

The following remain disabled:

- MT5 orders;
- demo orders;
- `final_signal`;
- `live_ready`;
- AI discretionary changes.

## Candidate

`CANDLE_STATE_SURVIVAL_DUAL_STRICT_EPISODE_HEALTH_P75_V3`

The Shadow freezes the four state/action pairs selected for the prospective 2026H2 observation boundary. It does not recalculate or optimize the selected list from post-cutoff results.

## State generation

Only closed rows are used.

- Session uses the entry-decision boundary (`M15 time + 15 minutes`).
- H1/H4 uses only bars whose timeframe close is no later than the decision time.
- H1/H4 `UP`: `close > EMA20 > EMA50` on both timeframes.
- H1/H4 `DOWN`: `close < EMA20 < EMA50` on both timeframes.
- Volatility: current M15 ATR14 versus tertiles of the prior 5,760 closed M15 ATR14 observations.
- Momentum: four-M15 close change divided by current ATR14; threshold ±0.50.
- Expansion: current range divided by the prior 96-M15 range median; `COMP <= 0.80`, `EXP >= 1.50`.
- Candle type: directional body fraction at least 0.60, otherwise `WEAK`.

## Runtime lifecycle

1. Bootstrap advances the cursor to the latest existing M15 row. It creates no historical entry and sends no Discord entry.
2. Only a newly appended M15 row after the cursor can become a candidate.
3. Entry requires the exact M1 open at `signal_time + 15 minutes`.
4. A missing exact M1 entry is suppressed fail-closed.
5. Only one primary M1 position may be open.
6. M1 is the primary lifecycle; a conservative M5 mirror is recorded for health auditing.
7. Same-state episode entry rearms only after the M1 position exits and the state is absent on two consecutive closed M15 rows.
8. Health uses only actually executed prospective trades whose M1 and M5 outcomes were both resolved before the decision boundary.

## Exit

- spread: 0.30 USD once through the adjusted entry price;
- initial SL: 5 USD;
- 75% exit at +5 USD;
- remaining 25% stop moves to breakeven;
- remaining final target: +10 USD;
- maximum holding time: 240 minutes.

## Discord

Only a newly accepted pseudo-entry is sent. The message includes:

- LONG/SHORT;
- MT5 signal and entry times;
- adjusted entry, 75% TP, final TP and SL;
- exact fine state;
- observation-only and no-order warnings;
- optional M15 chart.

No Discord message is sent for NO_SIGNAL, recovery rows, suppression, TP, SL, BE or TIME exits.

The webhook is read from the existing local V19 config by default. The secret is not copied into Git.

## Persistent files

Default root:

`%LOCALAPPDATA%\xauusd_signal_lab\gold_scalp_state_survival_shadow`

Files include:

- `shadow_state.json`;
- `bootstrap_report.json`;
- `latest_cycle_summary.json`;
- `entry_events.csv`;
- `suppression_events.csv`;
- `trade_results.csv`;
- `health_decisions.csv`;
- `discord_send_ledger.csv`;
- logs and optional entry charts.

## Verification completed in the implementation environment

- `pytest`: 8 passed;
- `compileall`: passed;
- real uploaded-candle bootstrap: passed;
- bootstrap M15 cursor: `2026-07-31 23:30:00` MT5;
- historical entries created at bootstrap: zero;
- Discord notifications created at bootstrap: zero;
- immediate restart/run-once parity: passed with unchanged cursor, trade count, queue and health state;
- M1 union: 1,239,132 rows after deterministic source precedence;
- one malformed concatenated M1 boundary row was rejected and recorded in `bootstrap_report.json`;
- later-configured source wins on duplicate timestamps;
- Discord queue persistent deduplication: tested;
- episode rearm requires both M1 exit and two absent closed M15 rows: tested.

No real Discord webhook was called and no Windows activation evidence was produced in the implementation environment.

## CSV recovery contract

Ordinary MT5 comma CSV is parsed strictly first. If a source contains a malformed concatenated boundary row, the parser switches to audited rejection mode:

- the malformed row is not repaired or used;
- rejected count and a bounded field sample are written to the source audit;
- numeric/time-invalid required rows are counted separately;
- all source precedence and timestamp deduplication counts are recorded;
- the Shadow fails if required columns are unavailable.

## User-PC activation order

1. `01_INSTALL.bat`
2. `02_BOOTSTRAP_ACTIVATE_SHADOW.bat`
3. `06_TEST_DISCORD.bat`
4. `03_RUN_SHADOW_LOOP.bat`
5. `04_SHADOW_STATUS.bat` when status inspection is needed

Keep the implementation PR draft and unmerged until the Windows checkout passes bootstrap and Discord evidence.
