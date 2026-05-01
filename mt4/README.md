# MT4 CSV Export

このフォルダには、MT4からローソク足データをCSV出力するためのEAを置く。

## EA

```text
export_ohlc_multi.mq4
```

このEAは売買しない。
XAUUSDやBTCUSDなど、指定した複数銘柄・複数時間足のOHLCデータをCSVへ出力する。

---

## 初期用途

```text
XAUUSD M15 / H1
BTCUSD M15 / H1
```

ただし、BTC/USDのシンボル名はブローカーによって異なる。

例：

```text
BTCUSD
BTCUSDm
BTC/USD
BTCUSD.
```

MT4の気配値表示に出ている名前をそのまま使う。

---

## 使い方

1. GitHub DesktopでPullして、`mt4/export_ohlc_multi.mq4` を取得する。
2. MT4を開く。
3. `ファイル` → `データフォルダを開く` を押す。
4. `MQL4/Experts/` を開く。
5. `export_ohlc_multi.mq4` を `MQL4/Experts/` にコピーする。
6. MT4のMetaEditorを開く。
7. `export_ohlc_multi.mq4` をコンパイルする。
8. MT4へ戻り、ナビゲーターのEA一覧を更新する。
9. 任意のチャート1つにEAを入れる。
10. 入力パラメータを確認してOKを押す。

---

## 入力パラメータ

### InpSymbolsCSV

出力したい銘柄をカンマ区切りで指定する。

例：

```text
XAUUSD,BTCUSD
```

ブローカーの銘柄名が違う場合：

```text
XAUUSDm,BTCUSDm
```

### InpTimeframesCSV

出力したい時間足をカンマ区切りで指定する。

初期値：

```text
M15,H1
```

対応候補：

```text
M1,M5,M15,M30,H1,H4,D1,W1,MN1
```

### InpBarsToExport

出力する本数。

初期値：

```text
20000
```

### InpTimerSeconds

何秒ごとに再出力するか。

初期値：

```text
60
```

リアルタイム監視前のバックテスト用途なら、頻繁に動かす必要はない。

---

## 出力先

MT4の仕様上、ファイルは以下へ出力される。

```text
MT4データフォルダ/MQL4/Files/
```

例：

```text
xauusd_m15.csv
xauusd_h1.csv
btcusd_m15.csv
btcusd_h1.csv
```

Pythonでバックテストする場合は、まず手動で以下へコピーする。

```text
data/raw/
```

---

## CSV形式

```csv
time,open,high,low,close,volume,spread
2026.05.01 10:00,2320.10,2325.20,2318.40,2323.80,1234,25
```

---

## 注意点

### 1. EAは1つだけでよい

このEAは複数銘柄に対応しているため、XAUUSD用とBTCUSD用で別々に入れる必要はない。

### 2. 対象銘柄を気配値表示に出す

`SymbolSelect`で選択を試みるが、うまくいかない場合は、MT4の気配値表示に対象銘柄を表示しておく。

### 3. ブローカーごとに銘柄名が違う

BTC/USDは特に名前が違う可能性が高い。
MT4上の正確なシンボル名を入力する。

### 4. コンパイルエラーが出た場合

MetaEditorのエラー内容をそのまま共有する。
行番号とエラーメッセージが重要。

### 5. EAは取引しない

このEAには注文処理は入っていない。
CSVを書き出すだけ。
