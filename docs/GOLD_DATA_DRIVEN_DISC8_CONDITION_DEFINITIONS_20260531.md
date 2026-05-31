# GOLD data-driven DISC8 固定条件定義

作成日: 2026-05-31

## 目的

`gold_data_driven_static_rebacktest_20260531_outputs.zip` の再バックテストで採用候補にした `DISC_*` 8条件を、AI評価サンプル作成・通知実装・バックテスト再現のための固定定義として明記する。

この文書は、次の2ファイルを原本として転記したもの。

```text
recommended8_static_rules.csv
static_rule_definitions.csv / static_rule_definitions.json
```

## 重要ルール

- この8条件を `data-driven DISC8` のsource of truthとする。
- AI評価前に、必ず `static_rule_trade_ledger.csv` の `candidate_id` がこの8条件と一致するか監査する。
- ローソク足から別ロジックで近似再実装したものをAI評価対象にしない。
- H1/H4/D1は `source_close_time <= M15 entry_time` の確定済み足だけを使う。
- M15は足確定後の `close_time` でエントリーする。
- AI評価サンプルはタグ抽出用であり、勝率/PF再計算用ではない。

## AI評価サンプル予定

```text
1シグナル最大80件
LOSS系 最大45件
WIN/SMALL_WIN/BREAKEVEN等 最大35件
8シグナル合計 最大640件
AI実行前に必ず audit-only を通す
```

## DISC8 一覧

| order | candidate_id | direction | TP | SL | RR | trades | WR | PF | Test PF |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | `DISC_01_BUY_TP200_SL100_RR2` | BUY | 200 | 100 | 2.00 | 107 | 0.6262 | 3.3500 | 4.4000 |
| 2 | `DISC_02_BUY_TP80_SL50_RR1p6` | BUY | 80 | 50 | 1.60 | 94 | 0.7340 | 4.4160 | 2.0571 |
| 3 | `DISC_04_BUY_TP150_SL100_RR1p5` | BUY | 150 | 100 | 1.50 | 92 | 0.6739 | 3.0649 | 3.0000 |
| 4 | `DISC_05_BUY_TP80_SL50_RR1p6` | BUY | 80 | 50 | 1.60 | 105 | 0.6857 | 3.4909 | 2.4889 |
| 5 | `DISC_06_SELL_TP80_SL50_RR1p6` | SELL | 80 | 50 | 1.60 | 118 | 0.6780 | 3.3684 | 2.4000 |
| 6 | `DISC_08_BUY_TP200_SL100_RR2` | BUY | 200 | 100 | 2.00 | 159 | 0.5220 | 2.0253 | 2.7500 |
| 7 | `DISC_09_BUY_TP80_SL50_RR1p6` | BUY | 80 | 50 | 1.60 | 193 | 0.5907 | 2.3089 | 2.0923 |
| 8 | `DISC_11_SELL_TP80_SL50_RR1p6` | SELL | 80 | 50 | 1.60 | 79 | 0.5949 | 2.3500 | 2.4000 |

---

## 1. `DISC_01_BUY_TP200_SL100_RR2`

```text
direction: BUY
exit_model: TP200_SL100_RR2
tp_pips: 200
sl_pips: 100
rr: 2.0
```

Machine rule:

```text
h4_donch_pos_32 > 0.9956 AND h4_ret_8_atr > 2.196 AND donch_pos_72 <= 0.8082
```

Conditions JSON:

```json
[
  {"feature": "h4_donch_pos_32", "operator": ">", "threshold": 0.9956},
  {"feature": "h4_ret_8_atr", "operator": ">", "threshold": 2.196},
  {"feature": "donch_pos_72", "operator": "<=", "threshold": 0.8082}
]
```

Notification:

```text
GOLD BUY DISC_01_BUY_TP200_SL100_RR2 TP200/SL100
買い条件: H4が直近32本レンジの高値圏/上抜けが強い/上側（h4_donch_pos_32 > 0.9956）、H4直近8本の上昇モメンタムが強い/上側（h4_ret_8_atr > 2.196）、M15の直近72本レンジ位置が抑制/下側（donch_pos_72 <= 0.8082）
```

---

## 2. `DISC_02_BUY_TP80_SL50_RR1p6`

```text
direction: BUY
exit_model: TP80_SL50_RR1p6
tp_pips: 80
sl_pips: 50
rr: 1.6
```

Machine rule:

```text
d1_adx14 > 13.03 AND donch_pos_32 <= 0.3689 AND h1_donch_pos_48 > 0.7981 AND d1_macd_hist <= 5.422
```

Conditions JSON:

