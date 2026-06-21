# GOLD V3 Stage269 定義固定
## 2026 applicability audit + M15/M5 entry-resolution discovery

作成日: 2026-06-21
状態: `GOLD_V3_269_2026_APPLICABILITY_AND_M15_M5_ENTRY_RESOLUTION_DEFINITION_LOCKED_AUDIT_ONLY`

## 目的

Stage268の厳格セルが2026年単独でも両方向に通用しているかを確認し、維持された上位足regimeだけを土台にM15/M5をエントリー解像度として探索する。

短期足自体を新しい相場仮説にはしない。H1/H4が環境認識、M15/M5がentry timingである。

## 絶対契約

- audit-only。
- GOLD V2、旧GOLD、DISC8、Stage41を読まない。
- CSV各行は確定足、timeはOPEN時刻。
- M5はtime+5分、M15はtime+15分、H1はtime+1時間、H4はtime+4時間で利用可能。
- source_close_time <= decision/trigger timeのみ。
- 形成中M5/M15のhigh/low/closeを使わない。
- trigger成立は足確定時。entryはその確定後の同source最初のM1 open。
- maintenance中は失効させず最初の実在M1へ繰り越す。
- source跨ぎ禁止。
- 2026はStage268発見に使用済みのためclean holdoutとは呼ばない。
- 2025でentry triggerを比較し、2026をpseudo-period stressとして別集計する。
- SL/TP・portfolio・live promotionはまだ作らない。

## 2026 applicability対象regime

### R1_H1_WEAK_TREND_LOW_VOL
- H1 trend_state=WEAK_TREND
- H1 volatility_bucket=LOW
- direction=TIMEFRAME_TREND
- reference horizon=48 trading hours

### R2_H1_UTC08_11_HIGH_VOL
- H1 hour_bin=UTC08_11
- H1 volatility_bucket=HIGH
- direction=BAR_CONTINUATION
- reference horizons=48 and 72 trading hours

### R3_H1_INDECISION_RANGE
- H1 candle_state=INDECISION
- H1 trend_state=RANGE
- direction=BAR_CONTINUATION
- reference horizon=8 trading hours

### secondary H4 diagnostic only
- strong directional × conflict, 48h
- indecision × weak trend, 12h
- opposed alignment × healthy extension, 12h
- strong directional × weak trend, 8h

H4は2026件数が少ないため、M15/M5正式探索の主対象にしない。

## 2026 provisional applicability基準

regime全体:
- 2026 n>=60
- mean return >0
- median return >0
- LONG/SHORT各20件以上
- LONG/SHORT双方でmean >0
- LONG/SHORT双方でmedian >0
- 片方向positive rateが50%未満なら`WEAK_DIRECTION`を付ける

これはclean validationではなく`PROVISIONALLY_APPLICABLE_2026_CONTAMINATED`判定。

## M15/M5 entry trigger families

各H1 regime decision後、最大4取引時間までtriggerを探索する。

### T0_IMMEDIATE_BASELINE
- regime activation直後の最初のM1 open

### T1_EMA20_PULLBACK_RECLAIM
- entry timeframe EMA20へ方向逆側からtouch/cross
- 確定足closeがEMA20を方向側へ回復
- body/range>=0.35
- close locationが方向側>=0.60

### T2_THREE_BAR_BREAKOUT
- LONG: 確定足close > 直前3本high最大
- SHORT: 確定足close < 直前3本low最小

### T3_FALSE_BREAK_RECLAIM
- LONG: 確定足low < 直前3本low最小、closeはその最小値より上、close location>=0.60
- SHORTは反転

### T4_COMPRESSION_RELEASE
- 直前4本全体range <= 1.25 * entry timeframe ATR14
- 確定足closeが直前4本方向側境界をbreak

### T5_STRONG_MOMENTUM
- body/range>=0.65
- range/ATR14>=1.0
- close locationが方向側>=0.80

### T6_INSIDE_BAR_RELEASE
- 直前足がその1本前のinside bar
- 確定足closeがmother bar方向側境界をbreak

## entry availability

- M5 trigger_time = bar time + 5分
- M15 trigger_time = bar time + 15分
- entry_time = trigger_time以降の同source最初のM1
- entry_price = entry M1 open
- trigger windowはregime activation後4取引時間
- 同familyで複数trigger時は最初の1件
- trigger無しも全件台帳へ残す

## 評価

各regime × entry timeframe × triggerについて:

- eligible regime count
- triggered count / coverage
- median entry delay trading minutes
- decision-anchored reference endpointに対するentry price return
- entry-anchored 8/24/48/72h return・MFE・MAE
- immediate baselineとの差
- 2025 / 2026別
- LONG / SHORT別
- source×direction別
- entry price improvement versus T0

ATR正規化はregime decision H1 ATR14を使用する。

## researchable entry-resolution基準

- total triggered>=60
- 2026 triggered>=20
- trigger coverage>=25%
- 2025 mean/median return >0
- 2026 mean/median return >0
- LONG/SHORT各20件以上
- LONG/SHORT双方mean >0
- immediate baseline比で:
  - median return改善 >=0.10 ATR、または
  - median MAE改善 >=0.15 ATRかつmedian return悪化<=0.05 ATR
- top month share<=35%

基準通過でもstrategyとは呼ばず、`ENTRY_RESOLUTION_RESEARCH_LEAD`とする。

## 重要な禁止

- 2026で良かったtriggerだけを後付け採用しない
- M5/M15に独立trend filterを追加しない
- LONG only / SHORT only化しない
- triggerごとにSL/TPを最適化しない
- 4時間windowや閾値を結果後に変更しない

## 次段階

Stage270では通過したentry-resolution leadだけを対象に、entry後path timingとexit familyを別に設計する。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
