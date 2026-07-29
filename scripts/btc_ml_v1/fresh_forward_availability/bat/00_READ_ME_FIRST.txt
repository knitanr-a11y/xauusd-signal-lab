BTC ML V1 / FF01 fresh-forward availability audit
=================================================

このフォルダはユーザーが操作するBAT専用です。
Pythonを直接起動する必要はありません。

実行順
------
1. 01_run_availability_audit.bat を1回だけ起動してください。
2. 監査完了後、LATESTフォルダが自動で開きます。
3. あとから結果を開き直す場合だけ、02_open_latest_results.bat を起動してください。
4. ChatGPTへ提出するファイルは、LATEST内の 99_UPLOAD_PACKAGE.zip だけです。
5. ZIPを提出した時点で停止してください。FF02は未承認です。

同時実行禁止
------------
01_run_availability_audit.bat は複数同時に起動しないでください。
01が完了するまで02を起動しないでください。

成功・BLOCKED・FAILED
---------------------
監査処理そのものが完了すると、候補ごとにREADYまたはBLOCKEDが出力されます。
全時間足がそろわなくても、必要データがある候補まで一括BLOCKしません。

FAILEDや致命的BLOCKEDの場合も、作成できたLATESTフォルダを開きます。
コマンド画面は自動で閉じず、キー入力待ちになります。

重要な訂正
----------
2017年開始の古いH4は、過去成績を完全再現するために使った
BTCUSD_H4_WARMUP_PACKAGE.zip の履歴データです。
現在のfresh-forward availabilityのREADY条件には使用しません。
ユーザーが古いH4データを探したり復元したりする必要はありません。

出力先
------
%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\01_fresh_forward_availability\
  LATEST\
    00_READ_ME_FIRST.txt
    01_availability_summary.json
    02_availability_report.txt
    99_UPLOAD_PACKAGE.zip

  archive\
    <UTC実行日時>\

FF01で確認するもの
------------------
- M5 fresh tail
- M15 fresh tail
- H1 fresh tail
- D1 fresh tail
- H4 fresh tail
- MT5 broker-server timestamp
- main正本のbroker UTC offset変換
- cutoff後の行数
- 時刻昇順違反
- 重複時刻
- 候補別READY／BLOCKED

候補別の必要データ
------------------
- BTC4: H4 after cutoff + M5 after cutoff
- BTC5: M5 after cutoff
- BTC6: M15 after cutoff
- BTC7R: M5 + M15 + H1 after cutoff
- BTC9R: M5 + M15 + H1 + D1 after cutoff

安全契約
--------
- source CSVは読取専用です。
- source CSVの追記、上書き、copy、merge、rename、deleteを行いません。
- PC全体を再帰検索しません。
- naive時刻をUTCとして扱いません。
- candidate engine、fresh trade生成、fresh performance評価を実行しません。
- reproduce_btc_stacking_portfolio.pyをfresh CSVへ実行しません。
- collector、M7C、M8C、GOLD loopへ触れません。
- feature/mochipoyo-alert-researchをcheckout、merge、変更しません。
- M10W24Bおよびその他M10W系へ触れません。
- Discord、MT5 order、live-ready、final signalはOFFです。
