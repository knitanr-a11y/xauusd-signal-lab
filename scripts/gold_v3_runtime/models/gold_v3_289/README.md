# Stage289 local model directory

This directory is populated locally by `gold_v3_289_train_live_models_audit.py` from the existing contractually closed `goldsharp_*.csv` history.

Generated files:

- `stage280_rev_long_2026_model.txt`
- `stage280_rev_long_2026_contract.json`
- `stage281_med4h_cont_long_2026_model.txt`
- `stage281_med4h_cont_long_2026_contract.json`
- `stage289_model_training_report.json`

The live SHADOW cycle starts only when local training and the four parity checks pass. Model download, substitute models, and fallback thresholds are prohibited.
