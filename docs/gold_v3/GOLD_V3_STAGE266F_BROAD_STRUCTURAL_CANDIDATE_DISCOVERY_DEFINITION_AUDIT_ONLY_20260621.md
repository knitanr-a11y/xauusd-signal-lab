# GOLD V3 Stage266F 定義固定
## Broad structural candidate discovery

作成日: 2026-06-21  
状態: `GOLD_V3_266F_BROAD_STRUCTURAL_CANDIDATE_DISCOVERY_DEFINITION_LOCKED_AUDIT_ONLY`

## 目的

C1以外の収益componentを見つけるため、単なるchannel期間違いではなく、構造の異なる候補群を一括探索する。候補単体のraw品質、負け分離可能性、C1との重複、stack後の実現頻度を比較する。

## 絶対契約

- audit-only。
- CSV各行は確定足、timeはOPEN時刻。
- M1=time+1分、H1=time+1時間、H4=time+4時間、D1=time+1日から利用。
- source_close_time <= decision_timeのみ。
- 形成中足の最終OHLCを使わない。
- M1は事前pending stopのgap/touchとexit順序だけに使う。
- raw candidate、expired、rejected、suppressedを全件保存。
- 個別負けtradeの手動削除禁止。
- LONG only、SHORT only、年別除外禁止。
- 2025/2026は既知期間。結果はdiscovery rankingでありlive validationではない。
- C1のfeature・gate・判定は変更しない。

## 共通execution

### H4 entry families

- decision_time=H4 time+4時間
- decision hours UTC 00,04,08
- pending expiry 4時間
- M1 gap/touch fill
- SL=1.25 H4 ATR14
- TP=2.5 H4 ATR14
- max hold=8時間
- UTC20:00を越えるfillはblock

### H1 entry families

- decision_time=H1 time+1時間
- decision hours UTC 07〜14
- pending expiry 1時間
- M1 gap/touch fill
- SL=1.0 H1 ATR14
- TP=2.0 H1 ATR14
- max hold=6時間
- UTC20:00を越えるfillはblock

same M1はSL優先。

## H4候補群

### F1_FALSE_BREAK_RECLAIM
上位trend方向と逆側へ直近2本の構造を一度sweepし、完了H4で水準内へreclaim。次H4内部でreclaim足高安を方向側へ突破。

### F2_SHALLOW_EMA20_RECLAIM
trend中、最新H4がEMA20へ浅くtouchし、方向側body・終値位置60%以上で回復。stop=最新H4高安。

### F3_DEEP_PULLBACK_RECOVERY
2〜4本の逆行後、最新H4がEMA20を方向側へ再crossし、前H4高安を回復。stop=最新H4高安。

### F4_THREE_BAR_BASE
直近3本の全体range<=1.25ATR、平均overlap>=0.55、trend方向context。stop=3本base境界。

### F5_NR7_RELEASE
最新H4がNR7、ATR14/ATR50<=1.05、trend方向context。stop=最新H4高安。

### F6_OUTSIDE_CONTINUATION
最新H4がoutside bar、方向側body、方向側close location>=0.75。stop=最新H4高安。

### F7_EMA_SQUEEZE_RELEASE
EMA20-EMA50 spread<=0.45ATR、両EMA slopeが方向側、MACD histogram方向側。stop=直近3本高安。

### F8_RSI_RESET_RESUME
trend中、直近3本のどこかでRSI14が中立帯45〜55へ戻り、最新H4が方向側へ55超/45割れ。stop=最新H4高安。

### F9_MOTHER_BAR_BREAKOUT
最新H4がinside barで、母足が方向側bodyかつrange<=1.5ATR。stop=母足方向側境界。

### F10_EXHAUSTION_REJECTION_REVERSAL
D1/H4 trend不一致またはH4 EMA spread<=0.25ATR。最新H4がEMA20から2ATR以上乖離、RSI>=75または<=25、反転側wick>=45%、反転側entry。stop=最新H4反転側境界。

## H1候補群

D1/H4方向一致をcontextとする。

### F11_H1_FOUR_BAR_COMPRESSION
直近4本H1のrange<=1.4 H1 ATR、ATR14/ATR50<=1.05。stop=4本高安。

### F12_H1_FALSE_BREAK_RECLAIM
H1直近3本構造を逆側へsweepし、最新H1で水準内へ回復。stop=最新H1方向側高安。

### F13_H1_EMA20_RECLAIM
H1がEMA20へtouch後、方向側body・終値位置>=0.65で回復。stop=最新H1高安。

### F14_H1_NR7_RELEASE
最新H1がNR7、H4/D1方向一致。stop=最新H1高安。

## discovery evaluation

各familyについて:

- independent M1 execution outcome
- raw resolved count
- cost2/cost5 win rate、expectancy、PF
- 2025/2026 source別
- LONG/SHORT別
- monthly median count
- C1 accepted候補とのdecision-time overlap率
- top5 profit share
- max drawdown

## family-specific OOF gate

raw resolved 30件以上のfamilyのみ。

- pending作成時点のentry-known特徴だけ
- family別elastic-net logistic regression
- target=cost2_pnl>0
- monthly expanding walk-forward
- minimum train=max(30, family raw resolvedの40%)
- retention候補40/55/70/85%
- trainingでcost2勝率>=60%、cost5期待値>0を満たす最大retention
- 該当なしはcost2勝率最大、同点はcost5期待値、さらに同点はretention最大

## discovery ranking

以下を満たすfamilyを新component候補とする。

- OOF accepted>=25件
- retention 35〜85%
- cost2勝率>=60%
- raw比+5 percentage point以上
- cost5勝率>=55%
- cost5 expectancy>0
- cost5 PF>=1.25
- 2025/2026両source expectancy>=0
- LONG/SHORT各10件以上かつexpectancy>=0
- top5 profit share<=60%
- C1 overlap<=70%

合格familyが複数なら、C1 overlapが低く、月間trade中央値が高い順に優先する。

## stack診断

C1 frozen + discovery合格familyだけを使用。

- one pending / one active
- first come
- same decision timeはOOF probability降順
- stack後のcost2/cost5勝率、expectancy、PF、月間中央値、方向・source安定性を正式指標にする

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
