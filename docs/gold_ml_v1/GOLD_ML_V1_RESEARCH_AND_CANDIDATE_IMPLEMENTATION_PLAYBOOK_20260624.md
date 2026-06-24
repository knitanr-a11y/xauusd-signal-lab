# GOLD_ML_V1 研究・候補実装プレイブック

更新日: 2026-06-24

この文書は、探索、候補生成、機械学習、検証、ローカル再現、候補台帳更新を、チャットや担当者が変わっても同じ手順で行うための実装正本である。

## 1. ディレクトリ設計

```text
docs/gold_ml_v1/       人間向け契約、研究計画、引き継ぎ、監査説明
config/gold_ml_v1/     候補・特徴・label・split・policyのimmutable JSON
scripts/gold_ml_v1/    探索、特徴生成、評価、replay、report生成
models/gold_ml_v1/     model/scaler/encoder/clustererとmanifest
tests/gold_ml_v1/      causality、timestamp、execution、parity tests
```

候補出力を一時フォルダだけに置かず、採用・監視・棄却判断は必ず `config/gold_ml_v1/` に記録する。

## 2. IDとlineage

### 候補ID

- 手動ルールまたは固定イベント: `GML1-PROV-NNN`
- 監視専用・研究モデル: `GML1-WATCH-NNN-X`
- feature set: `GML1-FEAT-NNN`
- label family: `GML1-LABEL-NNN`
- model: `GML1-MODEL-NNN`
- experiment batch: `GML1-BATCH-NNN`

### 不変性

以下のどれかが変われば新ID。

- threshold
- feature formula
- lookback
- timeframe
- direction
- entry mode
- TP/SL
- horizon
- spread treatment
- model seed
- model hyperparameter
- loss exclusion

古いIDのconfigやmetricsを書き換えて別ロジックにしない。

## 3. 生データ読み込み

### 入力

```python
REQUIRED_COLUMNS = [
    "time", "open", "high", "low", "close",
    "tick_volume", "spread", "real_volume",
]
```

### ルール

1. `time`をMT5 server timeのnaive timestampとして読む。
2. timeframe durationを加えて`bar_close_time`を作る。
3. duplicate/out-of-order/OHLC invalidを検査する。
4. historicalを主系列とする。
5. liveはhistorical max open timeより後だけappendする。
6. latest rowをopen扱いで落とさない。
7. M1 gapsを記録し、exact entry/horizon判定へ使う。

### 例

```python
TF_DELTA = {
    "M1": pd.Timedelta(minutes=1),
    "M5": pd.Timedelta(minutes=5),
    "M15": pd.Timedelta(minutes=15),
    "H1": pd.Timedelta(hours=1),
    "H4": pd.Timedelta(hours=4),
    "D1": pd.Timedelta(days=1),
}

df["bar_open_time"] = pd.to_datetime(df["time"])
df["bar_close_time"] = df["bar_open_time"] + TF_DELTA[tf]
```

## 4. 因果的as-of join

HTF特徴はHTF openではなくHTF close後に利用する。

```python
merged = pd.merge_asof(
    decision_df.sort_values("bar_close_time"),
    htf_features.sort_values("bar_close_time"),
    on="bar_close_time",
    direction="backward",
    allow_exact_matches=True,
)
```

HTF rowの`bar_close_time`がdecision rowの`bar_close_time`を超えていないことをtestで保証する。

## 5. 特徴量実装

全特徴は次を持つ。

- name
- formula
- timeframe
- lookback
- availability time
- normalization
- NaN policy
- version

### 推奨正規化

- price distance / ATR14
- slope / ATR14
- spread * point / ATR14
- rolling percentile
- rolling z-score
- volume / rolling mean

絶対価格をそのままモデルへ入れない。

### Causal pivot

pivotは右側確認本数が揃った時点からのみ利用可能。

```python
pivot_at_i = (
    high[i] == max(high[i-left:i+right+1])
)
available_at = i + right
```

pivot priceを過去のpivot時刻へ遡って利用可能にしない。

### Trendline

- last two available confirmed high pivots
- last two available confirmed low pivots
- decision時点へ直線をproject
- slope/ATR、distance/ATR、touch count、break、retestを作る
- breakout時のlineをfreezeし、retest中に後から引き直さない

### Channel

- confirmed-pivot channel
- rolling linear-regression channel
- Donchian20/40/60
- width/ATR
- channel position
- break、failed break、reentry

### Bollinger

