@echo off
cd /d "%~dp0.."
python bootstrap\materialize_assets.py || exit /b 20
call launchers\local_paths.bat
"%PYTHON_EXE%" scripts\shadow_full95_all_q20_v1.py process --m1 "%M1_CSV%" --m15 "%M15_CSV%" --h1 "%H1_CSV%" --h4 "%H4_CSV%" --d1 "%D1_CSV%"
pause
