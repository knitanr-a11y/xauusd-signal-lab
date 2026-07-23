MOCHIPOYO Alert Research / M8BY Pullback Entry Opportunity Audit

このフォルダでユーザーが起動するのは番号付きBATだけです。Pythonを直接起動しないでください。

01_run_pullback_entry_opportunity_audit.bat
- 1回だけ実行します。
- M8C / M7C / collector と同時稼働で構いません。
- M8Bの固定18トレードとMT5 M1を使い、実際のBID価格の押し・戻し待ちエントリーを探索します。
- スプレッドを逆行として数えません。
- シグナルM1内で条件に触れても、その同じM1内ではエントリーせず、次の観測M1始値でのみ仮想エントリーします。
- [M8BY PASS] が成功です。
- [M8BY BLOCKED] が出た場合は連打せず、その表示をChatGPTへ送ってください。

02_open_latest_results.bat
- 最新結果フォルダを開きます。
- 提出物は 99_UPLOAD_PACKAGE.zip だけです。

出力:
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M8BY\LATEST

注意:
- M8BYは過去18件を使った仮説生成です。ここで一番良かった条件をそのまま採用しません。
- 新しいpullback entryルールを採用する場合は、別の新規forward startで検証します。
- 現在動いているM8Cのprospective startはresetしません。
- audit-only。Discord送信、MT5注文、live ready、final signal、実売買entry gateはOFFです。
