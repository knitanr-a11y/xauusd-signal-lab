# GOLD_ML_V1 未実施・未完了研究インベントリ

更新日: 2026-06-24

この文書は、チャット移行時に「何を既に実施したか」「何が未実施か」「何を優先すべきか」を取り違えないための正本である。

## 1. 引き継ぎ整合確認

以下の正本を突き合わせ、内容が一致していることを確認した。

- `AGENTS.md`
- `config/gold_ml_v1/current_state_snapshot_20260624.json`
- `config/gold_ml_v1/provisional_candidate_stack_20260624.json`
- `docs/gold_ml_v1/NEXT_CHAT_HANDOFF_GOLD_ML_V1_20260624.md`
- `docs/gold_ml_v1/GOLD_ML_V1_RESEARCH_AND_CANDIDATE_IMPLEMENTATION_PLAYBOOK_20260624.md`

確認済み一致事項:

- audit-only
- 旧GOLD資産の利用禁止と生CSVだけの例外
- MT5 server time / bar-close availability
- 2026はdiagnostic専用
- fresh prospective cutoffは `2026-06-23 18:15:00`
- 積み重ね候補は6本
- PF2以上をrefinement targetにする
- low-count候補は監視継続
- local replayとfresh prospective確認前に正式登録しない

## 2. 現在の積み重ね候補

- `GML1-PROV-007`
- `GML1-PROV-008`
- `GML1-PROV-010`
- `GML1-PROV-015`
- `GML1-PROV-020`
- `GML1-WATCH-014-A`

重要:

- `PROV-007`と`PROV-008`は同じparent `PROV-002`の派生であり、独立edgeを2本得たと単純に数えない。
- `PROV-010`、`PROV-015`、`PROV-020`も親子lineageであり、重複監査が必須。
- `WATCH-014-A`も`PROV-015`のentry母集団を形状クラスタで削る派生研究候補。
- 現在6本だが、独立した市場edge数はまだ未確定。

## 3. ユーザーが強く求めている方向

1. GOLDの潜在的な値動き量に見合う十分な件数。
2. PF2以上。可能ならさらに上。
3. 件数を極端に落として見かけのPFを作らない。
4. 勝ち負け特徴を比較し、負け側に集中する複合状態を削る。
5. low-countでも構造的に有望なら捨てず監視する。
6. LONGだけへ偏らず、強いSHORT候補を作る。
7. EMA、RCI、MACDだけでなく、トレンドライン、チャネル、ボリンジャー、価格帯、時間帯、出来高、経路形状など別視点を使う。
8. 機械学習を使う場合も、再現性・因果性・説明可能性を残す。
9. ユーザーPCでは重い広域探索を行わず、絞った候補のexact replayだけを依頼する。
10. 少しプラス、PF1.1程度、小標本だけで候補追加しない。

## 4. 既に実施した探索

### 4.1 ルール・構造

- EMA20/30/40 alignment、距離、傾き
- RCI9/14/18
- TORYS MACD
- ATR regime、normalized return
- candle body、wick、close location
- tick-volume ratio
- causal ZigZag
- confirmed-pivot trendline
- trendline break / retestの初期探索
- pivot channel
- regression channel
- Donchian20/40/60
- Bollinger20/40/60
- squeeze、release、band walk、reentry
- previous-day high/lowの単純break/sweep
- server opening range
- session/time features
- efficiency ratio
- lag-1 autocorrelation

### 4.2 負け領域削除

- H4伸び切り＋上ヒゲ拒否
- M15 Bollinger低帯域圧縮
- D1 low participation＋3日進捗不足
- server hour＋高spread/ATR

### 4.3 機械学習・統計

- basic shallow tree / loss leaf
- regularized score selectionの初期検査
- LightGBM系の初期screen
- entry前12本H1 path-shape KMeans
- multiple seedの初期安定性検査

### 4.4 別視点

