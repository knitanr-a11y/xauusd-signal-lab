# 実行手順

## 1. 配置

このFull95 Shadowは、既存Stage55とは別のフォルダ・別ウィンドウ・別runtime stateで動作します。Stage55側へ上書きしません。

## 2. パス設定

`launchers/local_paths.example.bat`を`launchers/local_paths.bat`へコピーし、M1・M15・H1・H4・D1 CSVの実際の場所を設定します。

## 3. 初回activation

CSV互換版では次を使います。

1. `00_INSTALL_REQUIREMENTS.bat`
2. `01_VERIFY.bat`
3. `02_INIT_ONCE_CSV_COMPAT.bat`

`02_INIT_ONCE_CSV_COMPAT.bat`はactivationを一度だけ作ります。activation成功後は再実行・削除・作り直しをしません。

現在の正式activation watermarkは`2026-08-05 20:00:00` MT5 broker timeです。

## 4. 常駐観測ループ

activation後は`03_PROCESS_CSV_COMPAT.bat`を起動したままにします。

ウィンドウタイトル：

`BTC AI V1 Full95 Q20 Shadow - ACTIVE OBSERVATION LOOP`

動作：

- 起動直後に凍結資産を検証する;
- 60秒ごとにCSVを読み、未処理の確定H4がある場合だけ処理する;
- 新しいH4がなければ台帳を増やさず次周期へ進む;
- 正常時は自動的にループを継続する;
- 処理エラー時は自動再試行せず、安全のためウィンドウ内で停止する;
- ウィンドウを閉じるとFull95 Shadowループだけが停止する;
- Stage55は別ウィンドウで独立して動作する。

## 5. 状態確認

`04_STATUS.bat`で現在件数、見送り数、レビュー条件を確認します。

状態確認ウィンドウのタイトルは、

`BTC AI V1 Full95 Q20 Shadow - STATUS`

です。

## 6. Discord

Discord通知を使う場合は、Windows環境変数`BTC_AI_V1_FULL95_Q20_DISCORD_WEBHOOK_URL`を設定します。通知は監査用で、注文は行いません。
