@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0..\..\..") do set "REPO_ROOT=%%~fI"
call "%REPO_ROOT%\scripts\btc_ml_v1\fresh_forward_availability\bat\01_run_availability_audit.bat" %*
exit /b %ERRORLEVEL%
