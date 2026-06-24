@echo off
setlocal EnableExtensions

if "%~1"=="" (
  echo ERROR: exact handoff ZIP path is required.
  echo Usage: %~nx0 GOLD_ML_V1_EXACT_HANDOFF_ARTIFACTS_20260625.zip
  exit /b 2
)

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\..") do set "REPO_ROOT=%%~fI"

python "%SCRIPT_DIR%install_exact_handoff_artifacts.py" "%~1" ^
  --locator "%REPO_ROOT%\config\gold_ml_v1\exact_artifact_locator_20260625.json" ^
  --output-dir "%REPO_ROOT%\config\gold_ml_v1\registries"

set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo ERROR: exact artifact installation failed with exit code %RC%.
  exit /b %RC%
)

echo PASS: exact artifacts installed under config\gold_ml_v1\registries.
exit /b 0
