@echo off
setlocal
cd /d "%~dp0\..\..\.."

python scripts\gold_v2_runtime\audit_gold_v2_25c84_deep_cluster_representative_reconstruction_audit_only.py

endlocal
