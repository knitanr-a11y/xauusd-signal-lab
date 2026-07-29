BTC ML V1 / FF04 bar-time semantics and causal rebuild foundation
=================================================================

このフォルダはユーザー操作用BAT専用です。Pythonを直接起動しません。

目的
----
CSVのtimeを足のclose時刻と誤解して未来参照する事故を防止します。
FF04では候補の成績探索を行いません。

必須時刻契約
------------
CSVのtimeはraw MT5 broker-serverの足OPEN時刻です。

M5:
  open time = time
  利用可能時刻 = time + 5分

M15:
  open time = time
  close／判定可能時刻 = time + 15分

H1:
  open time = time
  利用可能時刻 = time + 60分

H4:
  open time = time
  利用可能時刻 = time + 4時間

D1:
  open time = time
  利用可能時刻 = time + 24時間

新しい再構築では、H1などの上位足はsignal M15のOPEN時点までに確定した足だけを使います。
M15のclose値はM15 timeの時点では使用できず、time+15分で初めて使用できます。
エントリーはその時刻と完全一致するM5のopenだけです。
近い行、次に存在する行、nearest futureへのfallbackは禁止です。

実行順
------
1. GitHub Desktopでfeature/btc-fresh-forward-researchをFetch/Pullします。
2. 01_run_bar_time_semantics_audit.batを1回だけ起動します。
3. 完了後に選択される99_UPLOAD_PACKAGE.zipだけをChatGPTへ提出します。
4. 停止します。成績探索は自動実行しません。

前提
----
FF01:
  READY_ALL_FIVE_CANDIDATES

FF03:
  DIRECT_CAUSALITY_PASS_SELECTION_PROVENANCE_FAIL

出力
----
%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\04_bar_time_semantics_rebuild_foundation\LATEST\

00_READ_ME_FIRST.txt
01_time_semantics_summary.json
02_time_semantics_report.txt
03_timeframe_manifest.csv
04_causal_sentinel_tests.csv
05_rebuild_preregistration.json
06_current_engine_contract.json
99_UPLOAD_PACKAGE.zip

FF04で行わないこと
------------------
候補成績計算
108セル探索
条件選択
今回の6敗を使った除外条件作成
lot設計
live化
Discord
MT5注文
GOLD/MOCHIPOYO変更
