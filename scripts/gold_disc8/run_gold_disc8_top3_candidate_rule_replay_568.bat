@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ============================================================
echo GOLD DISC8 top3 candidate rule replay 568 AUDIT ONLY
echo ============================================================
echo.
echo Purpose:
echo   Replay candidate numeric rules from miss feature_probe over all 568 reviewed trades.
echo   This checks whether missed AI_BLOCK trades can be captured without false-blocking AI_ALLOW trades.
echo.
echo Target strategies ONLY:
echo   DISC_08_BUY_TP200_SL100_RR2
echo   DISC_01_BUY_TP200_SL100_RR2
echo   DISC_09_BUY_TP80_SL50_RR1p6
echo.
echo Target tag group:
echo   risk only
echo.
echo Rule source SOT:
echo   data\runtime_logs\gold_disc8_ai_block_numeric_miss_analysis_568\latest\gold_disc8_ai_block_numeric_miss_feature_probe.csv
echo.
echo Replay universe SOT:
echo   data\runtime_logs\gold_disc8_ai_tag_vs_numeric_gate_replay_568\latest\gold_disc8_ai_tag_vs_numeric_gate_replay_568_trade_audit.csv
echo.
echo Feature source SOT:
echo   data\gold_disc8\verification\ai_review_data_driven\disc8_ai_review\trade_feature_snapshot.csv
echo.
echo Candidate filters:
echo   missed_tag_capture_rate ^>= 0.40
echo   ai_allow_false_hit_rate ^<= 0.15
echo   precision_to_missed_tag ^>= 0.60
echo   hit_total_r ^< 0
echo   probe_hit_rows ^>= 5
echo.
echo Safety:
echo   No OpenAI API, no Discord, no MT5, no SOT mutation, no runtime gate mutation.
echo   Candidate rules are audit probes only. Do NOT promote directly.
echo.

python scripts\gold_disc8\audit_gold_disc8_top3_candidate_rule_replay_568.py ^
  --trade-audit-csv "data\runtime_logs\gold_disc8_ai_tag_vs_numeric_gate_replay_568\latest\gold_disc8_ai_tag_vs_numeric_gate_replay_568_trade_audit.csv" ^
  --trade-feature-snapshot-csv "data\gold_disc8\verification\ai_review_data_driven\disc8_ai_review\trade_feature_snapshot.csv" ^
  --feature-probe-csv "data\runtime_logs\gold_disc8_ai_block_numeric_miss_analysis_568\latest\gold_disc8_ai_block_numeric_miss_feature_probe.csv" ^
  --out-root "data\runtime_logs\gold_disc8_top3_candidate_rule_replay_568" ^
  --strategies "DISC_08_BUY_TP200_SL100_RR2,DISC_01_BUY_TP200_SL100_RR2,DISC_09_BUY_TP80_SL50_RR1p6" ^
  --tag-group risk ^
  --expected-trade-rows 568 ^
  --min-probe-hit-rows 5 ^
  --min-missed-tag-capture-rate 0.40 ^
  --max-ai-allow-false-hit-rate 0.15 ^
  --min-precision-to-missed-tag 0.60 ^
  --max-hit-total-r -0.000001

set EXIT_CODE=%ERRORLEVEL%
echo.
echo exit_code=%EXIT_CODE%
echo outputs: data\runtime_logs\gold_disc8_top3_candidate_rule_replay_568\latest
pause
exit /b %EXIT_CODE%
