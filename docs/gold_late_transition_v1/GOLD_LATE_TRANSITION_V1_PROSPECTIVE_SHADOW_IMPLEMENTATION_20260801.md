# GOLD Late Transition V1 Prospective Shadow Implementation Contract

Date: 2026-08-01  
Instrument: XAUUSD / GOLD  
Mode: observation-only prospective shadow  
Authorization: user-authorized Shadow and Discord entry delivery

## 1. Frozen Challenger

```text
LATE_TRANSITION_VACANCY_V1
+ SEMIANNUAL_EXPANDING
+ selected-direction causal rank < 0.90
+ selected-direction wave state is IMPULSE_LATE or CORRECTION_EARLY
+ first confirmable exact state-event onset only
+ TP20 / SL10
+ 480 exact M1 bars
+ V19 always priority
```

This is the preregistered historical lead that produced 123 resolved-only Challenger observations. Its historical result is research evidence only and is not proof of future profit.

No low-volatility exclusion, July rescue rule, rank floor, side deletion, state deletion, TP/SL change, timing rescue, health gate, rolling gate, or candidate-survival gate is added.

## 2. Absolute time and execution contract

- Time basis is MT5 broker-server naive time.
- The latest valid CSV row is closed by contract.
- Open/as-of bars are prohibited.
- Entry is the exact M1 open at the decision index.
- Fixed spread is USD 0.30.
- TP is USD 20 and SL is USD 10.
- Same-M1 TP/SL collision is SL first.
- At the exact 480-M1 boundary, exit occurs at that M1 open before that bar's high or low can be used.
- No higher-timeframe execution fallback is allowed.

## 3. Read-only dependency on frozen V19

The Challenger does not retrain or reproduce a new E40 router. It consumes the causal output already produced by the frozen V19 runtime:

- `%LOCALAPPDATA%\xauusd_signal_lab\gold_v19_shadow\runtime_state.json`
- `%LOCALAPPDATA%\xauusd_signal_lab\gold_v19_shadow\outputs\shadow_score_ledger.csv`
- exact M1 and M15 paths from `config/gold_wave_shadow_v19/local_config.json`

Required causal fields are normalized from the V19 score ledger:

- decision/entry time
- selected LONG or SHORT
- selected-direction past-only rank
- selected-direction causal wave state
- V19 early-episode ID when present

The V19 config, state, ledgers, models, score history, candidate ledger, trade ledger, and Discord state are read-only. The Challenger never writes to them.

If the V19 runtime is unavailable, behind its own session-guarded cursor, contract-mismatched, or inconsistent with the reconstructed V19 open position/count, the Challenger fails closed and does not advance its cursor.

## 4. Causal event definition

A Challenger target row requires:

- `chosen_rank < 0.90`; and
- `wave_state` is `IMPULSE_LATE` or `CORRECTION_EARLY`.

A contiguous event continues only while decisions remain exactly 15 minutes apart with the same selected direction and same target state.

A new event begins when:

- the selected direction changes;
- `IMPULSE_LATE` and `CORRECTION_EARLY` switch; or
- the previous decision gap is not exactly 15 minutes.

The first target row after a non-15-minute gap is consumed without entry. This prevents a gap/restart from being interpreted as a confirmed fresh onset.

## 5. V19 portfolio priority

The runtime reconstructs the frozen V19 first-P90-per-`IMPULSE_EARLY` episode sequentially from the same causal score ledger. Historical verification matched the authoritative 169 V19 entries, PnL values, and exit indexes exactly.

Processing order at each exact M1 index:

1. Process a new V19 decision.
2. If V19 fires while a Challenger is open, close the Challenger at the current exact M1 open with `V19_PREEMPT`.
3. Accept V19.
4. Evaluate the current Challenger event onset.
5. Suppress and consume the Challenger event when either V19 or Challenger is already open.
6. Process the current M1 TP/SL/TIME outcome.

There is only one combined Shadow position.

Future V19 overlap is never inspected at Challenger entry time.

## 6. Activation and recovery

State root:

`%LOCALAPPDATA%\xauusd_signal_lab\gold_late_transition_v1_shadow`

Initial activation is no-backfill:

- current V19 decision cursor becomes the activation cutoff;
- current Challenger target event is marked consumed;
- all previously consumed V19 early episodes are seeded without creating trades;
- the current V19 open observation, when present, is imported read-only as portfolio state;
- no historical Challenger entry is created.

At every process startup, decisions already present at startup are recovery replay:

- event and V19 priority state are reconstructed;
- an existing open observation is resolved from exact M1 data;
- a missed V19 entry can preempt an already-open Challenger at the correct historical M1 open;
- missed Challenger entries are recorded as `RECOVERY_REPLAY_NOT_TRADED` and are not traded or notified.

## 7. Output

Main files:

- `runtime_state.json`
- `runtime_health.json`
- `discord_notifier_state.json`
- `outputs/shadow_candidate_ledger.csv`
- `outputs/shadow_trade_ledger.csv`
- `outputs/shadow_suppressed_ledger.csv`
- `outputs/v19_priority_ledger.csv`
- `outputs/recovery_replay_ledger.csv`
- `outputs/discord_charts/*.png`
- `logs/shadow_runtime.log`
- `logs/discord_notifier.log`

`counters.accepted_trades` counts Challenger entries only. Discord watches this counter.

## 8. Prospective evidence gate

Do not assess promotion or modify the frozen contract until both are met:

1. at least 30 resolved prospective Challenger observations; and
2. at least four full calendar months after activation.

Interim wins or losses do not authorize changes to rank, volatility, direction, state, TP/SL, event timing, V19 priority, or horizon.

## 9. Trading boundaries

Authorized:

- observation-only prospective Shadow
- separate Discord delivery for newly accepted Challenger entries

Still prohibited:

- live-ready status
- final signal
- AI judgement
- MT5 order
- automatic trading
- NO_SIGNAL notification
- exit notification
