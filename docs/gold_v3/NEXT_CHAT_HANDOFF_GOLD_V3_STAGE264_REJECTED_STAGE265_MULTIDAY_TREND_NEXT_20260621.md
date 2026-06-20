# GOLD V3 引き継ぎ
## Stage264 H1/H4中期自動売買 REJECT

正式状態:

`GOLD_V3_264_H1_H4_MEDIUM_TERM_AUTOTRADE_REJECTED_AUDIT_ONLY`

## 結果

### H1 pullback reclaim

- 308 raw candidates
- 224 resolved trades
- coverage 100%
- cost2 PnL -645.64
- expectancy -2.882
- PF 0.545
- 2023〜2026全年度赤字
- LONG / SHORTとも赤字

### H4 aligned breakout

- 256 raw candidates
- 223 resolved trades
- coverage 99.55%
- cost2 PnL -475.37
- expectancy -2.132
- PF 0.701
- 2020〜2024合算 -484.49
- LONG / SHORTとも赤字

### correctness

- prefix signal parity 12/12 PASS
- H1 M1 path 35/35 entry・exit理由・PnL一致
- H4 M1 path 15/15 entry・exit理由・PnL一致
- tests 3/3 PASS

## 解釈

予備診断の24〜48時間単純保有で見えた利益は、H1/H4 entry timing edgeではなく、2025〜2026の長時間trend exposureへの依存が大きかった。

同日内6〜8時間、ATR stop/target、押し戻り回復またはbreakoutという正式EA契約ではedgeを確認できなかった。

## 禁止

- Stage264結果後のATR倍率調整
- 保有時間調整
- LONG only / SHORT only
- 年別・時間帯filter
- H1/H4 parameter grid探索
- 2025/2026だけを採用根拠にする

## 次の分岐

自動売買を続けるなら、同じentry調整ではなく構造を変更する。

第一候補:

`GOLD_V3_265_MULTI_DAY_CHANNEL_TREND_FOLLOWING_WITH_SWAP_CALENDAR_AUDIT_ONLY`

必要:
- broker official session calendar
- swap long / short history or current contract
- rollover and holiday handling
- D1/H4 channel breakout
- volatility position sizing
- multi-day trailing exit
- 2025/2026既知期間への依存監査

第二候補:

複数資産trend-following portfolio。gold単独依存を避ける。

運用状態:

`NO_LIVE_PROMOTION_AUDIT_ONLY`
