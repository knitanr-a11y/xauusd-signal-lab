# GOLD_ML_V1 勝率改善監査 — 2026-06-26

Status: `THREE_HIGH_CONFIDENCE_DERIVATIVES_FOUND_PROSPECTIVE_ONLY`

## 結論

4R利確を維持したまま、入口の成熟・過熱を除外することで勝率を改善できた。A候補は件数重視、B候補は勝率重視として親子別管理する。

| ID | 親 | 件数 | 勝率 | PF | 平均R | 合計R | DD |
|---|---|---:|---:|---:|---:|---:|---:|
| WATCH-026-B | WATCH-026-A | 30 | 63.3% | 5.956 | +1.817R | +54.52R | 2R |
| WATCH-027-B | WATCH-027-A | 35 | 57.1% | 5.146 | +1.777R | +62.20R | 2R |
| WATCH-028-B | WATCH-028-A | 31 | 61.3% | 6.333 | +2.065R | +64.00R | 6R |

3本をglobal one-openで合算した診断は91件、勝率58.2%、PF5.335、平均+1.810R、合計+164.74R、最大DD5R。

## WATCH-026-B

追加条件はM5 ADX14 <= 26.7394201216。強いM15 breakoutでも、M5 trendが既に完成した後を追わず、点火初期だけを通す。

- 通常: 30件、勝率63.3%、PF5.956
- spread2倍＋往復0.10 slippage: 勝率63.3%、PF5.702
- q33/q50/q67近傍: 勝率56.8〜63.3%、PF4.420〜5.956

## WATCH-027-B

追加条件はH4 ATR14/ATR50 <= 1.0272994926 AND H1 12本return/ATR <= 1.6743096954。inside expansionでも、H4 volatilityとH1上昇が既に過熱した局面を除外する。

- 通常: 35件、勝率57.1%、PF5.146
- spread2倍＋往復0.10 slippage: 勝率45.7%、PF3.095
- 近傍でもPFはプラスだが、勝率57%はWATCH-026-Bほどplateau安定ではない

## WATCH-028-B

追加条件はD1 BB20 width/ATR >= 2.7046129954 AND M5 range/ATR <= 1.3521477874。D1の値幅環境は必要だが、大き過ぎるM5陰線で追い売りしない。

- 通常: 31件、勝率61.3%、PF6.333
- spread2倍＋往復0.10 slippage: 32件、勝率53.1%、PF4.268
- 近傍: 24〜39件、勝率51.3〜62.1%、PF4.21〜6.55
- 2024単年は勝率33.3%だがPF2.0でプラス

## 共通原因

負けの中心は方向判定よりentry timingだった。

- 下位足ADXが既に高い
- confirmation barのrangeが大き過ぎる
- H1/H4の直前moveが既に伸び切っている

この状態では正しい方向でもentryが遅く、SL first-touchが増える。高信頼Bは「上位足方向があるが、下位足はまだ成熟前」の地点だけを残す。

## 判断

- 4R利確とstop構造は変更しない。
- A候補はcoverage用、B候補はhigh-confidence用として別管理。
- B候補は積み重ねへ自動昇格しない。
- 2026-06-26より後の固定prospective dataで確認する。
- 既存10候補、portfolio、health gate、live、MT5、Discordは変更しない。
