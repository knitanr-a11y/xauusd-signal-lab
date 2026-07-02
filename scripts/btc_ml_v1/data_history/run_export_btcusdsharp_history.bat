@echo off
setlocal
cd /d "%~dp0\..\..\..\"
python scripts\btc_ml_v1\data_history\run_btcusdsharp_history.py %*
exit /b %ERRORLEVEL%
