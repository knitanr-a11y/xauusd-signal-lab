@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"

echo ============================================================
echo M9P GOLD Dynamic Core Deterministic Reproduction - ONE TIME
echo Keep M8C / M7C / collector running. Do not reset anything.
echo Reads: MT5 Files\gold_v3_2023_2026\
echo ============================================================
echo.

python "..\python\run_gold_dynamic_core_reproduction_audit.py"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo.
  echo [M9P BLOCKED]
  echo Keep M8C, M7C, and collector unchanged.
  echo Send the full screen output to ChatGPT.
  pause
  exit /b %RC%
)

echo.
echo [M9P PASS]
echo Open 02_open_latest_results.bat and submit 99_UPLOAD_PACKAGE.zip.
pause
exit /b 0
