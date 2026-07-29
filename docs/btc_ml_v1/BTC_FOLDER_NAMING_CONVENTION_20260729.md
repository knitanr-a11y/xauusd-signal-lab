# BTC folder naming convention

- repository: `knitanr-a11y/xauusd-signal-lab`
- working branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-29`

## 1. User-facing workflow folders

Every normal BTC workflow folder begins with a stable series code and two-digit sequence number:

`FFNN_short_plain_purpose`

Current canonical user-facing folders:

1. `FF01_data_availability`
2. `FF02_performance_evaluation`
3. `FF03_btc7r_causality_audit`
4. `FF04_bar_time_audit`

The next ordinary stage, only after explicit authorization, will use `FF05_...`.

A user-facing folder must contain:

- `00_READ_ME_FIRST.txt`
- `01_run_*.bat`
- optionally `02_open_latest_results.bat`

The folder name must describe what the user actually does. Internal architecture terms such as `foundation`, `kernel`, `adapter`, or `orchestrator` must not be used as the primary user-facing name unless they are necessary to distinguish two different actions.

## 2. Recovery and incident folders

Recovery, forced-reboot, incident, forensic, and emergency material must not be buried among ordinary numbered stages.

Use an English category word first:

- `RECOVERY_FF03_runtime_fix`
- `RECOVERY_FORCED_REBOOT_20260729`
- `INCIDENT_FF04_cadence_classification`
- `FORENSIC_FF02_result_mismatch`

Do not name recovery material only with a number such as `05_recovery`.

## 3. Compatibility paths

Existing implementation directories are retained temporarily so completed BAT files, documents, and output gates do not break. They are compatibility/internal paths and are no longer the preferred user entry points.

Canonical user execution starts from the `FFNN_...` folders. A later cleanup may move internal code only after every reference and BAT has been migrated and verified.

## 4. Outputs and documents

New output roots should also begin with the stage code, for example:

`FF05_candidate_rebuild_search`

Existing FF01-FF04 output roots are not renamed retroactively because FF02-FF04 gates contain those exact paths. Renaming them would create unnecessary recovery risk.

Documents and configs keep the stage prefix in the filename, for example:

- `BTC_FF04_...`
- `btc_ff04_...`

## 5. Prohibitions

- no silent renumbering;
- no reuse of an old stage number for a different purpose;
- no user instruction that points directly to an unnumbered internal implementation folder;
- no recovery directory hidden behind an ordinary numeric prefix;
- no GOLD or MOCHIPOYO naming/path change from this convention update.
