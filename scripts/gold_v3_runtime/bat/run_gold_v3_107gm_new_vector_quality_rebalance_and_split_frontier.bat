@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\..\.."
set "REPO_ROOT=%CD%"
if not defined MT5_FILES_DIR set "MT5_FILES_DIR=%APPDATA%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"
set "OUT_DIR=%MT5_FILES_DIR%\FX_OUTPUTS\gold_v3\107gmc"
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"
echo GOLD V3 Stage107GM audit-only
echo Runtime estimate: light, seconds to minutes. Stop and report if over 1 hour.
echo MT5_FILES_DIR=%MT5_FILES_DIR%
echo OUT_DIR=%OUT_DIR%
echo.
py -3 "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_107gm_new_vector_quality_rebalance_and_split_frontier_audit.py" --mt5-files-dir "%MT5_FILES_DIR%"
if errorlevel 1 (
  echo py failed. Trying python...
  python "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_107gm_new_vector_quality_rebalance_and_split_frontier_audit.py" --mt5-files-dir "%MT5_FILES_DIR%"
)
echo.
echo Paste this file back into ChatGPT:
echo %OUT_DIR%\paste_me.txt
echo.
pause
