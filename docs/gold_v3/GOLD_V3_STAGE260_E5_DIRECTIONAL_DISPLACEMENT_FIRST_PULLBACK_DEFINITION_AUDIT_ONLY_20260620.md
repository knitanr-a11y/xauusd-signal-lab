# GOLD V3 Stage260 E5 定義固定
## 一方向displacement後の初回浅押し・再受容

作成日: 2026-06-20  
状態: `GOLD_V3_260_E5_DEFINITION_AND_LIVE_STATE_MACHINE_CONTRACT_LOCKED_AUDIT_ONLY`

## 目的

静的価格帯の突破ではなく、実際に発生した高効率の一方向displacementをanchorとし、その後の最初の浅い押し戻りと元方向への再受容だけを候補とする。

方向は実際のdisplacement方向から決まり、年、月、レジームで固定しない。

## live再現性

`GOLD_V3_STAGE260_LIVE_REPRODUCIBILITY_CONTRACT_LOCKED_AUDIT_ONLY`を必須適用する。

E5は次の二実装を作る。

- batch detector: 全履歴監査用
- streaming state machine: 完了M15を1本ずつ受け取るlive-replay用

両者が完全一致しなければ、性能評価へ進まない。

## 1. displacement定義

完了M15を3本連続で使用する。3本のOPEN時刻は15分間隔で、週末・欠損を跨がない。

anchor decision_timeは3本目M15の確定時刻。

### LONG displacement

1. 3本の最初のOPENから3本目CLOSEまでの上昇幅が、anchor decision_timeで利用可能な因果H1 ATR14の`0.80倍以上`。
2. 方向効率 `abs(close3-open1) / sum(TR3本)` が`0.70以上`。
3. 3本中2本以上が陽線。
4. 3本目CLOSEが3本全体高安レンジの上位20%以内。
5. 直前8本の完了M15に、同方向・同等以上のdisplacement anchorがない。

SHORTは上下反転。

固定値:

- `anchor_start_price = 1本目OPEN`
- `anchor_end_price = 3本目CLOSE`
- `anchor_move = abs(anchor_end_price-anchor_start_price)`
- `direction`
- `anchor_atr14`
- `pullback_zone_near = 0.20 retracement`
- `pullback_zone_far = 0.50 retracement`
- `invalidation = 0.65 retracement`

これらはanchor完成時に固定し、その後のATR変化で動かさない。

## 2. 初回pullback

anchor後6本の完了M15、最大90分以内。

LONG:

- anchor_endから20%以上50%以下の押しを初めて付けたM15をfirst pullbackとする。
- 20%未満の小さな揺れはpullback未成立。
- first pullback前にヒゲを含む最大押しが50%を超えた場合、その最初の押しは浅押しではないため`INVALID_TOO_DEEP`。
- first pullback前に確定終値が65%超を押し戻した場合は`INVALID_CLOSE`。同一足ではこの判定を最優先する。
- first pullback前に90分経過した場合はEXPIRED。

SHORTは上下反転。

ヒゲでpullback zoneへ入った時点をfirst pullbackとするが、同じM15の確定終値が65% invalidationを越えた場合はINVALIDを優先する。

## 3. 再受容

first pullback M15を含め、その後3本以内、最大45分以内。

LONG:

- M15確定終値がanchor moveの上位20%領域へ戻る。
- 確定終値が直前M15終値を上回る。
- 再受容M15が陽線。
- 再受容前に65% invalidationを終値で越えた場合はINVALID。

SHORTは上下反転。

E5 decision_timeは再受容M15確定時刻。

- `entry_time = decision_time`
- entry価格は同時刻に始まるM1 OPEN
- M1欠落時はentryを作らない

## 4. state machine

状態:

- `IDLE`
- `ANCHOR_ACTIVE`
- `PULLBACK_SEEN`
- `REACCEPTED`
- `INVALID`
- `EXPIRED`

遷移:

- IDLE → ANCHOR_ACTIVE: displacement anchor確定
- ANCHOR_ACTIVE → PULLBACK_SEEN: first pullback成立
- ANCHOR_ACTIVE → INVALID: 65%終値invalidまたは50%超の深押し
- ANCHOR_ACTIVE → EXPIRED: 90分
- PULLBACK_SEEN → REACCEPTED: 45分以内の再受容
- PULLBACK_SEEN → INVALID: 65%終値invalid
- PULLBACK_SEEN → EXPIRED: 45分

同じM15でINVALIDとREACCEPTEDが両方成立する場合はINVALID優先。

## 5. 重複排除

- anchor確定後、同方向の新anchorは既存stateがINVALID/EXPIRED/REACCEPTEDになるまで作らない。
- 既存stateを解決した同一M15を新anchor確定足として再利用せず、次の完了M15から新anchor判定を再開する。
- LONGとSHORT stateは別管理するが、E5 entry後120分は全方向で新tradeを作らない。
- candidate_keyは`E5|direction|anchor_time|decision_time`から決定的に生成する。

## 6. matched control

E5完成イベント1件につき非復元で1件。

一致条件:

- 同じ曜日
- 同じMT5 hour
- 同じ方向
- 同じH1 ATR過去分位帯
- 同じH4 ATR過去分位帯
- 同じanchor_move/H1_ATR帯
- 同じefficiency帯
- 同月、なければ同四半期、さらに不足時だけ90日以内

controlは同等displacement anchorが存在するが、規定のfirst pullback＋再受容が成立していない時点から選ぶ。

正確なStage258レジームがない場合はproxyを作らない。

## 7. 評価

- horizon: 60 / 120 / 180 / 240分
- TP: 5 / 10 / 15 / 20 / 25ドル
- SL: 5 / 10 / 15ドル
- cost: 0 / 1 / 2 / 3 / 5ドル
- 同一M1 TP/SLはSL優先
- full-horizon MFE/MAE
- 月、四半期、半期、方向、MT5 hour、H1/H4 ATR帯

表示:

- raw anchor
- first pullback
- reaccepted event
- dedup120
- complete path
- batch/live parity
- prefix parity
- restart parity

## 8. プラセボ

- displacement-only
- pullback到達のみ、再受容なし
- 2回目以降のpullback
- efficiency条件なし
- anchor_move 0.60 ATR
- anchor_move 1.00 ATR
- direction reversal
- entry time +15 / +30分
- 診断用entry time -15分。未来方向を使うため昇格禁止
- 同件数random flag
- 曜日入れ替え

## 9. 事前採否基準

性能基準:

1. 120分MFEがmatched controlより2ドル以上大きい。
2. 120分MAEがcontrolより1ドル超悪化しない。
3. 全固定グリッド最大cost0期待値3ドル以上。
4. 2025H1 cost2最良セルが期待値プラスかつPF1.10以上。
5. 同じ固定セルが2025H2でも期待値プラスかつPF1.10以上。
6. 主要プラセボより良い。

live再現性基準:

7. batch / streaming候補完全一致。
8. prefix invariance PASS。
9. restart invariance PASS。
10. source_close_time違反、candidate_key重複、entry M1欠落の誤発火が0件。

1〜3または7〜10のいずれかを失敗した場合、追加特徴量で救済せず早期不採用またはBLOCKEDとする。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
