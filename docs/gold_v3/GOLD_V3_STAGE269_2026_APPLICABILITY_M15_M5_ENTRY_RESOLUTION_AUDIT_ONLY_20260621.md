# GOLD V3 Stage269 2026 applicability / M15-M5 entry-resolution audit

作成日: 2026-06-21  
正式状態: `GOLD_V3_269_2026_APPLICABLE_REGIMES_FOUND_NO_STRICT_SHORT_ENTRY_LEAD_AUDIT_ONLY`

## 結論

Stage268で残ったH1 regimeは、2026年単独でも平均・中央値がLONG/SHORT双方でプラスだった。ただしStage268の発見に2026年を使用済みなので、これはclean holdoutではなく`PROVISIONALLY_APPLICABLE_2026_CONTAMINATED`である。

M15/M5をH1 regime内のentry timingとして探索した結果:

- strict entry-resolution lead: 0
- near lead: M15 false-break reclaim × H1 indecision/range
- M5はentry timing改善を確認できず
- 一部triggerは良い候補を選別したが、同じ候補を即時entryした場合よりentry価格・MAEが悪化した

## 2026 regime applicability

### R1 H1 weak trend × low volatility / 48h

- n=208
- positive rate=53.85%
- mean=+0.957 ATR
- median=+0.291 ATR
- LONG n=128、positive=53.13%、mean=+0.709、median=+0.189
- SHORT n=80、positive=55.00%、mean=+1.353、median=+0.642

両方向プラスだが、2025のpositive 67.96%、median +2.983 ATRから大幅に弱化。2026でも残るが強いedgeとはまだ呼ばない。

### R2 H1 UTC08-11 × high volatility / bar continuation

48h:
- n=107
- positive=57.94%
- mean=+1.388 ATR
- median=+0.861 ATR
- LONG positive=54.90%、median=+0.464
- SHORT positive=60.71%、median=+0.903

72h:
- positive=55.14%
- mean=+1.470 ATR
- median=+1.008 ATR
- LONG positive=50.98%、median=+0.418
- SHORT positive=58.93%、median=+1.181

2026では48hの方が方向バランスが良い。

### R3 H1 indecision × range / bar continuation / 8h

- n=72
- positive=59.72%
- mean=+0.253 ATR
- median=+0.431 ATR
- LONG n=26、positive=57.69%、mean=+0.508、median=+0.282
- SHORT n=46、positive=60.87%、mean=+0.109、median=+0.437

3 regimeの中で短期horizonとして最も2026バランスが良い。

## H4 secondary 2026 diagnostic

- strong directional × conflict / 48h: n=35、positive65.71%、median+0.547 ATR
- indecision × weak trend / 12h: n=27、positive55.56%、median+0.329
- opposed × healthy extension / 12h: n=45、positive55.56%、median+0.216
- strong directional × weak trend / 8h: n=36、positive55.56%、median+0.175

すべて両方向の平均・中央値はプラスだが、2026件数が少ないためM15/M5主探索には使用しなかった。

## M15/M5 entry-resolution探索

### 唯一のnear lead

`R3 H1 indecision/range × M15 false-break reclaim`

- triggered=178
- coverage=77.06%
- positive rate=58.99%
- median return=+0.321 ATR
- 同じcandidateの即時entry中央値=+0.220 ATR
- paired median return improvement=+0.119 ATR
- median MAE improvement=+0.231 ATR
- 2025 mean=+0.255、median=+0.319
- 2026 mean=+0.133、median=+0.324

実際に待つことでentry timingとMAEが改善した唯一の候補。

しかし2026方向別:

- LONG n=20、mean=+0.461、median=+0.234
- SHORT n=35、mean=-0.054、median=+0.485

2026 SHORT平均が負のため、strict leadではなく:

`ENTRY_RESOLUTION_NEAR_LEAD_SOURCE_DIRECTION_UNSTABLE`

とする。SHORTだけ除外することは禁止。

## 良く見えるがentry timingではないもの

### R2 × M5 inside-bar release

48h:
- n=211、positive64.45%、median+1.765 ATR
- 2026 mean+2.289、median+1.240

72h:
- n=208、positive63.94%、median+2.270 ATR

ただし同じtrigger candidateを即時entryした場合よりpaired returnは約-0.16 ATR、MAEも悪化。これは強いcandidate subsetを見つけるfilter効果であり、M5 entryを待つ効果ではない。

### R3 × M15 compression release

- n=68
- positive69.12%
- median+0.642 ATR

同じcandidateの即時entryはpositive76.47%、median+0.992 ATR。trigger待ちでpaired median -0.248 ATR。selection filterでありentry improvementではない。

### R1 × M5 EMA20 pullback reclaim

- n=375
- positive62.40%
- median+1.589 ATR

同じcandidateの即時entryはpositive63.73%、median+1.942 ATR。paired median -0.176 ATR、MAEも悪化。multi-day low-vol trendでは短期足確認を待たずH1 activation付近の方が良い。

## M5とM15の違い

- M5 triggerはcoverageが高すぎ、ほぼ全regimeで発生するため選別力が弱い
- M5 false-breakはR3でcoverage96.6%、paired improvementは+0.026 ATRに留まった
- M15 false-breakはcoverage77.1%まで絞られ、paired return+0.119、MAE+0.231 ATR
- 今回はM15の方がentry解像度として有効

## correctness

- trigger_time < regime activation: 0
- entry_time < trigger_time: 0
- source crossing: 0
- M5 availability=time+5分
- M15 availability=time+15分
- regression tests: 4/4 PASS

## 正式判断

1. R1/R2/R3は2026でも暫定的に分布差を維持。
2. R2は48hを主horizonとする方が2026の方向バランスが良い。
3. M5/M15を入れれば自動的に改善するわけではない。
4. strict entry-resolution leadは0。
5. M15 false-break reclaim × R3だけをnear leadとして固定。
6. R1は短期足confirmationを待たない方が良い。
7. R2のM5 inside-barはentryではなく将来のsetup-quality filter研究候補。

## 次

pre-2025 M15/M5が現在ないため、同じ2025/2026でtriggerを増やすと過学習になる。

次に必要:

- 2023-2024 M15/M5（R3 M15 false-breakの固定条件検証）
- 可能なら同期間M1（exact activation/entry path）
- R2 M5 inside-barはentry timingではなくsetup filterとして別契約で検証

運用状態: `NO_LIVE_PROMOTION_AUDIT_ONLY`