- opening range
- volume impulse / climaxの初期検査
- efficiency transition
- autocorrelation mean reversion
- path-shape clustering

## 5. 最優先で未実施・未完了の項目

### P0-1: 6候補の重複・独立性監査

未実施。

必須出力:

- exact same entry overlap
- ±1 decision-bar overlap
- Jaccard matrix
- parent/derivative retention relation
- concurrent exposure
- monthly R correlation
- year/quarter/session/regime concentration
- 実質的な独立edge数

目的:

候補6本をそのまま6つの独立優位性と誤認しない。次の探索は、既存候補が弱い相場状態を埋める方向へ向ける。

### P0-2: PROV-020のfresh filter activation監視

未完了。

第二段除外条件は2026で0回しか発動していない。

必須:

- cutoff後のraw base signal
- second-stage exclusion activation log
- excluded tradeの仮想結果
- activation数
- parent PROV-015との差分
- 10件単位の更新

新規activationがない限り、PF2改善のfresh evidenceとはみなさない。

### P0-3: WATCH-014-Aの可読化とseed安定化

未完了。

必須:

- 各cluster centroid
- 各特徴の平均との差
- representative sequences
- excluded cluster共通motif
- seed間cluster matching
- seedを変えても同じmotifがloss-proneか
- motifを人間可読な固定ルールへ変換できるか

候補例:

- 高値更新後の失速
- 連続上昇後のrange縮小
- 上下反転が多いchop
- spread上昇を伴う停滞
- 大陽線後に進捗が止まる形

### P0-4: local replay package

未実施。

6候補全部ではなく、まず以下を優先する。

1. `PROV-015`
2. `PROV-020`
3. `WATCH-014-A`
4. `PROV-007`
5. `PROV-008`
6. `PROV-010`

必須:

- one-click BAT
- exact Python entrypoint
- candidate JSON
- dependency lock
- input hash
- model/scaler/clusterer hash
- expected trade registry hash
- expected metrics
- parity report

### P0-5: cutoff後prospective runtime

未実施または未完成。

新GOLD_ML_V1専用で作る。

出力:

- raw event registry
- selected registry
- watch registry
- filter activation registry
- no-signal health
- data freshness
- last closed bar times

旧runtime資産を流用しない。

## 6. 高優先度の新規探索

### P1-1: 独立SHORT候補

最重要未達。

既存SHORT探索は弱く、PF2候補に届いていない。

探索視点:

- previous-day/week high sweep rejection SHORT
- failed upside breakout
- upper channel acceptance failure
- BB upper walk exhaustion after volume climax
- trendline break downward after lower-high confirmation
- high-volatility downside continuation
- lower-timeframe retest after H4/D1 bearish regime transition
- server opening-range high false break
- NY/US-hours reversal versus continuationを別lineage

条件:

- LONG条件の単純反転だけにしない。
- SHORT固有のspread/ask exitを正確に使う。
- 1R、1.5R、2Rを別lineage。

### P1-2: MAE/MFE meta-labeling

未実施。

全base tradeに以下を付ける。

- MAE_R
- MFE_R
- time_to_MFE
- time_to_TP
- time_to_SL
- bars_underwater
- bars_above_0.5R
- stagnation_bars
- first impulse direction

目的:

- 早く伸びるtradeだけを選ぶ
- 停滞してから負けるtradeを除く
- entry後管理ではなく、entry時点特徴との関連を学習する
- future情報をentry featureへ混ぜない

### P1-3: 到達時間・survival/hazard

未実施。

- TP到達hazard
- SL到達hazard
- 時間経過による期待R低下
- horizon別のedge decay
- 3h / 6h / 12h / 24h / 48h

将来、timeout policy候補を作るが、現在の候補を上書きせず別label lineageにする。

### P1-4: stable regime transition

未実施。

特徴:

- ATR regime
- efficiency ratio
- autocorrelation
- spread state
- tick-volume state
- Bollinger width percentile
- trend slope
- session

