# XM KIWAMI local raw data

このフォルダは、XM KIWAMI極口座からMT5で出力したローソク足CSVをローカルに置くための場所です。

CSV本体はGitHubへコミットしません。
`.gitignore` で `data/raw/**/*.csv` を除外しています。

## 置くファイル

```text
data/raw/xm_kiwami/goldsharp_m15.csv
data/raw/xm_kiwami/goldsharp_h1.csv
data/raw/xm_kiwami/btcusdsharp_m15.csv
data/raw/xm_kiwami/btcusdsharp_h1.csv
```

## 対応するMT5シンボル

| CSV | MT5シンボル | 時間足 |
|---|---|---|
| `goldsharp_m15.csv` | `GOLD#` | M15 |
| `goldsharp_h1.csv` | `GOLD#` | H1 |
| `btcusdsharp_m15.csv` | `BTCUSD#` | M15 |
| `btcusdsharp_h1.csv` | `BTCUSD#` | H1 |

## 注意

- XM KIWAMIでは `#` 付きのシンボル名を使う。
- `#` を消さない。
- VantageやXMスタンダードのCSVと混ぜない。
- 古い `data/raw/gold_m15.csv` などとは別管理にする。
- バックテスト結果を見るときは、どのブローカー・どの口座種別のCSVを読んだか必ず確認する。

## CSV出力元

MT5用EA:

```text
mt5/export_ohlc_multi.mq5
```

出力元MT5:

```text
XM KIWAMI極口座
GOLD#
BTCUSD#
```
