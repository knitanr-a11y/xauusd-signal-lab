@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
python scripts\btc_ml_v1\research\audit_btc_fresh_forward_availability.py %*
set "EXITCODE=%ERRORLEVEL%"
echo.
echo BTC fresh forward availability audit exit code: %EXITCODE%
echo Output: outputs\btc_ml_v1\btc_fresh_forward_availability_audit
exit /b %EXITCODE%
