# Stage270 Seasonally Matched Window Addendum

作成日: 2026-06-21
状態: `GOLD_V3_270_SEASONALLY_MATCHED_WINDOW_ADDENDUM_LOCKED_AUDIT_ONLY`

## 理由

2025 sourceは通年、2026 sourceは2026-06-19までであり、単純な年比較には季節性と期間長差が混ざる。

## 固定比較

1. FULL_SOURCE_PERIOD
   - 2025 source全期間
   - 2026 source全期間

2. MATCHED_CALENDAR_WINDOW
   - 2025-01-13 00:00〜2025-06-19 23:59
   - 2026-01-13 00:00〜2026-06-19 23:59

市場構造差の主要判断はMATCHED_CALENDAR_WINDOWを優先する。FULL_SOURCE_PERIODは補助診断とする。

## 禁止

- 結果に合わせて開始日・終了日を変更しない
- 特定月を除外しない
- 2026年の不足月を補間しない
