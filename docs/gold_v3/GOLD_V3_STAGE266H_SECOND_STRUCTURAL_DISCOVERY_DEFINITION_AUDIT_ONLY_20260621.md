# GOLD V3 Stage266H 定義固定
## Second structural discovery: sweeps, retests, mother bars, early trend

作成日: 2026-06-21  
状態: `GOLD_V3_266H_SECOND_STRUCTURAL_DISCOVERY_DEFINITION_LOCKED_AUDIT_ONLY`

## 目的

Stage266F/Gで見えたF12 H1 sweep-reclaimの改善可能性、F9 mother-barの少数良好結果、C1と異なる構造を手掛かりに、第二候補群を事前固定して探索する。既存候補のparameter微調整ではなく、setup構造を分離する。

## 絶対契約

- audit-only。
- CSV行は確定足、timeはOPEN時刻。
- M1=time+1分、H1=time+1時間、H4=time+4時間、D1=time+1日から利用。
- source_close_time <= decision_timeのみ。
- M1は事前pending stopの執行だけ。
- raw/rejected/suppressedを全件保存。
- LONG only、SHORT only、年別filter禁止。
- 2025/2026はdiscovery期間でありlive validationではない。
- C1 frozen componentは変更しない。

## 共通execution

H4 family: pending4時間、SL1.25ATR、TP2.5ATR、最大8時間。
H1 family: pending1時間、SL1.0ATR、TP2.0ATR、最大6時間。
同一M1はSL優先。UTC20:00越えfillはblock。

## H1 families

### G1_H1_SWEEP_STRONG_CLOSE
F12構造に加え、sweep後の完了H1が方向側close location>=0.70、body/range>=0.45。stop=最新H1高安。

### G2_H1_SWEEP_LOW_VOL
F12構造に加え、H1 ATR percentile100<=0.55、H4 ATR percentile100<=0.70。stop=最新H1高安。

### G3_H1_MOTHER_BAR
最新H1がinside bar。母足は方向側body、close location>=0.65、range<=1.75ATR。stop=母足高安。

### G4_H1_ENGULFING_CONT
trend方向と逆色の前H1を、最新H1方向側bodyが実体でengulfし、close location>=0.70。stop=最新H1高安。

### G5_H1_THREE_BAR_BASE
直近3本全体range<=1.20ATR、平均overlap>=0.60、最新H1 volume ratio>=0.80。stop=3本高安。

### G10_H1_DAILY_LEVEL_RECLAIM
D1/H4 trend方向と逆側の前日高安を最新H1がsweepし、水準内へreclaimして方向側close。stop=最新H1高安。

## H4 families

### G6_H4_BREAKOUT_RETEST
前1〜2本のH4で、当時の直前6本channelを方向側へclose breakout。その後最新H4がbreakout水準へretestし、水準を維持して方向側close。stop=最新H4高安。

### G7_H4_FIRST_PULLBACK_AFTER_CROSS
H4 EMA20/EMA50 crossが直近3本以内。D1方向一致。最新H4がEMA20へpullbackし、方向側close location>=0.65。stop=最新H4高安。

### G8_H4_MOTHER_BAR_WIDE
最新H4がinside bar。母足は方向側body、close location>=0.65、range<=2.0ATR。stop=母足高安。

### G9_H4_DAILY_LEVEL_RECLAIM
D1/H4 trend方向と逆側の前日高安を最新H4がsweepし、水準内へreclaimして方向側close。stop=最新H4高安。

## 評価

- independent M1 outcomes
- raw source/direction/month stability
- C1 overlap
- family-specific monthly OOF gate
- raw30件以上はStage266Gのnonlinear model benchmarkも適用

## component合格基準

Stage266F/Gと同じ:
- accepted25件以上
- retention35〜85%
- cost2勝率>=60%、raw比+5pp
- cost5勝率>=55%、expectancy>0、PF>=1.25
- 2025/2026両sourceプラス
- LONG/SHORT各10件以上かつプラス
- top5 share<=60%
- C1 overlap<=70%

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
