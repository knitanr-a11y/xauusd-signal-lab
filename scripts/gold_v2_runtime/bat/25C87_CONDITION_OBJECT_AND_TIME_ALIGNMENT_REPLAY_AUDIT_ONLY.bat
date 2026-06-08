@echo off
setlocal
cd /d "%~dp0\..\..\.."

python scripts\gold_v2_runtime\audit_gold_v2_25c87_condition_object_and_time_alignment_replay_audit_only.py

endlocal
