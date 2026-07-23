MOCHIPOYO Alert Research / M8BX Excursion Path Audit

このフォルダでユーザーが起動するのは番号付きBATだけです。Pythonを直接起動しないでください。

01_run_excursion_path_audit.bat
- 1回だけ実行します。
- M8Bで固定済みの18 extra-entry tradeだけを対象にします。
- M1経路からMAE（最大逆行）、MFE（最大順行）、極値までの時間、含み益の吐き出し、underwater割合を計算します。
- GOLD/XAUUSDは勝ちトレードと負けトレードを分けて逆行量を比較します。
- M8C forward shadowと同時稼働して構いません。
- [M8BX PASS] が成功です。
- [M8BX BLOCKED] が出た場合は停止して画面を送ってください。

02_open_latest_results.bat
- 結果確認用です。何度起動しても構いません。

最新結果:
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M8BX\LATEST

通常提出物:
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M8BX\LATEST\99_UPLOAD_PACKAGE.zip

重要:
- この18件は仮説生成用であり、同じ18件から損切り閾値やentry filterを決めて同じ18件で採用判定してはいけません。
- 実際の損失削減ルールはM8Cまたはその後の新規forward sampleで検証します。
- M8BXはaudit-onlyです。Discord送信、MT5注文、live ready、final signal、実売買entry gateはOFFです。
