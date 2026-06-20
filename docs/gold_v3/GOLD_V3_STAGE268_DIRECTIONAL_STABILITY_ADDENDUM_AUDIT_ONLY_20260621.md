# Stage268 Directional Stability Addendum

作成日: 2026-06-21
状態: `GOLD_V3_268_DIRECTIONAL_STABILITY_ADDENDUM_LOCKED_AUDIT_ONLY`

## 理由

初回分布集計の正式判定前に、D1_TREND等の上位セルが2025〜2026の金上昇相場によるLONG偏重で成立している可能性を検出した。これはperformance最適化ではなく、researchable distribution cellを相場方向バイアスと誤認しないための診断完全性修正。

## 追加出力

各cell×horizon×hypothesisについて、仮説方向別に:

- LONG / SHORT件数
- positive rate
- mean / median ATR-normalized return
- 2025 / 2026件数とmean

を出す。

## 追加分類

### DIRECTION_STABLE

- H1: LONG/SHORT各40件以上
- H4: LONG/SHORT各15件以上
- LONG/SHORT双方でmean return > 0
- LONG/SHORT双方でmedian return > 0
- LONG/SHORT双方でpositive rate >= 52%

### DIRECTION_BIASED

上記を満たさず、全体のresearchable基準だけを満たすcell。

## 正式researchable cell

Stage268本体基準に加えて`DIRECTION_STABLE`を必須とする。

方向片側だけで成立したcellは削除せず、`DIRECTION_BIASED_RESEARCH_LEAD`として別台帳へ残す。

## 禁止

- LONGだけ・SHORTだけをstrategyとして採用しない
- direction不足を年・source filterで補わない
- 初回結果に合わせて閾値を変更しない
