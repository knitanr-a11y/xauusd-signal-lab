# GOLD V3 Stage260 E7 定義固定
## 因果的tick-volumeインパルス＋価格受容

作成日: 2026-06-20  
状態: `GOLD_V3_260_E7_DEFINITION_AND_LIVE_STATE_MACHINE_CONTRACT_LOCKED_AUDIT_ONLY`

## 目的

OHLC構造だけでは分離できなかった「注文活動の急増」を、M5のtick_volumeをbroker tick-count proxyとして因果的に使用し、価格インパルスと直後の受容が通常時点より強いか監査する。

tick_volumeを実出来高とは呼ばない。E7対象のM5/M15ではreal_volumeが全行0のため使用しない。

## live再現性

`GOLD_V3_STAGE260_LIVE_REPRODUCIBILITY_CONTRACT_LOCKED_AUDIT_ONLY`を必須適用する。

- batch detectorとstreaming state machineを別実装する。
- 性能を見る前にbatch/live、prefix、restart parityを確認する。
- 1件でも不一致なら性能評価を停止する。

## 1. 使用データ

- イベント判定: 完了M5
- 上位ボラティリティ: decision_timeまでに完了したH1 ATR14
- 結果評価: entry_timeと同時刻に始まるM1 OPEN
- tick_volumeとspreadはM5の確定値のみ

source parityは、gold# / goldsharpのM5完全重複58,092本でtick_volume差0、spread差0を必須前提とする。

## 2. 因果tick-volume基準

M5 OPEN時刻の`hour*12 + minute/5`をserver_slotとする。

各M5確定時点で、現在足を除いた過去の同一server_slotだけを使用する。

- 参照本数: 直近60観測
- 最低履歴: 20観測
- `slot_median_volume`: 過去同一slotの中央値
- `slot_volume_ratio = current_tick_volume / slot_median_volume`
- `slot_volume_percentile`: 過去同一slotに対する現在値の因果分位

さらに、現在足を除いた直近2,880本の完了M5を使用する。

- 最低履歴: 1,000本
- `global_volume_percentile`: 直近2,880本に対する因果分位

現在足を基準分布へ先入れしない。

## 3. volume-price impulse anchor

1本の完了M5で次をすべて満たす。

### volume条件

- `slot_volume_ratio >= 1.80`
- `slot_volume_percentile >= 0.90`
- `global_volume_percentile >= 0.85`

### price条件

- M5実体絶対値が因果H1 ATR14の`0.12倍以上`
- 実体比 `abs(close-open)/(high-low) >= 0.65`
- true rangeが、現在足を除く直近288本M5 true range中央値の`1.50倍以上`
- LONGは陽線かつ終値がM5レンジ上位15%以内
- SHORTは陰線かつ終値がM5レンジ下位15%以内

方向は当該M5実体方向から決める。年・月・レジームで固定しない。

anchor確定時に次を固定し、その後に変更しない。

- anchor_time
- anchor_open / high / low / close
- anchor_midpoint
- anchor_h1_atr14
- slot_median_volume
- slot_volume_ratio
- slot_volume_percentile
- global_volume_percentile
- body_ratio
- tr_ratio
- direction

## 4. 価格受容

anchor後2本の完了M5、最大10分以内に最初の受容を探す。

### LONG

- 受容前に確定終値がanchor midpoint以下になった場合はINVALID。
- M5確定終値が`anchor_close + 0.03 * anchor_h1_atr14`以上。
- 確定終値が直前M5終値を上回る。
- 受容M5が陽線。

### SHORT

上下を反転する。

同一M5でINVALIDと受容が成立する場合はINVALID優先。

2本以内に成立しなければEXPIRED。

## 5. entry

- decision_timeは受容M5の確定時刻。
- entry_time = decision_time。
- entry価格はentry_timeに始まるM1 OPEN。
- 同時刻M1がない場合はentry未成立。次のM1や近い価格へfallbackしない。

## 6. state machine

状態:

- `IDLE`
- `IMPULSE_ACTIVE`
- `ACCEPTED`
- `INVALID`
- `EXPIRED`
- `GAP`

遷移:

- IDLE → IMPULSE_ACTIVE: volume-price impulse確定
- IMPULSE_ACTIVE → ACCEPTED: 2本以内の価格受容
- IMPULSE_ACTIVE → INVALID: midpoint反対側へ終値確定
- IMPULSE_ACTIVE → EXPIRED: 2本経過
- IMPULSE_ACTIVE → GAP: M5欠損

同方向stateが解決するまで同方向の新anchorを作らない。state解決足を新anchorとして再利用せず、次の完了M5から再判定する。

E7 entry後120分は全方向で新tradeを作らない。

candidate_keyは`E7|direction|anchor_time|decision_time`から決定的に生成する。

## 7. live parity必須列

- candidate_key
- event_type
- direction
- anchor_time
- decision_time
- entry_time
- entry_price_source_time
- state_version
- anchor_open
- anchor_close
- anchor_h1_atr14
- tick_volume
- slot_median_volume
- slot_volume_ratio
- slot_volume_percentile
- global_volume_percentile
- body_ratio
- tr_ratio

batchとstreamingで完全一致しなければBLOCKED。

## 8. 絶対母集団評価

- horizon: 60 / 120 / 180 / 240分
- TP: 5 / 10 / 15 / 20 / 25ドル
- SL: 5 / 10 / 15ドル
- cost: 0 / 1 / 2 / 3 / 5ドル
- 同一M1 TP/SLはSL優先
- full-horizon MFE/MAE
- 月、四半期、半期、方向、MT5 hour、H1/H4 ATR帯、volume-ratio帯

表示:

- raw volume-price impulse
- accepted event
- live-reproducible entry
- complete path
- batch/live parity
- prefix parity
- restart parity

## 9. matched control

絶対母集団の事前基準を通過した場合だけ実行する。

E7完成イベント1件につき非復元で1件。

一致条件:

- 同じ曜日
- 同じMT5 hour
- 同じ方向
- 同じH1 ATR過去分位帯
- 同じH4 ATR過去分位帯
- 同じbody-ratio帯
- 同じTR-ratio帯
- 同月、なければ同四半期、さらに不足時だけ90日以内

controlは価格条件と受容条件は同等だが、`slot_volume_ratio 0.80〜1.20`かつ`slot_volume_percentile 0.35〜0.65`の非volume-burst時点から選ぶ。

## 10. プラセボ

絶対母集団の事前基準を通過した場合だけ実行する。

- volume条件なしのprice-only impulse
- 現在barではなく1本前のtick_volumeを割り当てるvolume shift
- 同一server_slot内のtick_volumeランダム置換
- acceptanceなしのimpulse-only
- direction reversal
- entry time +5 / +10分
- 診断用entry time -5分。未来受容方向を使うため昇格禁止
- 同件数random event flag
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
9. 1〜8を通過後、matched controlより120分MFEが2ドル以上大きく、MAEが1ドル超悪化しない。
10. 真のE7がprice-only、volume-shift、slot-random、random flagの主要プラセボより良い。

1〜4のいずれかを失敗した場合はBLOCKED。5〜8のいずれかを失敗した場合は、matched control・placebo・追加特徴量へ進まず早期不採用とする。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
