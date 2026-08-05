# Operational loop and title addendum — 2026-08-06

## Purpose

The Full95 Shadow activation had already been created successfully. Subsequent operational improvements added a 60-second observation loop and descriptive window titles.

## Frozen-asset boundary

`docs/RUNBOOK_JA.md` and `launchers/04_STATUS.bat` are part of the activation-time frozen manifest. They were temporarily edited for operational clarity, which correctly caused `FROZEN_ASSET_HASH_MISMATCH` during processing.

They have been restored byte-for-byte to their activation-time frozen contents. The model, 95 features, Q20 threshold, parent rule, activation watermark, prospective ledger, and Stage55 were not changed.

## Active operational launchers

- Continuous loop: `launchers/03_PROCESS_CSV_COMPAT.bat`
- Titled status view: `launchers/04_STATUS_FULL95_Q20.bat`

The continuous loop title is:

`BTC AI V1 Full95 Q20 Shadow - ACTIVE OBSERVATION LOOP`

The status title is:

`BTC AI V1 Full95 Q20 Shadow - STATUS`

The operational launchers are outside the activation-time frozen asset list. Processing still verifies every research-critical frozen asset before each cycle and stops on any mismatch.

## User-PC recovery

1. Pull the latest branch.
2. Run `00_REPAIR_WINDOWS_CHECKOUT.bat` once after the pull.
3. Run `03_PROCESS_CSV_COMPAT.bat`.
4. Do not run any initialization BAT again.
