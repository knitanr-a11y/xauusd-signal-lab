# GOLD_ML_V1 次チャット引き継ぎ

更新日: 2026-06-24

この文書は、チャット上限に達しても GOLD_ML_V1 の研究を同じ契約・同じ候補台帳・同じ検証基準から再開できるようにするための正本である。

## 1. 最初に守る境界

- リポジトリ: `knitanr-a11y/xauusd-signal-lab`
- 新規作業名前空間: `docs/config/scripts/models/tests/gold_ml_v1`
- 現在は audit-only。
- live signal、MT5注文、Discord通知、partial close、portfolio activation、automatic promotionは禁止。
- 旧 GOLD V3、GOLD V2、旧GOLD、DISC8、Stage41、および旧モデル・旧候補・旧特徴・旧出力を読まない、使わない、比較しない、fallbackにしない。
- 例外は、明示的に許可された生ローソク足CSVだけ。

開始時は必ず次を読む。

1. `AGENTS.md`
2. `config/gold_ml_v1/current_state_snapshot_20260624.json`
3. `config/gold_ml_v1/provisional_candidate_stack_20260624.json`
4. `docs/gold_ml_v1/GOLD_ML_V1_RESEARCH_AND_CANDIDATE_IMPLEMENTATION_PLAYBOOK_20260624.md`
5. この引き継ぎ文書

## 2. ユーザーの目的

- GOLDの大きな値動きを活かし、十分な件数と高い勝率・PFを両立する候補を複数積み上げる。
- PFは2.0以上を削り込み目標とし、可能ならそれ以上を狙う。
- 件数が少ないが構造的に有望な候補は捨てず、監視プールで固定条件のまま新規データを追加する。
- 単純なインジケーター条件だけでなく、トレンドライン、チャネル、ボリンジャーバンド、価格帯の受容・拒否、時間帯、出来高、価格経路、MAE/MFE、到達時間、相場状態遷移など、別視点で探索する。
- 件数を極端に減らして見かけ上のPFだけを作ることは禁止。

## 3. 生データ契約

許可された生データ:

- historical: `gold_v3_2023_2026_m1/m5/m15/h1/h4/d1.csv`
- live append: `goldsharp_m1/m5/m15/h1/h4/d1.csv`

契約:

- 列: `time,open,high,low,close,tick_volume,spread,real_volume`
- `time` はMT5サーバー時刻のbar open。
- CSV最新行はclosedであり、削除しない。
- `bar_close_time = bar_open_time + timeframe duration`。
- 上位足はそのbar close後にのみ利用可能。
- historicalを主系列とし、liveはhistorical最大時刻より後だけをappendする。
- provisional point = `0.01`。
- raw timeをJSTに書き換えない。

既知の品質監査:

- duplicate 0
- out-of-order 0
- invalid OHLC 0
- alignment violation 0
- historical/live overlap mismatch 0

## 4. 実行・ラベル契約

基本:

- decision barのclose時点で条件判定。
- entryは次のexact M1 open。
- LONG entry = M1 bid open + dynamic spread。
- SHORT entry = M1 bid open。
- SHORT closeはbid + dynamic spread。
- 同一M1内にTP/SL双方が触れた場合はSL優先。
- lineageごとにone position at a time。
- time exitはhorizon終了時点で終わる最後のM1 close。
- exact horizon closeがなく、TP/SLも未到達ならinvalid label。
- horizon途中でTP/SLが先に到達した場合、後続データ欠損があってもtradeは有効。

主なlane:

- M5-H4: 3h horizonを基本。
- M15-H4: 6hを基本。別lineageでは12h等も可。
- H1-D1: 48hを基本。

TP/SLやhorizonを変えた場合は、同じ候補を上書きせず別lineage IDを作る。

## 5. データ分割と現在のholdout扱い

- 2023: discovery/exploration
- 2024: validation
- 2025: test
- 2026: すでに複数回診断に使ったため、今後の候補選定・閾値調整には使わない。
- fresh prospective cutoff: MT5 server close `2026-06-23 18:15:00`
- 最終的な新規確認は、cutoffよりcloseが後のbarだけを使う。

2026で良かった下位条件を後から選び直すことは禁止。

## 6. これまでの探索方針の変化

### 初期問題

- 高い分位条件を最初から掛け合わせたため、候補件数が少なすぎた。
- false-to-true onsetだけに限定し、GOLDの繰り返し機会を落としていた。
- 少しプラス、PF1.1程度、小標本でも候補に追加しかけた。

### 修正後

1. 広い機会母集団を作る。
2. 全機会に因果的ラベルを付ける。
3. 勝ち負けの分布、2～3特徴の相互作用、浅いloss treeを調べる。
4. 負け側へ集中する複合領域だけを除く。
5. 件数維持率、年別成績、PF、DD、spread stressを同時評価する。
6. 件数が少ないものは監視プールへ移す。
7. PF2を refinement targetにする。

## 7. 現在の積み重ね候補 6本

正本: `config/gold_ml_v1/provisional_candidate_stack_20260624.json`

### GML1-PROV-007

