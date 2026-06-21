# GOLD V3 Stage272 定義固定
## R2 exit, horizon and path-management audit

作成日: 2026-06-21
状態: `GOLD_V3_272_R2_EXIT_HORIZON_AND_PATH_MANAGEMENT_DEFINITION_LOCKED_AUDIT_ONLY`

## 目的

Stage271で現在最も維持されたR2について、entry条件を固定したまま、Delayed・Persistent・Fade・Early-failを利益へ変換できるexit/horizon/path-managementを比較する。

新しいentry trigger、entry gate、方向filterは作らない。

## R2固定条件

- H1 decision hour-bin = UTC08_11
- H1 volatility bucket = HIGH
- direction = 完了H1足方向（BAR_CONTINUATION）
- entry = Stage267/268 activation timeの同source最初のM1 open
- H1 ATR14 = decision時点値

## 絶対契約

- audit-only。
- GOLD V2、旧GOLD、DISC8、Stage41を読まない。
- CSV各行は確定足、timeはOPEN時刻。
- entry以降のM1/H1のみをexit判定へ使用。
- H1構造exitはH1確定後、次の実在M1 openで約定。
- M1 level hitは同一M1で複数条件成立時、保守的にstop/利益返却側を優先。
- source跨ぎ禁止。
- 2025、2026、2026 latest60、LONG/SHORTを必ず分離。
- 最良単一設定だけでなく隣接設定のrobustnessを評価。
- live promotion禁止。

## 固定baseline

- FIXED_24H
- FIXED_48H
- FIXED_72H

horizonは実在M1行数ベースの取引時間。

## 固定loss-limited families

各horizon 48h / 72hについて:

- SL_1.0_ATR
- SL_1.5_ATR
- SL_2.0_ATR

stop level:
- LONG entry - k*H1_ATR14
- SHORT entry + k*H1_ATR14

## 固定H1 structure exits

### H1_EMA20_INVALIDATION

- LONG: 確定H1 close < EMA20
- SHORT: 確定H1 close > EMA20
- entry後最低2本のH1が完了してから有効
- cap 72h

### H1_THREE_BAR_STRUCTURE_BREAK

- LONG: 確定H1 close < 直前3本H1 lowの最小
- SHORT: 確定H1 close > 直前3本H1 highの最大
- cap 72h

### H1_TWO_ADVERSE_CLOSES

- LONG: 2本連続陰線
- SHORT: 2本連続陽線
- cap 72h

## 固定profit-management families

### PARTIAL_1ATR_RUNNER_48H / 72H

- +1.0 ATR到達で50%利確
- 残り50%は48hまたは72h固定exit
- initial SLは1.5 ATR
- 同一M1でTP1とSL成立時はSL優先

### PARTIAL_1ATR_STRUCTURE_RUNNER

- +1.0 ATRで50%利確
- 残り50%はH1_THREE_BAR_STRUCTURE_BREAKまたは72h cap
- initial SL 1.5 ATR

### BREAKEVEN_AFTER_1ATR_48H / 72H

- initial SL 1.5 ATR
- MFE +1.0 ATR到達後、stopをentryへ移動
- cap 48h / 72h

### TRAIL_AFTER_1ATR

- initial SL 1.5 ATR
- MFE +1.0 ATR到達後、peakから0.75 ATR返却で全exit
- cap 72h

### TRAIL_AFTER_1_5ATR

- initial SL 1.5 ATR
- MFE +1.5 ATR到達後、peakから1.0 ATR返却で全exit
- cap 72h

## 固定path-state families

### HOLD_DELAYED_UNLESS_STRUCTURE_BREAK

- 8h returnが負でも、H1_THREE_BAR_STRUCTURE_BREAK未発生なら48hまで保有
- structure break発生ならその時点でexit

### PROTECT_FADE_AFTER_1ATR

- +1.0 ATR到達後、H1 closeがentry方向と逆で、かつ含み益が+0.25 ATR未満へ低下したら次M1 openでexit
- cap 48h

## transaction-cost stress

gross USD/ozに対して:

- COST_0
- COST_2_USD
- COST_5_USD

を出す。bid/ask exact executionとは呼ばない。

## 出力

各exit familyについて:

- n
- win rate
- mean/median gross ATR return
- mean/median USD return
- cost2/cost5 expectancy
- profit factor
- median holding trading hours
- median MAE/MFE
- max loss / q10
- 2025 / 2026 / latest60
- LONG / SHORT
- year×direction
- path class別成績
- monthly trade count / expectancy
- baseline FIXED_48Hとの差

## strong exit-management lead基準

- total n>=250
- 2025・2026・latest60のcost2 expectancy >0
- LONG/SHORT双方cost2 expectancy >0
- 2025×LONG、2025×SHORT、2026×LONG、2026×SHORTの4区分でmean gross ATR>=0
- cost5 expectancy >0
- PF cost2 >=1.20
- median MAEがFIXED_48Hより改善、またはcost2 expectancyが+0.20 ATR相当以上改善
- 隣接設定でもcost2 expectancyが正
- top5 profit share<=55%
- latest60 n>=25

合格しても`EXIT_MANAGEMENT_RESEARCH_LEAD`でありlive-readyではない。

## 次段階

- leadあり: Stage273でcandidate overlap、portfolio suppression、exact spread/slippage stress
- leadなし: R2をpath edgeとして保管し、追加データまで売買戦略化を停止

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
