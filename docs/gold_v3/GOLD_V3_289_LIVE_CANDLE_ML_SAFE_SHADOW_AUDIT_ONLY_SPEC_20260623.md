# GOLD V3 Stage289 live確定足・ML・安全側統合 SHADOW仕様

Status names:

- `GOLD_V3_289_LIVE_CANDLE_ML_SAFE_SHADOW_READY_AUDIT_ONLY`
- `GOLD_V3_289_LIVE_CANDLE_ML_SAFE_SHADOW_PARTIAL_AUDIT_ONLY`
- `GOLD_V3_289_LIVE_CANDLE_ML_SAFE_SHADOW_BLOCKED_AUDIT_ONLY`

## 目的

Stage284 balanced + Stage286 strict SHORT safe admissionを、手入力candidate queueではなく、MT5 `MQL5/Files`直下のlive確定足CSVから再計算する。

このStageはSHADOW/audit-onlyであり、注文・Discord・final signalを実装しない。

## 絶対制約

- GOLD V3のみ。
- GOLD V2、旧GOLD、DISC8、Stage41 feature snapshotを読まない。
- source CSVを変更しない。
- candidate poolを手動削除しない。
- future outcome、未確定exit、open/as-of足を特徴量・gateへ使わない。
- CSV契約: open/in-progress candleはCSVに書かれず、最新行はclosed。
- `csv_open_bar_exclusion_required=false`。

## live入力

必須GOLD closed CSV:

- `goldsharp_m1.csv`
- `goldsharp_m5.csv`
- `goldsharp_m15.csv`
- `goldsharp_h1.csv`
- `goldsharp_h4.csv`
- `goldsharp_d1.csv`

Stage286 strict SHORT用の外部closed M15:

- `us500cashsharp_m15.csv`
- `us100cashsharp_m15.csv`

外部2ファイルがない場合、代替sourceやfallbackは使わずStage286だけをunavailableとし、Stage289 statusはPARTIALになる。

## モデル

### Stage280

- Candidate: `REV_LONG_Q95_BRK6_E175_SHADOW_RESEARCH`
- LightGBM 2026 deployment model
- fit: 2024-01-01 <= time < 2025-07-01
- calibration: 2025-07-01 <= time < 2026-01-01
- gate: calibration q95 = `0.5927349103795366`
- direction/context: prior closed H4 DOWN, LONG reversal
- trigger: M5 BRK6、directional body >= 0.20、60分以内
- entry: next M5 open
- exit contract: TP1.75ATR / SL1.0ATR / max6h

Parity fixture:

- decision `2026-06-19 08:00:00`
- expected score `0.5949591748604749`
- expected entry `2026-06-19 08:30:00`

### Stage281

- Candidate: `M15_CONT_LONG_Q85_EMA20_E225_AFTER_BASE_LOSS_72H_SHADOW_NEAR_MISS`
- LightGBM 2026 deployment model
- fit: 2024-01-01 <= time < 2025-07-01
- calibration: 2025-07-01 <= time < 2026-01-01
- gate: calibration q85 = `0.5525199124029727`
- direction/context: prior closed H4 UP, LONG continuation
- trigger: M5 EMA20 reclaim + prior M5 high break、directional body >=0.15、45分以内
- policy cooldown: 120分
- entry: next M5 open
- causal synergy: latest resolved BASE pnl < 0 and exitから72時間以内
- exit contract: TP2.25ATR / SL1.25ATR / max8h

Parity fixture:

- decision `2026-06-17 10:00:00`
- expected score `0.6586538142862226`

### Stage286

- Candidate: `SHORT_EXHAUST_MODERATE_OVERHEAT_SUBDUED_US_EQUITY`
- existing lower gate: GOLD M15 ret8/ATR >= `2.162461836828524`
- upper overheat gate: <= `2.992581130893`
- GOLD M15 pos4 >= 0.75
- GOLD upper wick >= lower wick
- mean(US500 M15 ret4/ATR, US100 M15 ret4/ATR) <= `0.410970621210`
- trigger: M5 EMA20 bearish cross + prior M5 low break、directional body >=0.12、60分以内
- cooldown: 120分
- exit contract: TP2.25ATR / SL1.25ATR / max8h

## 安全側統合

候補priority:

1. Stage280 = 10
2. Stage281 = 20
3. Stage286 = 60

固定制御:

- unresolved candidateは同時1件まで
- Stage280/281: resolved combined DD <= 30
- shared candidate cooldown: 12時間
- Stage281: resolved BASE loss後72時間以内
- Stage286: resolved combined DD <= 10
- Stage286: latest resolved accepted candidate loss後24時間停止

DD・直近損失・BASE lossは、必ず`exit_dt <= current entry_dt`のresolved rowsだけで計算する。

## BASE portfolio state adapter

Stage284 safe integrationにはprotected BASE streamが必要である。Stage289は存在しないファイルを推測しない。

`--base-resolved-csv`で指定するCSV契約:

- `entry_dt`
- `exit_dt`
- `pnl`

ファイル未接続時:

- ML/rule candidate detectionは実行する。
- 全candidate admissionは`BASE_PORTFOLIO_STATE_NOT_CONNECTED`で拒否する。
- Stage281は併せて`BASE_RESOLVED_STATE_MISSING`。
- statusはPARTIAL。

candidate-only equityへfallbackしてはいけない。

## 初回起動と過去candidate誤登録防止

初回起動時は最新closed M5 timeをwatermarkとして保存する。過去lookback候補は監査CSVに表示するが、decision ledgerへ新規登録しない。

次回以降、watermarkより後のentryだけを処理する。

`--replay-existing`はテスト・監査専用で、通常BATでは使用しない。

## 出力

`MQL5/Files/FX_OUTPUTS/gold_v3/289c/`

- `paste_me.txt`
- `gold_v3_289_detected_live_candle_candidates.csv`
- `gold_v3_289_decision_ledger.csv`
- `gold_v3_289_shadow_trade_ledger.csv`
- `gold_v3_289_latest_decisions.csv`
- `gold_v3_289_runtime_state.json`
- `gold_v3_289_summary.json`
- `gold_v3_289_validation.csv`

## 実行

```text
scripts/gold_v3_runtime/bat/run_gold_v3_289_live_candle_ml_safe_shadow.bat
```

ユーザーが返すファイル:

```text
MQL5/Files/FX_OUTPUTS/gold_v3/289c/paste_me.txt
```

## モデルartifact integrity

- Stage280 model SHA256: `b900b81646b8b5228f687ce65a3491bc80f638c8aa95898f76a689b736b020d9`
- Stage280 contract SHA256: `0045660e29fa4ac095c5e59cd02cdef8f7dfea2b7446c5ddc191b610584936c5`
- Stage281 model SHA256: `3fcf56ae274f04c81e4d786c027efdbb96beb1ddeb8671ea7300123e15c98376`
- Stage281 contract SHA256: `2540ebcc3bb4b0395077e2fb5f39ce30f82a74c437fd89e910944cfca2c906b9`

## Safety flags

- audit_only: true
- live_ready: false
- mt5_execution_enabled: false
- discord_live_enabled: false
- ai_api_called: false
- final_signal_enabled: false
- partial_close_enabled: false
