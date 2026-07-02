# BTC研究マスター追補：BTC7R採用・BTC9追加

作成日: 2026-07-02

## BTC7Rの採否変更

`BTC7R_M15_IMPULSE_HIGH_WIN_24_96_M22_R110`

ユーザー判断により、暫定候補から**積み重ね採用候補**へ昇格した。

現在の状態:

- `ADOPTED_STACKING_CANDIDATE_NOT_LIVE`
- ロット未設定
- 61件
- 45勝16敗
- 勝率73.77%
- PF2.956
- 合計+2,248.81pips
- 最大DD230.34pips
- 2026年以降のentry-only候補22件
- 2026年以降の損益未評価
- Discord OFF
- 注文 OFF
- `live_ready=false`
- `final_signal=false`

BTC7の低勝率基準238件は研究比較用に残すが、積み重ね監視ではBTC7Rを使用する。

## BTC9の追加探索

別ベクトルとして、確定済み前日高値・安値を使う価格構造候補を探索した。

完了した比較:

- 前日高値・安値の順張りブレイク
- 前日高値・安値のスイープ逆張り

UTCセッションのオープニングレンジブレイクは広いグリッドを試作したが、探索実行時間内に全比較が完了しなかったため、BTC9の選定・成績には使用していない。

TRAINとDEVだけで条件を選定し、正式確認期間は凍結後に開いた。

### 残った候補

`BTC9_M15_PREVDAY_BREAKOUT_H1_CLV85_RISK100_R110`

条件:

- 前日の確定済みUTC日足高値・安値。
- H1 EMA50/EMA200方向、EMA200の4時間傾斜、EMA間距離0.5ATR以上。
- 当日最初のM15終値ブレイクだけ。
- LONGは終値位置上位15%、SHORTは下位15%。
- 次の正確なM5始値でエントリー。
- SLはシグナル足外側0.1 M15 ATR14。
- 予定リスク100pips以下。
- TP1.1R。
- 最低純利益50pips。
- 同一M5足はSL優先。

結果:

| 期間 | 件数 | 勝ち | 負け | 勝率 | PF | 合計pips | 最大DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRAIN | 29 | 18 | 11 | 62.07% | 1.881 | +657.85 | 201.13 |
| DEV | 21 | 11 | 10 | 52.38% | 1.697 | +377.18 | 164.40 |
| 探索合計 | 50 | 29 | 21 | 58.00% | 1.804 | +1,035.03 | 201.13 |
| 正式確認 | 31 | 19 | 12 | 61.29% | 1.860 | +666.88 | 178.94 |
| 全体 | 81 | 48 | 33 | 59.26% | 1.825 | +1,701.91 | 201.13 |

既存候補との完全一致:

- BTC4: 0件
- BTC5: 0件
- BTC6: 0件
- BTC7R: 8件

BTC9の81件のうち73件は、既存BTC4・BTC5・BTC6・BTC7Rにない新しい正確なエントリー時刻。

既存候補群とBTC9を合わせた評価済みユニークエントリー時刻は170件。

現在の状態:

- `PROVISIONAL_CANDIDATE_NOT_ADOPTED`
- ロット未設定
- 2026年以降のentry-only候補26件
- 2026年以降の損益未評価
- Discord OFF
- 注文 OFF
- `live_ready=false`
- `final_signal=false`

詳細:

- `docs/btc_ml_v1/BTC9_M15_PREVDAY_BREAKOUT_EXPLORATION.md`
- `configs/btc_ml_v1/btc9_m15_prevday_breakout_candidate.json`
- `scripts/btc_ml_v1/research/btc9_m15_prevday_breakout_candidate.py`

## 現在の積み重ね採用候補

| 候補 | 時間足 | 状態 | ロット |
|---|---|---|---:|
| BTC4_RISK_CAP_400 | H4 | 採用候補 | 0.02 |
| BTC5_TWO_PIVOT_P2_CLEAN_N_382_786 | M5 | 採用候補 | 未設定 |
| BTC6_M15_TWO_PIVOT_P3_BROAD_N_236_886 | M15 | 採用候補 | 未設定 |
| BTC7R_M15_IMPULSE_HIGH_WIN_24_96_M22_R110 | M15 | 積み重ね採用候補 | 未設定 |

BTC9は今回の新規暫定候補であり、ユーザー採否待ち。
