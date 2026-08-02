# START HERE — BTC AI Candidate Research V1

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-ai-v1-data-acquisition`
- status: `BTC_AI_V1_DATA_ACQUISITION_SCRIPT_READY_PENDING_MT5_EXPORT`
- date: `2026-08-03`

## Scope

BTCをGOLDで確立したAI研究方式によりゼロベースで研究する。

旧BTC BCR、旧stacking、旧5候補は新研究のauthorityにしない。必要な場合のみ重複回避用のaudit historyとして扱う。

## Current stage

候補探索前のデータ取得段階。

Read:

1. `docs/btc_ai_v1/BTC_AI_MT5_HISTORY_EXPORTER_20260803.md`
2. `mt5/btc_ai_v1/BTC_AI_History_Exporter.mq5`
3. `config/btc_ai_v1/current_state_20260803.json`

## Required data

MT5 broker-server時刻の確定足:

- M1
- M5
- M15
- H1
- H4
- D1

期間:

- requested start: `2023-01-01 00:00:00`
- requested end: latest fully closed bar in 2026

## Hard boundaries

- CSV最新行を形成中足として出力しない。
- JSTへ変換しない。
- brokerに存在しない過去データを補間しない。
- CSV監査完了前に候補探索を開始しない。
- GOLD V19、Challenger C1、P75を変更しない。
- MT5 order、Discord、live-ready、final signalを作らない。
