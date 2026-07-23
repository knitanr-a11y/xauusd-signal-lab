M9G MINIMAL LOSS PRUNING CANDIDATE AUDIT

Run:
  01_run_minimal_loss_pruning_candidate_audit.bat

Mode:
  ONE TIME audit only.

Coexistence:
  Keep M8C, M7C, and collector running. Do not reset any prospective start.

Purpose:
  Compare a very small frozen set of M9F-derived first-turn avoid-state hypotheses.
  Evaluate PF, win rate, net bps, chronological max drawdown, max losing streak, ticker/direction results, and monthly retained trade counts.

Important:
  This is the SAME 852-trade Tier-B sample used to generate the hypotheses.
  It is NOT validation and cannot promote a live gate.
  P3 is sensitivity only; do not choose it merely because it fits this sample better.

Success:
  [M9G PASS]

Blocked:
  [M9G BLOCKED]
  Do not repeat an unchanged blocked BAT. Send the full screen output to ChatGPT.

Results:
  02_open_latest_results.bat

Submission:
  %LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9G\LATEST\99_UPLOAD_PACKAGE.zip

Safety:
  Discord OFF. MT5 orders OFF. live-ready OFF. final-signal OFF. entry gate OFF.
  M7C formula/threshold unchanged. M8C unchanged.
