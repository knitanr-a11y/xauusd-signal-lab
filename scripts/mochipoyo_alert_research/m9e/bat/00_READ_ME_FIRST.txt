M9E Causal Divergence Context Audit
==================================

Purpose
-------
Add regular divergence and hidden divergence context to the reviewed M9D adverse-path checkpoints and first causal turn entries.

Important
---------
- M9E is audit-only.
- Keep M8C, M7C, and the source collector running.
- Do not reset any prospective start.
- M7C formulas and thresholds are unchanged.
- M9E uses the existing Tier-B replay population only for exploratory path research.
- Tier B is NOT genuine Mochipoyo source truth.
- No divergence rule is promoted automatically.

Divergence types
----------------
BULLISH_REGULAR:
  price second low < first low, oscillator second low > first low
BULLISH_HIDDEN:
  price second low > first low, oscillator second low < first low
BEARISH_REGULAR:
  price second high > first high, oscillator second high < first high
BEARISH_HIDDEN:
  price second high < first high, oscillator second high > first high

Oscillators
-----------
- RCI9
- RCI14
- RCI18
- MACD line 6/13
- MACD histogram 6/13/4

Timeframes
----------
M1 / M5 / M15 / H1 / H4

Causality
---------
Only price pivots already confirmed by the decision time are used.
No future pivot confirmation is allowed.
The independent confirmed-pivot proxy does not claim exact proprietary ZigZag reproduction.

Run
---
1. Run 01_run_causal_divergence_context_audit.bat once.
2. Success: [M9E PASS]
3. On [M9E BLOCKED], do not repeat unchanged. Preserve the full screen error.
4. Run 02_open_latest_results.bat after PASS.
5. Submit:
   %LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9E\LATEST\99_UPLOAD_PACKAGE.zip
