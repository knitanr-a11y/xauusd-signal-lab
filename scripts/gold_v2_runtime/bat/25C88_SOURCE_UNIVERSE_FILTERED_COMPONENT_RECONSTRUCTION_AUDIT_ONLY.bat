@echo off
setlocal
cd /d "%~dp0\..\..\.."

python scripts\gold_v2_runtime\audit_gold_v2_25c88_source_universe_filtered_component_reconstruction_audit_only.py

endlocal
