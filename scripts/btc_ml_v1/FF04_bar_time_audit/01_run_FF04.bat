@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0..\..\..") do set "REPO_ROOT=%%~fI"
call "%REPO_ROOT%\scripts\btc_ml_v1\causal_rebuild_foundation\bat\01_run_bar_time_semantics_audit.bat" %*
exit /b %ERRORLEVEL%
