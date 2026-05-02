@echo off
setlocal
cd /d "%~dp0.."
echo Running XM KIWAMI GOLD# ABC v2 backtest...
echo.
py scripts\run_preset_backtest.py --preset xm_kiwami_gold_abc_v2 --data-dir data\raw\xm_kiwami --save
if errorlevel 1 (
  echo.
  echo Backtest failed.
  echo If Python is not found, install Python or try: python scripts\run_preset_backtest.py --preset xm_kiwami_gold_abc_v2 --data-dir data\raw\xm_kiwami --save
) else (
  echo.
  echo Backtest succeeded.
)
echo.
pause
