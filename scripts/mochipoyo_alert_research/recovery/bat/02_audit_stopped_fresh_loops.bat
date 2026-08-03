@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0\..\..\..\..\.."

set "ROOT=%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research"
set "BASE=%ROOT%\outputs\FRESH_LOOP_DIAGNOSTIC"
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%I"
set "ARCH=%BASE%\archive\%STAMP%"
set "LATEST=%BASE%\LATEST"
set "PKG=%BASE%\99_UPLOAD_PACKAGE.zip"
set "ZIPLOG=%BASE%\zip_command.log"

if not defined LOCALAPPDATA (
  echo [STOP] LOCALAPPDATA is unavailable.
  pause
  exit /b 2
)

mkdir "%ARCH%" >nul 2>&1
if not exist "%ARCH%" (
  echo [STOP] Could not create diagnostic folder:
  echo %ARCH%
  pause
  exit /b 2
)

echo ============================================================
echo MOCHIPOYO - STOPPED FRESH LOOPS READ-ONLY DIAGNOSTIC
echo ALL NINE FORWARD LOOPS / SELF-CONTAINED BAT
echo ============================================================
echo.
echo Targets: M9V M9Y M10B M10E M10P M10P2 M10W19 M10W26 M10W34
echo This BAT only reads/copies diagnostic evidence.
echo It does NOT remove locks, restart loops, reset runtimes,
echo change prospective starts, alter state/history, or touch MT5 CSVs.
echo.

(
  echo stage=ALL_NINE_FRESH_LOOP_STOP_DIAGNOSTIC_AUDIT_ONLY
  echo built_local=%DATE% %TIME%
  echo repository=%CD%
  echo mutations_performed=false
  echo locks_removed=false
  echo processes_started_or_stopped=false
  echo runtime_or_start_modified=false
) > "%ARCH%\00_READ_ME_FIRST.txt"

(
  echo ==== CURRENT DIRECTORY ====
  echo %CD%
  echo.
  echo ==== BRANCH ====
  git rev-parse --abbrev-ref HEAD
  echo.
  echo ==== COMMIT ====
  git rev-parse HEAD
  echo.
  echo ==== STATUS ====
  git status --short
  echo.
  echo ==== SPARSE CHECKOUT ====
  git sparse-checkout list
  echo.
  echo ==== TRACKED RECOVERY FILES ====
  git ls-files "scripts/mochipoyo_alert_research/recovery/*"
  echo.
  echo ==== LOCAL RECOVERY TREE ====
  dir /s /b "scripts\mochipoyo_alert_research\recovery"
) > "%ARCH%\01_repository_state.txt" 2>&1

powershell -NoProfile -ExecutionPolicy Bypass -Command "$markers=@('run_m9v_shadow_forever_safe','run_m9y_shadow_forever_safe.py','m10b_runtime.py','m10e_runtime.py','m10p_guarded_runtime.py','m10p2_guarded_runtime.py','m10w19_runtime.py','run_m10w26_private_snapshot','run_m10w34_private_snapshot.py'); $rows=Get-CimInstance Win32_Process ^| Where-Object { $cmd=$_.CommandLine; $cmd -and (($markers ^| ForEach-Object { $cmd -like ('*'+$_+'*') }) -contains $true) } ^| Select-Object ProcessId,CreationDate,CommandLine; if($rows){$rows ^| ConvertTo-Json -Depth 5}else{'[]'}" > "%ARCH%\02_matching_processes.json" 2>&1

set "INV=%ARCH%\03_file_inventory.txt"
> "%INV%" echo READ-ONLY FILE INVENTORY

call :capture "M9V_lock" "%ROOT%\m9v_runtime\m9v_shadow_loop.lock"
call :capture "M9V_runtime" "%ROOT%\m9v_runtime\m9v_runtime_manifest.json"
call :capture "M9V_status" "%ROOT%\logs\m9v\latest_m9v_shadow_loop_status.json"
call :capture "M9V_summary" "%ROOT%\outputs\M9V\LATEST\01_summary.json"
call :tailcopy "M9V_log_tail" "%ROOT%\logs\m9v\m9v_shadow_forever.log"

call :capture "M9Y_lock" "%ROOT%\m9y_runtime\m9y_shadow_loop.lock"
call :capture "M9Y_runtime" "%ROOT%\m9y_runtime\m9y_runtime_manifest.json"
call :capture "M9Y_status" "%ROOT%\logs\m9y\latest_m9y_shadow_loop_status.json"
call :capture "M9Y_summary" "%ROOT%\outputs\M9Y\LATEST\01_summary.json"
call :tailcopy "M9Y_log_tail" "%ROOT%\logs\m9y\m9y_shadow_forever.log"

