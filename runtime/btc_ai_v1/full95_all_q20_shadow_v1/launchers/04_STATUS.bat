@echo off
setlocal
title BTC AI V1 Full95 Q20 Shadow - STATUS
cd /d "%~dp0.."
echo ============================================================
echo BTC AI V1 FULL95 ALL-Q20 SHADOW - STATUS
echo Observation only / MT5 orders OFF / Stage55 separate
echo ============================================================
python bootstrap\materialize_assets.py || exit /b 20
python scripts\shadow_full95_all_q20_v1.py status
pause
