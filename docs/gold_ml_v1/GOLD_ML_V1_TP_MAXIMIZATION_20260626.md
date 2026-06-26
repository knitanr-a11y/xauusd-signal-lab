# GOLD_ML_V1 TP最大化探索 — 2026-06-26

Status: `TP100_ROBUST_MAX_WITH_TP75_PRACTICAL_PRIMARY`

## 探索方法

入口条件をTPに合わせて作り直さないため、以前のTP5〜10探索で2023事前基準を通った788入口ルールを固定した。同じ入口に対して固定TP5〜150、runner TP75〜200、SL4〜15、最大7日をexact M1で比較した。

強コストはspread2倍＋entry/exit各0.10ドル価格slippage。same-M1はprotective level優先。

## 結論

- 4年安定と実target hitを満たす固定TP上限: 100ドル価格
- 実用性重視の固定TP: 75ドル価格
- 100ドルを狙う実用runner: +50で25%確保、残り75%を+100へ
- TP125・150: 到達例はあるがtarget hitが2年に偏るためrobust maxではない
- TP200: runner到達0

## 共通入口

WATCH-034-A/B/Cは同じentry lineage。

- M15 Inside bar + NR7 compression
- H1/H4上方向整合
- MT5 server hour 19〜24
- bullish body fraction 0.50以上
- 確定M15で上方向breakout

## WATCH-034-A — 実用固定TP75

TP75 / protective distance 10 / 最大168時間。

| 条件 | 件数 | TP到達 | TP率 | PF | 平均 | 合計 | DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| 通常 | 96 | 18 | 18.8% | 2.403 | +9.939 | +954.17 | 74.25 |
| 強コスト | 98 | 17 | 17.3% | 2.195 | +8.744 | +856.90 | 70.70 |

強コストでも4年すべてtarget hitあり。2026年は17件、5回到達、PF3.090、+253.30。

## WATCH-034-B — 最大固定TP100

TP100 / protective distance 5 / 最大168時間。

| 条件 | 件数 | TP到達 | TP率 | PF | 平均 | 合計 | DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| 通常 | 112 | 6 | 5.4% | 2.195 | +5.067 | +567.47 | 80.00 |
| 強コスト | 112 | 7 | 6.3% | 2.095 | +4.785 | +535.87 | 81.60 |

4年すべて合計プラスだが、target hitは3年。2023年はTP100到達0でもtime exitを含む合計はプラス。絶対上限の研究variantであり、実用primaryではない。

## WATCH-034-C — TP100 runner

- initial protective distance 8
- +50で25%を確保
- 残り75%を+100へ
- +50到達後は残りのprotective levelを+10へ
- 最大168時間

| 条件 | 件数 | +50到達率 | +100到達 | +100率 | PF | 平均 | 合計 | DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 通常 | 101 | 23.8% | 8 | 7.9% | 2.573 | +8.845 | +893.37 | 68.0 |
| 強コスト | 101 | 21.8% | 7 | 6.9% | 2.279 | +7.489 | +756.37 | 69.2 |

強コスト4年すべてプラス、worst-year PF1.545。固定TP100より平均利益とDDのバランスが良い。

## 2026強コスト

- WATCH-034-A: 17件、TP75到達5、PF3.090、+253.30
- WATCH-034-B: 16件、TP100到達2、PF2.798、+128.40
- WATCH-034-C: 17件、TP100 runner到達3、PF2.679、+176.80

## 判定

TP最大化という意味の上限はWATCH-034-Bの100ドル。ただし実運用候補としてはWATCH-034-AのTP75が最もtarget hitの年分散と期待値が良い。100ドルを維持しながら実用性を上げる案はWATCH-034-C。

いずれもexit gridを確認後に選択したpost-audit candidateなので、2026-06-26より後の固定prospective専用。積み重ね15候補、portfolio、live、MT5、Discordは変更しない。
