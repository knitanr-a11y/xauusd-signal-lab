# WATCH-014-A centroid・seed安定性監査

更新日: 2026-06-24

## 状態

- audit ID: `GML1-BATCH-016-WATCH014-CENTROID-SEED-STABILITY-AUDIT`
- audit-only
- WATCH-014-Aの候補ロジック変更なし
- 実装・合成テスト完了
- exact feature registryと各seedのexact assignment registryが未保存のため実数監査は未実行

## 目的

KMeansのcluster IDはseedごとに単純入れ替わるため、ID番号一致で安定性を判断しない。

1. 2023だけでfeature standardizationをfit
2. 2023 assignmentだけで各seedのcentroidを算出
3. Hungarian assignmentで各seed clusterをreference seed 7307へ対応付け
4. 対応後にcentroid距離、cosine、membership Jaccard、ARI、NMIを測る
5. pre-2026、2026 diagnostic、fresh post-cutoffを分離してmotif persistenceを確認

2026はalignmentにもcluster選択にも使用しない。

## 必須入力

### Feature registry

最低限:

- `decision_close_time`
- `r_value`（retrospective attribution専用）
- configに固定した54個のpath-shape feature

### Assignment registry

seedごとに:

- `decision_close_time`
- `cluster_id`

対象seed:

- 7307（reference）
- 7001
- 7021
- 7041
- 7061
- 7081

feature registryと全assignment registryのtimestamp集合は完全一致が必要。assignmentをこの監査内で再学習・再生成しない。

## 出力

- `reference_centroid_feature_attribution.csv`
- `seed_membership_stability.csv`
- `seed_global_alignment.csv`
- `reference_cluster_metrics.csv`
- `centroid_seed_stability_summary.json`
- `manifest.json`

reference excluded cluster 1・2について、pre-2026のmembership Jaccardと2023 centroid cosineをsummaryへ集約する。

## 境界

- centroid alignmentは2023のみ
- r_valueはcluster performance説明にだけ使用
- 2026は診断表示のみ
- 新しいexcluded cluster、閾値、candidate IDを自動作成しない
- WATCHからPROVへの昇格をしない
- live signal / MT5 / Discord / portfolio activationはOFF

## 未完了条件

現在のrepoには、Batch014で使った54-feature registry本体と6 seed分のassignment registry本体がない。これらを投入し、出力を目視確認するまでWATCH-014-Aのseed安定性結論は確定しない。
