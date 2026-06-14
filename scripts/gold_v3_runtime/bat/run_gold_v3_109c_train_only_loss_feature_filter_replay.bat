@echo off
cd /d "%~dp0\..\..\.."
py -3 scripts\gold_v3_runtime\gold_v3_109c_train_only_loss_feature_filter_replay_audit.py
pause
