@echo off
setlocal
cd /d "%~dp0"
call scripts\btc_ml_v1\data_history\run_export_btcusdsharp_history.bat %*
exit /b %ERRORLEVEL%
