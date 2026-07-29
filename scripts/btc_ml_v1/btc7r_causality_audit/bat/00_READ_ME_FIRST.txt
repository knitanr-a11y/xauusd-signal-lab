BTC ML V1 / FF03 BTC7R causality and selection-leak audit
============================================================

目的
----
BTC7Rについて、次の3点を分離して監査します。

1. エントリー時点より後のローソク足を付け足すことで、既に存在したシグナル・方向・価格・risk・TPが変わらないか。
2. 現在のローカルデータで、旧正式2026評価22件・11勝11敗の再現指標が一致するか。
3. 旧VALIDATIONを本当に未見と扱える、検証期間前の不変な事前登録と完全な探索履歴が存在するか。

実行前提
--------
- FF01が READY_ALL_FIVE_CANDIDATES で完了済み。
- FF02が完了済み。
- FF02のBTC7R結果が6件・0勝・6敗であること。
- branchは feature/btc-fresh-forward-research。

実行順
------
1. GitHub DesktopでFetch origin、表示された場合はPull originを押します。
2. 01_run_btc7r_causality_audit.bat を1回だけ起動します。
3. 監査には数分かかることがあります。複数同時に起動しません。
4. 完了後に選択される 99_UPLOAD_PACKAGE.zip だけをChatGPTへ提出します。
5. 提出後は停止します。

監査方法
--------
現在のローカルM5/M15/H1で生成できるBTC7Rの全エントリーについて、各エントリー時点でCSVを切断し、特徴量と候補を最初から再計算します。

prefix実行と全期間実行を、次について照合します。
- signal time
- entry time
- direction
- entry bid
- stop / target
- risk / reward / RR
- H1 trend separation
- M15 impulse ATR multiple
- close location
- trend age
- その時点までに存在する候補集合全体

旧2026評価の再現
----------------
旧正本はnaive CSV時刻をUTCと記載していましたが、現在はMT5 broker-server wall-clockと判明しています。
旧22件との再現照合だけは、過去実装と同じraw時刻境界 2026-07-02 02:15:00 で行います。
新しいforward境界へ黙って読み替えません。

選定履歴の扱い
--------------
GitHubで確認できる最初のBTC7R候補契約は2026-07-02のcommitです。
一方、主張されているVALIDATIONは2026-01-01より前です。
検証期間前の不変なfreeze証拠と、比較した全条件・閾値の完全なtrial ledgerが見つからないため、旧VALIDATIONは未見成績として自動合格させません。

重要
----
prefix causalityがPASSしても、旧73.77%が未見検証として証明されたことにはなりません。
旧成績は監査完了まで信頼停止です。
FF03では6連敗を使った条件調整、救済、候補削除、新候補作成を行いません。

出力
----
%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\03_btc7r_causality_selection_audit\LATEST\
  00_READ_ME_FIRST.txt
  01_audit_summary.json
  02_audit_report.txt
  03_prefix_invariance.csv
  04_legacy_period_parity.csv
  05_selection_provenance.json
  06_input_manifest.csv
  99_UPLOAD_PACKAGE.zip

安全
----
- source CSVは変更しません。
- 安定snapshotは監査後に削除し、ZIPへ含めません。
- BTC7R条件を変えません。
- GOLD/MOCHIPOYO、collector、M7C、M8C、M10Wへ触れません。
- Discord、MT5注文、live-ready、final signalはOFFです。
