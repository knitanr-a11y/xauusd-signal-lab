# GOLD V3 Stage266E handoff

正式状態: `GOLD_V3_266E_C1_ONLY_COMPONENT_STACK_INSUFFICIENT_FREQUENCY_AUDIT_ONLY`

## C1

- Stage266D resolved OOF gate decision 74/74一致
- accepted 52
- cost2 WR 61.54%
- cost5 WR 57.69%
- cost5 expectancy +8.225 USD/oz
- cost5 PF 2.075
- rejected cost5 expectancy -14.994

C1は固定componentとして維持する。再調整禁止。

## C2

cost5専用gate accepted18:
- cost2 WR55.56%
- cost5 WR50.00%
- cost5 expectancy+0.455
- rejected expectancy+3.705

良い候補を削ったためgate破棄。setupを押しの深さ・回復形状でsubfamily分割する。

## C3

raw46:
- cost2 WR60.87%
- cost5 WR52.17%
- cost5 expectancy+8.356
- PF2.499

2026/SHORT少数大勝依存が強いためraw監視のみ。

## C4

previous-bar breakout:
- 全resolved223
- cost5 expectancy-1.200
- LONG193件 cost5 expectancy-3.361
- SHORT30件 cost5 expectancy+12.696

SHORT onlyは禁止。family不採用。

## C5

inside-bar breakout:
- resolved34
- cost2 WR47.06%
- cost5 expectancy-9.098
- PF0.377

family不採用。

## C1-only stack

pending/active suppression込み:
- 42 trades
- cost2 WR59.52%、expectancy+9.498、PF2.286
- cost5 WR57.14%、expectancy+6.498、PF1.750
- 月間中央値4件

利益品質は維持したが頻度不足。

## Next Stage266F

1. C1固定。
2. C2をpullback depth / recovery shapeでsubfamily分割。
3. C3 raw監視。
4. C6 H4 false-break reclaim continuation追加。
5. C7 H4 pullback subfamilies追加。
6. family単体のOOF勝率改善後だけstack。
7. stack後の実現勝率・頻度を正式指標にする。

禁止:
- C4 SHORT only
- C5救済
- C1再調整
- 2025/2026 year filter
- future information

運用: `NO_LIVE_PROMOTION_AUDIT_ONLY`
