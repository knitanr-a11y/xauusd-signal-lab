# GOLD_ML_V1 広域・狭SL候補探索 — 2026-06-26

Status: `ONE_HIGH_COVERAGE_RESEARCH_WATCH_FOUND_NO_AUTOMATIC_ACCUMULATION`

## WATCH-030-AのSL縮小

WATCH-030-AのTP+5 / emergency SL-10を、SL3〜7.5ドルや建値移動へ変更して再検証した。

- 元のTP5 / SL10 / 12時間: 106件、PF1.849、合計+178.11、4年すべてプラス
- TP5 / SL5 / 12時間: 114件、PF1.502、合計+109.71、プラス年3、最悪年PF0.936

SLを縮めるほど全期間PFと年別安定性が低下した。WATCH-030-Aは変更せず、新候補を狭SLで作る。

## 広域探索

以下11familyをraw M15/M5/H1/H4/M1から探索した。

- 前日高安スイープ・反転
- 前日高安ブレイク
- VWAP reclaim
- VWAP trend pullback
- 日始値reclaim
- 完了済み時間帯レンジのスイープ・ブレイク
- opening range fakeout・breakout
- EMA pullback
- Bollinger mean reversion
- inside + NR7 compression breakout
- rolling high-low failure・breakout

TP3/4/5、SL3/4/5/6、4/8/12時間を比較。

- 4,208ルール
- 49,306ユニーク発火
- 143,643profile
- 2023事前基準通過8,155
- family/direction別凍結97
- 固定外部診断の厳格profile 141
- spread2倍＋往復0.10滑りを通したprofile 57

## GML1-WATCH-031-A

4種類をlane内one-openで統合した狭SL coverage候補。

### COMP_DAY LONG

- H1/H4整合
- prior inside + NR7
- 前高値を0.10ATR以上上抜け
- bullish body fraction 0.50以上
- MT5時間10〜16
- TP5 / SL4 / 最大4時間

### COMP_NIGHT LONG

- 同じcompression breakout
- MT5時間19〜24
- TP3 / SL4 / 最大8時間

### ROLL20_NIGHT LONG

- 直近20本安値を0.30ATR以上下へスイープ
- 同じ確定M15で安値内側へ回復
- MT5時間19〜24
- TP5 / SL5 / 最大8時間

### BLOCK_SWEEP SHORT

- 完了したMT5時間07〜13レンジ高値を0.30ATR以上スイープ
- range state
- 上ヒゲ率15%以上
- 終値が足の下側25%以内
- MT5時間13〜19
- TP4 / SL3 / 最大8時間

全componentの平均SLは3.766ドル価格。

## 成績

| 年 | 件数 | PF | 合計 |
|---|---:|---:|---:|
| 2023 | 113 | 1.589 | +85.38 |
| 2024 | 129 | 1.531 | +100.78 |
| 2025 | 123 | 1.311 | +65.77 |
| 2026年6月19日まで | 59 | 1.347 | +35.00 |
| 全期間 | 424 | 1.444 | +286.93 |

全期間勝率56.6%、平均+0.677、最大DD43。

## 強コスト

spread2倍＋entry/exit各0.10ドル滑り:

- 423件
- 勝率53.4%
- PF1.213
- 平均+0.356
- 合計+150.75
- 最大DD52.8
- 2023〜2026の4年すべてプラス

## 2026年月別

| 月 | 件数 | 合計 |
|---|---:|---:|
| 1月 | 13 | +20 |
| 2月 | 8 | +30 |
| 3月 | 12 | +19 |
| 4月 | 14 | -13 |
| 5月 | 8 | -13 |
| 6月19日まで | 4 | -8 |

2026年全体はプラスだが、4〜6月単独は弱い。これが即積み重ねへ昇格させない主因。

## 重複

既存15候補に対する重複:

- LONG exact 1.89%、±60分 7.17%
- SHORT exact 3.14%、±60分 5.66%

低重複だがゼロではない。

## 構造SL監査

スイープ足・inside足などの構造にSLを置き、実SLを2.5〜5ドルへ限定する方法も検証した。しかし2026年の高ボラ相場では構造SLが5ドルを超えるケースが多く、現在の発火がほぼ消えた。残ったvariantも強コストで安定しなかった。

したがって、このlaneでは固定SL3〜5ドルの方が価格水準変化に対して安定した。

## WATCH-029-A + WATCH-030-A + WATCH-031-A 参考統合

registryを時系列に並べ、全体one-openにした参考診断。authoritativeなraw-event portfolio parityではない。

- 697件
- 勝率66.3%
- PF1.799
- 平均+1.282
- 合計+893.79
- 最大DD54.53

2026年:

- 93件
- 勝率66.7%
- PF1.861
- 合計+130

月別件数は19 / 15 / 18 / 18 / 13 / 10。

## 判定

WATCH-031-Aは件数不足を埋める力があり、SLも3〜5ドルに限定できる。ただし、強コストPFは1.213で、高信頼候補より薄い。また2026年4〜6月が弱い。

そのためResearch WATCHとして固定し、2026-06-26より後の固定prospective確認前には積み重ね・portfolio・liveへ使用しない。WATCH-030-Aは既存ルールのまま積み重ね候補として保持する。
