MOCHIPOYO Alert Research / M8C Forward Shadow

このフォルダでユーザーが起動するのは番号付きBATだけです。Pythonを直接起動しないでください。

01_initialize_forward_shadow.bat
- 1回だけ実行します。
- M8C専用prospective_start_utcを固定します。
- 過去M8B 18件はvalidationへ再利用しません。
- 既存manifestがある場合は保持し、勝手にresetしません。
- [M8C INIT PASS] が成功です。
- [M8C INIT BLOCKED] が出た場合は停止してください。

02_run_forward_shadow_forever.bat
- 01成功後に1つのウィンドウで常時実行します。
- collector / M7Cと同時稼働で構いません。
- 300秒ごとにfuture proxy PRIMARY候補を監査します。
- CONTROLは全proxy PRIMARY候補を受け入れます。
- CHALLENGERはproxy branchのBTCUSD PRIMARY_LONGだけを保留します。
- source anchorは別branchで、M8C gateでは抑制しません。
- source-match / extra確定は後日のattributionにだけ使い、gate入力には使いません。
- [M8C LOOP BLOCKED] が出たら、その画面を保存して停止してください。自動再初期化は禁止です。

03_open_latest_results.bat
- M8Cの最新結果フォルダを開くだけです。何度起動しても構いません。

最新結果:
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M8C\LATEST

レビュー時の通常提出物:
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M8C\LATEST\99_UPLOAD_PACKAGE.zip

M8Cはaudit-onlyです。Discord送信、MT5注文、live ready、final signal、実売買entry gateはOFFです。