- periods 20/40/60
- middle = rolling mean
- upper/lower = middle ± 2 * population std
- %B
- full width/ATR
- trailing width percentile
- squeeze/release
- band walk
- middle reclaim/rejection

## 6. event generator

イベントはstateと区別する。

### State

条件が成立している全bar。

### Onset

falseからtrueへ変化した最初のbar。

### Event

break、retest、failed break、reentryなどの明示的変化。

### Reentry/cooldown

state中も、前trade終了後または固定cooldown後に再entry可能な別lineage。

各方式を混ぜず別configで評価する。

## 7. exact M1 execution evaluator

### Entry

```python
entry_time = decision_close_time
entry_m1 = m1.loc[m1.bar_open_time == entry_time]
```

exact rowがなければtrade invalid。

### Price

```python
point = 0.01
spread_price = m1.spread * point

if direction == "LONG":
    entry = m1.open + spread_price
else:
    entry = m1.open
```

### Barrier

```python
if direction == "LONG":
    sl = entry - stop_atr_multiple * decision_atr
    tp = entry + target_r * stop_distance
else:
    sl = entry + stop_atr_multiple * decision_atr
    tp = entry - target_r * stop_distance
```

SHORT exit判定はask相当`bid + dynamic spread`を使う。

### 同一bar

TPとSL双方が同一M1でhitした場合はSL。

### Time exit

horizon終了時刻で終わる最後のM1 closeを使う。horizon時刻のM1 openを使わない。

## 8. trade registry

最低列:

```text
candidate_id
feature_set_id
label_id
decision_open_time
decision_close_time
entry_time
entry_price
direction
atr_at_decision
sl_price
tp_price
exit_time
exit_price
exit_reason
r_value
spread_at_entry
split_year
valid_label
```

MLの場合は追加:

```text
model_id
model_seed
score
selection_threshold
coverage_bucket
model_hash
scaler_hash
```

CSVをtimestamp順にsortし、SHA256を保存する。

## 9. metrics

最低限:

- trades
- wins/losses/time exits
- win rate
- gross positive R
- gross negative R
- PF
- total R
- maximum drawdown R
- average R
- median R
- monthly/yearly metrics
- session/volatility/regime breakdown
- spread stress
- overlap with other candidates

```python
pf = gross_positive_r / abs(gross_negative_r)
```

zero lossの場合は無限大をそのまま比較に使わず、標本数とともに扱う。

## 10. coverage-first loss subtraction

### 手順

1. 広いbase opportunity poolを作る。
2. baseの全tradeにentry時点特徴をjoinする。
3. winner/loserで単独特徴分布を比較する。
4. 2特徴・3特徴のAND条件でloss concentrationを探索する。
5. shallow tree leafやregularized modelも使う。
6. thresholdは2023だけから作る。
7. 2024/2025でconfirmする。
8. retained coverageとPFを同時評価する。
9. freeze後に2026 diagnosticを見る。

### 禁止

- 2026で良かったthresholdを選ぶ
- loss feature列そのものを削除する
- 20件だけ残してPFを作る
- parent configを上書きする

## 11. PF2 refinement

PF2は目標であり、唯一の採用条件ではない。

評価関数の例:

```python
score = (
    2.0 * min(pf_pre2026, 3.0)
    + 1.0 * min(pf_2025, 3.0)
    + 0.5 * min(pf_spread15, 3.0)
    + 0.02 * min(trades_pre2026, 300)
    - 0.2 * max_drawdown
    - scarcity_penalty
    - concentration_penalty
)
```

ただし、scoreだけで自動採用しない。

必須確認:

- 各年プラス
- 件数維持
- 2025の強さ
- spread1.5x
- neighborhood
- filter activation count
- fresh prospective activation

後期にfilterが一度も発動しない場合、親の後期成績を新filterの証拠にしない。

## 12. watch pool

分類:

- ACTIVE_PROVISIONAL
- WATCH_LOW_COUNT
- WATCH_BORDERLINE_EDGE
- RESEARCH_ONLY
- REJECTED

low-count watch:

- 条件をfreeze
- 新しいclosed tradeをappend
- 10件増えるごとに再集計
- 最低20 fresh tradesで再判定
- threshold変更禁止

## 13. ML実装

### 13.1 Tabular model

候補entry時点特徴で、loss riskまたはexpected Rを予測する。

推奨:

- logistic regression with regularization
- shallow tree
- LightGBM/XGBoost with depth and feature constraints
- calibration

目的:

- base entry生成器を置き換えるより、loss-prone regionの除外を優先。

