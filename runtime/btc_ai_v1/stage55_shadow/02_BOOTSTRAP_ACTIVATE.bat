@echo off
setlocal
title BTC Stage55 Shadow - Bootstrap Activate
cd /d "%~dp0"
echo ============================================================
echo BTC STAGE55 SHADOW - BOOTSTRAP / ACTIVATE
echo Observation only / No backfill / MT5 orders OFF
echo ============================================================
call .venv\Scripts\activate.bat
if not exist local_config.json (
  copy local_config.example.json local_config.json >nul
  notepad local_config.json
  echo.
  echo [BTC_STAGE55_SHADOW] Edit all four live CSV paths, save, and run this file again.
  pause
  exit /b 1
)
echo [BTC_STAGE55_SHADOW] Loading H4 / M15 / M5 / M1 live CSV files...
python ..\..\..\scripts\btc_ai_v1\stage55_shadow_runtime.py --config local_config.json --activate
echo.
echo [BTC_STAGE55_SHADOW] Bootstrap command finished.
pause
