@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ============================================================
echo GOLD DISC8 top3 candidate rule CONSOLIDATION AUDIT ONLY
echo ============================================================
echo.
echo Purpose:
echo   Consolidate the previous 16 candidate rules before demo MT5 gate design.
echo   This groups duplicate-like rules by strategy + feature + op + threshold.
echo   It classifies each group into BLOCK candidate / WATCH candidate / AI review continue / REJECT.
echo.
echo Input SOT:
echo   data\runtime_logs\gold_disc8_top3_candidate_rule_replay_568\latest
echo.
echo Outputs:
echo   data\runtime_logs\gold_disc8_top3_candidate_rule_consolidation\latest
echo.
echo Classification intent:
echo   BLOCK_CANDIDATE      = possible demo BLOCK gate candidate, still audit-only
  echo WATCH_CANDIDATE      = useful for demo notification/ledger/watch, not automatic block yet
  echo AI_REVIEW_CONTINUE   = numeric signal is not safe enough; keep AI/manual review path
  echo REJECT_CANDIDATE     = weak or unsafe candidate

echo.
echo Safety:
echo   No OpenAI API, no Discord, no MT5, no SOT mutation, no runtime gate mutation.
echo   The JSON output is audit-only and must NOT be used directly as runtime config.
echo.

python scripts\gold_disc8\audit_gold_disc8_top3_candidate_rule_consolidation.py ^
  --replay-root "data\runtime_logs\gold_disc8_top3_candidate_rule_replay_568\latest" ^
  --out-root "data\runtime_logs\gold_disc8_top3_candidate_rule_consolidation" ^
  --strategies "DISC_08_BUY_TP200_SL100_RR2,DISC_01_BUY_TP200_SL100_RR2,DISC_09_BUY_TP80_SL50_RR1p6" ^
  --expected-trade-rows 568 ^
  --min-hit-count 5 ^
  --block-min-precision 0.80 ^
  --block-max-false-rate 0.20 ^
  --block-max-positive-months 1 ^
  --watch-min-precision 0.60 ^
  --watch-max-false-rate 0.40 ^
  --watch-min-ai-block-hit 5 ^
  --ai-review-min-ai-block-hit 5

set EXIT_CODE=%ERRORLEVEL%
echo.
echo exit_code=%EXIT_CODE%
echo outputs: data\runtime_logs\gold_disc8_top3_candidate_rule_consolidation\latest
pause
exit /b %EXIT_CODE%
