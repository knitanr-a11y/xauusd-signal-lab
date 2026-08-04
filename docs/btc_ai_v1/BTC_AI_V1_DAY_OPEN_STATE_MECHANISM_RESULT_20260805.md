# BTC AI V1 — H4 day-open broad-state mechanism research result

日付: 2026-08-05  
branch: `feature/btc-day-open-state-mechanism-research`  
base: `feature/btc-broad-state-holding-research@4c4f7599fdbac489b6d83bccf6e8f2b8a9d93266`  
事前登録commit: `c8ccbff39c46477d00b6fbb7393d0d277cd89738`

## 正式結論

`BTC_AI_V1_DAY_OPEN_STATE_MECHANISM_ALL_SIX_FAMILIES_REJECTED_BASE_BROAD_STATE_LEAD_RETAINED`

入口を狭めず、H4終値とbroker-day openの上下関係を広いdesired stateとして維持したまま、6種類のstate機構と2種類のstopを結果前に固定して検証した。正式gateを通過したfamilyはない。

ただし、変更を加えない基準方式は2ATR・4ATRともcost後プラスを再現し、今回も全12構成中で最も強かった。持続確認、0.25ATRヒステリシス、週始値一致は改善せず、日替わり再武装とstop後1回再武装も合算プラスではあるが基準方式を上回らなかった。

## Formal period 2024–2026年7月

| family | config | trades | 勝率 | PF | net USD | Max DD | net/DD |
|---|---|---:|---:|---:|---:|---:|---:|
| BASE_FLAT_UNTIL_FLIP | `FLIP_OR_2ATR_STOP` | 1,357 | 22.25% | 1.080 | +38,861.76 | 36,599.83 | 1.062 |
| BASE_FLAT_UNTIL_FLIP | `FLIP_OR_4ATR_STOP` | 1,357 | 30.14% | 1.063 | +39,432.64 | 30,951.26 | 1.274 |
| ONE_REARM_NEXT_H4_SAME_STATE | `FLIP_OR_2ATR_STOP` | 1,738 | 23.30% | 1.052 | +32,385.00 | 30,855.89 | 1.050 |
| BROKER_DAY_RESET_REARM | `FLIP_OR_4ATR_STOP` | 1,395 | 29.82% | 1.043 | +28,030.97 | 35,756.47 | 0.784 |
| BROKER_DAY_RESET_REARM | `FLIP_OR_2ATR_STOP` | 1,489 | 21.56% | 1.028 | +15,242.79 | 32,071.58 | 0.475 |
| ONE_REARM_NEXT_H4_SAME_STATE | `FLIP_OR_4ATR_STOP` | 1,450 | 30.14% | 1.020 | +13,397.43 | 36,279.00 | 0.369 |
| PERSISTENCE_TWO_H4 | `FLIP_OR_4ATR_STOP` | 772 | 30.83% | 0.964 | -16,325.29 | 81,190.83 | -0.201 |
| HYSTERESIS_025_H4_ATR | `FLIP_OR_4ATR_STOP` | 864 | 30.79% | 0.961 | -20,306.51 | 37,268.85 | -0.545 |
| HYSTERESIS_025_H4_ATR | `FLIP_OR_2ATR_STOP` | 864 | 21.30% | 0.955 | -16,693.68 | 45,059.53 | -0.370 |
| PERSISTENCE_TWO_H4 | `FLIP_OR_2ATR_STOP` | 772 | 21.11% | 0.942 | -17,952.68 | 64,553.80 | -0.278 |
| BROKER_WEEK_OPEN_AGREEMENT | `FLIP_OR_4ATR_STOP` | 431 | 17.17% | 0.770 | -77,915.92 | 111,413.36 | -0.699 |
| BROKER_WEEK_OPEN_AGREEMENT | `FLIP_OR_2ATR_STOP` | 431 | 9.51% | 0.631 | -84,803.50 | 106,148.71 | -0.799 |

## 基準方式の再現結果

| config | trades | PF | net USD | Max DD | net/DD | 最大winner除外PF | double-cost PF |
|---|---:|---:|---:|---:|---:|---:|---:|
| `FLIP_OR_2ATR_STOP` | 1,357 | 1.080 | +38,861.76 | 36,599.83 | 1.062 | 1.054 | 1.016 |
| `FLIP_OR_4ATR_STOP` | 1,357 | 1.063 | +39,432.64 | 30,951.26 | 1.274 | 1.043 | 1.014 |

