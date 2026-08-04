# BTC AI V1 — H4 day-open broad-state 出口機構研究 正式結果

日付: 2026-08-05  
branch: `feature/btc-day-open-exit-mechanism-research`  
base: `feature/btc-day-open-state-mechanism-research@e9da46be4e4c9de721e976d4c46b3d6c3b10b2ee`  
事前登録commit: `b282d687b80d6fda75872d26c93eb16202514438`

## 正式結論

`BTC_AI_V1_DAY_OPEN_EXIT_MECHANISM_BE2ATR_FORMAL_HISTORICAL_GATE_PASS_RETROSPECTIVE_LEAD_AUTHORIZATION_PENDING`

結果前に固定した8出口のうち、次の1構成だけが全事前gateを通過した。

`FLIP_OR_4ATR_STOP_BE_AFTER_2ATR`

- 広い入口は変更しない
- closed H4終値がbroker-day openより上ならLONG、下ならSHORT
- 初期stopはentry時M15 ATR14の4倍
- 含み益が2ATRへ初めて到達したM1の次の実在M1からstopをentry価格へ移す
- desired state反転時はexact M1 openでexit・反転
- stopまたはbreak-even exit後は、同じstate中に再entryしない
- 次のstate反転までflat

これは2023～2026年7月を使用したretrospective evidenceであり、live採用ではない。Fresh no-backfill Prospective Shadowには別途ユーザー承認が必要。

## 8出口の合算結果 — 2024～2026年7月

| exit configuration | trades | 勝率 | PF | net USD | Max DD | net/DD | formal gate |
|---|---:|---:|---:|---:|---:|---:|---|
| `FLIP_OR_4ATR_STOP_BE_AFTER_2ATR` | 1,357 | 17.69% | 1.198 | +78,236.15 | 21,915.64 | 3.570 | PASS |
| `FLIP_OR_3ATR_STOP` | 1,357 | 27.86% | 1.100 | +57,676.83 | 28,497.94 | 2.024 | REJECT |
| `BASE_FLIP_OR_2ATR_STOP` | 1,357 | 22.25% | 1.080 | +38,861.76 | 36,599.83 | 1.062 | REJECT |
| `FLIP_OR_4ATR_STOP_TIMELOSS_3H4` | 1,357 | 28.30% | 1.066 | +39,055.48 | 25,505.02 | 1.531 | REJECT |
| `BASE_FLIP_OR_4ATR_STOP` | 1,357 | 30.14% | 1.063 | +39,432.64 | 30,951.26 | 1.274 | REJECT |
| `FLIP_OR_4ATR_STOP_TIMELOSS_6H4` | 1,357 | 29.99% | 1.062 | +38,837.17 | 31,235.60 | 1.243 | REJECT |
| `FLIP_OR_PREV_H4_STRUCTURE_STOP` | 1,357 | 27.78% | 1.055 | +32,542.88 | 31,287.88 | 1.040 | REJECT |
| `FLIP_OR_4ATR_STOP_BE_AFTER_1ATR` | 1,357 | 10.24% | 1.029 | +8,256.82 | 28,148.27 | 0.293 | REJECT |

## 通過構成の正式成績

| period | trades | 勝率 | PF | net USD | Max DD | net/DD |
|---|---:|---:|---:|---:|---:|---:|
| 2023 sanity | 528 | 13.07% | 0.760 | -13,630.72 | 20,064.17 | -0.679 |
| 2024 | 544 | 16.54% | 1.033 | +5,316.83 | 16,499.76 | 0.322 |
| 2025 | 527 | 18.22% | 1.247 | +38,944.90 | 21,394.14 | 1.820 |
| 2026-01～07 | 286 | 18.88% | 1.441 | +33,974.42 | 10,391.92 | 3.269 |
| combined | 1,357 | 17.69% | **1.198** | **+78,236.15** | **21,915.64** | **3.570** |
| 2026-07 diagnostic | 42 | 14.29% | 0.688 | -3,160.75 | 4,732.59 | -0.668 |

## 事前gate

| gate | threshold | result | pass |
|---|---|---:|---|
| frequency | combined >=100; 2024 >=20; 2025 >=20; 2026 >=12 | 1,357 trades | PASS |
| combined PF | >=1.15 | 1.198 | PASS |
| combined net | >0 | +78,236.15 | PASS |
| net / Max DD | >=1.50 | 3.570 | PASS |
| 2024 | PF>=1.00 and net>=0 | PF 1.033, +5,316.83 | PASS |
| 2025 | PF>=1.00 and net>=0 | PF 1.247, +38,944.90 | PASS |
| 2026-01～07 | PF>=0.95 | PF 1.441, +33,974.42 | PASS |
| largest winner removed | PF>=1.10 | 1.166 | PASS |
| double cost 45 USD | PF>=1.05 | 1.114 | PASS |
| LONG | PF>=0.85 | 1.174 / 678 trades | PASS |
| SHORT | PF>=0.85 | 1.226 / 679 trades | PASS |

## Break-even機構の内訳

正式期間1,357 tradesのうち、2ATR到達によりbreak-evenが有効になったtradeは796件（58.66%）。

| exit reason | trades | net USD |
|---|---:|---:|
| BE | 550 | -12,375.00 |
| BE_GAP_OPEN | 9 | -397.42 |
| SL | 241 | -233,680.70 |
| SL_GAP_OPEN | 1 | -617.44 |
| STATE_FLIP | 556 | +325,306.71 |

Break-even有効化後にstate flipまで伸びた237件が大きな利益を担った。550件はentry価格でbreak-even exitとなり固定costだけを失い、9件はbreak-even有効後のgap-openにより追加slippageが発生した。一方、2ATRへ届かなかったtradeでは初期4ATR stopまたはstate flipが使われる。

## 集中・耐性診断

- プラス月: 20/31
- マイナス月: 11/31
- 最大プラス月: 2026-01、+16,779.83 USD
- 最大マイナス月: 2025-12、-13,364.92 USD
- 最大プラス月のtotal gross profit比率: 6.24%
- top 5 winnerのgross profit比率: 11.06%
- 往復cost 45 USD: PF 1.114
- 往復cost 67.50 USD: PF 1.039、net +17,171.15 USD
- 2026年7月単月はPF 0.688、-3,160.75 USDであり、直近月まで一貫して勝ったわけではない。

## 実装・再現監査

- synthetic tests: 3/3 PASS
- Python referenceとNumba実装: 8 configurations、先頭500 H4 events、各122 tradesがentry/exit/価格/reasonまで完全一致
- control parity: 2ATR・4ATR controlは前回day-open state cycleとtrades/PF/net/Max DD/net-DDが完全一致
- raw closed-H4 events: 7,647
- exact decision M1 missing: 4、fallbackなし
- completed trades across 8 configs: 15,080
- unresolved trades: 0
- future/open/as-of使用: 0
- entry後のM1欠損区間は人工補完せずposition継続
- Stage55変更なし

## 境界

- 本結果は `RETROSPECTIVE_EXPLORATORY_EVIDENCE_ON_CONSUMED_HISTORY`
- 通過構成の最大statusは `RETROSPECTIVE_EXIT_LEAD_REQUIRES_FRESH_PROSPECTIVE_CONFIRMATION`
- Fresh no-backfill Shadowは未作成、承認待ち
- MT5 orders / live trading / live-ready / final signal / Discord / automatic promotionはOFF
- Stage55は変更していない
