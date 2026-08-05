@echo off
cd /d "%~dp0.."
python bootstrap\materialize_assets.py || exit /b 20
if not exist launchers\local_paths.bat (
  echo Copy local_paths.example.bat to local_paths.bat and edit the CSV paths.
  pause
  exit /b 2
)
call launchers\local_paths.bat
"%PYTHON_EXE%" scripts\shadow_full95_all_q20_v1.py init --m1 "%M1_CSV%" --m15 "%M15_CSV%" --h1 "%H1_CSV%" --h4 "%H4_CSV%" --d1 "%D1_CSV%"
pause
