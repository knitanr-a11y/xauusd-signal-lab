# GOLD V3 Stage289 live確定足・ML・安全側統合 SHADOW仕様

Status:

- `GOLD_V3_289_LIVE_CANDLE_ML_SAFE_SHADOW_READY_AUDIT_ONLY`
- `GOLD_V3_289_LIVE_CANDLE_ML_SAFE_SHADOW_PARTIAL_AUDIT_ONLY`
- `GOLD_V3_289_LIVE_CANDLE_ML_SAFE_SHADOW_BLOCKED_AUDIT_ONLY`

## 目的

Stage284 balanced + Stage286 strict SHORT safe admissionを、手入力candidate queueではなく、MT5 `MQL5/Files`直下のlive確定足CSVから再計算する。

SHADOW/audit-onlyであり、注文、Discord、final signal、partial closeは実装しない。

## 絶対制約

- GOLD V3のみ。GOLD V2、旧GOLD、DISC8、Stage41 feature snapshotを読まない。
- source CSVを変更しない。
- candidate poolを手動削除しない。
- future outcome、未確定exit、open/as-of足を特徴量やgateへ使わない。
- CSV契約上、open/in-progress candleは書かれず、最新行はclosed。
- open足を推測して削除しない。

## live入力

必須GOLD closed CSV:

- `goldsharp_m1.csv`
- `goldsharp_m5.csv`
- `goldsharp_m15.csv`
- `goldsharp_h1.csv`
- `goldsharp_h4.csv`
- `goldsharp_d1.csv`

Stage286 strict SHORT用:

- `us500cashsharp_m15.csv`
- `us100cashsharp_m15.csv`

外部2ファイルがなければ代替sourceを使わず、Stage286のみunavailable、全体statusはPARTIALとする。

## ローカル機械学習

初回BAT実行時、学習済みmodelがない場合は上記closed CSVの履歴からStage280・281 LightGBMをローカル学習する。

学習・校正期間:

- fit: `2024-01-01 <= time < 2025-07-01`
- calibration: `2025-07-01 <= time < 2026-01-01`
- 2026年はfit/calibrationに不使用
- historical labelは完全なM1 horizonがCSVに存在する行だけで作る

学習後、次の4項目を完全一致検査する。

Stage280:

- q95 threshold: `0.5927349103795366`
- fixture `2026-06-19 08:00:00` score: `0.5949591748604749`

Stage281:

- q85 threshold: `0.5525199124029727`
- fixture `2026-06-17 10:00:00` score: `0.6586538142862226`

1項目でも許容差`1e-12`を超えれば、`BLOCKED_PARITY_MISMATCH`としてSHADOW runtimeを起動しない。model download、別model、fallbackは使わない。

生成先:

`scripts/gold_v3_runtime/models/gold_v3_289/`

- `stage280_rev_long_2026_model.txt`
- `stage280_rev_long_2026_contract.json`
- `stage281_med4h_cont_long_2026_model.txt`
- `stage281_med4h_cont_long_2026_contract.json`
- `stage289_model_training_report.json`

## 固定候補

### Stage280

- `REV_LONG_Q95_BRK6_E175_SHADOW_RESEARCH`
- prior closed H4 DOWN
- M5 BRK6、directional body >= 0.20、60分以内
- next M5 open
- TP1.75ATR / SL1.0ATR / max6h

### Stage281

- `M15_CONT_LONG_Q85_EMA20_E225_AFTER_BASE_LOSS_72H_SHADOW_NEAR_MISS`
- prior closed H4 UP
- M5 EMA20 reclaim + prior high break、body >=0.15、45分以内
- source cooldown 120分
- latest resolved BASE lossから72時間以内
- TP2.25ATR / SL1.25ATR / max8h

### Stage286

- `SHORT_EXHAUST_MODERATE_OVERHEAT_SUBDUED_US_EQUITY`
- GOLD M15 ret8/ATR: `2.162461836828524 <= score <= 2.992581130893`
- GOLD M15 pos4 >= 0.75
- upper wick >= lower wick
- mean(US500, US100 M15 ret4/ATR) <= `0.410970621210`
- M5 bearish EMA20 cross + prior low break、body >=0.12、60分以内
- source cooldown 120分
- TP2.25ATR / SL1.25ATR / max8h

## 安全側統合

priority: Stage280=10、Stage281=20、Stage286=60。

- unresolved candidateは同時1件まで
- Stage280/281: resolved combined DD <= 30
- shared candidate cooldown 12時間
- Stage281: latest resolved BASE loss後72時間以内
- Stage286: resolved combined DD <= 10
- Stage286: latest resolved accepted candidate loss後24時間停止

DD、直近損失、BASE lossは必ず`exit_dt <= current entry_dt`のresolved rowsだけで計算する。

## BASE portfolio state

`--base-resolved-csv`の必須列:

- `entry_dt`
- `exit_dt`
- `pnl`

未接続時は候補検出だけ実行し、全candidate admissionを`BASE_PORTFOLIO_STATE_NOT_CONNECTED`で拒否してPARTIALとする。candidate-only equityへfallbackしない。

## 初回watermark

初回起動は最新closed M5 timeをwatermarkとして保存し、過去lookback候補を新規登録しない。次回からwatermark後のentryだけを処理する。

## 実行

`scripts/gold_v3_runtime/bat/run_gold_v3_289_live_candle_ml_safe_shadow.bat`

初回のみ自動学習とparity検査を行い、PASS後にSHADOW cycleを実行する。

出力:

`MQL5/Files/FX_OUTPUTS/gold_v3/289c/`

- `paste_me.txt`
- `gold_v3_289_detected_live_candle_candidates.csv`
- `gold_v3_289_decision_ledger.csv`
- `gold_v3_289_shadow_trade_ledger.csv`
- `gold_v3_289_latest_decisions.csv`
- `gold_v3_289_runtime_state.json`
- `gold_v3_289_summary.json`
- `gold_v3_289_validation.csv`

## Safety flags

- audit_only: true
- live_ready: false
- mt5_execution_enabled: false
- discord_live_enabled: false
- ai_api_called: false
- final_signal_enabled: false
- partial_close_enabled: false
