# GOLD V3 Stage266B Deep Win/Loss Pattern Audit

作成日: 2026-06-21

状態: `GOLD_V3_266B_DEEP_WIN_LOSS_PATTERN_ANALYZED_AUDIT_ONLY`

## 目的

C1/C2/C3それぞれで、勝ちと負けの違いをentry時点で既知の情報だけから多角的に分解した。

分析軸:
- D1/H4 trend strength
- setup geometry
- candle body/wick/close location
- momentum/acceleration
- volatility regime
- latest completed H1 internal state
- volume/spread/time/family overlap
- single-feature quartiles
- pairwise adverse intersections
- shallow descriptive trees
- monthly feature-selection stability

## C1 H4 six-bar channel

主な負けパターンは「勢い不足」ではなく、すでに伸び過ぎた状態での追いかけだった。

代表診断:
- H4 range/ATR >= 1.225: 34件、cost5勝率35.29%、期待値-7.10
- aligned 1-bar return/ATR >= 0.854: 34件、勝率32.35%、期待値-7.84
- aligned body/ATR >= 0.838: 34件、勝率29.41%、期待値-8.87
- range/ATR >=1.225 かつ body/ATR >=0.838: 27件、勝率29.63%、期待値-11.57
- H1 ATR ratio >=1.044 かつ aligned 2-bar return/ATR >=1.394: 20件、勝率25.00%、期待値-9.37

つまり、H4 channelを抜く前からH4実体・短期return・H1 volatilityが同時に膨張している場合、初動ではなく終盤を買う/売る形になりやすい。

一方、D1 momentumが維持され、直近H4/H1が過熱していない状態は勝ち側に多かった。

月次feature selectionで繰り返し選ばれたもの:
- H4 MACD aligned / ATR
- favorable wick ratio
- H4 range / ATR
- H4 volume ratio
- H1 ATR ratio
- H1 directional streak
- H4 body/range
- D1 MACD aligned / ATR

## C2 H4 pullback

負けは主に2種類。

1. 押しから十分に回復していない
- H4 20-bar aligned position bottom quartile: 20件、勝率35.00%、期待値-7.45
- H1 EMA20 aligned slopeが弱い下位2quartile: 勝率40.00% / 36.84%、期待値ともマイナス

2. 回復ではなく単発の大陽線/大陰線を追いかける
- H4 body/range top quartile: 20件、勝率35.00%、期待値-5.66
- large body + strong latest H1 returnの組合せも悪化

C2はH4位置、H1 slope、family overlapが良い側へ寄ると改善するが、source・directionで境界が動く。

## C3 H4 compression

C3は「低ボラ圧縮」なら良いが、「すでに高ボラ化した後の見せかけ圧縮」が悪い。

代表診断:
- ATR percentile <=4%: 16件、勝率75.00%、期待値+18.10
- ATR percentile top quartile: 12件、勝率33.33%、期待値+0.37
- volume ratio bottom quartile: 12件、勝率25.00%、期待値-0.36
- volume ratio third quartile: 11件、勝率81.82%、期待値+22.60
- H4 aligned position top halfほど改善
- H1 aligned streakが2本以上続いた後は期待値マイナス

つまり、十分に静かな圧縮、適度な参加、上位方向側の位置、H1 slope一致が重要。すでに走った後の圧縮は避けるべき。

## 固定pairwise vetoの結果

training上で負けが集中したquartile/pair ruleを翌月へそのまま適用するStage266Cも監査した。

結果:
- C1ではveto rejected群がcost5期待値+4.26となり、固定ruleが翌月で反転
- C2ではveto-onlyは改善したがmodelとのANDで悪化
- C3ではveto rejected群の方が良かった

結論:
- 負けパターンは存在する
- ただし境界値はvolatility/regimeとともに移動する
- 固定した1〜2本のhard ruleでは安定しない
- family別に複数特徴を重み付けし、月次更新するgateが必要

## 重要な解釈

「負けに多い形を削る」方針は正しい。ただし、
- 1条件だけ
- 全期間固定閾値
- trainingで最悪だった組合せをそのまま翌月へ適用

では過学習する。

正式な削減は、過去月だけで学習したfamily別gateのOOF成績で判断する。

運用状態: `NO_LIVE_PROMOTION_AUDIT_ONLY`
