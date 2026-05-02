# XM KIWAMI極口座 運用・検証メモ

このメモは、XM KIWAMI極口座で `GOLD#` / `BTCUSD#` を使って検証・将来運用するための注意事項です。

## 現在の方針

- 本命運用候補は XM KIWAMI極口座。
- XM KIWAMI極口座では、銘柄名の末尾に `#` が付く。
  - GOLD: `GOLD#`
  - BTCUSD: `BTCUSD#`
- Vantage の `XAUUSD` と XM KIWAMI の `GOLD#` は別シンボルとして扱う。
- Vantage用プリセットとXM KIWAMI用プリセットを混ぜない。

## XM KIWAMIで確認済みのこと

- MT5でXM KIWAMI極口座へログインできた。
- 気配値表示で `GOLD#` / `BTCUSD#` が表示された。
- `GOLD#` のチャートを開けた。
- MT5用エクスポートEAで、以下のCSVを出力できた。
  - `goldsharp_m15.csv`
  - `goldsharp_h1.csv`
  - `btcusdsharp_m15.csv`
  - `btcusdsharp_h1.csv`

## 出力済みXM KIWAMIデータの概要

2026-05-02時点の確認結果。

| ファイル | 銘柄 | 足 | 行数 | 期間 | spread平均 | spread最小 | spread最大 |
|---|---|---:|---:|---|---:|---:|---:|
| `goldsharp_m15.csv` | `GOLD#` | M15 | 7,772本 | 2026-01-02 08:00 ～ 2026-05-01 23:45 | 19.38 | 16 | 124 |
| `goldsharp_h1.csv` | `GOLD#` | H1 | 1,944本 | 2026-01-02 08:00 ～ 2026-05-01 23:00 | 18.62 | 16 | 33 |
| `btcusdsharp_m15.csv` | `BTCUSD#` | M15 | 5,685本 | 2026-03-04 00:00 ～ 2026-05-02 07:45 | 2250 | 2250 | 2250 |
| `btcusdsharp_h1.csv` | `BTCUSD#` | H1 | 1,424本 | 2026-03-04 00:00 ～ 2026-05-02 07:00 | 2250 | 2250 | 2250 |

補足:

- `GOLD#` の平均spreadは、以前の古い `gold_m15.csv` より低かった。
- `BTCUSD#` の `2250 points` は、価格差では約22.50ドル相当として見る。

## MT5からローソク足CSVを出す手順

1. XM KIWAMI極口座にログインしているMT5を開く。
2. 気配値表示に `GOLD#` / `BTCUSD#` が出ていることを確認する。
3. GitHubの `mt5/export_ohlc_multi.mq5` をMT5の `MQL5/Experts` にコピーする。
4. MT5を再起動する。
5. `GOLD#` のチャートを開く。
6. ナビゲーターの「エキスパートアドバイザ」から `export_ohlc_multi` をチャートへ入れる。
7. 初期値は以下。
   - `InpSymbolsCSV = GOLD#,BTCUSD#`
   - `InpTimeframesCSV = M15,H1`
   - `InpBarsToExport = 30000`
8. CSVは `MQL5/Files` に出る。

出力ファイル名:

```text
goldsharp_m15.csv
goldsharp_h1.csv
btcusdsharp_m15.csv
btcusdsharp_h1.csv
```

## データ置き場の方針

CSVデータは原則GitHubへコミットしない。

理由:

- ブローカー別データが混ざると検証結果が壊れる。
- CSVはサイズが大きくなりやすい。
- ローカルで差し替えるデータなので、GitHub管理よりもフォルダ分けの方が安全。

ローカルでは以下のように分ける。

```text
data/raw/xm_kiwami/goldsharp_m15.csv
data/raw/xm_kiwami/goldsharp_h1.csv
data/raw/xm_kiwami/btcusdsharp_m15.csv
data/raw/xm_kiwami/btcusdsharp_h1.csv
```

VantageやXMスタンダードは別フォルダにする。

```text
data/raw/vantage/...
data/raw/xm_standard/...
data/raw/xm_kiwami/...
```

## 重要な注意事項

### 1. `#` を消さない

XM KIWAMI極口座では `GOLD#` / `BTCUSD#` が正式なMT5シンボル名。

コードやプリセットで以下のような変換をしてはいけない。

```python
symbol = symbol.replace("#", "")
```

また、MT5に渡すシンボル名は、MT5上に表示されている名称をそのまま使う。

### 2. YAMLでは必ずクォートする

`#` はYAML上でコメント扱いになることがあるため、プリセットに書く場合は必ずクォートする。

```yaml
symbols:
  - "GOLD#"
```

BTCUSDの場合も同じ。

```yaml
symbols:
  - "BTCUSD#"
```

### 3. Vantage用とXM KIWAMI用のプリセットを分ける

既存の `gold_abc_v2` などを直接上書きして使い回さない。

推奨例:

```text
vantage_xauusd_gold_abc_v2
xm_kiwami_gold_abc_v2
xm_kiwami_btcusd_test_v1
```

### 4. 結果ファイル名にもブローカー名を入れる

検証結果が混ざるのを防ぐため、出力CSVやレポート名にはブローカー名・口座種別・シンボルを入れる。

例:

```text
xm_kiwami_gold_abc_v2_trades.csv
vantage_xauusd_gold_abc_v2_trades.csv
```

### 5. 比較は同じ期間・同じロジックで行う

Vantageで悪かった2026年3月が、XM KIWAMIでも悪いのかを必ず確認する。

見るべきポイント:

- 全期間の成績
- 後半30%の成績
- 2026-02〜2026-04
- 2026-03単月
- 2026-04単月
- モデル別 A / B / C / C2 の内訳

## 現在の比較観点

- XMスタンダード
- XM KIWAMI極
- Vantage

この3つで以下を比較する。

- GOLD系シンボル名
- BTCUSD系シンボル名
- スプレッド
- ローソク足の違い
- 約定対象として現実的か
- バックテスト成績
- 直近ドローダウン

## Pythonが苦手な場合の進め方

最初はPythonを触らず、MT5側で以下だけ確認する。

- XM KIWAMI極口座にログインできているか
- `GOLD#` が表示されるか
- `BTCUSD#` が表示されるか
- チャートが開けるか
- M15とH1に切り替えできるか

この確認が終わってから、Python側の設定変更に進む。

## 直近の作業順序

1. XM KIWAMI極口座でMT5にログインする。
2. `GOLD#` と `BTCUSD#` を気配値表示に出す。
3. `GOLD#` のM15/H1チャートを開く。
4. `mt5/export_ohlc_multi.mq5` でXM KIWAMIデータを出力する。
5. ローカルで `data/raw/xm_kiwami/` にCSVを置く。
6. Python検証ツール側でXM KIWAMI用プリセットを新規作成する。
7. まず `GOLD#` だけで `gold_abc_v2` 相当の検証を行う。
8. その後、BTCUSD検証を追加する。

## 絶対に避けること

- Vantage用の `XAUUSD` 設定をXM KIWAMI用に雑に上書きする。
- `#` を消す。
- `GOLD#` をクォートせずYAMLに書く。
- どのブローカーの結果かわからないCSV名で保存する。
- 全期間成績だけ見て判断する。
- 2026年3月のような悪い月を無視する。