call :capture "M10B_lock" "%ROOT%\m10b_runtime\m10b_shadow_loop.lock"
call :capture "M10B_runtime" "%ROOT%\m10b_runtime\m10b_runtime_manifest.json"
call :capture "M10B_status" "%ROOT%\logs\m10b\latest_m10b_shadow_loop_status.json"
call :capture "M10B_summary" "%ROOT%\outputs\M10B\LATEST\01_summary.json"
call :tailcopy "M10B_log_tail" "%ROOT%\logs\m10b\m10b_bounded_adapter_forever.log"

call :capture "M10E_lock" "%ROOT%\m10e_runtime\m10e_shadow_loop.lock"
call :capture "M10E_runtime" "%ROOT%\m10e_runtime\m10e_runtime_manifest.json"
call :capture "M10E_status" "%ROOT%\logs\m10e\latest_m10e_shadow_loop_status.json"
call :capture "M10E_summary" "%ROOT%\outputs\M10E\LATEST\01_summary.json"
call :tailcopy "M10E_log_tail" "%ROOT%\logs\m10e\m10e_bounded_adapter_forever.log"

call :capture "M10P_lock" "%ROOT%\m10p_runtime\m10p_shadow_loop.lock"
call :capture "M10P_runtime" "%ROOT%\m10p_runtime\m10p_runtime_manifest.json"
call :capture "M10P_state" "%ROOT%\m10p_runtime\m10p_runtime_state.json"
call :capture "M10P_status" "%ROOT%\logs\m10p\latest_m10p_shadow_loop_status.json"
call :capture "M10P_summary" "%ROOT%\outputs\M10P\LATEST\01_summary.json"
call :tailcopy "M10P_log_tail" "%ROOT%\logs\m10p\m10p_bounded_adapter_forever.log"

call :capture "M10P2_lock" "%ROOT%\m10p2_runtime\m10p2_shadow_loop.lock"
call :capture "M10P2_runtime" "%ROOT%\m10p2_runtime\m10p2_runtime_manifest.json"
call :capture "M10P2_state" "%ROOT%\m10p2_runtime\m10p2_runtime_state.json"
call :capture "M10P2_status" "%ROOT%\logs\m10p2\latest_m10p2_shadow_loop_status.json"
call :capture "M10P2_summary" "%ROOT%\outputs\M10P2\LATEST\01_summary.json"
call :tailcopy "M10P2_log_tail" "%ROOT%\logs\m10p2\m10p2_bounded_adapter_forever.log"

call :capture "M10W19_lock" "%ROOT%\m10w19_runtime\m10w19_shadow_loop.lock"
call :capture "M10W19_runtime" "%ROOT%\m10w19_runtime\m10w19_runtime_manifest.json"
call :capture "M10W19_state" "%ROOT%\m10w19_runtime\m10w19_runtime_state.json"
call :capture "M10W19_status" "%ROOT%\logs\m10w19\latest_m10w19_shadow_loop_status.json"
call :capture "M10W19_summary" "%ROOT%\outputs\M10W19\LATEST\01_summary.json"
call :tailcopy "M10W19_log_tail" "%ROOT%\logs\m10w19\m10w19_bounded_adapter_forever.log"

call :capture "M10W26_lock" "%ROOT%\m10w26_runtime\m10w26_shadow_loop.lock"
call :capture "M10W26_runtime" "%ROOT%\m10w26_runtime\m10w26_runtime_manifest.json"
call :capture "M10W26_state" "%ROOT%\m10w26_runtime\m10w26_runtime_state.json"
call :capture "M10W26_start_receipt" "%ROOT%\m10w26_runtime\m10w26_runtime_start_receipt.json"
call :capture "M10W26_status" "%ROOT%\logs\m10w26\latest_m10w26_shadow_loop_status.json"
call :capture "M10W26_summary" "%ROOT%\outputs\M10W26\LATEST\01_summary.json"
call :capture "M10W26_snapshot_receipt" "%ROOT%\bounded_csv_source_adapter\loop_snapshots\M10W26\00_snapshot_receipt.json"
call :tailcopy "M10W26_log_tail" "%ROOT%\logs\m10w26\m10w26_private_snapshot_forever.log"

