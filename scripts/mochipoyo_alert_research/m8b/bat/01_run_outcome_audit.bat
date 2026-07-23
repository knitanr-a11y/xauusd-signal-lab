@echo off
setlocal
set "ROOT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research"
set "REPO=%~dp0..\..\..\.."
set "SKELETON=%REPO%\config\mochipoyo_alert_research\m8b_frozen_trade_skeleton_20260723.csv"
set "NORMALIZED=%ROOT%\runtime\m8b\m8b_frozen_trade_skeleton_20260723.normalized.csv"
set "OUTPUT=%ROOT%\outputs\M8B"
set "SCRIPT=%~dp0..\python\run_extra_signal_outcome_audit.py"

rem Git may convert LF to CRLF on Windows. Normalize only BOM/newline bytes;
rem the frozen CSV rows and values are not changed.
python -c "from pathlib import Path; src=Path(r'%SKELETON%'); dst=Path(r'%NORMALIZED%'); dst.parent.mkdir(parents=True, exist_ok=True); text=src.read_text(encoding='utf-8-sig'); dst.write_bytes(('\n'.join(text.splitlines())+'\n').encode('utf-8'))"
if errorlevel 1 (
  echo [M8B BLOCKED] failed to normalize frozen trade skeleton for portable SHA verification.
  pause
  exit /b 2
)

python "%SCRIPT%" --trade-skeleton "%NORMALIZED%" --output-root "%OUTPUT%"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
  echo [STOP] M8B outcome audit was blocked.
  echo Do not change M7C formulas, thresholds, runtime manifest, or prospective start.
  echo If the message says MT5 symbol is ambiguous, copy the displayed symbol names and send them to ChatGPT.
  pause
  exit /b %RC%
)
echo [OK] 01 complete. Run 02_open_latest_results.bat to open the result folder.
pause
exit /b 0
