# IMPLEMENTATION PLAN

xauusd-signal-lab の実装順序をまとめる。

原則として、いきなりDiscord通知やAI評価には進まない。
まずはバックテストで検証できる土台を作る。

---

## Phase 1: MT4からCSVを出力する

目的：XAUUSDのM15/H1データをPythonで読める形にする。

出力ファイル：

```text
data/raw/xauusd_m15.csv
data/raw/xauusd_h1.csv
```

CSV形式：

```csv
time,open,high,low,close,volume,spread
```

注意：

```text
時刻形式を統一する
欠損足を確認する
スプレッドを可能なら出力する
MT4のサーバー時間を記録する
```

---

## Phase 2: Pythonでデータを読み込む

作成候補：

```text
src/data_loader.py
src/config.py
```

役割：

```text
CSV読み込み
時刻のdatetime変換
重複行チェック
欠損チェック
数値型変換
M15/H1データの整形
```

---

## Phase 3: インジケーター計算

作成候補：

```text
src/indicators.py
```

計算するもの：

```text
EMA20
EMA50
MACD Fast/Slow/Signal
MACDライン
MACDシグナル
MACDヒストグラム
ATR
```

MACDはTradingView / Pine Script と同じ設定値をPython側で再計算する。

---

## Phase 4: 確定スイング判定

作成候補：

```text
src/swings.py
```

初期設定：

```text
SWING_LEFT = 3
SWING_RIGHT = 2
```

注意：

```text
スイングが発生した足ではなく、確定した足から使用可能にする
右側の足が確定する前に使わない
```

---

## Phase 5: H1環境をM15へ結合

作成候補：

```text
src/data_loader.py
src/signal_logic.py
```

H1環境：

```text
BUY環境：H1 EMA20 > H1 EMA50 かつ H1終値 > H1 EMA20
SELL環境：H1 EMA20 < H1 EMA50 かつ H1終値 < H1 EMA20
```

注意：

```text
M15の各足には、その時点で確定済みのH1足だけを結合する
未確定H1足を使わない
```

---

## Phase 6: ダイバージェンス判定

作成候補：

```text
src/divergence.py
```

実装対象：

```text
強気通常ダイバージェンス
弱気通常ダイバージェンス
強気ヒドゥンダイバージェンス
弱気ヒドゥンダイバージェンス
```

初期方針：

```text
ヒドゥンダイバージェンス：順張り条件
通常ダイバージェンス：見送り要素
```

---

## Phase 7: ルールベースシグナル生成

作成候補：

```text
src/signal_logic.py
```

BUY候補：

```text
H1がBUY環境
M15でEMA20付近まで押し目
強気ヒドゥンダイバージェンス
MACD反転または改善
RR1.5以上
```

SELL候補：

```text
H1がSELL環境
M15でEMA20付近まで戻り目
弱気ヒドゥンダイバージェンス
MACD反転または悪化
RR1.5以上
```

---

## Phase 8: バックテスト

作成候補：

```text
src/backtest.py
```

ルール：

```text
判定：M15足確定後
エントリー：次のM15足始値
SL：今回押し目/戻り目区間の外側
TP：SL幅 × 1.5
勝敗：先にTPなら勝ち、先にSLなら負け
```

同一足でTP/SL両方に到達した場合：

```text
初期案：保守的に負け扱い、または別集計
```

---

## Phase 9: レポート出力

作成候補：

```text
src/report.py
```

集計項目：

```text
総トレード数
勝率
平均R
PF
最大DD
最大連敗
BUY成績
SELL成績
時間帯別成績
曜日別成績
月別成績
年別成績
SL幅別成績
時間帯×方向別成績
```

---

## Phase 10: 負けパターン分析

バックテスト結果を見て、以下を確認する。

```text
レンジ中央で負けていないか
SL幅が狭すぎないか
SL幅が広すぎないか
時間帯の偏りがないか
BUY/SELLで差が大きすぎないか
H1トレンドが弱い場面で負けていないか
通常ダイバージェンス逆行時に負けていないか
```

---

## Phase 11: 機械学習フィルター

作成候補：

```text
src/features.py
src/labeling.py
src/train_model.py
src/predict.py
```

役割：

```text
ルールベースで候補を出す
各候補に勝ち負けラベルを付ける
LightGBMなどで勝率予測する
予測勝率や期待値が高い候補だけ通す
```

禁止：

```text
ランダム分割
未来データ混入
勝率だけで評価
```

---

## Phase 12: Discord通知

作成候補：

```text
src/discord_notify.py
src/runner.py
```

通知内容：

```text
銘柄
時間足
方向
エントリー候補
SL
TP
RR
H1環境
M15条件
MACD状態
ダイバージェンス状態
バックテスト上の類似条件成績
注意点
```

---

## Phase 13: AI評価

AIは売買判断の主役にしない。

役割：

```text
通知内容の整理
見送り理由の列挙
相場状況の文章化
注意点の補足
```

最終判断は人間が行う。

---

## 初期の完成条件

まずは以下を満たせば v0.1 とする。

```text
M15/H1 CSVを読み込める
PythonでMACD/EMA/ATRを計算できる
確定スイングを判定できる
ヒドゥンダイバージェンスを判定できる
H1環境をM15へ未来参照なしで結合できる
RR1.5固定でバックテストできる
BUY/SELL別・時間帯別・月別の成績を出せる
```
