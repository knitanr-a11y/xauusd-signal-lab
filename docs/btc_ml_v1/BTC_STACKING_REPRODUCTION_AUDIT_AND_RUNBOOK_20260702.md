# BTC積み重ね候補：再現性監査と実行手順

作成日: 2026-07-02

## 結論

5候補の条件コード、個別テスト、固定configはmainに存在する。

ただし監査前の引き継ぎには次が不足していた。

1. 生CSVはGitHubへコミットされておらず、必要パッケージ名とSHA256が引き継ぎに明記されていなかった。
2. 5候補を一括で再実行するコマンドがなかった。
3. 2026年entry-onlyを決着させ、全体185件へ集計する正本スクリプトがGitHubになかった。
4. 入力CSVの行数・時刻範囲・SHA256と、候補エントリー指紋を照合するfail-closed検証がなかった。
5. CIは条件単体テストのみで、外部の大容量CSVを使うgolden-data再計算は実行していなかった。

これらを補うため、以下を追加した。

- `scripts/btc_ml_v1/research/reproduce_btc_stacking_portfolio.py`
- `configs/btc_ml_v1/btc_stacking_reproduction_reference.json`
- `RUN_BTC_STACKING_REPRODUCTION.bat`
- 本runbook

## GitHubだけで再現できる範囲

GitHubだけで可能:

- 候補条件の確認
- Python構文確認
- 単体契約テスト
- 候補ID・パラメーター・時刻契約の確認

GitHubだけでは不可能:

- 142件、43件、185件の取引再計算
- 2026年のTP/SL決着
- 正確な候補エントリー時刻の再生成

理由は、ブローカー履歴CSVが大容量でGitHubにコミットされていないため。

## 新チャットへ渡す必須入力

### 1. 通常履歴パッケージ

```text
BTCUSD_HISTORY_CHAT_PACKAGE.zip
SHA256: 9b0b74e9937eca05e895047f5737c6794332af7ec25f2a30b64d9440c9e0dd22
```

再現に必要なCSV:

```text
btcusdsharp_m5.csv
btcusdsharp_m15.csv
btcusdsharp_h1.csv
btcusdsharp_d1.csv
```

M1と通常H4もパッケージに含まれるが、今回の5候補一括再現では上記4本を直接使用する。

### 2. H4長期ウォームアップ

```text
BTCUSD_H4_WARMUP_PACKAGE.zip
SHA256: d150eaee0c126e2eb4c4aecb667ff0ad181a9a0a6e060cc5c1613b60e0a8019a
```

必要CSV:

```text
btcusdsharp_h4.csv
```

このH4は2017年開始。BTC4のEMA200位置をMT5と合わせるため必須。通常履歴パッケージ内の2024年開始H4で代用しない。

## 入力CSV正本

| CSV | 行数 | 最初 | 最後 | SHA256 |
|---|---:|---|---|---|
| M5 | 209,588 | 2024-07-02 02:25 | 2026-07-02 02:15 | `2871723be0df6b27c9ba49c378280671c26f7e8ff2504d873058bc74a4a8a604` |
| M15 | 69,969 | 2024-07-02 02:30 | 2026-07-02 02:00 | `201f9c77565e458bf3206e1e7f3bf725c361ef388b34217175de3a3eebe7c419` |
| H1 | 17,519 | 2024-07-02 03:00 | 2026-07-02 01:00 | `2ca5178255943496c897a71ccc8720dad19e9b71dd4518db0c3b4e400ca99a43` |
| D1 | 729 | 2024-07-03 00:00 | 2026-07-01 00:00 | `fc992f14d2680f6ce2f16466472d38091b8153db5abbe01fa887164af990b0ed` |
| H4 warmup | 17,270 | 2017-01-02 04:00 | 2026-07-02 00:00 | `61c9ce1a5bbda80614d4d25597ffe6ec1d7c4e450baacea307fa2161bd945caa` |

一括スクリプトは既定で、行数・最初時刻・最後時刻・SHA256が1つでも違えば停止する。

## 推奨環境

```text
Python 3.12
numpy 2.1.3
pandas 2.2.3
pytest 8.4.1
```

インストール例:

```bat
python -m pip install numpy==2.1.3 pandas==2.2.3 pytest==8.4.1
```

MT5 Pythonパッケージは、既に取得済みCSVから再計算するだけなら不要。

## 展開例

```text
C:\BTC_REPRO\history\btcusdsharp_m5.csv
C:\BTC_REPRO\history\btcusdsharp_m15.csv
C:\BTC_REPRO\history\btcusdsharp_h1.csv
C:\BTC_REPRO\history\btcusdsharp_d1.csv
C:\BTC_REPRO\h4_warmup\btcusdsharp_h4.csv
```

## 一括再現コマンド

リポジトリのルートから:

```bat
RUN_BTC_STACKING_REPRODUCTION.bat ^
  "C:\BTC_REPRO\history" ^
  "C:\BTC_REPRO\h4_warmup\btcusdsharp_h4.csv" ^
  "outputs\btc_ml_v1\btc_stacking_reproduction_20260702"
```

Pythonを直接実行する場合:

```bat
python scripts\btc_ml_v1\research\reproduce_btc_stacking_portfolio.py ^
  --history-dir "C:\BTC_REPRO\history" ^
  --h4-warmup-csv "C:\BTC_REPRO\h4_warmup\btcusdsharp_h4.csv" ^
  --output-dir "outputs\btc_ml_v1\btc_stacking_reproduction_20260702"
```

