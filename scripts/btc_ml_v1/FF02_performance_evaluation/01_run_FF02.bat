@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0..\..\..") do set "REPO_ROOT=%%~fI"
call "%REPO_ROOT%\scripts\btc_ml_v1\fresh_forward_performance\bat\01_run_fresh_forward_evaluation.bat" %*
exit /b %ERRORLEVEL%
