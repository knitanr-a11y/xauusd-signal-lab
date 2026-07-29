BTC ML V1 / FF02 frozen-five fresh-forward performance
===========================================================

このフォルダはユーザー操作用BAT専用です。Pythonを直接起動しません。

実行順
------
1. GitHub Desktopで feature/btc-fresh-forward-research をFetch/Pullします。
2. 01_run_fresh_forward_evaluation.bat を1回だけ起動します。
3. 完了後、LATESTの99_UPLOAD_PACKAGE.zipが選択されます。
4. そのZIPだけをChatGPTへ提出し、停止します。

前提
----
FF01のLATEST/01_availability_summary.jsonが存在し、
overall_status=READY_ALL_FIVE_CANDIDATESである必要があります。

対象
----
entry_time_utc > 2026-07-02 02:15:00
BTC4 / BTC5 / BTC6 / BTC7R / BTC9R の凍結済み5候補だけです。

時刻
----
候補エンジンはraw MT5 broker-server時刻のまま実行します。
UTC変換はcutoff判定・exit表示・月別集計だけに使用します。
候補エンジン入力の時刻を書き換えません。

snapshot
--------
source CSVを変更せず、copy前後と内部snapshotのSHA256が一致した場合だけ評価します。
snapshotは評価後に削除し、提出ZIPへ含めません。

出力
----
%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\02_fresh_forward_performance\LATEST\
  00_READ_ME_FIRST.txt
  01_fresh_forward_summary.json
  02_fresh_forward_report.txt
  03_fresh_forward_trade_ledger.csv
  04_candidate_metrics.csv
  05_monthly_metrics.csv
  06_direction_metrics.csv
  07_input_manifest.csv
  08_candidate_engine_manifest.csv
  99_UPLOAD_PACKAGE.zip

固定ルール
----------
条件・threshold・TP・SL・exit順・spread・pip・overlapを変更しません。
simple候補は同一barでSL先、BTC4はTP1後の同一M5でBE先です。
exact-time overlapは重複排除せず、global one-position capは使いません。
OPEN_AT_DATA_ENDは勝敗と実現指標から除外し、件数を別記します。
lot設計・金額DD・再最適化・新候補探索は行いません。

GOLD/MOCHIPOYO
--------------
collector、M7C、M8C、GOLD、M10Wを停止・変更・checkout・mergeしません。
Discord、MT5注文、live-ready、final signalはOFFです。
