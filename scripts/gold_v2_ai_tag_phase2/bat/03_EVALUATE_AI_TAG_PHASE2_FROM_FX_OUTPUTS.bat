@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "BAT_DIR=%~dp0"
for %%I in ("%BAT_DIR%..\..\..") do set "REPO_ROOT=%%~fI"
for %%I in ("%REPO_ROOT%\..\..") do set "FILES_DIR=%%~fI"

set "PHASE2_DIR=%FILES_DIR%\FX_OUTPUTS\gold_v2_ai_tag_phase2"
set "TAGS=%PHASE2_DIR%\gold_v2_ai_phase2_ai_tags.csv"
set "TRUTH=%PHASE2_DIR%\gold_v2_ai_phase2_eval_truth_hidden.csv"
set "EVAL_SCRIPT=%PHASE2_DIR%\evaluate_gold_v2_ai_tag_phase2.py"
set "OUTDIR=%PHASE2_DIR%\phase2_eval"

echo [GOLD V2 AI TAG PHASE2] Evaluate
echo PHASE2_DIR=%PHASE2_DIR%
echo.

if not exist "%TAGS%" (
  echo [ERROR] tags not found: %TAGS%
  echo Run 02_RUN_AI_TAG_PHASE2_FROM_FX_OUTPUTS.bat first.
  pause
  exit /b 1
)
if not exist "%TRUTH%" (
  echo [ERROR] truth not found: %TRUTH%
  pause
  exit /b 1
)
if not exist "%EVAL_SCRIPT%" (
  echo [ERROR] evaluator not found: %EVAL_SCRIPT%
  pause
  exit /b 1
)

python "%EVAL_SCRIPT%" ^
  --tags "%TAGS%" ^
  --truth "%TRUTH%" ^
  --outdir "%OUTDIR%"

set "RC=%ERRORLEVEL%"
echo.
echo [GOLD V2 AI TAG PHASE2] Evaluation finished with exit code %RC%
echo Output: %OUTDIR%
pause
exit /b %RC%
