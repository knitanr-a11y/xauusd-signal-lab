@echo off
setlocal
cd /d "%~dp0\..\..\..\"
python scripts\btc_ml_v1\data_history\export_btcusdsharp_history.py %*
exit /b %ERRORLEVEL%
