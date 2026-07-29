@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0..\..\..") do set "REPO_ROOT=%%~fI"
call "%REPO_ROOT%\scripts\btc_ml_v1\btc7r_causality_audit\bat\01_run_btc7r_causality_audit.bat" %*
exit /b %ERRORLEVEL%
