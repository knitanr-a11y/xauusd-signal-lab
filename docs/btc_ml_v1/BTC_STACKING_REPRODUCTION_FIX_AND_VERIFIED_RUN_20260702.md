# BTC積み重ね一括再現 — BTC6 CLI修正と実測検証

作成日: 2026-07-02

repo: `knitanr-a11y/xauusd-signal-lab`

## 結論

基準コミット `97fd7ae097bf608d8fbc954d2641e8c9b72dc7ed` は、BTC6が取引台帳等を書き出した後、存在しない `engine._json_default` を参照して終了コード1となるため、生CSVからのend-to-end一括再現を完走できなかった。

BTC6の候補条件、エントリー、決済、TP/SL、リスク、指標計算には触れず、CLIの最終JSON表示だけをローカルserializerへ置換した。さらに `main()` を実際に通す回帰テストを追加した。

修正後、指定された2つの元データパッケージから5候補を再生成する一括スクリプトを、入力SHA検証を省略せずに最初から実行した。終了コード0で完走し、実物の `btc_stacking_reproduction_report.json` に `"reproduction_pass": true` が記録された。

## 修正

対象:

```text
scripts/btc_ml_v1/research/btc6_video_m15_ema200_nwave_candidate.py
```

旧実装:

```python
print(json.dumps(result, ensure_ascii=False, indent=2, default=engine._json_default))
```

問題:

```text
btc5_video_5m_ema200_nwave_candidate に _json_default は存在しない
```

修正後はBTC6内の `_json_default()` を使用する。NumPy scalarは `.item()`、日時系は `.isoformat()`、その他は文字列へ変換する。

取引ロジックの変更はない。

## 回帰テスト

対象:

```text
tests/btc_ml_v1/test_btc6_video_m15_ema200_nwave_candidate.py
```

追加した確認:

- `main()` が終了コード0を返す
- stdoutが有効なJSONとして読める
- NumPy整数・浮動小数が数値として保持される
- `pandas.Timestamp` がISO形式になる
- safety flagがboolのまま保持される

実測:

```text
5 passed
```

## 入力パッケージ

```text
BTCUSD_HISTORY_CHAT_PACKAGE.zip
SHA256: 9b0b74e9937eca05e895047f5737c6794332af7ec25f2a30b64d9440c9e0dd22

BTCUSD_H4_WARMUP_PACKAGE.zip
SHA256: d150eaee0c126e2eb4c4aecb667ff0ad181a9a0a6e060cc5c1613b60e0a8019a
```

入力CSVのSHA、行数、開始時刻、終了時刻の検証は有効のまま実行した。

## 実行環境

```text
Python 3.13.5
NumPy 2.3.5
pandas 2.2.3
pytest 9.0.2
```

referenceに記録された予定環境とはPython・NumPy・pytestが異なるが、入力検証、候補指紋、全体集計はすべて完全一致した。

## end-to-end再現結果

```json
{
  "reproduction_pass": true,
  "metric_errors": {},
  "fingerprint_errors": {},
  "unresolved_post2026": 0,
  "maximum_simultaneous_positions": 3
}
```

### 2026年以前

```text
trades: 142
wins: 104
losses: 38
win rate: 73.23943661971832%
profit factor: 2.786707805257423
total pips: 5768.321236393678
max drawdown pips: 345.1760610365195
```

### 開封済み2026評価

```text
trades: 43
wins: 26
losses: 17
win rate: 60.46511627906976%
profit factor: 2.023409973468012
total pips: 1199.4233575223682
max drawdown pips: 247.83957401328757
```

### 全期間

```text
trades: 185
wins: 130
losses: 55
win rate: 70.27027027027027%
profit factor: 2.58341607495273
total pips: 6967.744593916048
max drawdown pips: 345.1760610365195
```

## 指紋と出力不変性

候補エントリー指紋は全件referenceと一致した。

BTC6について、修正後の以下3ファイルは、表示処理だけを暫定回避した診断実行の出力とbyte-for-byte一致した。

- `btc6_m15_candidate_trade_ledger.csv`
- `btc6_m15_candidate_summary.csv`
- `btc6_m15_post2026_entry_only.csv`

したがって、修正は候補生成結果へ影響していない。

## 実物レポート指紋

```text
btc_stacking_reproduction_report.json
SHA256: 45fcde35def8d82e2ff67f11fc7131fbf8f3112eeccb761706bfb3e37f4e1989
```

## safety状態

```text
orders_enabled = false
discord_enabled = false
live_ready = false
final_signal = false
```

再現成功はライブ稼働許可ではない。

BTC5・BTC6・BTC7R・BTC9Rのロットは、この再現修正では設定していない。既存5候補も2026年結果で再最適化していない。
