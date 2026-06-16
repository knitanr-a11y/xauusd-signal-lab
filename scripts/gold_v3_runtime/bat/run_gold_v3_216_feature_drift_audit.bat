@echo off
cd /d "%~dp0\..\..\.."
py -3 scripts\gold_v3_runtime\gold_v3_216_feature_drift_monitoring_rule_audit.py %*
exit /b %ERRORLEVEL%
