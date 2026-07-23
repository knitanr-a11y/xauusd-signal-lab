MOCHIPOYO Alert Research / M8A

ユーザーが起動するのはこの bat フォルダ内の番号付きBATだけです。
Pythonファイルを直接起動しないでください。

01_prepare_inputs.bat
- 1回だけ実行
- M7C formal gate到達後の7ファイルを固定コピーします
- M7C collector / shadowと同時稼働していても構いません
- [M8A PREP PASS] が出れば成功
- [M8A PREP BLOCKED] が出たら停止し、M7Cを再初期化しないでください

02_run_coverage_audit.bat
- 01成功後に1回だけ実行
- future outcomeを使わずcoverage gapを監査します
- [M8A PASS] が出れば成功
- [M8A BLOCKED] が出たら停止してください

03_open_latest_results.bat
- 結果確認用。何度起動しても構いません
- M8AのLATESTフォルダを開きます

通常提出物:
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M8A\LATEST\99_UPLOAD_PACKAGE.zip

M8AではDiscord送信、MT5注文、live ready、final signal、entry gateを有効化しません。

補足: pending source-arrival graceはextra確定扱いにせず、M8B outcome評価から除外します。
