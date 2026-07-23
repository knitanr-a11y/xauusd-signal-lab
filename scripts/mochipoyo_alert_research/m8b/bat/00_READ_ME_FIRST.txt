MOCHIPOYO Alert Research / M8B

目的:
もちぽよ完全複製ではなく、固定済みextraが実トレードとして優位性を持つかを評価します。
勝率・PF・DD・連敗・頻度を重視します。

01_run_outcome_audit.bat
- 1回だけ実行してください。
- M8Aをローカルで再実行する必要はありません。
- M7C collector / shadowが動いていても構いません。M8BはGitHubに固定した35件freeze由来のtrade skeletonだけを母集団にします。
- MT5のM1 CSVとSYMBOL_POINTを自動取得します。
- [M8B PASS] が出れば成功です。
- [M8B BLOCKED] が出たら停止してください。M7Cを再初期化しないでください。
- MT5 symbol ambiguityと表示された場合だけ、表示されたsymbol名をChatGPTへ送ってください。

02_open_latest_results.bat
- 結果確認用です。01成功後に起動してください。

出力:
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M8B\LATEST\

通常提出:
99_UPLOAD_PACKAGE.zip 1個だけです。

重要:
- 36 extra signal = 36 trades ではありません。
- WR/PF対象はextra PRIMARY entryから始まった18 tradesです。
- extra EXIT 18件は独立tradeとして二重計上しません。
- primary costはhistorical M1 spread x1.0、感度確認はx1.5/x2.0です。
- commission/swapはM8B V1では未モデルです。
- 同じ18件を見てgateを調整し、その18件を改善後の検証成績として主張することは禁止です。
- Discord / MT5 order / live ready / final signal / entry gateはOFFのままです。