```json
[
  {"feature": "d1_adx14", "operator": ">", "threshold": 13.03},
  {"feature": "donch_pos_32", "operator": "<=", "threshold": 0.3689},
  {"feature": "h1_donch_pos_48", "operator": ">", "threshold": 0.7981},
  {"feature": "d1_macd_hist", "operator": "<=", "threshold": 5.422}
]
```

Notification:

```text
GOLD BUY DISC_02_BUY_TP80_SL50_RR1p6 TP80/SL50
買い条件: D1トレンド強度が強い/上側（d1_adx14 > 13.03）、M15の直近32本レンジ位置が抑制/下側（donch_pos_32 <= 0.3689）、H1の直近48本レンジ位置が強い/上側（h1_donch_pos_48 > 0.7981）、D1 MACDヒストグラムが抑制/下側（d1_macd_hist <= 5.422）
```

---

## 3. `DISC_04_BUY_TP150_SL100_RR1p5`

```text
direction: BUY
exit_model: TP150_SL100_RR1p5
tp_pips: 150
sl_pips: 100
rr: 1.5
```

Machine rule:

```text
h4_donch_pos_16 <= 1.11 AND d1_adx14 > 14.53 AND ret_96_atr <= 17.8 AND donch_pos_8 > 0.5705 AND h1_ret_8_atr > 3.818
```

Conditions JSON:

```json
[
  {"feature": "h4_donch_pos_16", "operator": "<=", "threshold": 1.11},
  {"feature": "d1_adx14", "operator": ">", "threshold": 14.53},
  {"feature": "ret_96_atr", "operator": "<=", "threshold": 17.8},
  {"feature": "donch_pos_8", "operator": ">", "threshold": 0.5705},
  {"feature": "h1_ret_8_atr", "operator": ">", "threshold": 3.818}
]
```

Notification:

```text
GOLD BUY DISC_04_BUY_TP150_SL100_RR1p5 TP150/SL100
買い条件: H4の直近16本レンジ位置が抑制/下側（h4_donch_pos_16 <= 1.11）、D1トレンド強度が強い/上側（d1_adx14 > 14.53）、M15直近96本の変化率が抑制/下側（ret_96_atr <= 17.8）、M15直近8本レンジ位置が強い/上側（donch_pos_8 > 0.5705）、H1直近8本の変化率が強い/上側（h1_ret_8_atr > 3.818）
```

---

## 4. `DISC_05_BUY_TP80_SL50_RR1p6`

```text
direction: BUY
exit_model: TP80_SL50_RR1p6
tp_pips: 80
sl_pips: 50
rr: 1.6
```

Machine rule:

```text
d1_adx14 > 13.03 AND donch_pos_32 <= 0.3689 AND h1_donch_pos_48 > 0.7981 AND h1_ret_72_atr <= 6.742
```

Conditions JSON:

```json
[
  {"feature": "d1_adx14", "operator": ">", "threshold": 13.03},
  {"feature": "donch_pos_32", "operator": "<=", "threshold": 0.3689},
  {"feature": "h1_donch_pos_48", "operator": ">", "threshold": 0.7981},
  {"feature": "h1_ret_72_atr", "operator": "<=", "threshold": 6.742}
]
```

Notification:

```text
GOLD BUY DISC_05_BUY_TP80_SL50_RR1p6 TP80/SL50
買い条件: D1トレンド強度が強い/上側（d1_adx14 > 13.03）、M15の直近32本レンジ位置が抑制/下側（donch_pos_32 <= 0.3689）、H1の直近48本レンジ位置が強い/上側（h1_donch_pos_48 > 0.7981）、H1直近72本の変化率が抑制/下側（h1_ret_72_atr <= 6.742）
```

---

## 5. `DISC_06_SELL_TP80_SL50_RR1p6`

```text
direction: SELL
exit_model: TP80_SL50_RR1p6
tp_pips: 80
sl_pips: 50
rr: 1.6
```

Machine rule:

```text
macd_hist > 3.026 AND h4_ret_48_atr <= 0.9836 AND h1_donch_pos_8 > 0.409
```

Conditions JSON:

```json
[
  {"feature": "macd_hist", "operator": ">", "threshold": 3.026},
  {"feature": "h4_ret_48_atr", "operator": "<=", "threshold": 0.9836},
  {"feature": "h1_donch_pos_8", "operator": ">", "threshold": 0.409}
]
```

Notification:

```text
GOLD SELL DISC_06_SELL_TP80_SL50_RR1p6 TP80/SL50
売り条件: M15 MACDヒストグラムが強い/上側（macd_hist > 3.026）、H4直近48本の変化率が抑制/下側（h4_ret_48_atr <= 0.9836）、H1直近8本レンジ位置が強い/上側（h1_donch_pos_8 > 0.409）
```

