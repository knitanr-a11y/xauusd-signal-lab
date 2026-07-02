@echo off
setlocal
cd /d "%~dp0\..\..\..\"
python scripts\btc_ml_v1\broker_audit\btc0_mt5_audit.py %*
exit /b %ERRORLEVEL%