## 一括スクリプトが実行するもの

### BTC4

```text
run_btc3_video_ema_user_contract.py
EMA Applied to = close
spread = 30 USD
pivot bars = 3
lookback = 500 H4 bars
risk cap = 400 pips
H4 = 長期warmup CSV
entry/exit判定 = M5
```

### BTC5

```text
btc5_video_5m_ema200_nwave_candidate.py
input = M5
```

### BTC6

```text
btc6_video_m15_ema200_nwave_candidate.py
input = M15
entry/exit判定もM15
```

### BTC7R

```text
btc7r_m15_impulse_high_win_candidate.py
input = M5 / M15 / H1
```

### BTC9R

```text
btc9r_m15_prevday_breakout_high_win_candidate.py
input = M5 / M15 / H1 / D1
```

各候補の2026年entry-onlyを、条件を変更せずデータ終端まで決着させる。その後、完全一致時刻を重複排除せず、別候補取引として積み上げる。

## 成功条件

最終出力:

```text
btc_stacking_reproduction_report.json
```

次がすべて成立した場合のみ:

```text
reproduction_pass = true
```

検証内容:

- 入力CSVの行数・期間・SHA256一致
- BTC4～BTC9Rの候補エントリー指紋一致
- 2026年未決着0件
- 2026年以前の全体指標一致
- 2026年の全体指標一致
- 全評価期間の全体指標一致

期待値:

| 区分 | 件数 | 勝ち | 負け | 勝率 | PF | 合計pips | 最大DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026年以前 | 142 | 104 | 38 | 73.24% | 2.787 | +5,768.32 | 345.18 |
| 2026年 | 43 | 26 | 17 | 60.47% | 2.023 | +1,199.42 | 247.84 |
| 全期間 | 185 | 130 | 55 | 70.27% | 2.583 | +6,967.74 | 345.18 |

## 個別再現コマンド

### BTC4

```bat
python scripts\btc_ml_v1\research\run_btc3_video_ema_user_contract.py ^
  --ema-applied-price close ^
  --data-dir "BTC4_INPUT_DIR" ^
  --output-dir "OUTPUT_DIR\btc4" ^
  --spread-usd 30 ^
  --pivot-bars 3 ^
  --lookback-bars 500
```

`BTC4_INPUT_DIR`には、長期warmup H4を`btcusdsharp_h4.csv`、通常M5を`btcusdsharp_m5.csv`として置く。その後、予定リスク400pips以下だけを残す。

### BTC5

```bat
python scripts\btc_ml_v1\research\btc5_video_5m_ema200_nwave_candidate.py ^
  --m5 "HISTORY_DIR\btcusdsharp_m5.csv" ^
  --out "OUTPUT_DIR\btc5"
```

### BTC6

```bat
python scripts\btc_ml_v1\research\btc6_video_m15_ema200_nwave_candidate.py ^
  --m15 "HISTORY_DIR\btcusdsharp_m15.csv" ^
  --out "OUTPUT_DIR\btc6"
```

### BTC7R

```bat
python scripts\btc_ml_v1\research\btc7r_m15_impulse_high_win_candidate.py ^
  --m5 "HISTORY_DIR\btcusdsharp_m5.csv" ^
  --m15 "HISTORY_DIR\btcusdsharp_m15.csv" ^
  --h1 "HISTORY_DIR\btcusdsharp_h1.csv" ^
  --out "OUTPUT_DIR\btc7r"
```

### BTC9R

```bat
python scripts\btc_ml_v1\research\btc9r_m15_prevday_breakout_high_win_candidate.py ^
  --m5 "HISTORY_DIR\btcusdsharp_m5.csv" ^
  --m15 "HISTORY_DIR\btcusdsharp_m15.csv" ^
  --h1 "HISTORY_DIR\btcusdsharp_h1.csv" ^
  --d1 "HISTORY_DIR\btcusdsharp_d1.csv" ^
  --out "OUTPUT_DIR\btc9r"
```

個別候補スクリプトは2026年以降をentry-onlyとして出す。一括スクリプトがそのentry-onlyを決着させ、ポートフォリオへ統合する。

## CIについて

GitHub Actionsは以下をコンパイル・単体テストする。

- BTC3/BTC4契約
- BTC5
- BTC6
- BTC7/BTC7R
- BTC9/BTC9R
- 再現スクリプト

ただし大容量CSVはGitHubへ置かないため、GitHub Actions上で185件のgolden-data再計算はしない。新チャットまたはユーザーPCで上記2パッケージを展開し、一括再現を実行して`reproduction_pass=true`を確認する必要がある。

## 再現不能になる条件

- 通常履歴H4をBTC4の長期warmup H4として使う
- EMA Applied toをClose以外へ変更する
- スプレッド30ドルを変更する
- BTC pip契約を変更する
- CSVの行追加・削除・並び替え・丸めを行う
- BTC6をM5で決済判定する
- 同一足のSL優先を変更する
- BTC4のTP1後の建値優先を変更する
- 2026年結果を使って既存条件を再最適化する
- 完全一致時刻を勝手に重複排除する
- グローバル1ポジション制限を追加する

## 現在の安全状態

- 自動注文 OFF
- Discord OFF
- `live_ready=false`
- `final_signal=false`

再現成功はライブ稼働許可ではない。
