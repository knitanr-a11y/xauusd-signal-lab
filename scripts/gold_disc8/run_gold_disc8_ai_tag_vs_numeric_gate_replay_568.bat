@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

python scripts\gold_disc8\audit_gold_disc8_ai_tag_vs_numeric_gate_replay_568.py ^
  --ai-review-ledger-jsonl "data\gold_disc8\verification\ai_review_data_driven\disc8_ai_review\trade_ai_review_ledger.jsonl" ^
  --trade-feature-snapshot-csv "data\gold_disc8\verification\ai_review_data_driven\disc8_ai_review\trade_feature_snapshot.csv" ^
  --base-trade-csv "data\gold_disc8\verification\ai_review_data_driven\disc8_ai_review\disc8_review_trade_outcome_sample.csv" ^
  --kept-ledger-csv "data\gold_disc8\source_of_truth\group_tag_filtered\group_tag_filtered_source_trade_ledger.csv" ^
  --gate-rules-json "data\gold_disc8\operational_candidate\group_tag_filtered\gold_disc8_runtime_group_tag_gate_rules.json" ^
  --numeric-rules-json "data\runtime_logs\gold_disc8_ai_tag_numeric_tagger_from_review\gold_disc8_ai_tag_numeric_tagger_rules.json" ^
  --tag-recall-csv "data\runtime_logs\gold_disc8_ai_tag_numeric_tagger_from_review\gold_disc8_ai_tag_numeric_tagger_tag_recall_summary.csv" ^
  --out-root "data\runtime_logs\gold_disc8_ai_tag_vs_numeric_gate_replay_568" ^
  --expected-base-rows 568 ^
  --promotable-only

set EXIT_CODE=%ERRORLEVEL%
echo.
echo exit_code=%EXIT_CODE%
echo outputs: data\runtime_logs\gold_disc8_ai_tag_vs_numeric_gate_replay_568\latest
pause
exit /b %EXIT_CODE%
