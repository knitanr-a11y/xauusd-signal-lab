# GOLD V3 Stage260 E8 定義固定
## 高tick activity下の吸収・拒否と反対方向受容

作成日: 2026-06-20  
状態: `GOLD_V3_260_E8_DEFINITION_AND_LIVE_STATE_MACHINE_CONTRACT_LOCKED_AUDIT_ONLY`

## 目的

高いbroker tick-count activityが発生しているにもかかわらず、価格実体が進まず、片側の長いヒゲとレンジ端からのclose-backが生じたM5を吸収・拒否anchorとする。その後、反対方向の価格受容が確定した場合だけ候補を作る。

E7のvolume継続閾値を微調整するのではなく、別の市場メカニズムとして固定する。

## live再現性

`GOLD_V3_STAGE260_LIVE_REPRODUCIBILITY_CONTRACT_LOCKED_AUDIT_ONLY`を必須適用する。

- batch detectorとstreaming state machineを別実装する。
- 性能を見る前にbatch/live、prefix、restart parityを確認する。
- 1件でも不一致なら性能評価を停止する。

## 1. 使用データ

- anchor・受容判定: 完了M5
- 上位ボラティリティ: decision_timeまでに完了したH1 ATR14
- 結果評価: entry_timeと同時刻に始まるM1 OPEN
- tick_volumeはM5確定値のみ
- real_volumeはM5/M15で全行0のため使用しない

## 2. 因果tick-volume基準

E7と同じsource-parity済み基準を変更せず使用する。

各M5のserver_slotを`hour*12 + minute/5`とする。

現在足を除いた過去だけで計算する。

- 同一server_slot直近60観測
- 最低20観測
- slot_median_volume
- slot_volume_ratio
- slot_volume_percentile
- 直近2,880本global_volume_percentile、最低1,000本

volume条件:

- `slot_volume_ratio >= 1.80`
- `slot_volume_percentile >= 0.90`
- `global_volume_percentile >= 0.85`

## 3. 吸収・拒否anchor

1本の完了M5で次をすべて満たす。

### 共通条件

- M5 true rangeが因果H1 ATR14の`0.10倍以上`
- M5 true rangeが現在足を除く直近288本TR中央値の`1.25倍以上`
- 実体比 `abs(close-open)/(high-low) <= 0.30`
- 片側wick比がM5レンジの`0.55以上`
- 優勢wickは反対側wickの`1.50倍以上`

### upper-wick absorption → SHORT

- `upper_wick / range >= 0.55`
- `upper_wick >= 1.50 * lower_wick`
- closeが高値からレンジの45%以上押し戻されている
- E8方向はSHORT

### lower-wick absorption → LONG

上下を反転する。

anchor確定時に次を固定し、その後変更しない。

- anchor_time
- anchor_open / high / low / close
- anchor_range
- anchor_midpoint
- anchor_h1_atr14
- tick_volume
- slot_median_volume
- slot_volume_ratio
- slot_volume_percentile
- global_volume_percentile
- body_ratio
- upper_wick_ratio
- lower_wick_ratio
- tr_ratio
- direction

同一足でupper/lowerの両条件を満たす場合は候補を作らない。

## 4. 反対方向受容

anchor後2本の完了M5、最大10分以内に最初の受容を探す。

### SHORT

- 受容前に確定終値が`anchor_high - 0.15 * anchor_range`以上へ戻った場合はINVALID。
- M5確定終値が`anchor_close - 0.03 * anchor_h1_atr14`以下。
- 確定終値が直前M5終値を下回る。
- 受容M5が陰線。

### LONG

上下を反転する。

同一M5でINVALIDと受容が成立する場合はINVALID優先。

2本以内に成立しなければEXPIRED。

## 5. entry

- decision_timeは受容M5の確定時刻。
- entry_time = decision_time。
- entry価格はentry_timeに始まるM1 OPEN。
- 同時刻M1がない場合はentry未成立。
- 次のM1、最寄りM1、M5 closeへのfallbackは禁止。

## 6. state machine

状態:

- `IDLE`
- `ABSORPTION_ACTIVE`
- `ACCEPTED`
- `INVALID`
- `EXPIRED`
- `GAP`

遷移:

- IDLE → ABSORPTION_ACTIVE: anchor確定
- ABSORPTION_ACTIVE → ACCEPTED: 2本以内の反対方向受容
- ABSORPTION_ACTIVE → INVALID: wick極値側上位15%へ終値復帰
- ABSORPTION_ACTIVE → EXPIRED: 2本経過
- ABSORPTION_ACTIVE → GAP: M5欠損

同方向stateが解決するまで同方向の新anchorを作らない。state解決足を新anchorとして再利用せず、次の完了M5から再判定する。

E8 entry後120分は全方向で新tradeを作らない。

candidate_keyは`E8|direction|anchor_time|decision_time`から決定的に生成する。

## 7. live parity必須列

- candidate_key
- event_type
- direction
- anchor_time
- decision_time
- entry_time
- entry_price_source_time
- state_version
- anchor_open / high / low / close
- anchor_h1_atr14
- tick_volume
- slot_median_volume
- slot_volume_ratio
- slot_volume_percentile
- global_volume_percentile
- body_ratio
- upper_wick_ratio
- lower_wick_ratio
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

- raw absorption anchor
- accepted event
- live-reproducible entry
- complete path
- batch/live parity
- prefix parity
- restart parity

## 9. matched control

絶対母集団の事前基準を通過した場合だけ実行する。

一致条件:

- 同じ曜日
- 同じMT5 hour
- 同じ方向
- 同じH1 ATR帯
- 同じH4 ATR帯
- 同じbody-ratio帯
- 同じwick-ratio帯
- 同じTR-ratio帯
- 同月、なければ同四半期、さらに不足時だけ90日以内

controlは同じ吸収形状と受容条件を満たすが、`slot_volume_ratio 0.80〜1.20`かつ`slot_volume_percentile 0.35〜0.65`の非volume-burst時点から選ぶ。

## 10. プラセボ

絶対母集団の事前基準を通過した場合だけ実行する。

- volume条件なしのshape-only absorption
- 1本前のtick_volumeを割り当てるvolume shift
- 同一server_slot内のtick_volumeランダム置換
- acceptanceなしのanchor-only
- direction reversal
- entry time +5 / +10分
- 診断用entry time -5分
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
9. 1〜8通過後、matched controlより120分MFEが2ドル以上大きく、MAEが1ドル超悪化しない。
10. 真のE8がshape-only、volume-shift、slot-random、random flagより良い。

1〜4のいずれかを失敗した場合はBLOCKED。5〜8のいずれかを失敗した場合は、matched control・placebo・追加特徴量へ進まず早期不採用とする。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
