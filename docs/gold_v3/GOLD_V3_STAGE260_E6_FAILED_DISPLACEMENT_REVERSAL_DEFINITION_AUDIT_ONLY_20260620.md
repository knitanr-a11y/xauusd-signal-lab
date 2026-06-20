# GOLD V3 Stage260 E6 定義固定
## displacement継続失敗後の反対方向受容

作成日: 2026-06-20  
状態: `GOLD_V3_260_E6_DEFINITION_AND_LIVE_STATE_MACHINE_CONTRACT_LOCKED_AUDIT_ONLY`

## 目的

E5と同一の因果的displacement anchorを使用し、その継続が失敗した後、反対方向への価格受容が確定した場合だけ逆方向候補を作る。

深押しを見ただけではentryしない。失敗確定前の逆張り、将来方向の持ち込み、最良反転時刻の後付け選択は禁止する。

## live再現性

`GOLD_V3_STAGE260_LIVE_REPRODUCIBILITY_CONTRACT_LOCKED_AUDIT_ONLY`を必須適用する。

- batch detectorとstreaming state machineを別実装する。
- 性能を見る前にbatch/live、prefix、restart parityを確認する。
- 1件でも不一致があれば性能評価を停止する。

## 1. displacement anchor

E5で結果前に固定した定義を変更せず使用する。

完了M15を3本連続で使用し、3本目確定時点で次を満たす。

1. 3本の最初のOPENから3本目CLOSEまでの純移動が、因果H1 ATR14の0.80倍以上。
2. 方向効率 `abs(close3-open1) / sum(TR3本)` が0.70以上。
3. 3本中2本以上が同方向実体。
4. 3本目CLOSEが3本レンジ端20%以内。
5. 直前8本の完了M15に、同方向・同等以上のanchorがない。

anchor完成時に次を固定し、その後のATRで動かさない。

- anchor_start_price
- anchor_end_price
- anchor_move
- anchor_atr14
- original_direction
- midpoint = 50% retracement
- original_invalidation = 65% retracement
- reversal_acceptance = 80% retracement

## 2. 継続失敗

anchor後6本の完了M15、最大90分以内を監視する。

### 元LONG displacement

最初に次のいずれかを満たすM15をfailure barとする。

- intrabar lowが50% retracementを超え、かつ確定終値が50% retracement以下。
- 確定終値が65% retracement以下。

### 元SHORT displacement

上下を反転する。

優先順位:

1. GAP
2. 65% close invalidation
3. 50%超のdeep close failure
4. expiry

failure barの確定前には反対方向候補を作らない。

failure_type:

- `INVALID_CLOSE_65`
- `DEEP_CLOSE_50`

## 3. 反対方向受容

failure barを含め、その後3本以内、最大45分以内に最初の反対方向受容を探す。

### 元LONG → E6 SHORT

- M15確定終値が、anchor_start_priceから元LONG方向へ20%以内の領域まで戻る。これは元moveの80%以上の反転を意味する。
- 確定終値が直前M15終値を下回る。
- 受容M15が陰線。

### 元SHORT → E6 LONG

上下を反転する。

同じfailure barが80%反転領域まで確定し、反対方向実体・終値更新も満たす場合は、そのM15確定時点で受容成立としてよい。

受容前に元方向の上位20%領域へ確定終値で復帰した場合、E6は`ORIGINAL_DIRECTION_RECLAIMED`として無効。

## 4. entry

- E6 directionはoriginal directionの反対。
- decision_timeは反対方向受容M15の確定時刻。
- entry_time = decision_time。
- entry価格はentry_timeに始まるM1 OPEN。
- 同時刻M1が存在しない場合はentry未成立。次のM1や近い価格へfallbackしない。

## 5. state machine

方向ごとに次のstateを持つ。

- `IDLE`
- `ANCHOR_ACTIVE`
- `FAILURE_SEEN`
- `REVERSAL_ACCEPTED`
- `ORIGINAL_DIRECTION_RECLAIMED`
- `EXPIRED`
- `GAP`