### 13.2 Sequence model

入力例:

```text
last N bars × [return/ATR, body/ATR, range/ATR, close_location,
               volume_ratio, spread/ATR, BB%B, EMA distance/ATR]
```

契約:

- fixed sequence length
- gap reset/mask
- train-only scaling
- deterministic seed
- output score and coverage bucket

### 13.3 Clustering

- scalerをtrainだけでfit
- clustererをtrainだけでfit
- multiple seeds
- centroid export
- excluded clusterの特徴説明
- cluster IDをロジックの意味として扱わず、centroid patternを保存

### 13.4 Regime model

候補:

- volatility regime
- trend efficiency
- autocorrelation
- spread state
- volume state
- session

HMMやclusteringを使う場合も、state numberingがseedで変わり得るためcentroid/state signatureで識別する。

## 14. Walk-forward

例:

```text
Fold A: train 2023-H1, validate 2023-H2
Fold B: train 2023, validate 2024-H1
Fold C: train 2023-2024-H1, validate 2024-H2
Fold D: train 2023-2024, validate 2025-H1
Fold E: train 2023-2025-H1, validate 2025-H2
```

各foldで:

- scaler/model再fit
- thresholdはfold train/validationだけで決める
- prediction registryを保存
- fold合算成績とworst foldを報告

## 15. MAE/MFE meta-labeling

entry後、SL/TP/horizonまでの経路から以下を作る。

```text
MAE_R
MFE_R
time_to_MFE
time_to_TP
time_to_SL
bars_underwater
bars_above_0_5R
stagnation_bars
first_impulse_direction
```

用途:

- 早く伸びるtradeと停滞tradeを分離
- entry filter
- timeout policy候補
- partial exitの将来研究

ただし現在partial closeは無効であり、実装してもresearch-only。

## 16. candidate overlap

2候補間で次を計算する。

- exact same entry timestamp overlap
- ±1 decision bar overlap
- Jaccard
- same direction/opposite direction
- concurrent exposure
- monthly R correlation
- regime concentration

parent/derivativeの重複は当然高いため、候補数を独立edge数として誤解しない。

## 17. prospective monitoring

cutoff後のbarだけで:

- frozen condition evaluation
- raw signal registry
- selected trade registry
- filter activation log
- health log

過去データでthresholdを変更した時点で新candidate IDにする。

## 18. local replay package

推奨構成:

```text
scripts/gold_ml_v1/replay/run_<candidate_id>.py
scripts/gold_ml_v1/replay/run_<candidate_id>.bat
config/gold_ml_v1/candidates/<candidate_id>.json
config/gold_ml_v1/manifests/<candidate_id>_inputs_sha256.json
config/gold_ml_v1/expected/<candidate_id>_metrics.json
config/gold_ml_v1/expected/<candidate_id>_trade_registry_sha256.json
```

BATは探索をせず、exact replayだけを行う。

終了コード:

- 0: exact parity
- 1: input mismatch
- 2: registry mismatch
- 3: metrics mismatch
- 4: dependency/environment error

## 19. テスト

最低限:

- latest row retained
- HTF unavailable before close
- pivot unavailable before right confirmation
- trendline freeze
- exact M1 entry requirement
- dynamic spread
- short ask exit
- same-bar SL priority
- time-exit close semantics
- year boundary horizon
- deterministic model output
- registry SHA equality

## 20. 候補判断テンプレート

各batch result JSONに必須:

```json
{
  "result_id": "...",
  "selection_window": {},
  "rule": {},
  "metrics": {},
  "spread_stress": {},
  "neighborhood": {},
  "activation_counts": {},
  "decision": "ACTIVE|ACCUMULATED_WITH_CAVEAT|WATCH|REJECT",
  "reason": "...",
  "boundaries": {
    "not_registered": true,
    "local_replay_pending": true,
    "fresh_prospective_pending": true
  }
}
```

## 21. 現在の正本

- current state: `config/gold_ml_v1/current_state_snapshot_20260624.json`
- candidate stack: `config/gold_ml_v1/provisional_candidate_stack_20260624.json`
- next-chat handoff: `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_20260624.md`
- PF2 policy: `config/gold_ml_v1/pf2_refinement_policy_20260624.json`
- watch policy: `config/gold_ml_v1/watch_pool_policy_20260624.json`
- reproducibility: `config/gold_ml_v1/reproducibility_contract_20260624.json`

この文書と上記正本に反する一時的なチャット説明があれば、リポジトリの最新正本を優先する。
