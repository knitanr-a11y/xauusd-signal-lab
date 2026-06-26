# GOLD_ML_V1 多角的候補再探索 — 2026-06-26

Status: `MULTIVIEW_RESEARCH_WATCHES_FOUND_NO_AUTOMATIC_ACCUMULATION`

## WATCH-025-A

WATCH-025-Aは削除せず、`RESEARCH_WATCH_PENDING_FULL_AUDIT` として保持する。研究・再実行・比較は可能。完全な実装、trade registry、選定契約、閾値近傍、コスト、重複、将来データ確認がそろえば積み重ねへ昇格できる。現時点では積み重ね数へ含めず、portfolio使用は禁止する。

## 探索範囲

12 mechanismをLONG・SHORT別に探索した。上位足押し戻り、breakout、compression release、liquidity sweep、failed breakout、impulse continuation、inside/NR expansion、session range、overextension、regime flip、volatility expansion、multi-timeframe alignmentを含む。

ATR固定・構造SL、2R/3R/4R、12/24/48時間を分けた。

- 解釈可能rule: 604
- union event: 27,942
- 評価profile: 19,147
- 2023初期合格: 555
- 2023時系列安定＋近傍支持: 513
- 凍結profile: 28
- 一次厳格合格: 0

一次探索上位を、上位足構造、値位置、ボラティリティ、確認足、時間帯へ分解し、raw eventからone-openを完全再実行した。

## GML1-WATCH-026-A

H1/H4 bullishの強いM15 impulse breakout LONG。ただしM5 EMA gapとH1の直前上昇が伸び過ぎていない場面に限定する。

- 59件
- 勝率44.1%
- PF2.749
- 平均+0.978R
- 平均勝ち3.489R
- 合計+57.72R
- DD4.56R
- 強コストPF2.439

閾値近傍にPF2以上の隣接cellが複数ある。既存候補とのexact entry一致は0だが、H1-D1 LONG lineageとは近接・同時保有があるためportfolio独立性は未確定。

## GML1-WATCH-027-A

H4 bullish環境で、M15 inside圧縮がH4下ヒゲ拒否とM15 momentum expansionを伴って上方解放されるLONG。

- 101件
- 勝率36.6%
- PF2.228
- 平均+0.778R
- 平均勝ち3.853R
- 合計+78.56R
- DD8R

件数補完力は高いが、spread 1.5倍＋slippageでPF1.917、強コストでPF1.616。既存LONG発火±60分を除いた部分はPF1.987で、costと重複に敏感。

## GML1-WATCH-028-A

H4 bearish環境で、M15がEMA20を再度下抜き、M5 bearish HOLD/BOSが出る早期トレンド再開SHORT。暴落後の追い売りを避けるため、H4高値距離とM5傾斜を制限する。

- 59件
- 勝率40.7%
- PF2.743
- 平均+1.034R
- 平均勝ち4R
- 合計+61R
- DD12R
- 強コストPF2.029

既存LONG候補とのexact entryと±60分一致は0で独立性は高い。ただし2024年PF1.143とDD12Rが弱いため、積み重ねではなくWATCH-onlyとする。

## 現在の状態

積み重ね候補は10件のまま。

- 既存9候補
- GML1-WATCH-024-A

Research WATCH pool:

- GML1-WATCH-025-A: 再監査待ちLONG仮説
- GML1-WATCH-026-A: impulse continuation LONG
- GML1-WATCH-027-A: compression expansion LONG
- GML1-WATCH-028-A: trend resumption SHORT

2024〜2026を確認後に最終条件を選んだため、3候補とも未使用holdout合格ではない。固定したまま2026-06-26より後のprospective確認とauthoritative exact overlapを完了するまで積み重ねへ昇格しない。health gate、live、MT5、DiscordはOFFのまま。
