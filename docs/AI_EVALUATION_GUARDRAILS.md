# AI評価ガードレール

このドキュメントは、将来のリアルタイムシグナル評価でAIを使うときに、
変な判定・見送り過多・過剰最適化・未来情報混入を避けるための設計方針です。

## 結論

`data/results/ai_cases/xm_kiwami_gold_abc_v3_balanced_ai_cases.csv` は、
AI評価の第一歩としては有用。

ただし、このCSVだけをAIに渡して売買判断をさせるのは危険。

理由:

- 現在のケースCSVは、トレード結果中心の情報であり、エントリー前の相場特徴がまだ不足している。
- 勝ちケースと負けケースの比率によってAIの判定バイアスが変わる。
- 負けケースだけを強く読ませると見送り過多になりやすい。
- 勝ちケースだけを強く読ませると警戒不足になりやすい。
- `result`, `r`, `exit_time`, `bars_held` は過去ケースのラベルとしては有用だが、現在シグナルの評価時には未来情報なので使えない。

## AIにやらせること

AIは売買の最終判断者ではない。

AIにやらせるのは以下。

```text
現在のシグナルが、過去の勝ちパターンにどれだけ近いか
現在のシグナルが、過去の負けパターンに危険なほど似ていないか
エントリー前に人間が確認すべき注意点は何か
```

## AIにやらせないこと

```text
このシグナルは絶対に入るべき
このシグナルは絶対に見送るべき
勝率を断定する
バックテスト結果よりAI判断を優先する
未来情報を使う
```

## 入力データの分離

AIに渡す情報は、必ず以下の2つに分ける。

### 1. Historical cases

過去ケース。
ここには結果を含めてよい。

含めてよいもの:

- case_type: win_pattern / loss_pattern
- model: A / B / C / C2
- side: BUY / SELL
- entry_time
- jst_entry_hour
- entry_price
- sl
- tp
- risk
- result
- r
- bars_held
- exit_reason

ただし、`result`, `r`, `exit_time`, `bars_held` は「過去ケースの結果ラベル」と明示する。

### 2. Current signal snapshot

現在シグナル。
ここにはエントリー前に分かる情報だけを入れる。

含めるべきもの:

- model
- side
- signal_time
- jst_hour
- entry_price_candidate
- sl
- tp
- risk
- ATR
- risk_atr_ratio
- spread
- H1 trend state
- H1 EMA alignment
- H1 EMA gap ATR
- M15 EMA alignment
- MACD line/signal/histogram
- MACD histogram acceleration
- recent swing position
- breakout strength
- recent candle body/wick information
- recent volatility/chop state

含めてはいけないもの:

- 未来のexit_time
- 未来のresult
- 未来のr
- 未来のbars_held

## 判定の基本順序

AIは以下の順番で評価する。

### Step 1: ルールシグナルを尊重する

バックテストで期待値があるルールから出たシグナルであることを前提にする。
AIは最初から疑ってかかるのではなく、まず期待値のあるシグナルとして扱う。

### Step 2: 勝ちパターン一致度を見る

現在シグナルが、同じモデル・同じ方向・近い時間帯の勝ちケースに似ているかを見る。

出力:

```text
winning_pattern_match: high / medium / low
```

### Step 3: 負けパターン類似度を見る

現在シグナルが、過去の負けケースに危険なほど似ていないかを見る。

出力:

```text
losing_pattern_similarity: high / medium / low
```

### Step 4: 総合判定

```text
final_risk_label: normal / caution / strong_caution / skip_candidate
```

ただし、`skip_candidate` は簡単に出さない。

## skip_candidate を出す条件

AIが `skip_candidate` を出してよいのは、以下のように複数の強い根拠が重なった場合だけ。

例:

- 勝ちパターン一致度が low
- 負けパターン類似度が high
- H1とM15の方向が噛み合っていない
- MACD加速が弱い
- ブレイク後に押し戻されやすいローソク足
- risk/ATRが極端
- スプレッドが通常より悪い

時間帯が同じ、モデルが同じ、過去に似た負けが1つある、だけでは `skip_candidate` にしない。

## caution の扱い

`caution` は見送りではない。

```text
caution = 入る前に確認すべき注意点がある
strong_caution = 見送りも含めて慎重に判断
skip_candidate = ルール上は出ているが、相場状態がかなり悪い可能性
```

## ケース検索の考え方

AIに毎回すべてのケースを渡すのではなく、まずは近いケースを選ぶ。

優先順位:

1. 同じモデル
2. 同じside
3. 近いJST時間帯
4. 近いrisk/ATR
5. 近いH1環境
6. 近いM15形状

例:

```text
現在が C BUY なら、まず C BUY の勝ちケースと負けケースを見る。
A SELL やB SELLのケースは補助情報に留める。
```

## 現在のケースCSVの位置づけ

現在生成しているケースCSV:

```text
data/results/ai_cases/xm_kiwami_gold_abc_v3_win_cases.csv
data/results/ai_cases/xm_kiwami_gold_abc_v3_loss_cases.csv
data/results/ai_cases/xm_kiwami_gold_abc_v3_balanced_ai_cases.csv
```

これは、AI評価の「ケース集の土台」。

ただし、次の改善が必要。

- entry前特徴量を増やす
- ATR、risk/ATR、EMA状態、MACD状態を追加する
- H1/M15の相場状態を追加する
- 勝ちケース・負けケースをモデル別に検索できるようにする
- AI評価結果を保存し、後から当たり外れを検証する

## 運用前に必ずやること

### Shadow mode

最初からAI評価で実トレードを止めない。

まずは一定期間、AI評価だけを記録する。

```text
シグナルは通常どおり記録
AI評価も記録
実際の結果とAI評価を後から比較
```

見る項目:

- AIがnormalにしたシグナルの成績
- AIがcautionにしたシグナルの成績
- AIがstrong_cautionにしたシグナルの成績
- AIがskip_candidateにしたシグナルの成績
- AIが見送り寄りにしすぎていないか
- AIが危険シグナルを見逃していないか

## プロンプト出力フォーマット

AIにはJSONまたは固定形式で出力させる。

```json
{
  "winning_pattern_match": "high | medium | low",
  "losing_pattern_similarity": "high | medium | low",
  "final_risk_label": "normal | caution | strong_caution | skip_candidate",
  "evidence_for_entry": [
    "..."
  ],
  "evidence_against_entry": [
    "..."
  ],
  "human_checkpoints": [
    "..."
  ],
  "do_not_use_as_final_trade_decision": true
}
```

## 現時点の判断

現在の `balanced_ai_cases.csv` は、このまま「補助ケース集」としては使える。

ただし、実運用AI評価に使うには、以下を満たす必要がある。

```text
1. 現在シグナルのentry前特徴量を作る
2. 近い勝ちケース・近い負けケースだけを抽出する
3. AIに勝ち一致度と負け類似度を両方出させる
4. skip_candidateを簡単に出させない
5. shadow modeでAI評価の癖を検証する
```
