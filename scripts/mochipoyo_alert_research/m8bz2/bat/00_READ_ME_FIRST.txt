MOCHIPOYO Alert Research / M8BZ2 Multi-Timeframe RCI Context Audit

01_run_multitimeframe_rci_context_audit.bat
- 1回だけ実行します。
- M8C / M7C / collector と同時稼働で構いません。
- M8Bの固定18トレードとM8BZ最初の因果的反転候補を使います。
- 既存MT5 M1からMT5サーバー時刻基準でM5/H1/H4を再構成します。
- M5/H1/H4は、その判定境界までに完全に終了したバーだけを使います。
- M15アラート発生時のM5 RCI9過熱と、その後の初期押しの関係を調べます。
- 押し反転候補時のH1/H4 RCI9方向性と、その後の順行の関係を調べます。
- ユーザー仮説は検証対象であり、正しい前提にはしません。
- [M8BZ2 PASS] が成功です。
- [M8BZ2 BLOCKED] が出た場合は連打せず、その表示をChatGPTへ送ってください。

02_open_latest_results.bat
- 最新結果フォルダを開きます。
- 提出物は 99_UPLOAD_PACKAGE.zip だけです。

出力:
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M8BZ2\LATEST

注意:
- M8BZ2は過去サンプルを使う仮説生成です。
- M5 RCI9>=80、H1/H4 RCI9上向き等をこの結果だけで採用しません。
- 有望な特徴があれば別の新規forward sampleで検証します。
- 現在動いているM8Cのprospective startはresetしません。
- audit-only。Discord送信、MT5注文、live ready、final signal、実売買entry gateはOFFです。