- parent: `GML1-PROV-002`
- lane: M15-H4 LONG
- 概要: H4高RCI・低spread/ATRの親候補から、H4 EMA40伸び切りと上ヒゲ拒否が同時に出る負け領域を除外。
- 全期間診断: 154件、99勝、勝率64.29%、PF1.792、+42.92R、maxDD約5.98R。
- source: `config/gold_ml_v1/provisional_loss_subtraction_batch003.json`

### GML1-PROV-008

- parent: `GML1-PROV-002`
- lane: M15-H4 LONG
- 概要: 親候補から、M15 BB20/BB60が低帯域の圧縮状態を除外。
- 全期間診断: 169件、105勝、勝率62.13%、PF1.623、+39.37R、maxDD4R。
- source: `config/gold_ml_v1/provisional_bollinger_loss_subtraction_batch005.json`

### GML1-PROV-010

- independent lineage
- lane: H1-D1 LONG
- 概要: H1 closeがBB60上限を上抜け、last closed D1 RCI18が非負。
- exact registry audit: 254件、155勝、勝率61.02%、PF1.572、+55.95R、maxDD5R。
- 2026 diagnostic: 27件、19勝、PF約2.262、+10.09R。
- source: `config/gold_ml_v1/provisional_loss_subtraction_batch007.json`

### GML1-PROV-015

- parent: `GML1-PROV-010`
- lane: H1-D1 LONG
- 概要: PROV-010から、D1 tick-volume participationが弱く、3日進捗もATR比で小さいダマシ上抜け領域を除外。
- 全期間診断: 225件、147勝、勝率65.33%、PF1.899、+68.95R、maxDD4R。
- 2026 diagnostic: 25件、19勝、PF約3.016、+12.09R。
- source: `config/gold_ml_v1/provisional_loss_subtraction_batch007.json`

### GML1-PROV-020

- parent: `GML1-PROV-015`
- lane: H1-D1 LONG
- 概要: PROV-015から、server hour 08-16かつH1 spread/ATRが高い負け領域を追加除外。
- pre-2026: 179件、120勝、勝率67.04%、PF2.071、+61.86R、maxDD4R。
- all-period diagnostic: 204件、139勝、勝率68.14%、PF2.160、+73.95R。
- spread1.5x all-period PF約2.063。
- caveat: 第二段除外は2026で0回発動。2026の改善は親候補から継承しているため、fresh activationが必要。
- source: `config/gold_ml_v1/provisional_pf2_pruning_batch013.json`

### GML1-WATCH-014-A

- parent context: `GML1-PROV-015`
- lane: H1-D1 LONG
- 概要: entry前12本のH1価格経路をATR正規化し、KMeansでloss-prone path clusterを除外。
- pre-2026: 178件、120勝、勝率67.42%、PF2.088、+62.33R、maxDD3R。
- 2026 diagnostic: 23件、PF3.419、+12.09R。
- caveat: seed stabilityが未解決。clusterの意味を人間が監査可能な形へ変換する必要がある。
- source: `config/gold_ml_v1/alternative_path_shape_batch014_result.json`

`PROV-020`と`WATCH-014-A`はユーザーの明示指示で積み重ね候補に含める。注意事項は消さない。

## 8. reference/watch/rejected

### reference only

- `GML1-PROV-002`: PROV-007/008の不変parent。単独では現在のPF基準に届かない。

### watch only / research only

- PROV-004
- PROV-009
- PROV-013
- PROV-014
- PROV-016
- PROV-018
- PROV-019
- WATCH-012-A
- WATCH-012-B

低件数は捨てず、`config/gold_ml_v1/watch_pool_policy_20260624.json`に従い、固定条件のまま新規tradeを追加する。

### rejected

- PROV-017: 2026で明確に崩れ、近傍も全滅。

## 9. PF2 refinement方針

正本: `config/gold_ml_v1/pf2_refinement_policy_20260624.json`

- PF2以上を目標。
- pre-2026 150件以上を基本。
- 各年プラス。
- 2025 PF1.8以上を推奨。
- 原則70%以上の件数を残す。
- DDを悪化させない。
- spread1.5xでもPF1.8以上、できれば2.0。
- filterが後期データで実際に発動すること。
- dormant filterはwatch。
- 単独特徴を削除せず、複合loss regionを除外する。
- 件数を減らすだけでPFを作らない。

## 10. 特徴量・探索視点

すでに使用・監査済み:

- EMA20/30/40、傾き、距離、alignment
- RCI9/14/18
- TORYS MACD EMA6/13 signal EMA4、SMA4別lineage
- ATR、ATR regime、normalized returns
- candle body、upper/lower wick、close location
- tick-volume ratios
- causal fast/slow ZigZag
- causal confirmed-pivot trendline
- pivot channel、regression channel、Donchian20/40/60
- Bollinger20/40/60、%B、width/ATR、trailing percentile、squeeze、release、band walk、reentry
- previous-day high/low
- server opening range
- efficiency ratio
- lag-1 autocorrelation
- session/time features
- path-shape sequences

次に強化する:

