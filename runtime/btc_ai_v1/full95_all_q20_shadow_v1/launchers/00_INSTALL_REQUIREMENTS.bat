@echo off
cd /d "%~dp0.."
python bootstrap\materialize_assets.py || exit /b 20
python -m pip install -r requirements.txt
pause
