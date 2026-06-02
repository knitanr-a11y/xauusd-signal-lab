@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "BAT_DIR=%~dp0"
for %%I in ("%BAT_DIR%..\..\..") do set "REPO_ROOT=%%~fI"
for %%I in ("%REPO_ROOT%\..\..") do set "FILES_DIR=%%~fI"

set "OUTPUT_DIR=%FILES_DIR%\FX_OUTPUTS\gold_v2_ai_tag_phase1"
set "EVAL_SCRIPT=%REPO_ROOT%\scripts\gold_v2_ai_tag_phase1\evaluate_gold_v2_ai_tag_phase1.py"
set "TAGS=%OUTPUT_DIR%\gold_v2_ai_phase1_ai_tags.csv"
set "TRUTH=%OUTPUT_DIR%\gold_v2_ai_phase1_eval_truth_hidden.csv"
set "EVAL_OUT=%OUTPUT_DIR%\phase1_eval"

echo [GOLD V2 AI TAG PHASE1] Evaluate
echo OUTPUT_DIR=%OUTPUT_DIR%
echo.

if not exist "%TAGS%" (
  echo [ERROR] AI tag output not found: %TAGS%
  echo Run 02_RUN_AI_TAG_PHASE1.bat first.
  pause
  exit /b 1
)

if not exist "%TRUTH%" (
  echo [ERROR] Hidden truth file not found: %TRUTH%
  echo Put/extract gold_v2_ai_phase1_eval_truth_hidden.csv under Files\FX_OUTPUTS\gold_v2_ai_tag_phase1
  pause
  exit /b 1
)

python "%EVAL_SCRIPT%" ^
  --tags "%TAGS%" ^
  --truth "%TRUTH%" ^
  --outdir "%EVAL_OUT%"

set "RC=%ERRORLEVEL%"
echo.
echo [GOLD V2 AI TAG PHASE1] Evaluation finished with exit code %RC%
echo Evaluation output: %EVAL_OUT%
echo.
pause
exit /b %RC%
