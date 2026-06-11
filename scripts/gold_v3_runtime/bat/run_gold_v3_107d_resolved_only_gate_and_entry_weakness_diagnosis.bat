@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM GOLD V3 Stage107D audit-only runner.
REM Resolved-only health gate recovery search and entry weakness diagnosis.
REM No MT5 execution, Discord, AI API, live hook, live evaluator, or final signal.

set "BAT_DIR=%~dp0"
pushd "%BAT_DIR%\..\..\.."
set "REPO_ROOT=%CD%"

if "%MT5_FILES_DIR%"=="" (
  for /f "usebackq delims=" %%D in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=(Resolve-Path -LiteralPath '%REPO_ROOT%').Path; while($true){ $leaf=Split-Path -Leaf $p; $parent=Split-Path -Parent $p; $pleaf=Split-Path -Leaf $parent; if($leaf -ieq 'Files' -and $pleaf -ieq 'MQL5'){ Write-Output $p; exit 0 }; if([string]::IsNullOrEmpty($parent) -or $parent -eq $p){ exit 1 }; $p=$parent }"`) do set "MT5_FILES_DIR=%%D"
)
if "%MT5_FILES_DIR%"=="" set "MT5_FILES_DIR=%REPO_ROOT%"

set "OUT_DIR=%MT5_FILES_DIR%\FX_OUTPUTS\gold_v3\107dc"
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"
set "LOG_PATH=%OUT_DIR%\stage107d_console.log"

call :log ============================================================
call :log GOLD V3 Stage107D audit-only runner started
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
call :log Running Stage107D Python...

%PY_CMD% "%REPO_ROOT%\scripts\gold_v3_runtime\gold_v3_107d_resolved_only_gate_and_entry_weakness_diagnosis_audit.py" --mt5-files-dir "%MT5_FILES_DIR%" %* > "%LOG_PATH%.tmp" 2>&1
set "EXITCODE=%ERRORLEVEL%"
type "%LOG_PATH%.tmp"
type "%LOG_PATH%.tmp" >> "%LOG_PATH%"
del "%LOG_PATH%.tmp" >nul 2>nul

:finish
call :log ============================================================
call :log Stage107D finished with exit code %EXITCODE%.
call :log Paste this file back into ChatGPT: %OUT_DIR%\paste_me.txt
call :log Console log: %LOG_PATH%
call :log Expected READY status: GOLD_V3_107D_RESOLVED_ONLY_GATE_AND_ENTRY_WEAKNESS_DIAGNOSIS_READY_AUDIT_ONLY
call :log Expected BLOCKED status: GOLD_V3_107D_RESOLVED_ONLY_GATE_AND_ENTRY_WEAKNESS_DIAGNOSIS_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
call :log ============================================================

echo.
echo Window is paused so errors remain visible.
echo Paste this file back into ChatGPT:
echo   %OUT_DIR%\paste_me.txt
echo.
pause

popd
exit /b %EXITCODE%

:log
echo %*
echo %*>> "%LOG_PATH%"
exit /b 0
