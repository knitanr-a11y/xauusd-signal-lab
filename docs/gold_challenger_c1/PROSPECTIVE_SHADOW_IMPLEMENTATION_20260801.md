# GOLD Challenger C1 DATA_V3 prospective Shadow implementation

Date: 2026-08-01

## Formal interpretation

The retrospective result remains `RETROSPECTIVE_STRUCTURAL_ROBUSTNESS_FAILED`. The user explicitly authorized an observation-only prospective Shadow and Discord entry delivery so that future entry timing can be inspected. This authorization does not change the retrospective gate, validate the candidate, or permit live trading.

## Isolation

- Frozen V19 clone: `C:\gold-v19-shadow`; do not switch its branch.
- Challenger clone/worktree: recommended `C:\gold-challenger-c1`.
- Branch: `feature/gold-v19-challenger-c1-audit`.
- Challenger state root: `%LOCALAPPDATA%\xauusd_signal_lab\gold_challenger_c1_shadow`.
- V19 config, runtime state and ledgers are read-only.
- No file is written under the V19 state root or the V19 repository paths.

## Frozen candidate

- `wave_state in {IMPULSE_LATE, CORRECTION_EARLY}`
- `chosen_rank < 0.90`
- chosen side retained for LONG and SHORT
- decision timestamp is the close time of the prior M15 bar
- entry is the M1 open whose timestamp equals decision timestamp
- TP20 / SL10 / exact 480 M1
- fixed spread USD 0.30
- same-M1 collision is SL-first
- TIME exit uses boundary M1 open before boundary high/low
- one position total
- same exit index remains occupied

The runtime reads the frozen V19 `outputs/shadow_score_ledger.csv` as the authoritative prospective E40 chosen-side/rank stream. It verifies that the score-ledger cursor exactly matches the V19 runtime cursor, then applies only the frozen DATA_V3 wave grammar and candidate engine. It does not retrain a second router, accept outcome columns, or redefine the candidate condition.

## V19 priority

1. Challenger waits until frozen V19 has processed the same decision timestamp.
2. If V19 entered at that timestamp or remains open at that timestamp, Challenger is suppressed.
3. Future V19 entries are not looked up to reject a Challenger in advance.
4. If an accepted Challenger is open and V19 later actually enters, Challenger is closed at that exact M1 open before reading that M1 high/low.
5. V19 runtime and files are never changed.

## No-backfill

- Bootstrap reproduces the current timeline, sets the latest decision as baseline and consumes all existing events.
- The first loop iteration after every process start is recovery-only.
- A manual one-shot run is recovery-only.
- More than one unprocessed decision is always `RECOVERY_REPLAY_NOT_TRADED`.
- Even one unprocessed decision is not entered when the loaded M1 cursor has already moved beyond its decision timestamp; it is recorded as stale recovery, not backfilled.
- An existing open Challenger may still be resolved over downtime from raw M1 and actual V19 entry timestamps.
- Discord starts from the current accepted counter and never sends delayed missed-entry alerts.

## DATA_V3 source validation

The runtime inherits M1/M5/H1/H4 paths from the existing V19 local config unless explicit Challenger paths are provided. Bootstrap requires exactly one immutable DATA_V3 base file per timeframe to match the preregistered SHA256. M15 is not inherited: it is derived from the complete old+sharp M1 union and only closed M15 buckets are scored.

If the active V19 config does not reference these DATA_V3 sources, bootstrap fails closed. Set explicit Challenger paths in the external local config; do not change V19.

## Discord

Discord is a separate sidecar process. It reads the existing V19 webhook from the V19 local config without copying it into the repository or Challenger config.

Only a newly accepted Challenger entry is sent. The message contains direction, MT5 time, Entry, TP, SL, wave state, chosen rank, V19 priority and observation-only notices. It may attach an M15 chart.

No messages are sent for NO_SIGNAL, recovery, suppressed candidates, exits, TP, SL, TIME, V19 entry or V19 preemption.

## Commands

From the separate Challenger clone:

1. `scripts\gold_challenger_c1\01_INSTALL_SHADOW.bat`
2. `scripts\gold_challenger_c1\02_BOOTSTRAP_ACTIVATE_SHADOW.bat`
3. `scripts\gold_challenger_c1\04_SHADOW_STATUS.bat`
4. `scripts\gold_challenger_c1\06_VALIDATE_DISCORD.bat`
5. `scripts\gold_challenger_c1\07_TEST_DISCORD.bat`
6. Keep `03_RUN_SHADOW_LOOP.bat` open.
7. Keep `08_RUN_DISCORD_ALERTS.bat` open.

Do not start steps 6-7 until bootstrap status is READY and the Discord test is confirmed.

## Semiannual updates

E40 semiannual training, score maturity and boundary updates remain owned by frozen V19. Challenger does not create a second model lifecycle. If the V19 score ledger and runtime cursor do not match exactly, Challenger fails closed.
