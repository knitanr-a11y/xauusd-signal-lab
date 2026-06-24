@echo off
setlocal EnableExtensions

REM GOLD_ML_V1 audit-only overlap runner.
REM Usage:
REM   run_candidate_overlap_audit.bat REG007 REG008 REG010 REG015 REG020 REG014A [OUTPUT_DIR]
REM Each REG argument must be the exact trade-registry CSV for that immutable candidate.

if "%~6"=="" (
  echo ERROR: six exact trade-registry CSV paths are required.
  echo Usage: %~nx0 REG007 REG008 REG010 REG015 REG020 REG014A [OUTPUT_DIR]
  exit /b 2
)

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\..") do set "REPO_ROOT=%%~fI"
set "OUTPUT_DIR=%~7"
if "%OUTPUT_DIR%"=="" set "OUTPUT_DIR=%REPO_ROOT%\FX_OUTPUTS\gold_ml_v1\audits\GML1-BATCH-015-overlap"

python "%SCRIPT_DIR%candidate_overlap_audit.py" ^
  --config "%REPO_ROOT%\config\gold_ml_v1\candidate_overlap_audit_20260624.json" ^
  --registry "GML1-PROV-007=%~1" ^
  --registry "GML1-PROV-008=%~2" ^
  --registry "GML1-PROV-010=%~3" ^
  --registry "GML1-PROV-015=%~4" ^
  --registry "GML1-PROV-020=%~5" ^
  --registry "GML1-WATCH-014-A=%~6" ^
  --output-dir "%OUTPUT_DIR%"

set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo ERROR: overlap audit failed closed with exit code %RC%.
  exit /b %RC%
)

echo PASS: audit-only overlap outputs written to "%OUTPUT_DIR%".
exit /b 0
