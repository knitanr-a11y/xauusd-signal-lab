M9P GOLD Dynamic Core Deterministic Reproduction

Purpose:
- Reproduce canonical N1/N2/N3 from the supplied GOLD 2023-2026 history.
- Report N6 H4-RCI risk state only; N6 is NOT a gate.
- This is audit-only. No Discord send, MT5 order, final signal, or live entry gate is enabled.

Data location:
MT5 Files\gold_v3_2023_2026\

Keep running unchanged:
- M8C forward shadow
- M7C prospective shadow
- Mochipoyo source collector

Execution order:
1. Run 01_run_gold_dynamic_core_reproduction_audit.bat ONCE.
2. Success text: [M9P PASS]
3. If blocked: [M9P BLOCKED] and send the full screen output to ChatGPT.
4. On success, run 02_open_latest_results.bat.
5. Submit 99_UPLOAD_PACKAGE.zip from the opened LATEST folder.

Output folder:
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9P\LATEST

Important:
- Do not stop or reset M8C.
- Do not change M7C formulas or thresholds.
- Do not use N6 as an entry filter or stop.
- Historical spread is included. Commission and swap are not modeled.
