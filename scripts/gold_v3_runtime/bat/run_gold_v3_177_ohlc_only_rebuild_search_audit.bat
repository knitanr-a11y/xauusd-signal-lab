@echo off
setlocal
cd /d "%~dp0\..\..\.."
py -3 scripts\gold_v3_runtime\gold_v3_177_ohlc_only_rebuild_search_audit.py %*
if errorlevel 1 pause
endlocal
