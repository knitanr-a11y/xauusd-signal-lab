@echo off
setlocal EnableExtensions
chcp 65001 >nul

echo [GOLD V2 MT5 DATA] Installing Python requirements...
python -m pip install --upgrade pip
python -m pip install pandas MetaTrader5

echo.
echo [DONE] Requirements installed.
pause
