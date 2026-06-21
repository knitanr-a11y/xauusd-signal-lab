# Stage269 Source × Direction Stability Addendum

作成日: 2026-06-21
状態: `GOLD_V3_269_SOURCE_DIRECTION_STABILITY_ADDENDUM_LOCKED_AUDIT_ONLY`

## 理由

正式結果確定前に、entry-resolution triggerが全体・2025/2026・LONG/SHORTではプラスでも、2026 SHORTなど特定のsource×direction区分で負になる可能性を検出した。

2026年に通用するかというユーザー要求へ正面から答えるため、entry-resolution正式leadにはsource×direction安定性を追加する。

## 追加必須条件

各triggerについて:

- 2025 LONG n>=10、mean>0、median>0
- 2025 SHORT n>=10、mean>0、median>0
- 2026 LONG n>=10、mean>0、median>0
- 2026 SHORT n>=10、mean>0、median>0

Stage269本体基準を満たすが、この追加条件だけを満たさないものは:

`ENTRY_RESOLUTION_NEAR_LEAD_SOURCE_DIRECTION_UNSTABLE`

として全件保持する。

## 禁止

- 負の区分をLONG only / SHORT onlyで除外しない
- source別に別triggerを採用しない
- 閾値を結果に合わせて変更しない
