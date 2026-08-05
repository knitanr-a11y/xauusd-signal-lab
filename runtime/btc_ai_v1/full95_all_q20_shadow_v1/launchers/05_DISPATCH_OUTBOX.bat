@echo off
cd /d "%~dp0.."
python bootstrap\materialize_assets.py || exit /b 20
python scripts\shadow_full95_all_q20_v1.py dispatch-outbox
pause
