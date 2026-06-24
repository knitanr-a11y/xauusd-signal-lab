# GOLD_ML_V1 exact入力ファイル追補

更新日: 2026-06-25

## 重要な訂正

Batch015・PROV-020 monitor・Batch016の実装は完了していたが、実行に必要なexact CSV本体の保存先が引き継ぎに書かれていなかった。新チャットが入力場所を特定できなかったのは正しい。

exact artifact一式は再構成済みで、正本locatorは次。

- `config/gold_ml_v1/exact_artifact_locator_20260625.json`

bundle名とSHA256:

- `GOLD_ML_V1_EXACT_HANDOFF_ARTIFACTS_20260625.zip`
- SHA256: `1c4cb9677ff54db177005fcec4225aa59c31140f4e2356e9dad9c5becba10bdb`

bundleを受け取ったら、次のrunnerでSHA256検証後に展開する。

- `scripts/gold_ml_v1/tools/run_install_exact_handoff_artifacts.bat <ZIP_PATH>`

展開先:

- `config/gold_ml_v1/registries/`

## 6候補 exact trade registry

- `config/gold_ml_v1/registries/GML1-PROV-007_exact_trade_registry.csv`
- `config/gold_ml_v1/registries/GML1-PROV-008_exact_trade_registry.csv`
- `config/gold_ml_v1/registries/GML1-PROV-010_exact_trade_registry.csv`
- `config/gold_ml_v1/registries/GML1-PROV-015_exact_trade_registry.csv`
- `config/gold_ml_v1/registries/GML1-PROV-020_exact_trade_registry.csv`
- `config/gold_ml_v1/registries/GML1-WATCH-014-A_exact_trade_registry.csv`

canonical必須列:

- `candidate_id`
- `decision_close_time`
- `entry_time`
- `exit_time`
- `r_value`
- `direction`

Batch015 runnerへ上記6パスを順番に渡す。

## PROV-015 parent-event registry

- 全利用可能event:
  `config/gold_ml_v1/registries/GML1-PROV-015_parent_event_registry_all_available.csv`
- cutoffより後だけ:
  `config/gold_ml_v1/registries/GML1-PROV-015_parent_event_registry_post_cutoff.csv`

PROV-020 monitorが読む列:

- `decision_close_time`
- `h1_decision_close_server_hour`
- `h1_spread_price_div_atr14`

現在与えられているraw dataは、H1 closeが`2026-06-23 18:00:00`、M15 closeが`2026-06-23 18:15:00`までである。fresh cutoffは`2026-06-23 18:15:00`なので、strictly post-cutoff CSVは現在0行で正しい。これは現実の将来期間にeventがなかったという意味ではなく、提供済みraw dataにcutoff後のcoverageがないという意味である。

## WATCH-014-A exact registry

54特徴量registry:

- `config/gold_ml_v1/registries/GML1-WATCH-014-A_54_feature_registry.csv`

6 seed cluster assignment registry:

- `config/gold_ml_v1/registries/GML1-WATCH-014-A_cluster_assignments_6seeds.csv`

seed:

- 7307
- 7001
- 7021
- 7041
- 7061
- 7081

再現補助model/centroid情報:

- `config/gold_ml_v1/registries/GML1-WATCH-014-A_cluster_models_6seeds.json`

## 実行上の境界

- 集計値からentry timestampを推定しない。
- exact CSVが展開されるまで実matrix・activation・centroid結果を主張しない。
- 2026でthreshold、cluster、候補を選び直さない。
- bundle SHAと各file SHAはlocator JSONで照合する。
- audit-onlyを維持する。