### 年別

| config | 2024 | 2025 | 2026年1–7月 | 2026年7月 |
|---|---:|---:|---:|---:|
| `FLIP_OR_2ATR_STOP` | PF 0.926 / -14,031.81 | PF 1.220 / +44,592.03 | PF 1.088 / +8,301.54 | PF 0.628 / -4,095.78 |
| `FLIP_OR_4ATR_STOP` | PF 0.926 / -18,211.21 | PF 1.154 / +40,036.78 | PF 1.150 / +17,607.07 | PF 0.751 / -3,497.72 |

## 各機構の判定

| family | 2ATR PF/net | 4ATR PF/net | paired support | 正式判定 |
|---|---:|---:|---:|---|
| BASE_FLAT_UNTIL_FLIP | 1.080 / +38,861.76 | 1.063 / +39,432.64 | 2/2 | REJECT |
| PERSISTENCE_TWO_H4 | 0.942 / -17,952.68 | 0.964 / -16,325.29 | 0/2 | REJECT |
| HYSTERESIS_025_H4_ATR | 0.955 / -16,693.68 | 0.961 / -20,306.51 | 0/2 | REJECT |
| BROKER_DAY_RESET_REARM | 1.028 / +15,242.79 | 1.043 / +28,030.97 | 2/2 | REJECT |
| BROKER_WEEK_OPEN_AGREEMENT | 0.631 / -84,803.50 | 0.770 / -77,915.92 | 0/2 | REJECT |
| ONE_REARM_NEXT_H4_SAME_STATE | 1.052 / +32,385.00 | 1.020 / +13,397.43 | 2/2 | REJECT |

## 分かったこと

- **基準方式を複雑化しても改善しなかった。** 2本継続確認と0.25ATRヒステリシスは取引回数を減らしたが、合算PFは1未満になった。
- **broker-week openとの一致は逆効果だった。** 2ATR PF 0.631、4ATR PF 0.770で、入口を週始値で整える根拠は得られなかった。
- **再武装は利益を増やさなかった。** day resetとstop後1回rearmは両stopでプラスを保ったが、PF、DD、cost耐性はいずれも基準方式より弱かった。
- **基準方式の弱点は残った。** 2024年は両stopで赤字、2026年7月も赤字で、最大winner除外とdouble-cost gateにも届いていない。

## 診断情報（post-hoc、採用条件には不使用）

基準方式ではbroker-dayの最初のH4 decision（phase 0）が最も強く、2ATR PF 1.226、4ATR PF 1.255だった。一方、phase 3とphase 5は両stopでPF 1未満だった。

day-openから0.5–1.0 H4 ATR離れたentryは2ATR PF 1.311、4ATR PF 1.245だった。ただし、これらは結果後に得た診断であり、時間帯や距離を追加filterとして採用・救済していない。

broker-week openと方向が一致していないentryの方が、基準方式では一致entryより高いPFだった。このためweek-open confluenceを前提にする仮説は支持されなかった。

## Pipeline / causal audit

| 項目 | 件数・状態 |
|---|---:|
| raw closed-H4 decisions | 7,647 |
| exact decision M1欠損 | 4 |
| completed trades（12構成合計） | 17,773 |
| unresolved end-of-data | 8 |
| synthetic tests | 2/2 PASS |
| reference / optimized parity | 122 trades complete match |
| future/open/as-of use | 0 |
| next-M1 fallback | 0 |
| health gate | OFF / not applicable |
| Stage55 modified | false |

未解決8件は各構成の最終open positionであり、勝敗を推定せずformal成績から除外した。entry時のexact M1欠損は無効で、次のM1へfallbackしていない。

## 正式境界

- new prospective Shadow: not authorized
- result後のphase・distance filter救済: prohibited
- MT5 orders / live trading / live-ready / final signal / Discord: OFF
- Stage55: unchanged

## 次の研究判断

入口をさらに狭めるより、基準方式の利益がstate-flip決済で生まれ、固定stopで失われている構造を、入口を変えずにexit architectureとして事前登録して調べる。候補は固定3ATR、closed-H4構造stop、利益側だけのbreak-even移動、state-flip＋時間underwater exitであり、今回のphase・distance診断をselectionには使用しない。
