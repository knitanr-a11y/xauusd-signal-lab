# GOLD V3 Stage272 R2 Exit / Horizon / Path-Management Audit

作成日: 2026-06-21  
正式状態: `GOLD_V3_272_R2_BASE_48_72H_ROBUST_NO_EXIT_MANAGEMENT_LEAD_AUDIT_ONLY`

## 結論

R2のentry条件を固定し、72取引時間まで同一source M1経路を完全に追える300候補で22種類のexit/horizon管理を比較した。

- 2025: 193件
- 2026: 107件
- latest60: 34件（LONG 16 / SHORT 18）
- FIXED 48h / 72hは、2025・2026・latest60・LONG/SHORTでプラスを維持
- しかし固定時間exitはtail lossとMAEが大きく、単独では実運用可能なrisk managementではない
- SL、breakeven、partial、trail、H1 structure、fade保護のうち、latest60 LONG/SHORT双方を維持してFIXED48より改善したものは0件
- Stage272 strict exit-management research lead: 0

R2は「48〜72時間のpath distribution edge」は残るが、完成したtrade strategyではない。

## Base horizon

### FIXED 48h

- ALL n=300、mean +0.959 ATR、median +0.773 ATR
- cost2 expectancy +21.74 USD、PF 1.504
- 2025 median +0.725 ATR
- 2026 median +0.861 ATR
- latest60 mean +1.086 ATR、median +0.567 ATR、PF 1.803
- latest60 LONG cost2 expectancy +1.046 ATR
- latest60 SHORT cost2 expectancy +0.956 ATR

判定: `BASE_HORIZON_CURRENTLY_ROBUST`

ただし:

- median MAE -2.300 ATR
- q10 return -6.617 ATR
- worst return -19.450 ATR
- positive cost2 months 11 / 18

### FIXED 72h

- ALL n=300、mean +1.089 ATR、median +1.248 ATR
- cost2 expectancy +22.91 USD、PF 1.491
- 2025 median +1.512 ATR
- 2026 median +1.008 ATR
- latest60 mean +1.013 ATR、median +0.716 ATR、PF 1.570
- latest60 LONG cost2 expectancy +1.317 ATR
- latest60 SHORT cost2 expectancy +0.577 ATR

判定: `BASE_HORIZON_CURRENTLY_ROBUST`

ただし:

- median MAE -2.934 ATR
- q10 return -8.002 ATR
- worst return -16.937 ATR
- positive cost2 months 10 / 18

## Path trade-off

| Path class | n | FIXED48 mean ATR | FIXED72 mean ATR |
|---|---:|---:|---:|
| PERSISTENT | 96 | +5.702 | +6.177 |
| DELAYED | 56 | +4.114 | +4.540 |
| FADE | 51 | -2.749 | -4.147 |
| EARLY_FAIL | 73 | -5.444 | -5.431 |
| MIXED | 24 | +1.977 | +3.648 |

72hはPersistent/Delayedを伸ばすがFadeを悪化させる。

## Stop / breakeven

全期間ではSL 1.5〜2.0ATRが高いPFを示したが、latest60ではSHORTが崩れた。

- SL2.0 / 48h latest60 LONG +1.530 ATR、SHORT -1.451 ATR
- SL1.5 / 72h latest60 LONG +1.242 ATR、SHORT -1.307 ATR
- Breakeven +1ATR / 48h latest60 LONG +1.642 ATR、SHORT -1.172 ATR
- Breakeven +1ATR / 72h latest60 LONG +1.938 ATR、SHORT -1.172 ATR

現在R2 SHORTは先に逆行してから回復するDelayedが多く、固定stop/breakevenがその回復前に切っている。

## H1 structure / trail

H1 3-bar structure breakは:

- Early-fail: FIXED48 -5.444 ATR → -1.412 ATR
- Fade: FIXED48 -2.749 ATR → +0.306 ATR

まで改善したが:

- Delayed: +4.114 ATR → -0.557 ATR
- Persistent: +5.702 ATR → +2.345 ATR

となり、良いDelayed/Persistentも早期終了した。

TRAIL_AFTER_1.5ATRもFadeを改善するがDelayed/Persistent利益を大幅に削った。

## Fade protection

PROTECT_FADE_AFTER_1ATRは全体でcost2 expectancy +17.20 USD、PF 1.672だったが、latest60では:

- LONG +2.207 ATR
- SHORT -0.620 ATR

となり方向安定性を満たさなかった。

## Strict lead判定

初期条件だけでは6設定がlead候補に見えたが、current robustness addendumの:

- latest60 median >0
- latest60 PF >=1.20
- latest60 top5 profit share <=70%
- latest60 LONG/SHORT双方のcost2 expectancy >=0
- latest60 LONG/SHORT双方PF >=1.0

をすべて満たした設定は0。

正式結果: `NO_EXIT_MANAGEMENT_RESEARCH_LEAD`

## 正式判断

1. R2の48hと72h base horizonは、現在もLONG/SHORT双方でプラス。
2. 48hはrisk効率が72hより良く、72hはPersistent/Delayedの上振れを伸ばす。
3. どちらもtail lossとMAEが大きく、そのまま売買戦略にはできない。
4. stop/breakevenはEarly-failを改善するが、現在のDelayed SHORTを損失化する。
5. structure/trailはFadeを改善するが、Delayed/Persistentを削る。
6. 事前固定した単一exit管理で全pathを同時に改善するものはなかった。
7. R2は`PATH_EDGE_ONLY_NOT_COMPLETE_STRATEGY`として保持する。
8. 同じ2025/2026で追加path-adaptive ruleを作ると過学習になるため停止する。

## 次

- 2023〜2024の同broker H1/M1またはH1 pathを追加
- pre-registered path-adaptive exitを外部期間で検証
- candidate overlap / one-position suppression
- exact spread / slippage / weekend carry

追加データなしではR2をlive strategyへ昇格しない。

## correctness

- common sample 300
- 全22 exitで同一sample
- source crossing 0
- decision前entry 0
- M1 same-bar stop priority
- regression tests 4/4 PASS
- Stage272 acceptance criteria ALL PASS

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
