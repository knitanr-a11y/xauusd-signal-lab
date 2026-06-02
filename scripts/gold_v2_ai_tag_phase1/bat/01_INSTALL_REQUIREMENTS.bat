@echo off
setlocal EnableExtensions
chcp 65001 >nul

echo [GOLD V2 AI TAG PHASE1] Installing Python requirements...
echo This installs only Python packages. It does not call API, MT5, or Discord.

python --version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] python command not found. Please install Python or add it to PATH.
  pause
  exit /b 1
)

python -m pip install --upgrade pip
python -m pip install openai pandas numpy

if errorlevel 1 (
  echo [ERROR] pip install failed.
  pause
  exit /b 1
)

echo [OK] Requirements installed.
pause
