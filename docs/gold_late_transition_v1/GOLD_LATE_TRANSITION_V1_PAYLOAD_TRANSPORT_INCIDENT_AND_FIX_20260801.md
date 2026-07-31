# GOLD Late Transition V1 payload transport incident and fix

Date: 2026-08-01  
Scope: packaging only; strategy contract unchanged

## Incident

The first GitHub implementation stored the packaged Python runtime in unmarked raw binary parts. The repository bytes were valid, but Windows checkout line-ending conversion altered the raw payload on the user PC. The wrapper therefore failed before bootstrap with:

```text
zipfile.BadZipFile: Bad magic number for file header
```

No Challenger Shadow activation or trade occurred. The frozen V19 runtime was unaffected.

## Resolution

- Replaced the old `.bin` checkout paths with new `.raw` paths.
- Added root `.gitattributes` rules that force both `.raw` files to `binary` / `-text`.
- Both wrappers reconstruct the payload and verify the frozen SHA256 before opening the ZIP.
- The reconstructed ZIP SHA256 remains `0b59b0d91cf9dedaf81fd23c2b16fd03f23a44a790e4c5bf80914dbcb9e4c69a`.
- `01_INSTALL.bat` and `02_BOOTSTRAP_ACTIVATE.bat` now pause on completion or failure.

## Contract impact

None. Rank, wave states, event definition, TP20/SL10, 480 exact M1, V19 priority, no-backfill and Discord scope are unchanged. AI judgement, MT5 order, final signal and live trading remain OFF.

## User action

1. Fetch and pull `feature/gold-v19-wave-shadow`.
2. Leave the existing V19 loops running.
3. Run Challenger `02_BOOTSTRAP_ACTIVATE.bat` again.
4. Confirm Challenger `04_STATUS.bat` reports `READY` and V19 parity `PASS`.
5. Continue with the Challenger Discord test and the two Challenger loops.
