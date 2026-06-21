# GOLD V3 Stage274 定義固定
## Liquidity sweep / reclaim structural families

作成日: 2026-06-21
状態: `GOLD_V3_274_LIQUIDITY_SWEEP_RECLAIM_FAMILY_DEFINITION_LOCKED_AUDIT_ONLY`

## 目的

2023〜2024年を発見期間、2025年を確認期間、2026年を最終判定期間として、GOLD向けの新規structural signal familyを検証する。

対象は2familyのみ。

1. `HTF_TREND_LIQUIDITY_SWEEP_RECLAIM_FIRST_PULLBACK`
2. `RANGE_FAILED_BREAK_RECLAIM_REVERSAL`

Stage265〜273の旧候補はREFERENCE_ONLYのままとし、新familyへ混ぜない。

## 絶対契約

- audit-only。
- GOLD V2、旧GOLD、DISC8、Stage41を読まない。
- CSVは確定足、timeはbar OPEN時刻。
- availability: M1 +1m、M15 +15m、H1 +1h、H4 +4h、D1 +1d。
- 全as-of joinはsource_close_time <= decision_time。
- entryはM15 trigger確定後、同sourceの最初のM1 open。
- 同一M1でSL/TP成立時はSL優先。
- LONG/SHORT双方。
- 年、方向、時間帯による後付け救済禁止。
- candidate poolを暗黙に除外しない。
- 2026は最終判定でありthreshold調整に使わない。
- live promotion禁止。

## データ分割

- DISCOVERY: 2023-01-01〜2024-12-31
- CONFIRMATION: 2025-01-01〜2025-12-31
- FINAL_CURRENT: 2026-01-01〜データ末尾

2023〜2024年内でfamily定義は固定済みの有限variantのみ比較可能。2025/2026を見て条件追加・閾値変更しない。

## 共通feature

### M15

- ATR14
- EMA20
- body/range
- candle range / ATR
- previous-day high/low（直前の確定D1足）
- rolling H1 swing20 high/low（直前20本の確定H1）

### H4 context

確定H4足のみ使用。

- EMA20
- EMA50
- ATR14
- EMA20 slope3 / ATR
- EMA spread / ATR

## Family A: HTF trend + sweep + reclaim + first pullback

### H4 trend context

LONG:

- H4 close > EMA20 > EMA50
- (EMA20 - EMA50) / ATR14 >= 0.35
- (EMA20 - EMA20.shift(3)) / ATR14 >= 0.10

SHORTは完全反転。

### Level variants

- `A_PD`: previous-day low/high
- `A_H1S20`: rolling confirmed H1 swing20 low/high

### Sweep / reclaim bar

LONG:

- M15 low < level
- M15 close > level
- sweep depth >= 0.05 * M15 ATR14
- M15 range >= 0.80 * ATR14
- body/range >= 0.35
- bullish close

SHORTは反転。

### First pullback

reclaim確定後1〜4本目のM15で最初に:

LONG:

- low <= reclaim candle midpoint
- close > reclaimed level
- close >= M15 EMA20 - 0.10*ATR14

SHORTは反転。

entryはpullback M15 close後の最初のM1 open。

SL:

- sweep extremeの外側へ0.15 * reclaim M15 ATR14

固定評価:

- TP 1.5R / SL 1R
- TP 2.0R / SL 1R
- TP 2.5R / SL 1R
- horizon cap 24 trading hours

## Family B: range failed break reclaim reversal

### H4 range context

- abs(EMA20 - EMA50) / ATR14 <= 0.75
- abs(EMA20 - EMA20.shift(3)) / ATR14 <= 0.20

### Level variants

- `B_PD`: previous-day high/low
- `B_H1S20`: rolling confirmed H1 swing20 high/low

### False-break reclaim bar

SHORT:

- M15 high > resistance level
- M15 close < resistance level
- sweep depth >= 0.05 * M15 ATR14
- M15 range >= 0.70 * ATR14
- body/range >= 0.25

LONGは反転。

### Confirmation

次の1〜2本のM15内で最初に:

SHORT:

- close < reclaim bar midpoint
- close < level
- high <= sweep extreme + 0.05*ATR14

LONGは反転。

entryはconfirmation M15 close後の最初のM1 open。

SL:

- sweep extremeの外側へ0.15 * reclaim M15 ATR14

固定評価:

- TP 1.5R / SL 1R
- TP 2.0R / SL 1R
- TP 2.5R / SL 1R
- horizon cap 24 trading hours

## 重複処理

同family・同directionでentryが24 trading hours以内に重複する場合:

- 全候補台帳は保持
- `independent_stream`では最初の候補だけ採用
- 後続候補はsuppressed ledgerへ保存

family間は統合せず別評価する。

## 発見期間のvariant選択

4 variant × 3 TP = 12固定セル。

2023〜2024年で次を満たすセルのみ`DISCOVERY_LEAD`:

- independent n >= 60
- 2023、2024各 n >= 20
- cost2 expectancy > 0
- PF cost2 >= 1.20
- median R > 0
- LONG/SHORT双方 n >= 20
- LONG/SHORT双方mean R >= 0
- top5 profit share <= 55%
- 2023/2024双方mean R >= 0

複数ある場合の選択順位:

1. 2023/2024の低い方のexpectancy
2. LONG/SHORTの低い方のexpectancy
3. total PF
4. total n

familyごとに最大1セルを2025へ持ち込む。

## 2025確認条件

- n >= 25
- cost2 expectancy > 0
- PF cost2 >= 1.10
- median R > 0
- LONG/SHORT双方mean R >= 0（各n>=8）

通過時のみ2026最終判定。

## 2026最終判定条件

- n >= 15
- cost2 expectancy > 0
- PF cost2 >= 1.10
- median R >= 0
- LONG/SHORT双方mean R >= 0。ただし方向別n<5なら`INSUFFICIENT_DIRECTION_SAMPLE`
- latest60 cost2 expectancy >= 0（n>=8の場合）

## 正式分類

- `STRONG_MULTI_PERIOD_RESEARCH_LEAD`
- `DISCOVERY_ONLY_FAILED_2025`
- `CONFIRMED_2025_FAILED_2026`
- `NO_DISCOVERY_LEAD`
- `INSUFFICIENT_SAMPLE`

合格してもlive-readyではない。

## 出力

- all candidate ledger
- independent accepted/suppressed ledger
- 12-cell discovery summary
- chosen discovery cell
- 2025 confirmation
- 2026 final result
- year/direction/month breakdown
- MFE/MAE/path timing
- acceptance criteria
- formal audit and handoff

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
