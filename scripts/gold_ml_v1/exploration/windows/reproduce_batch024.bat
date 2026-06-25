@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\..\..\.."
set "PYTHON_CMD="
if exist ".venv_batch023_bridge\Scripts\python.exe" set "PYTHON_CMD=.venv_batch023_bridge\Scripts\python.exe"
if not defined PYTHON_CMD if exist ".venv_batch023\Scripts\python.exe" set "PYTHON_CMD=.venv_batch023\Scripts\python.exe"
if not defined PYTHON_CMD where py >nul 2>nul && set "PYTHON_CMD=py -3.12"
if not defined PYTHON_CMD where python >nul 2>nul && set "PYTHON_CMD=python"
if not defined PYTHON_CMD exit /b 4
%PYTHON_CMD% scripts\gold_ml_v1\exploration\run_batch024_local_reproduction.py --raw-dir "%~1" --config "%~2" --frozen-result "%~3" --output-dir outputs\gold_ml_v1\exploration_batch024_local_reproduction
exit /b %ERRORLEVEL%
