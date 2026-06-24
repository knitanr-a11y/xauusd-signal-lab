# GOLD V3 Stage330 Candidate Scarcity Decomposition Audit-Only

日付: 2026-06-24  
状態: `GOLD_V3_330_CANDIDATE_SCARCITY_DECOMPOSITION_AUDIT_ONLY`

## 目的

Stage329の固定anchorを変更せず、候補件数がどの段階で減っているかを分解し、勝率を維持しやすい「一軸だけ変更した兄弟候補」を探索する。

Stage330は候補採用、router再学習、final signal変更、MT5注文、Discord送信を行わない。結果はhuman audit用であり、自動昇格はない。

## 絶対維持事項

- GOLD V3 audit-only。
- GOLD V2、旧GOLD、DISC8、Stage41を読まない・使わない・fallbackにしない。
- Stage329のcontract、runtime state、journal、候補poolを変更しない。
- Stage328 contract/bootstrapを変更しない。
- CSV最新行はclosed。open/as-of判定は禁止。
- 時刻はMT5 server time。JST変換しない。
- TP/SL同一M1内はSL優先。
- RR 1.5、最大保有720分。
- source one-position適用後の純増だけを評価する。
- 2026年の結果を候補選定・順位付けに使わない。
- MT5注文、Discord、partial close、automatic promotionはOFF。

## 固定anchor

```text
M5_H4|MOCHI_UNION|SHORT|RR1_5|ATR_GE_1_AND_NO_ROUND
policy = RELATIVE_TRAILING_MEAN_R_N2
lane = BALANCED_OR_PREMIUM
cost = 1p0x
```

Stage329 watch JSONのstatus、固定contract、frozen lineage SHA、安全フラグ、integrity passを実行前に検証する。Stage330はStage329のruntime stateまたはjournalを読み書きしない。

## 開発・選定期間

```text
2024-01-01 00:00:00 inclusive
2026-01-01 00:00:00 exclusive
```

2024年と2025年だけを候補比較に使用する。M1は2026-01-01より前で切り、年境界を越える未完了tradeに2026年のTP/SL/exitを使用しない。

## 比較する一軸variant

| variant | 変更軸 | 内容 |
|---|---|---|
| `ANCHOR_STAGE329_EXACT` | なし | Stage329 source条件そのまま |
| `RELAX_ATR_MIN_TO_0P90_ONLY` | ATRのみ | ATR ratio下限を1.00から0.90へ変更 |
| `ALLOW_ROUND_NUMBER_ONLY` | roundのみ | round近傍除外だけを解除 |
| `ALLOW_OUTSIDE_FIXED_LANE_ONLY` | laneのみ | SHORT・ATR・round条件は維持し、Balanced/Premium外も研究対象にする |
| `LONG_MIRROR_DIAGNOSTIC_ONLY` | 方向鏡像 | 同条件LONG。候補選定対象ではなく方向非対称の診断専用 |

複数条件の同時緩和はStage330では行わない。

## scarcity flow

各variantについて、次を順番に出力する。

1. 4 MOCHIPOYO trackのraw onset
2. direction
3. ATR ratio
4. round除外
5. decision時刻canonical統合
6. lane membership
7. tradable preparation
8. source one-position accepted
9. accepted resolved

前段からの減少数とretention rateをCSVに保存する。

## incremental評価

兄弟variant単体の成績だけでは採用判断しない。

Stage329 anchorをpriority 0、兄弟variantをpriority 10として同じsource one-positionに通し、anchorを置換せずに残った兄弟tradeだけを`pure incremental`として評価する。

次を分離して出力する。

- standalone accepted resolved
- anchorとのexact decision overlap
- anchor + sibling combined
- anchor precedence後のpure incremental resolved
- 2024/2025年別件数
- win rate、PF、total R、max DD、largest winner share
- 95% Wilson win-rate interval

## human review bucket

### A_PROMISING_HUMAN_REVIEW_ONLY

- pure incremental resolvedが20件以上
- 2024年、2025年の各年5件以上
- combined勝率低下が2 percentage points以内
- combined PFがanchor未満にならない
- combined total Rが増える
- added max DDが2R以内

### B_MORE_SAMPLE_OR_MIXED_HUMAN_REVIEW_ONLY

- pure incremental resolvedが10件以上
- combined勝率低下が3 percentage points以内
- combined PFがanchorの95%以上
- combined total Rが増える

いずれも採用・昇格ではない。Aでもhuman auditを開始できるだけで、Stage329やfinal signalは変更しない。

## context分解

以下をMT5 server time基準で集計する。

- ATR ratio band
- decision hour
- pooled track count
- pooled track combination
- router group

高ATR SHORT、時間帯偏り、単一track・複数trackの差を後続監査で判断できる形にする。

## 出力

```text
stage330_candidate_scarcity_decomposition.json
stage330_candidate_scarcity_flow.csv
stage330_candidate_variant_summary.csv
stage330_candidate_near_miss.csv
stage330_candidate_incremental_trades.csv
stage330_candidate_context_summary.csv
```

`near_miss.csv`には、anchorとの差が一軸だけのcanonical候補を保存し、anchor優先one-position後に本当に純増したかも記録する。

## 実行BAT

```text
scripts\gold_v3_runtime\bat\run_gold_v3_330_candidate_scarcity_decomposition_audit.bat
```

## 完了判定

コード・BAT・specの配置だけではStage330結果完了としない。実際にBATを実行して生成されたJSON/CSVを読み、件数、SHA、期間、2026除外、anchor parity、pure incremental成績を監査した後に結果判定する。
