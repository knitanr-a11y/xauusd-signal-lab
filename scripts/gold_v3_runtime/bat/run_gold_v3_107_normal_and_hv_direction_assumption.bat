@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 Stage107 audit-only runner.
REM Do not use GOLD V2 / old GOLD / DISC8 / Stage41 as trading source.
REM Do not mutate source CSVs, CSV contract, candidate pool, Stage45, Stage69, runtime, live evaluator, or final signal.
REM CSV latest row is contractually closed. open/as-of treatment is forbidden.

set "BAT_DIR=%~dp0"
pushd "%BAT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

REM If MT5_FILES_DIR is not set, locate the nearest ancestor named MQL5\Files.
REM This matters when the repo itself is under MQL5\Files\xauusd-signal-lab-clean\xauusd-signal-lab.
if "%MT5_FILES_DIR%"=="" (
  for /f "usebackq delims=" %%D in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=(Resolve-Path -LiteralPath '%REPO_ROOT%').Path; while($true){ $leaf=Split-Path -Leaf $p; $parent=Split-Path -Parent $p; $pleaf=Split-Path -Leaf $parent; if($leaf -ieq 'Files' -and $pleaf -ieq 'MQL5'){ Write-Output $p; exit 0 }; if([string]::IsNullOrEmpty($parent) -or $parent -eq $p){ exit 1 }; $p=$parent }"`) do set "MT5_FILES_DIR=%%D"
)
if "%MT5_FILES_DIR%"=="" set "MT5_FILES_DIR=%REPO_ROOT%"

set "OUT_DIR=%MT5_FILES_DIR%\FX_OUTPUTS\gold_v3\107c"
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"
set "LOG_PATH=%OUT_DIR%\stage107_console.log"

call :log ============================================================
call :log GOLD V3 Stage107 audit-only runner started
call :log REPO_ROOT=%REPO_ROOT%
call :log MT5_FILES_DIR=%MT5_FILES_DIR%
call :log OUT_DIR=%OUT_DIR%
call :log LOG_PATH=%LOG_PATH%
call :log ============================================================

where py >nul 2>nul
if "%ERRORLEVEL%"=="0" (
  set "PY_CMD=py -3"
) else (
  where python >nul 2>nul
  if "%ERRORLEVEL%"=="0" (
    set "PY_CMD=python"
  ) else (
    call :log ERROR: Python was not found. Install Python or add it to PATH.
    set "EXITCODE=9009"
    goto :finish
  )
)

call :log Using Python command: %PY_CMD%
call :log Running Stage107 Python...

%PY_CMD% "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_107_normal_and_hv_direction_assumption_audit.py" --mt5-files-dir "%MT5_FILES_DIR%" %* > "%LOG_PATH%.tmp" 2>&1
set "EXITCODE=%ERRORLEVEL%"
type "%LOG_PATH%.tmp"
type "%LOG_PATH%.tmp" >> "%LOG_PATH%"
del "%LOG_PATH%.tmp" >nul 2>nul

:finish
call :log ============================================================
call :log Stage107 finished with exit code %EXITCODE%.
call :log BAT path: scripts\gold_v3_runtime\bat\run_gold_v3_107_normal_and_hv_direction_assumption.bat
call :log Paste this file back into ChatGPT: %OUT_DIR%\paste_me.txt
call :log Console log: %LOG_PATH%
call :log Expected READY status: GOLD_V3_107_NORMAL_AND_HV_DIRECTION_ASSUMPTION_AUDIT_READY_AUDIT_ONLY
call :log Blocked status is acceptable if inputs are incomplete: BLOCKED_INPUT_INCOMPLETE_AUDIT_ARTIFACTS_WRITTEN
call :log ============================================================

echo.
echo Window is paused so errors remain visible.
echo If Stage107 is blocked or failed, paste one of these files back into ChatGPT:
echo   1^) %OUT_DIR%\paste_me.txt
echo   2^) %LOG_PATH%
echo.
pause

popd
exit /b %EXITCODE%

:log
echo %*
echo %*>> "%LOG_PATH%"
exit /b 0