手法:

- deterministic clustering
- HMM-like state transition
- transition probability
- state duration

必須:

- multiple seed
- state signature matching
- 2023 fit
- 2024/2025 confirmation
- 2026はdiagnosticのみ

### P1-5: 価格帯のacceptance/rejection

一部のみ実施。未完成。

未実施重点:

- previous-week high/low
- previous-month high/low
- weekly open
- daily open
- opening-range high/low retest
- level突破後のN本滞在
- level下へ即復帰
- volume/spreadを伴うacceptance
- wickだけのsweepとbody close突破の分離

### P1-6: M1/M5の高件数探索

未完成。

- M1はメモリ負荷のため広域探索未完了。
- chunked feature buildが必要。
- M5も一部イベントだけで、十分な別視点探索は未完了。

実装:

- calendar chunk
- rolling warmup overlap
- feature state handoff
- chunk boundary parity test
- M1 label evaluatorのvectorization

## 7. 中優先度の探索

### P2-1: label familyの体系探索

未完成。

現在は候補ごとに1R、1.5R、2Rを一部試しただけ。

体系化:

- TP: 1.0R / 1.25R / 1.5R / 2.0R / 2.5R
- SL: 0.75ATR / 1.0ATR / 1.25ATR
- horizon: laneごとに複数

全組合せを無差別探索せず、early dataでfamilyをfreezeする。

### P2-2: walk-forward ML

初期screenのみで未完成。

- fold別fit
- fold別scaler
- worst-fold PF
- coverage bucket
- calibration
- expected R regression
- loss-risk classification
- seed stability

単一full-period modelの結果だけで候補化しない。

### P2-3: path modelの別方式

未実施。

- shapelet-like distance
- symbolic sequence
- DTW prototype
- small 1D CNN
- GRU/LSTMの小型モデル
- temporal convolution

まず解釈可能なprototype/shapeletを優先する。

### P2-4: cross-candidate specialization model

未実施。

候補を混ぜて1つのsignalにするのではなく、

- どのregimeでどの候補が強いか
- 同時発火時の優先順位
- parent/derivativeの重複処理
- opposite-direction conflict

をaudit-onlyで調べる。

### P2-5: robustness audit

一部未実施。

- monthly/quarterly breakdown
- sequential losing streak
- bootstrap confidence interval
- block bootstrap
- parameter perturbation
- spread 2.0x
- fixed slippage
- missing M1 stress
- point metadata確定
- broker-symbol specification確認

## 8. まだ着手しないもの

次は研究できるが、現段階でlive実装しない。

- position sizing optimization
- portfolio capital allocation
- automatic candidate promotion
- live MT5 orders
- Discord
- partial close
- trailing stop
- martingale/grid

これらは候補のlocal parityとfresh prospective evidence後。

## 9. 次チャットでの推奨実行順

1. 5正本を読む。
2. この未実施インベントリを読む。
3. 6候補のoverlap matrixを作る。
4. PROV-020 fresh activation monitorの仕様を作る。
5. WATCH-014-A centroid/seed解析を行う。
6. MAE/MFE registryを6候補または親base poolへ付与する。
7. 独立SHORT探索を並行開始する。
8. 結果がPF2・件数・年別安定性を満たす場合だけ積み重ね候補へ提案する。
9. 十分に絞れた候補からlocal replay packageを作る。

## 10. 引き継ぎ完了判定

次チャットで以下を説明できれば引き継ぎ成功。

- なぜ6本だが独立edgeは6とは限らないか
- PROV-020の注意点
- WATCH-014-Aの注意点
- 2026を再調整に使えない理由
- PF2を件数削減だけで作ってはいけない理由
- exact M1 execution contract
- 次にoverlap、fresh activation、centroid、MAE/MFE、SHORTを行うこと

この内容を説明できない場合、探索を始めず正本を読み直す。