遷移:

- IDLE → ANCHOR_ACTIVE: anchor確定
- ANCHOR_ACTIVE → FAILURE_SEEN: 50% deep closeまたは65% close invalidation
- ANCHOR_ACTIVE → EXPIRED: 90分
- ANCHOR_ACTIVE → GAP: M15欠損
- FAILURE_SEEN → REVERSAL_ACCEPTED: 45分以内の80%反転受容
- FAILURE_SEEN → ORIGINAL_DIRECTION_RECLAIMED: 元方向上位20%へ終値復帰
- FAILURE_SEEN → EXPIRED: 45分
- FAILURE_SEEN → GAP: M15欠損

同一M15の判定優先順位:

1. GAP
2. 反対方向受容
3. 元方向reclaim
4. expiry

## 6. 重複排除

- 同方向anchor stateが解決するまで、同方向の新anchorを作らない。
- stateを解決した同一M15を新anchor確定足として再利用しない。
- E6 entry後120分は、元anchor方向・反対方向を問わず新しいtradeを作らない。
- candidate_keyは`E6|reversal_direction|anchor_time|decision_time`から決定的に生成する。

## 7. live parity必須列

- candidate_key
- event_type
- direction
- original_direction
- anchor_time
- failure_time
- decision_time
- entry_time
- entry_price_source_time
- state_version
- anchor_start_price
- anchor_end_price
- anchor_move
- anchor_atr14
- efficiency
- failure_type

batchとstreamingで完全一致しなければBLOCKED。

## 8. matched control

絶対母集団の事前基準を通過した場合だけ実行する。

E6完成イベント1件につき非復元で1件。

一致条件:

- 同じ曜日
- 同じMT5 hour
- 同じE6方向
- 同じH1 ATR過去分位帯
- 同じH4 ATR過去分位帯
- 同じanchor_move/H1 ATR帯
- 同じefficiency帯
- 同じfailure_type
- 同月、なければ同四半期、さらに不足時だけ90日以内

controlは同等anchorとfailureが存在するが、規定の80%反転受容が成立していない時点から選ぶ。

## 9. 評価

- horizon: 60 / 120 / 180 / 240分
- TP: 5 / 10 / 15 / 20 / 25ドル
- SL: 5 / 10 / 15ドル
- cost: 0 / 1 / 2 / 3 / 5ドル
- 同一M1 TP/SLはSL優先
- full-horizon MFE/MAE
- 月、四半期、半期、方向、original direction、failure type、MT5 hour、H1/H4 ATR帯

表示:

- raw anchor
- failure seen
- reversal accepted
- live-reproducible entry
- complete path
- batch/live parity
- prefix parity
- restart parity

## 10. プラセボ

絶対母集団の事前基準を通過した場合だけ実行する。

- failure時点entry、80%受容なし
- 50%ではなく40% failure
- 65% close invalidationだけ
- direction reversal
- entry time +15 / +30分
- 診断用entry time -15分。未来受容方向を使うため昇格禁止
- 同件数random flag
- 曜日入れ替え

## 11. 事前採否基準

live再現性:

1. batch / streaming候補完全一致。
2. prefix invariance PASS。
3. restart invariance PASS。
4. source_close_time違反、candidate_key重複、entry M1欠落の誤発火が0件。

性能:

5. 全固定グリッド最大cost0期待値3.0ドル以上。
6. 2025H1 cost2最良セルが期待値プラスかつPF1.10以上。
7. 同じ固定セルが2025H2でも期待値プラスかつPF1.10以上。
8. 固定2026で期待値プラスを維持する。
9. 1〜4を通過後、matched controlより120分MFEが2ドル以上大きく、MAEが1ドル超悪化しない。
10. 主要プラセボより良い。

1〜4のいずれかを失敗した場合はBLOCKED。5〜8のいずれかを失敗した場合は、matched control・placebo・追加特徴量へ進まず早期不採用とする。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
