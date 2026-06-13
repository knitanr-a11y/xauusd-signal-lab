@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\..\.."
set "REPO_ROOT=%CD%"
if not defined MT5_FILES_DIR set "MT5_FILES_DIR=%APPDATA%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"
set "OUT_DIR=%MT5_FILES_DIR%\FX_OUTPUTS\gold_v3\107grc"
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"
echo GOLD V3 Stage107GR audit-only
echo Runtime estimate: light-to-medium, seconds to minutes. Stop and report if over 1 hour.
echo Purpose: reduce trade count to improve OOS win rate; density frontier 0.5 / 1.0 / 1.5 / 2.0 trades per business day.
echo MT5_FILES_DIR=%MT5_FILES_DIR%
echo OUT_DIR=%OUT_DIR%
echo.
py -3 "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_107gr_winrate_first_density_frontier_audit.py" --mt5-files-dir "%MT5_FILES_DIR%"
if errorlevel 1 (
  echo py failed. Trying python...
  python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_107gr_winrate_first_density_frontier_audit.py" --mt5-files-dir "%MT5_FILES_DIR%"
)
echo.
echo Paste this file back into ChatGPT:
echo %OUT_DIR%\paste_me.txt
echo.
pause
