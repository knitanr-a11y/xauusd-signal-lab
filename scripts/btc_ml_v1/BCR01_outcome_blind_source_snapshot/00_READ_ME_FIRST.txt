BCR01 — Outcome-blind Collector source snapshot

Purpose
-------
Create one logical read-only snapshot of the Mochipoyo Collector source/provenance tables needed for BTC candidate research.

This stage does NOT:
- stop or restart Collector or M7C;
- copy or upload the raw SQLite database;
- query outcome-bearing tables;
- design a candidate formula;
- evaluate WR, PF, DD, MFE or MAE;
- send Discord messages or MT5 orders.

Run
---
1. Confirm GitHub Desktop repository C:\btc-ff is on:
   feature/btc-fresh-forward-research
2. Fetch origin / Pull origin.
3. Double-click:
   01_run_BCR01.bat
4. Run only once.
5. Upload the ZIP selected by Explorer:
   %LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\BCR01_outcome_blind_source_snapshot\LATEST\99_UPLOAD_PACKAGE.zip

Source
------
The exact source is:
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\mochipoyo_alerts.sqlite3

The script opens it in SQLite read-only/query-only mode and uses one consistent read transaction. Collector and M7C remain running unchanged.

Allowlisted source tables
-------------------------
- collector_state
- raw_alerts
- raw_alert_annotations
- collection_runs

Forbidden source tables
-----------------------
- episodes
- episode_events
- episode_build_anomalies
- episode_build_runs
- mt5_alignment
- feature_snapshots
- virtual_entries
- outcomes

Stop
----
After the ZIP is created, upload it and stop. Do not run the BAT again unless the submitted package is proven invalid.
