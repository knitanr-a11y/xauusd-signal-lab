@echo off
cd /d "%~dp0\..\..\..\.."
python scripts\gold_ml_v1\exploration\run_batch024_local_reproduction.py --raw-dir "%~1" --config "%~2" --frozen-result "%~3" --output-dir outputs\gold_ml_v1\exploration_batch024_local_reproduction