---

## 6. `DISC_08_BUY_TP200_SL100_RR2`

```text
direction: BUY
exit_model: TP200_SL100_RR2
tp_pips: 200
sl_pips: 100
rr: 2.0
```

Machine rule:

```text
h4_donch_pos_32 > 0.9956 AND h4_ret_8_atr > 2.196 AND h4_donch_pos_4 <= 1.906 AND dist_ema50_atr <= 2.897
```

Conditions JSON:

```json
[
  {"feature": "h4_donch_pos_32", "operator": ">", "threshold": 0.9956},
  {"feature": "h4_ret_8_atr", "operator": ">", "threshold": 2.196},
  {"feature": "h4_donch_pos_4", "operator": "<=", "threshold": 1.906},
  {"feature": "dist_ema50_atr", "operator": "<=", "threshold": 2.897}
]
```

Notification:

```text
GOLD BUY DISC_08_BUY_TP200_SL100_RR2 TP200/SL100
買い条件: H4が直近32本レンジの高値圏/上抜けが強い/上側（h4_donch_pos_32 > 0.9956）、H4直近8本の上昇モメンタムが強い/上側（h4_ret_8_atr > 2.196）、H4直近4本レンジ位置が抑制/下側（h4_donch_pos_4 <= 1.906）、M15価格とEMA50の距離が抑制/下側（dist_ema50_atr <= 2.897）
```

---

## 7. `DISC_09_BUY_TP80_SL50_RR1p6`

```text
direction: BUY
exit_model: TP80_SL50_RR1p6
tp_pips: 80
sl_pips: 50
rr: 1.6
```

Machine rule:

```text
d1_adx14 > 13.03 AND donch_pos_32 <= 0.3689 AND h1_donch_pos_48 > 0.7981
```

Conditions JSON:

```json
[
  {"feature": "d1_adx14", "operator": ">", "threshold": 13.03},
  {"feature": "donch_pos_32", "operator": "<=", "threshold": 0.3689},
  {"feature": "h1_donch_pos_48", "operator": ">", "threshold": 0.7981}
]
```

Notification:

```text
GOLD BUY DISC_09_BUY_TP80_SL50_RR1p6 TP80/SL50
買い条件: D1トレンド強度が強い/上側（d1_adx14 > 13.03）、M15の直近32本レンジ位置が抑制/下側（donch_pos_32 <= 0.3689）、H1の直近48本レンジ位置が強い/上側（h1_donch_pos_48 > 0.7981）
```

---

## 8. `DISC_11_SELL_TP80_SL50_RR1p6`

```text
direction: SELL
exit_model: TP80_SL50_RR1p6
tp_pips: 80
sl_pips: 50
rr: 1.6
```

Machine rule:

```text
macd_hist > 3.026 AND h4_ret_48_atr <= 0.9836 AND h1_donch_pos_8 > 0.409 AND h4_dist_ema200_atr <= 0.5223
```

Conditions JSON:

```json
[
  {"feature": "macd_hist", "operator": ">", "threshold": 3.026},
  {"feature": "h4_ret_48_atr", "operator": "<=", "threshold": 0.9836},
  {"feature": "h1_donch_pos_8", "operator": ">", "threshold": 0.409},
  {"feature": "h4_dist_ema200_atr", "operator": "<=", "threshold": 0.5223}
]
```

Notification:

```text
GOLD SELL DISC_11_SELL_TP80_SL50_RR1p6 TP80/SL50
売り条件: M15 MACDヒストグラムが強い/上側（macd_hist > 3.026）、H4直近48本の変化率が抑制/下側（h4_ret_48_atr <= 0.9836）、H1直近8本レンジ位置が強い/上側（h1_donch_pos_8 > 0.409）、H4価格とEMA200の距離が抑制/下側（h4_dist_ema200_atr <= 0.5223）
```

## 次の実装予定

次はこの8条件をsource of truthとして、`static_rule_trade_ledger.csv` からAI評価サンプルを抽出する。

予定ファイル:

```text
scripts/gold_specialist_8/build_gold_data_driven_ai_review_sample_80_loss45.py
scripts/gold_specialist_8/run_gold_data_driven_ai_review_sample_80_loss45_AUDIT_ONLY.bat
data/gold_specialist_8/verification/ai_review_data_driven/ai_review_sample_80_loss45.csv
```

停止条件:

```text
DISC8が8件揃わない
sample_total > 640
strategy別 sample_total > 80
strategy別 loss_sample > 45
source ledger の candidate_id がこの定義と一致しない
```
