MOCHIPOYO Alert Research / M9B Genuine Primary Expanded Context Audit

このフォルダでユーザーが起動するのは番号付きBATだけです。Pythonを直接起動しないでください。

01_run_genuine_primary_expanded_context_audit.bat
- 1回だけ実行します。
- M8C / M7C / collector と同時稼働で構いません。
- M9Aで固定した本物もちぽよPRIMARY 43件だけを使います。
- proxy replayは混ぜません。
- 本物PRIMARYから対応する本物source EXITまでを1トレードとして評価します。
- M5/H1/H4はMT5 M1から再構成し、各判定時点までに完全終了したバーだけを使います。
- 最初の因果的な押し反転候補も評価します。
- [M9B PASS] が成功です。
- [M9B BLOCKED] が出た場合は連打せず、その表示をChatGPTへ送ってください。

02_open_latest_results.bat
- 最新結果フォルダを開きます。
- 提出物は 99_UPLOAD_PACKAGE.zip だけです。

出力:
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9B\LATEST

注意:
- M9Bの43件は本物sourceですが、同じ43件で特徴を見つけて同じ43件をvalidationとは呼びません。
- M5 RCI9>=80やH1/H4方向条件をこの結果だけでlive採用しません。
- M9B後にTier Bの凍結proxy historical replayへ進みます。
- 現在動いているM8Cのprospective startはresetしません。
- audit-only。Discord送信、MT5注文、live ready、final signal、実売買entry gateはOFFです。
