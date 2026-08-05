# 実行手順

## 1. 展開

ZIPを専用フォルダへ展開します。既存Stage55、既存Day Open Shadow、他の研究フォルダへ上書きしません。

## 2. パス設定

`launchers/local_paths.example.bat`を`local_paths.bat`へコピーし、M1・M15・H1・H4・D1 CSVの実際の場所を設定します。

## 3. 初回だけ

1. `00_INSTALL_REQUIREMENTS.bat`
2. `01_VERIFY.bat`
3. `02_INIT_ONCE.bat`

`02_INIT_ONCE.bat`はactivationを一度だけ作ります。再実行・削除・作り直しは禁止です。

## 4. 継続処理

ローソク足CSV更新後に`03_PROCESS.bat`を実行します。H4確定より短い間隔で実行しても、新しいH4がなければ台帳は増えません。

Discord通知を使う場合は、Windows環境変数`BTC_AI_V1_FULL95_Q20_DISCORD_WEBHOOK_URL`を設定します。通知は監査用で、注文は行いません。

## 5. 状態確認

`04_STATUS.bat`で現在件数、見送り数、レビュー条件を確認します。
