MOCHIPOYO Alert Research / M9A Sample Expansion Availability Audit

01_run_sample_expansion_availability_audit.bat
- 1回だけ実行します。
- M8C / M7C / collector と同時稼働で構いません。
- SQLiteに実際に保存済みの本物Webhookイベントを読み、全期間のPRIMARY / REENTRY / EXIT件数を状態機械から再集計します。
- 既存episode_eventsがあるイベントは役割の一致も確認します。既存役割と矛盾すればBLOCKEDです。
- MT5のXAU/BTC M1/M15履歴期間と、後で凍結proxyを過去リプレイできる容量を監査します。
- 本物アラートとproxy replayは混ぜません。
- [M9A PASS] が成功です。
- [M9A BLOCKED] の場合は連打せず、表示をChatGPTへ送ってください。

02_open_latest_results.bat
- 最新結果フォルダを開きます。
- 提出物は 99_UPLOAD_PACKAGE.zip だけです。

出力:
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9A\LATEST

重要:
- M9Aは件数・期間・再現可能範囲の監査です。まだ過去proxy replayを実行しません。
- 次段階では、まず本物PRIMARYを拡張したTier AでM5/H1/H4仮説を再検証します。
- その後、凍結proxyの過去リプレイをTier B = PROXY_REPLAY_NOT_SOURCE_TRUTHとして別集計します。
- 現在動いているM8Cのprospective startをresetしません。
- audit-only。Discord送信、MT5注文、live ready、final signal、実売買entry gateはOFFです。
