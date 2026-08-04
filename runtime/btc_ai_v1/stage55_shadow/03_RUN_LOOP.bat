@echo off
setlocal
title BTC Stage55 Shadow - Observation Loop
cd /d "%~dp0"
echo ============================================================
echo BTC STAGE55 SHADOW - OBSERVATION LOOP
echo Observation only / Discord sidecar separate / MT5 orders OFF
echo Close this window to stop the Stage55 Shadow loop.
echo ============================================================
call .venv\Scripts\activate.bat
:loop
echo.
echo [%date% %time%] [BTC_STAGE55_SHADOW] Starting observation cycle...
python ..\..\..\scripts\btc_ai_v1\stage55_shadow_runtime.py --config local_config.json
echo [%date% %time%] [BTC_STAGE55_SHADOW] Cycle finished. Next cycle in 60 seconds.
timeout /t 60 /nobreak >nul
goto loop