- MAE/MFE path meta-labeling
- time-to-TP/SL、stagnation duration
- level acceptance/rejection
- previous-week levels
- regime transition / HMM-like state persistence
- stable human-auditable path motifs
- independent SHORT candidates
- active候補間のoverlap、concentration、regime specialization

## 11. 候補の実装契約

候補ごとに必須:

1. 新しいimmutable candidate ID。
2. JSON configに次を固定。
   - parent ID
   - lane/timeframe
   - direction
   - event definition
   - exact feature formula
   - exact threshold full precision
   - label TP/SL/horizon
   - entry mode
   - spread handling
   - split policy
   - random seed/model parameters
3. future leakageを防ぐas-of join。
4. exact trade registry CSVを出力。
5. monthly/yearly metricsを出力。
6. SHA256 manifestを出力。
7. neighborhood、spread stress、year stabilityを記録。
8. 2026を見ずにfreezeしてからdiagnostic。
9. current lineageを上書きせず、変更時は別ID。

## 12. 機械学習の実装契約

MLはルール候補と同じくaudit可能にする。

### 入力

- decision時点までにclosedになったbarのみ。
- 価格絶対値よりATR正規化・rolling rankを優先。
- HTFはclose後as-of。
- sequence featureは固定長とmask/gap policyを明示。

### 学習

- train fitは2023のみ、または明示したwalk-forward foldのみ。
- scaler、encoder、clusterer、modelはtrainだけでfit。
- seedを固定し、複数seed安定性を検査。
- hyperparameter選択に2026を使わない。
- class probabilityだけでなく、coverage bucket別成績を保存。

### 出力

- prediction timestamp
- candidate/event ID
- score/probability
- selected threshold or coverage percentile
- label outcome/R
- feature-set version
- model/scaler hash
- input hash
- seed

### 採用条件

- 単一seedの好成績だけでは不可。
- feature attributionまたはcluster centroidを保存。
- opaque exclusionは、人間監査可能な特徴へ変換するまで注意付き候補。
- local replayでprediction/trade registryが完全一致すること。

## 13. ローカル再現パッケージの要件

ユーザーPCでは広域探索を行わない。十分に絞った候補だけを再現する。

必須物:

- one-click Windows BAT
- Python entrypoint
- exact candidate JSON
- dependency lock
- input SHA256 manifest
- model/scaler hash
- expected trade-registry hash
- expected metrics JSON
- comparison report
- failure時に差分を止めず出力するdiagnostic

local parityに合格するまで、正式candidate registryやportfolioへ入れない。

## 14. 研究上の重要な反省

- 少しプラスの候補を積み重ねと呼ばない。
- small sampleの高勝率を過大評価しない。
- 2026で良い下位条件を後から採用しない。
- neighborhoodの良さで弱いcentral ruleを救済しない。
- parentとderivativeを混同しない。
- 同じLONGの微調整だけで候補数を水増ししない。
- SHORT、時間帯、regime、path shapeなど独立した視点を優先する。
- exact registryの集計値をmanual summaryより優先する。

## 15. 次の作業

1. 6積み重ね候補のoverlap・相関・regime concentration監査。
2. PROV-020のsecond-stage filter fresh activation監視。
3. WATCH-014-Aのcentroid解析と人間可読path motif化。
4. MAE/MFE、到達時間、停滞時間を使ったPF2 refinement。
5. 独立SHORTの探索。
6. cutoff後データのprospective watch。
7. さらに絞った後、local replay package作成。

## 16. 次チャット開始用プロンプト

以下を新しいチャットにそのまま貼る。

```text
repo: knitanr-a11y/xauusd-signal-lab

GOLD_ML_V1の続きです。
最初に以下だけを読んで、そこから続けてください。

AGENTS.md
config/gold_ml_v1/current_state_snapshot_20260624.json
config/gold_ml_v1/provisional_candidate_stack_20260624.json
docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_20260624.md
docs/gold_ml_v1/GOLD_ML_V1_RESEARCH_AND_CANDIDATE_IMPLEMENTATION_PLAYBOOK_20260624.md

旧GOLD V3 / GOLD V2 / 旧GOLD / DISC8 / Stage41、および旧候補・旧モデル・旧特徴・旧出力は読まない、使わない、参照しない、比較しない、fallbackにしないでください。
許可された生ローソク足CSV以外の旧資産は禁止です。

現在はaudit-onlyです。
積み重ね候補は6本です:
GML1-PROV-007
GML1-PROV-008
GML1-PROV-010
GML1-PROV-015
GML1-PROV-020
GML1-WATCH-014-A

PF2以上を削り込み目標とし、件数・年別安定性・spread stress・fresh activationを同時に重視してください。
2026はdiagnosticのみで、閾値調整には使わないでください。
fresh prospective cutoffはMT5 server close 2026-06-23 18:15:00です。

次は、候補間overlap監査、PROV-020のfresh activation監視、WATCH-014-Aの可読化、MAE/MFE・到達時間・停滞時間によるPF2 refinement、独立SHORT探索から進めてください。
```
