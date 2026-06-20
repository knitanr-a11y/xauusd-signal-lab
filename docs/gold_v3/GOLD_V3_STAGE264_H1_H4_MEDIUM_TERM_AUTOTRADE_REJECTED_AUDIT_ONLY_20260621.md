# GOLD V3 Stage264 H1/H4中期自動売買監査

作成日: 2026-06-21  
正式状態: `GOLD_V3_264_H1_H4_MEDIUM_TERM_AUTOTRADE_REJECTED_AUDIT_ONLY`

## 結論

H1本命・H4比較の2戦略を、結果前に固定したD1/H4方向一致、H1押し戻り回復、H4ブレイク、ATR連動SL/TP、同日内最大6〜8時間保有で監査した。

両方とも不採用。

### Strategy A H1 pullback reclaim

- raw candidates: 308
- resolved trades: 224
- coverage: 100.00%
- cost2 PnL: -645.64 USD
- cost2 expectancy: -2.882 USD
- cost2 PF: 0.545
- cost5 expectancy: -5.882 USD
- max drawdown: 752.54 USD

2023〜2026の全年度がcost2赤字。LONG・SHORTも両方赤字。

### Strategy B H4 aligned breakout

- raw candidates: 256
- resolved trades: 223
- coverage: 99.55%
- cost2 PnL: -475.37 USD
- cost2 expectancy: -2.132 USD
- cost2 PF: 0.701
- cost5 expectancy: -5.132 USD
- max drawdown: 552.87 USD

2021年と2025年だけ小幅黒字で、2020〜2024合算は-484.49 USD。LONG・SHORTも両方赤字。

## 予備診断との違い

予備診断では、D1/H4 EMA方向一致後に無条件で次足へ入り、24〜48時間保有する広いtrend exposureが2025〜2026で利益を出していた。

正式Stage264では、

- H1押し戻り回復またはH4ブレイクを待つ
- ATR SL/TPを置く
- session端を跨がないよう6〜8時間で終了する
- cost2 / cost5を監査する

という自動売買可能な契約へ変えた。

結果が赤字になったため、予備診断の利益は精密なentry timing edgeではなく、主として2025〜2026の長時間trend exposureに依存していたと解釈する。

## H1年別

| 年 | trades | cost2 PnL | expectancy | PF |
|---|---:|---:|---:|---:|
| 2023 | 49 | -128.02 | -2.613 | 0.334 |
| 2024 | 67 | -180.97 | -2.701 | 0.426 |
| 2025 | 72 | -269.67 | -3.745 | 0.459 |
| 2026 | 36 | -66.98 | -1.861 | 0.838 |

## H4年別

| 年 | trades | cost2 PnL | expectancy | PF |
|---|---:|---:|---:|---:|
| 2020 | 31 | -56.97 | -1.838 | 0.651 |
| 2021 | 21 | +3.77 | +0.180 | 1.046 |
| 2022 | 43 | -143.38 | -3.334 | 0.544 |
| 2023 | 18 | -58.34 | -3.241 | 0.341 |
| 2024 | 39 | -229.58 | -5.887 | 0.276 |
| 2025 | 56 | +21.29 | +0.380 | 1.047 |
| 2026 | 15 | -12.16 | -0.811 | 0.930 |

## 方向別

### H1

- LONG: 179 trades、PnL -617.28、expectancy -3.449、PF 0.453
- SHORT: 45 trades、PnL -28.36、expectancy -0.630、PF 0.902

### H4

- LONG: 167 trades、PnL -258.46、expectancy -1.548、PF 0.776
- SHORT: 56 trades、PnL -216.91、expectancy -3.873、PF 0.503

方向片側だけ残す救済は成立しない。

## exit内訳

### H1

- SL_EXIT: 127
- TP_EXIT: 49
- TIME_EXIT: 48
- one-active suppressed: 84
- data blocked: 0

### H4

- SL_EXIT: 68
- TP_EXIT: 12
- TIME_EXIT: 143
- one-active suppressed: 32
- data blocked: 1

H4ではTP到達が少なく、2.5ATR targetへ届く前にTIME_EXITまたはSLになる比率が高かった。ただし結果後にTP/SLや保有時間を変更しない。

## causal / M1監査

- prefix signal parity: 12/12 PASS
- H1 M1 path対象: 35 trades、entry price parity 100%、exit reason match 100%、PnL一致100%
- H4 M1 path対象: 15 trades、entry price parity 100%、exit reason match 100%、PnL一致100%

2026年のM1範囲ではH1/H4 bar判定とM1 pathが一致した。敗因はtimestampや同一bar順序の不具合ではない。

## 合否

### H1

PASS:
- trade数
- coverage
- LONG/SHORT件数
- 年間gross profit集中
- DD / gross profit
- M1 entry parity

FAIL:
- cost2 expectancy
- PF 1.15
- cost5 expectancy
- 2023+2024 PnL
- LONG/SHORT各PnL

### H4

PASS:
- trade数
- coverage
- LONG/SHORT件数
- 年間gross profit集中
- DD / gross profit
- M1 entry parity

FAIL:
- cost2 expectancy
- PF 1.15
- cost5 expectancy
- 2020〜2024 PnL
- LONG/SHORT各PnL

## formal verdict

`H1_H4_MEDIUM_TERM_AUTOTRADE_REJECTED`

この固定2戦略はEA化しない。

ただし、高時間足という研究領域全体を完全否定する結果ではない。今回否定されたのは、

- EMA20/50方向一致
- H1 pullback reclaim
- H4 6-bar breakout
- ATR 1:2 risk/reward
- 同日内6〜8時間保有

の固定組合せ。

次に同じデータで多数のH1/H4parameterを探索すると2025〜2026への過学習になるため禁止。

## 次の合理的な分岐

自動売買を残すなら、次は同じentry parameter探索ではなく、構造を変える必要がある。

1. 日跨ぎを許可する正式broker calendar・swap込みのmulti-day trend following。
2. 完全に価格だけで定義する長期channel breakout＋volatility sizing。
3. 複数資産のtrend-following portfolioへ拡張してgold単独依存を下げる。

いずれもStage264のTP/SL微調整ではなく別研究として事前固定する。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
