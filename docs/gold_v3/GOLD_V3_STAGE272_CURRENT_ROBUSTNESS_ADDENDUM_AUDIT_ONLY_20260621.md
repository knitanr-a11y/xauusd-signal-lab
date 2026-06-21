# Stage272 Current Robustness Addendum

作成日: 2026-06-21
状態: `GOLD_V3_272_CURRENT_ROBUSTNESS_ADDENDUM_LOCKED_AUDIT_ONLY`

## 理由

正式結果確定前の初回集計で、SL/breakeven系が全期間では高いPFを示す一方、latest60 SHORTではマイナスとなり、少数LONG大勝への依存が確認された。

2026年、特に現在相場で通用する強い候補という目的に合わせ、全期間平均だけでexit-management leadと誤認しないため、現在robustness条件を追加する。

## 追加必須条件

`EXIT_MANAGEMENT_RESEARCH_LEAD`にはStage272本体条件に加えて:

- latest60全体 cost2 expectancy ATR > 0
- latest60全体 median gross ATR > 0
- latest60全体 PF cost2 >= 1.20
- latest60全体 top5 profit share cost2 <= 70%
- latest60 LONG cost2 expectancy ATR >= 0
- latest60 SHORT cost2 expectancy ATR >= 0
- latest60 LONG/SHORT各PF cost2 >= 1.0

を必須とする。

## baseline status

FIXED_24H/48H/72Hはexit-management改善leadとは別に:

- `BASE_HORIZON_CURRENTLY_ROBUST`
- `BASE_HORIZON_CURRENTLY_WEAK`

として評価する。

## 禁止

- latest60 SHORTが負のstop/breakevenを、全期間PFだけで採用しない
- LONGだけにexitを適用しない
- latest60条件に合わせてstop幅やtrail幅を追加探索しない
