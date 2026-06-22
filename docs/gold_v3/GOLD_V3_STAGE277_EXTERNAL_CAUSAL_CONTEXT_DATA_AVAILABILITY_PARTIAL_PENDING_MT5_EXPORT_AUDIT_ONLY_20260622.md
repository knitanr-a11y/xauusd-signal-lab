# GOLD V3 Stage277 External Causal Context Data Availability Audit

作成日: 2026-06-22  
現在状態: `GOLD_V3_277_EXTERNAL_CAUSAL_CONTEXT_DATA_AVAILABILITY_PARTIAL_PENDING_MT5_EXPORT_AUDIT_ONLY`

## 結論

Stage277のdefinition、同一MT5端末からexact broker symbolとclosed-bar履歴範囲を取得するread-only exporter、raw CSV検証器、regression testを作成した。

ただし、`XMTrading-MT5 3`端末のraw inventory CSVをまだ受領していないため、外部sourceのexact symbol・実在・2023〜2026 coverageは未確認である。Webや別brokerで推測補完せず、正式状態を`PARTIAL_PENDING_MT5_EXPORT`とする。

## 作成した実装

- `tools/mt5/ExportGoldV3ExternalContextInventory.mq5`
- `tools/gold_v3/stage277_audit_external_context_inventory.py`
- `tests/gold_v3/test_stage277_external_context_inventory.py`
- `docs/gold_v3/GOLD_V3_STAGE277_EXTERNAL_CAUSAL_CONTEXT_DATA_AVAILABILITY_DEFINITION_AUDIT_ONLY_20260622.md`
- `docs/gold_v3/README_EXPORT_GOLD_V3_EXTERNAL_CONTEXT_INVENTORY_MT5_JA.md`
- `docs/gold_v3/stage277_source_inventory_pending_20260622.csv`
- `docs/gold_v3/stage277_summary_pending_20260622.json`

## Exporterが確認する内容

broker serverが返す全symbolをexact nameのまま保存し、priority source候補と`GOLD#` baselineについて次を監査する。

- symbol existence
- M1 / M5 / M15 / H1 / H4 / D1
- 2023 / 2024 / 2025 / 2026 row count
- first / last bar OPEN time
- broker company / account server / terminal build
- closed availability
- duplicate / non-monotonic
- raw gap intervals
- trading session
- spread points / point / tick size / contract size

source group tokenはinventory hintだけであり、自動source選択やACTIVE化ではない。

## Causal contract

- CSV time: broker server bar OPEN time
- JST変換: なし
- closed bar only
- join: `source_close_time <= decision_time`
- forming bar: 禁止
- nearest future: 禁止
- gap fill: 禁止
- source fallback: 禁止

## 現在のsource台帳

- `GOLD#`: Stage273でbaseline reference確認済み
- XAGUSD / USDJPY / EURUSD / US500 / NAS100 / USD index / yield proxy: `PENDING_MT5_EXPORT`
- economic calendar: `BLOCKED_SEPARATE_NON_SYMBOL_SOURCE_NOT_AUDITED`

外部sourceのexact symbolを、この時点で`XAGUSD#`等と推測して記録していない。

## Test結果

ローカルsynthetic inventoryで:

- partial inventory generation: PASS
- account server mismatch BLOCKED: PASS
- fallback flag violation BLOCKED: PASS
- MQL5 read-only / closed-only static safety: PASS

合計: `4/4 PASS`

MetaEditorによる実端末compileはまだ実行されていないため、`NOT_YET_RUN`と明記する。

## Stage277を完了する次の入力

`ExportGoldV3ExternalContextInventory.mq5`を`XMTrading-MT5 3`の`GOLD#` chartで1回実行し、次の4 CSVを取得する。

- `*_symbols.csv`
- `*_timeframe_coverage.csv`
- `*_sessions.csv`
- `*_run_metadata.csv`

取得後、Python auditorでsource inventory、availability matrix、history coverage matrix、causal contract、unavailable ledgerを生成する。

## 変更していないもの

- Stage276は再実行していない。
- Stage275 / 276 thresholdを変更していない。
- current Specialist Health Router V3を変更していない。
- phase2 HV retestはSHADOW-only。
- continuous tick collectionは追加していない。
- candidateごとのtick取得は追加していない。
- performance gridを実行していない。
- candidateを作成していない。

## Safety state

`audit_only=ON / live_ready=OFF / final_signal=OFF / MT5_order=OFF / Discord_notify=OFF / partial_close=OFF`

運用状態: `NO_LIVE_PROMOTION_AUDIT_ONLY`
