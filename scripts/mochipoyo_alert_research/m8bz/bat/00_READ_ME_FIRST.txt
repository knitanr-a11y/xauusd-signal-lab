MOCHIPOYO Alert Research / M8BZ Pullback-State Feature Audit

このフォルダでユーザーが起動するのは番号付きBATだけです。Pythonを直接起動しないでください。

01_run_pullback_state_feature_audit.bat
- 1回だけ実行します。
- M8C / M7C / collector と同時稼働で構いません。
- 固定bpsをエントリー条件には使いません。
- シグナル後のM1確定足だけで押し→反転候補を認識し、次のM1始値を仮想エントリーにします。
- 押し地点で M1 RCI9/14/18、EMA20/30/40、MACD6/13/4、ATR14、ローソク足、ヒゲ、出来高、スプレッド、押し深さ、戻し幅、経過時間を記録します。
- 元シグナル時点のRCI/EMAコンテキストも併記します。
- [M8BZ PASS] が成功です。
- [M8BZ BLOCKED] が出た場合は連打せず、その表示をChatGPTへ送ってください。

02_open_latest_results.bat
- 最新結果フォルダを開きます。
- 提出物は 99_UPLOAD_PACKAGE.zip だけです。

出力:
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M8BZ\LATEST

注意:
- M8BZは同じM8B固定18件を使う仮説生成です。ここで見えた特徴量条件をそのまま採用しません。
- 18件へ機械学習をfitしません。
- 良さそうな特徴の組合せが見つかった場合、新しいforward sampleで別途検証します。
- 現在動いているM8Cのprospective startはresetしません。
- audit-only。Discord送信、MT5注文、live ready、final signal、実売買entry gateはOFFです。
