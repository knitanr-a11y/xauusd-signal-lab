MOCHIPOYO Alert Research / M9C Frozen Proxy Historical Replay

このフォルダでユーザーが起動するのは番号付きBATだけです。Pythonを直接起動しないでください。

01_run_frozen_proxy_historical_replay.bat
- 1回だけ実行します。
- M8C / M7C / collector と同時稼働で構いません。停止・reset不要です。
- 既に凍結済みのM7C formulaを、本物source収集開始前の過去M15へそのままリプレイします。
- formula / threshold / M7C state contractは変更しません。
- Tier Bは PROXY_REPLAY_NOT_SOURCE_TRUTH です。本物のもちぽよアラートとは呼びません。
- 過去M15全体では候補密度・状態遷移を取得します。
- exact M1 entry/exitが存在するproxy tradeだけ、historical spread込みの仮想成績・MFE/MAE・M5/H1/H4・最初の因果的押し反転を評価します。
- nearest M1 fallbackは使用しません。
- [M9C PASS] が成功です。
- [M9C BLOCKED] が出た場合は同じBATを連打せず、画面全文をChatGPTへ送ってください。

02_open_latest_results.bat
- 最新結果フォルダを開きます。
- 提出物は 99_UPLOAD_PACKAGE.zip だけです。

出力:
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M9C\LATEST

重要:
- Tier Aの本物source 43件とTier B proxy replayをsource再現精度の計算で混ぜません。
- replay結果を見てM7C formulaやthresholdを救済変更しません。
- M9Cは仮説生成・母数拡張です。ここで見つかったfeature thresholdをそのままlive採用しません。
- 現在動いているM8C prospective start、M7C runtime manifest/prospective startはresetしません。
- audit-only。Discord送信、MT5注文、live ready、final signal、実売買entry gateはOFFです。
