M9I GENUINE SOURCE VS PROXY GAP AUDIT

TYPE: ONE_TIME AUDIT

PURPOSE
- Compare the 43 frozen genuine source PRIMARY boundaries against unchanged frozen M7C proxy PRIMARY states.
- Separate exact/within-one-bar/missed source events from proxy-only extra PRIMARY events.
- Compare causal closed-bar M5/M15/H1/H4 RCI/EMA/MACD/volatility and fresh divergence context.
- Compare spread-adjusted outcomes only after the decision-time features are frozen.

IMPORTANT
- Keep M8C forward shadow running.
- Keep M7C and the source collector unchanged.
- Do NOT reset any prospective start.
- This does NOT modify M7C formulas or thresholds.
- This does NOT call proxy events genuine Mochipoyo alerts.
- This does NOT promote a gate or live rule.
- Commission and swap are NOT modeled.

RUN EXACTLY ONCE
  01_run_genuine_source_vs_proxy_gap_audit.bat

SUCCESS
  [M9I PASS]

BLOCKED
  [M9I BLOCKED]
  Do not repeat unchanged. Send the full screen output to ChatGPT.

OUTPUT
  %LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9I\LATEST

SUBMIT
  %LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9I\LATEST\99_UPLOAD_PACKAGE.zip
