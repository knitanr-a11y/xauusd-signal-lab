# BTC BCR13 — LocalAppData single-upload ZIP workflow correction

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T23:05:00+09:00`
- classification: `BCR13_OUTPUT_HANDOFF_WORKFLOW_INCIDENT_CORRECTED`
- B3 outcome access: unchanged, not opened
- BCR14 authorization: unchanged, not authorized

## 1. Incident

The first BCR13 runner incorrectly used a repository-relative output directory:

`<repo>\outputs\btc_ml_v1\BCR13_b3_outcome_blind_density_audit\latest`

It also instructed the user to upload three separate files. This departed from the established BTC research BAT workflow used by earlier BCR stages.

The established workflow is:

1. write stage output under `%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs`;
2. assemble the user-facing deliverables into one `99_UPLOAD_PACKAGE.zip`;
3. open Explorer automatically with that ZIP selected;
4. ask the user to upload only the selected ZIP.

The deviation was an implementation mistake, not an intentional specification change.

## 2. Corrected output contract

BCR13 now writes to:

`%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\BCR13_b3_outcome_blind_density_audit\LATEST`

On the current user machine this resolves to:

`C:\Users\regen\AppData\Local\xauusd_signal_lab\btc_ml_v1\outputs\BCR13_b3_outcome_blind_density_audit\LATEST`

The sole upload file is:

`C:\Users\regen\AppData\Local\xauusd_signal_lab\btc_ml_v1\outputs\BCR13_b3_outcome_blind_density_audit\LATEST\99_UPLOAD_PACKAGE.zip`

## 3. ZIP contents

`99_UPLOAD_PACKAGE.zip` contains exactly the three previously separate handoff files:

1. `BCR13_B3_OUTCOME_BLIND_DENSITY_AUDIT_20260730.zip`
2. `deterministic_repeat.json`
3. `package_sha256.txt`

The inner deterministic evidence ZIP continues to contain the label-free BCR13 metrics, ledgers, summary and manifest. The outer `99_UPLOAD_PACKAGE.zip` is the standard single user upload container.

## 4. Corrected BAT behavior

After a successful run, `01_run_BCR13.bat` now:

1. confirms the deterministic evidence ZIP and repeat files exist;
2. creates `99_UPLOAD_PACKAGE.zip` in the LocalAppData `LATEST` directory;
3. opens Explorer with `99_UPLOAD_PACKAGE.zip` selected;
4. pauses so the result and any message remain visible;
5. instructs the user to upload only that selected ZIP.

`02_open_latest_results.bat` resolves the same LocalAppData path and selects the same ZIP.

## 5. Correction commits

- runner BAT correction: `5ae358ab06c3183da2486d31ffa8d4f1721c57f4`
- result-opener correction: `5809d2a09ed8d31aab646901a0716c028ce0480e`
- README correction: `e281ff1ef9f1c3fc3dcbae91520fd9584d1f0e48`

## 6. Unchanged research boundary

This correction does not change:

- the frozen BTC M15 SHA256 or 30,661-row boundary;
- the eight B3 machines;
- any breakout, retest, re-acceleration, entry or exit predicate;
- causal closed-bar semantics;
- gap or fallback behavior;
- capability gates;
- outcome access;
- candidate promotion status.

No BCR13 real-data result was opened while making this correction.

BCR14 value evaluation, portfolio selection, prospective start, shadow, Discord, MT5 order, live-ready and final signal remain unauthorized.

## 7. Current user action

Pull `feature/btc-fresh-forward-research`, then run:

`scripts\btc_ml_v1\BCR13_b3_outcome_blind_density_audit\01_run_BCR13.bat`

After success, upload only the Explorer-selected:

`99_UPLOAD_PACKAGE.zip`
