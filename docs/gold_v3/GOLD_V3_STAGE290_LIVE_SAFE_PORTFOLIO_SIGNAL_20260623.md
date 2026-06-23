# GOLD V3 Stage290 安全側ポートフォリオ live final signal

## 位置づけ

SHADOWではない。Files直下の最新closed candleから、BASE・Stage280・Stage281・Stage286厳格SHORTを生成し、安全側ポートフォリオ条件を通過した候補を`gold_v3_290_final_signal.csv`へ正式なlive signalとして出力する。

MT5自動発注・Discord通知・partial closeは別機能であり、Stage290ではOFFのままにする。実運用とは、final signalをlive時系列で確定し、実際に観測されたfill/closeを状態へ返す運用を指す。

## 読み込むclosed candle

MQL5/Files直下:

- goldsharp_m1.csv
- goldsharp_m5.csv
- goldsharp_m15.csv
- goldsharp_h1.csv
- goldsharp_h4.csv
- goldsharp_d1.csv
- us500cashsharp_m15.csv
- us100cashsharp_m15.csv

CSV最新行はexporter契約上closedとして扱う。未確定足を推測して追加しない。

## live経路

1. Stage69でBASE条件を最新closed M15から検出
2. Stage289の凍結済みLightGBM bundleでStage280/281を推論
3. Stage286厳格SHORTをGOLD・S&P500・NASDAQ100のclosed M15から判定
4. M5トリガーはトリガー足がclosedになった時点で確定し、そのclose時刻をplanned entryとする
5. priority BASE=0、Stage280=10、Stage281=20、Stage286=60で同時刻を処理
6. resolved-only安全ゲートを適用
7. 通過候補をPENDING_FILLのfinal signalとして記録
8. FILLED/CANCELLED/CLOSEDの観測済み更新だけで状態を変更

未来のM5足を待ってentry価格を取る処理、将来M1を走査するshadow exit simulationは本番経路で使用しない。

## BASE health

Stage67 event ledgerとStage53 closed ledgerをopportunity_idで結合し、candidate_key・実際のclose_time・resultを持つ履歴を作る。

各BASE候補のentry時点で`exit_dt <= current entry_dt`だけを使用し、次を再計算する。

- rolling window 30
- minimum history 20
- PF >= 1.10
- loss streak < 3

新しいlive決済もactual CLOSED update後に同じ履歴へ入る。静的なStage67 latest stateだけに固定しない。

## 安全側ポートフォリオ

- pending/openは全体で1件まで
- Stage280/281: realized combined DD <= 30
- 追加候補共有cooldown 12時間
- Stage281: 最新のresolved BASE loss後72時間以内
- Stage286: realized combined DD <= 10
- Stage286: 最新のresolved accepted candidate loss後24時間以上
- BASE: planned holding区間がMT5 server 00:00-01:59へ重なる場合は不採用

DD・損失時刻・BASE lossは必ず決済済み結果だけで更新する。

## 本番昇格ゲート

次の全項目がPASSしない限りfinal signalは出さない。

- FilesのM1/M5/M15および外部指数がfresh
- M1とM5のclosed時刻が整合
- Stage289 model bundleのhash・feature contractがPASS
- BASE resolved health履歴が生成可能
- Stage69がFiles最新M15と同じ時刻でREADY
- BASE・Stage280・Stage281・厳格SHORTから安全側を再実行し、2024/2025/2026が242/229/102件の成績へ一致
- PLUS_STRICT_SAFE台帳のreference metrics一致
- ユーザー許可token一致

最初の起動時は最新closed時刻をwatermarkとして保存し、過去候補を遡ってfinal signalにしない。

## 過去parity入力

環境変数:

- GOLD_V3_SAFE_PORTFOLIO_LEDGER
- GOLD_V3_PARITY_BASE_TRADES
- GOLD_V3_PARITY_STAGE280_TRADES
- GOLD_V3_PARITY_STAGE281_TRADES
- GOLD_V3_PARITY_STRICT_TRADES

想定ファイル:

- gold_v3_stage286_short_selected_portfolio_trades.csv
- gold_v3_execution_rollover_shadow_trades.csv
- gold_v3_stage280_cal_rev_q95_brk6_e175_trades.csv
- gold_v3_stage281_medium_frequency_near_miss_trades.csv
- gold_v3_stage286_short_strict_trades.csv

## 実約定更新

`FX_OUTPUTS/gold_v3/290_live_safe_portfolio/gold_v3_290_execution_updates.csv`

列:

`candidate_id,event_type,event_dt,price,pnl,reason`

- FILLED: 実fill時刻と価格
- CANCELLED: 未約定取消
- CLOSED: 実決済時刻・価格・確定損益

CLOSED結果は`event_dt <= 次のcandidate entry_dt`になって初めてDD・health・lockoutへ入る。

## 出力

- gold_v3_290_final_signal.csv
- gold_v3_290_decision_ledger.csv
- gold_v3_290_live_signal_ledger.csv
- gold_v3_290_execution_updates.csv
- gold_v3_290_readiness_report.json
- gold_v3_290_summary.json
- historical_parity/gold_v3_290_historical_parity.json

## 実行

`scripts/gold_v3_runtime/bat/run_gold_v3_290_live_safe_portfolio_signal.bat`

現時点で自動発注とDiscordは実装対象外。final signalのローカル確認とactual fill/close入力が本番運用範囲。
