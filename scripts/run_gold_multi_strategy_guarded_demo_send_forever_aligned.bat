@echo off
setlocal

cd /d "%~dp0.."

echo ============================================================
echo GOLD multi-strategy GUARDED DEMO SEND FOREVER aligned runner
echo Independent sidecar / existing Mochipoyo GOLD BAT is not modified
echo Sender --send requires BOTH --allow-demo-send and --send
echo Position policy: allow_any_until_max / duplicate guard: order_key ledger
echo Adapter lot: BUY=0.01, SELL B_ONLY=0.01, SELL CORE_AB=0.02
echo OUT_DIR=data\research_results\gold_multi_strategy_guarded_demo_send_forever_aligned
echo Stop with Ctrl+C
echo ============================================================

python scripts\run_gold_multi_strategy_guarded_demo_send_forever_aligned.py ^
  --out-dir data\research_results\gold_multi_strategy_guarded_demo_send_forever_aligned ^
  --interval-minutes 1 ^
  --offset-seconds 2 ^
  --position-policy allow_any_until_max ^
  --max-symbol-positions 20 ^
  --max-symbol-lot 1.0 ^
  --max-orders 1 ^
  --allow-demo-send ^
  --send

set EXITCODE=%ERRORLEVEL%
echo ============================================================
echo GOLD multi-strategy guarded demo-send forever aligned exit code: %EXITCODE%
echo ============================================================
exit /b %EXITCODE%
