# BTC AI V1 Stages 38–39 — AIメタ騙し判定・組み合わせ結果

日付: 2026-08-04

正式状態:

`META_FAKEOUT_LONG_SHORT_AND_GLOBAL_ONE_POSITION_STACK_SUPPORTED_STAGE39_ROBUSTNESS_PASS`

## 目的

過去に作った5つのscoreモデルを捨てず、発火後にclosed M15を待って、モデル同士の不一致・確認足・状態から「この高score発火は騙しか、継続しやすいか」をAIで再判定した。

入力モデル:

- EXPANDING
- EXP_DECAY_HL3M
- EXP_DECAY_HL6M
- EXP_DECAY_HL12M
- EXP_DECAY_HL24M

元の5モデルのいずれかが前月P90を超えた発火を候補とし、1/2/4本待ち、Logistic/LGBM、score-only確認またはstate込み確認、Q50/Q75/Q90を比較した。

- candidate rows: 8,595
- model groups: 48
- configurations: 144
- 2024H2 discovery pass: 39
- 2025を含むformal support: 14
- 2024H2だけのtie-breakで固定した構成: 2

## 固定されたLONG

`UNION_FIRST_CROSS__L1__LONG__SCORE_CONFIRM_STATE__LGBM_D3__Q90`

| 期間 | 件数 | PF | 純損益 | 最大DD |
|---|---:|---:|---:|---:|
| 2024H2 discovery | 23 | 2.3678 | 3,656.22 | 1,286.33 |
| 2025 validation | 71 | 1.5719 | 8,536.14 | 3,067.58 |
| 合算 | 94 | 1.6927 | 12,192.36 | 3,067.58 |

## 固定されたSHORT

`UNION_FIRST_CROSS__L1__SHORT__SCORE_CONFIRM__LGBM_D3__Q90`

| 期間 | 件数 | PF | 純損益 | 最大DD |
|---|---:|---:|---:|---:|
| 2024H2 discovery | 20 | 3.4213 | 5,604.22 | 704.18 |
| 2025 validation | 80 | 1.1216 | 1,960.59 | 1,996.80 |
| 合算 | 100 | 1.4103 | 7,564.81 | 1,996.80 |

## LONG＋SHORT one-position stack

| 期間 | 件数 | PF | 純損益 | 最大DD | positive halfyears |
|---|---:|---:|---:|---:|---:|
| 2024H2 discovery | 43 | 2.8567 | 9,260.44 | 1,335.27 | 1/1 |
| 2025 validation | 145 | 1.3901 | 11,439.68 | 3,376.32 | 2/2 |
| 合算 | 188 | 1.6033 | 20,700.13 | 3,376.32 | 3/3 |

block-bootstrap P(net > 0): `0.99975`

同じfirst-cross lag1母集団をメタ判定しないbaselineでは、2025 SHORTがPF約0.869、純損益約-23,605 USDだった。メタ判定後はSHORTがPF `1.1216`、純損益 `1960.59` USDまで改善した。

## Stage39 robustness

- 1.5倍spreadの2025 PF: `1.3507`、純損益 `10402.03`
- 2倍spreadの2025 PF: `1.2037`、純損益 `6394.12`
- Q85/Q90/Q95のうち2025合算net positive: 3/3
- Q90の3 seedで2025 PF>=1かつnet positive: LONG 3/3、SHORT 3/3
- matched-random net percentile: `1.0000`
- matched-random PF percentile: `1.0000`
- 2025 positive months: `8/12`
- positive D1 regimes: `3/3`

全Stage39 formal gateがPASS。

## 少件数の積み重ね診断

Stage37 deterministic LONGとStage38 meta LONG/SHORTを、結果確認後に組み合わせたためformalではなくdiagnostic。

global first-arrival one-position:

- 2025: 272件、PF `1.2452`、純損益 `14066.47`
- 2024H2＋2025: 394件、PF `1.3508`、純損益 `26827.16`
- exact-M15同方向一致: 0件

0件一致なので、deterministicとmetaは同じentryを重複して拾うのではなく、別の機会を積み重ねている可能性が高い。ただしこの合算自体は正式候補ではない。

## 因果監査

future/current training、refit時点未解決label、calibration/validation期間違反、outcome feature、2026 rows、2025列を使った選択はすべて0。2024だけの再選択結果も完全一致。

監査結果: `PASS`

研究候補としてsupportされた段階であり、Shadow、Discord、MT5発注、live-ready、final signalはすべてOFF。