call :capture "M10W34_lock" "%ROOT%\m10w34_runtime\m10w34_shadow_loop.lock"
call :capture "M10W34_runtime" "%ROOT%\m10w34_runtime\m10w34_runtime_manifest.json"
call :capture "M10W34_state" "%ROOT%\m10w34_runtime\m10w34_runtime_state.json"
call :capture "M10W34_start_receipt" "%ROOT%\m10w34_runtime\m10w34_runtime_start_receipt.json"
call :capture "M10W34_prestart" "%ROOT%\m10w34_runtime\m10w34_prestart_causal_engine_audit.json"
call :capture "M10W34_status" "%ROOT%\logs\m10w34\latest_m10w34_shadow_loop_status.json"
call :capture "M10W34_summary" "%ROOT%\outputs\M10W34\LATEST\01_summary.json"
call :capture "M10W34_snapshot_receipt" "%ROOT%\bounded_csv_source_adapter\loop_snapshots\M10W34\00_snapshot_receipt.json"
call :tailcopy "M10W34_log_tail" "%ROOT%\logs\m10w34\m10w34_private_snapshot_forever.log"

set "META=%ROOT%\outputs\M8B\LATEST\06_symbol_metadata.json"
call :capture "M8B_symbol_metadata" "%META%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$result=[ordered]@{metadata_path=$env:META;metadata_exists=(Test-Path -LiteralPath $env:META);files=[ordered]@{}}; if(Test-Path -LiteralPath $env:META){try{$m=Get-Content -Raw -LiteralPath $env:META ^| ConvertFrom-Json; $root=[string]$m.mt5_files_root; $result.data_root=$root; $map=[ordered]@{M1='goldsharp_m1.csv';M5='goldsharp_m5.csv';M15='goldsharp_m15.csv';H1='goldsharp_h1.csv';H4='goldsharp_h4.csv';D1='goldsharp_d1.csv'}; foreach($k in $map.Keys){$p=Join-Path $root $map[$k]; $row=[ordered]@{path=$p;exists=(Test-Path -LiteralPath $p)}; if($row.exists){$f=Get-Item -LiteralPath $p; $row.size_bytes=$f.Length; $row.modified_at=$f.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss'); $row.last_row=(Get-Content -LiteralPath $p -Tail 1 -ErrorAction Stop)}; $result.files[$k]=$row}}catch{$result.error=$_.Exception.Message}}; $result ^| ConvertTo-Json -Depth 8" > "%ARCH%\04_feed_frontiers.json" 2>&1

if exist "%PKG%" del /q "%PKG%" >nul 2>&1
if exist "%ZIPLOG%" del /q "%ZIPLOG%" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path (Join-Path $env:ARCH '*') -DestinationPath $env:PKG -Force" > "%ZIPLOG%" 2>&1
if not exist "%PKG%" (
  copy /y "%ZIPLOG%" "%ARCH%\05_zip_command.log" >nul 2>&1
  echo [STOP] Diagnostic files were collected, but ZIP creation failed.
  echo Folder: %ARCH%
  pause
  exit /b 2
)
copy /y "%PKG%" "%ARCH%\99_UPLOAD_PACKAGE.zip" >nul
if exist "%LATEST%" rmdir /s /q "%LATEST%"
mkdir "%LATEST%" >nul 2>&1
xcopy "%ARCH%\*" "%LATEST%\" /e /i /y >nul

echo.
echo [DIAGNOSTIC COMPLETE]
echo %LATEST%\99_UPLOAD_PACKAGE.zip
start "" explorer "%LATEST%"
echo.
echo Upload only 99_UPLOAD_PACKAGE.zip.
echo Do not delete locks, rerun initializers, or restart BAT03 until reviewed.
pause
exit /b 0

:capture
set "LABEL=%~1"
set "SRC=%~2"
if exist "%SRC%" (
  for %%F in ("%SRC%") do echo PRESENT %LABEL% size=%%~zF modified=%%~tF path=%SRC%>>"%INV%"
  copy /y "%SRC%" "%ARCH%\%LABEL%.txt" >nul
) else (
  echo MISSING %LABEL% path=%SRC%>>"%INV%"
)
exit /b 0

:tailcopy
set "LABEL=%~1"
set "SRC=%~2"
if exist "%SRC%" (
  for %%F in ("%SRC%") do echo PRESENT %LABEL% size=%%~zF modified=%%~tF path=%SRC%>>"%INV%"
  powershell -NoProfile -Command "Get-Content -LiteralPath $env:SRC -Tail 250" > "%ARCH%\%LABEL%.txt" 2>&1
) else (
  echo MISSING %LABEL% path=%SRC%>>"%INV%"
)
exit /b 0
