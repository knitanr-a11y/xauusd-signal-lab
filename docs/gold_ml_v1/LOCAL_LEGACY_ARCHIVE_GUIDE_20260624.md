# GOLD ML V1 — Local Legacy Archive Guide

Date: 2026-06-24  
Status: `LOCAL_ARCHIVE_TOOL_READY`

## Purpose

This tool safely compresses old local GOLD artifacts while keeping them completely outside `GOLD_ML_V1` research.

The tool performs only:

- opaque byte-level ZIP compression;
- SHA256 recording for each archived file;
- ZIP entry-count verification;
- archive-session reporting.

It does not parse old strategy content, extract old metrics, import old models, or use old artifacts as a new-project source.

## One-click runner

After GitHub Desktop `Fetch origin -> Pull origin`, run:

`scripts\gold_ml_v1\tools\run_archive_legacy_gold_local.bat`

The BAT prefers PowerShell 7 when installed and otherwise uses Windows PowerShell 5.1.

## Automatically detected targets

The tool checks for:

1. `FX_OUTPUTS\gold_v3` below every detected MT5 terminal `MQL5\Files` directory;
2. repo-local `FX_OUTPUTS\gold_v3`, when present;
3. optional external legacy project folders with the exact names:
   - `gold_ai_system`
   - `gold_signal_system_step1`
   - `gold_signal_system_step2`
   - `gold_signal_system_step3`
4. optional old root candle CSV backups such as:
   - `goldsharp_m1.csv`
   - `goldsharp_m5.csv`
   - `goldsharp_m15.csv`
   - `goldsharp_h1.csv`
   - `goldsharp_h4.csv`
   - `goldsharp_d1.csv`
   - legacy `candles_history_*.csv`
   - `M5_backtest.csv`

Git-managed old repository source directories such as `docs/gold_v3` and `scripts/gold_v3_runtime` are not moved or removed by this tool.

## Archive destination

Default destination:

`%USERPROFILE%\Documents\GOLD_OLD_ARCHIVES\GOLD_OLD_ARCHIVE_YYYYMMDD_HHMMSS\`

Each session contains:

- one or more ZIP archives;
- `file_manifest.csv` with original path, size, timestamp, and SHA256;
- `archive_session.json` with success or error state;
- `README.txt`.

## Safety sequence

The execution sequence is fixed:

1. detect targets;
2. show the exact target list;
3. ask whether to begin compression;
4. hash the source files;
5. create ZIP archives;
6. reopen each ZIP and verify its file-entry count;
7. write the manifest and session report;
8. only then offer the option to clear the verified original local folders.

No original is cleared before its ZIP passes verification.

The default answer for clearing originals is `No`.

Old root candle CSVs have a separate confirmation and should normally remain as emergency backup. Their default is also `No`.

When any archive operation fails, that target remains in place and the error is written to `archive_session.json`.

## Recommended answers on the first run

- External legacy project folders: `Y`
- Old root candle CSV backup: `Y`
- Begin ZIP compression: `Y`
- Clear verified old output/project folders: choose `Y` only when the ZIP destination has enough free space and the displayed target list is correct
- Clear old candle CSVs: `N`

## Important boundary

These ZIP files are historical storage only.

Do not copy their contents into:

- `FX_OUTPUTS\gold_ml_v1\raw\`
- new feature generation;
- new model training;
- candidate comparison;
- threshold selection;
- fallback or parity checks.

`GOLD_ML_V1` still starts from freshly exported raw data.

## Implementation

- Runner: `scripts/gold_ml_v1/tools/run_archive_legacy_gold_local.bat`
- PowerShell: `scripts/gold_ml_v1/tools/archive_legacy_gold_local_v2.ps1`
- Compatibility wrapper: `scripts/gold_ml_v1/tools/archive_legacy_gold_local.ps1`
