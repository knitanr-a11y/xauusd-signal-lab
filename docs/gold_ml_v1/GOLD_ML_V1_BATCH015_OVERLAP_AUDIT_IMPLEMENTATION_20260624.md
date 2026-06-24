# GOLD_ML_V1 Batch015: 6候補 overlap・独立性監査 実装記録

更新日: 2026-06-24

## 1. 状態

`GML1-BATCH-015-SIX-CANDIDATE-OVERLAP-INDEPENDENCE-AUDIT`

- audit-only
- 候補ロジック変更なし
- 新candidate IDの発行なし
- live signal / MT5注文 / Discord / portfolio activationはすべてOFF
- 実装と合成データテストは完了
- 実候補の数値監査は、6本のexact trade registry CSV投入と生成物の目視検査が終わるまで未完了

対象:

- `GML1-PROV-007`
- `GML1-PROV-008`
- `GML1-PROV-010`
- `GML1-PROV-015`
- `GML1-PROV-020`
- `GML1-WATCH-014-A`

## 2. なぜ結果をまだ確定しないか

現在のリポジトリ正本には候補metricsと一部trade-registry SHA256はあるが、6本すべてのtrade registry CSV本体は保存されていない。したがって、集計値からentry timestampを逆算したり、推定overlapを作ったりしない。

Batch015は、exact registryを入力として初めて実数matrixを生成する。SHAが正本にある候補は既定で照合し、不一致ならfail closedする。

## 3. 入力契約

各候補CSVに最低限、次の列が必要。

```text
decision_close_time
entry_time
exit_time
r_value
direction
```

設定JSONにあるaliasも使用できる。時刻はtimezone変換していないMT5 server naive timestampとする。

検査:

- 6候補の不足・余分なregistry指定を拒否
- required column不足・曖昧aliasを拒否
- timezone-aware timestampを拒否
- `decision_close_time > entry_time`を拒否
- `exit_time < entry_time`を拒否
- duplicate `entry_time`を拒否
- 候補方向とregistry方向の不一致を拒否
- 非有限`r_value`を拒否
- 正本SHA256がある場合は完全一致を要求

## 4. overlap定義

### Exact overlap

同一`entry_time`の集合一致を使う。

- matched count
- union count
- Jaccard
- 各候補から見たmatch fraction
- same/opposite direction count

### ±1 decision-bar overlap

候補ペアの遅い側のdecision timeframeを許容幅にする。

- M15同士: ±15分
- H1同士: ±60分
- M15とH1: ±60分

`decision_close_time`を使い、距離の短い組から一対一greedy matchする。これはexact identityの代替ではなく、近接発火の診断である。

### Concurrent exposure

`[entry_time, exit_time)`の区間が正の長さで重なるtrade pairを数える。

## 5. 親子lineage

構造上のlineage rootは2群に固定する。

1. `GML1-PROV-002` root: `PROV-007`, `PROV-008`
2. `GML1-PROV-010` root: `PROV-010`, `PROV-015`, `PROV-020`, `WATCH-014-A`

これは独立edge数の結論ではない。実測のmonthly-R effective rank、overlap、concentrationと合わせて診断する。

親registryが6本の入力内にある場合は、次を出力する。

- retention vs parent
- child contained fraction
- parent-only count
- unexpected child-only count

`PROV-007/008`のparent `PROV-002`は今回の6本に含まれないため、親子retention欄は`parent_registry_available=false`になる。両者同士のoverlapは通常どおり測定する。

## 6. 期間分離

同じ固定ロジックで次を別々に出力する。

- `all`
- `pre_2026`: 2026-01-01より前
- `diagnostic_2026_to_cutoff`: 2026-01-01からMT5 server close `2026-06-23 18:15:00`まで
- `fresh_post_cutoff`: cutoffより後

2026の値から閾値、候補条件、redundancy判定閾値を調整しない。redundancy閾値は報告フラグ専用で、候補の削除・統合・昇格を行わない。

## 7. 主な出力

```text
candidate_window_metrics.csv
exact_entry_overlap.csv
plus_minus_one_decision_bar_overlap.csv
exact_entry_jaccard_matrix_<window>.csv
plus_minus_one_decision_bar_jaccard_matrix_<window>.csv
parent_derivative_retention.csv
concurrent_exposure.csv
monthly_r_<window>.csv
monthly_r_correlation_<window>.csv
monthly_r_correlation_long.csv
concentration_breakdown.csv
independence_summary.json
manifest.json
```

`concentration_breakdown.csv`はyear、quarter、MT5 server-hour session、およびregistryに存在する場合のregimeを分ける。

`independence_summary.json`のeffective rankとthreshold-flagged componentsは診断値であり、登録・portfolio利用の許可ではない。

## 8. 実行

Windows:

```bat
scripts\gold_ml_v1\audit\run_candidate_overlap_audit.bat ^
  path\GML1-PROV-007.csv ^
  path\GML1-PROV-008.csv ^
  path\GML1-PROV-010.csv ^
  path\GML1-PROV-015.csv ^
  path\GML1-PROV-020.csv ^
  path\GML1-WATCH-014-A.csv
```

Python直接実行も可能。

```text
python scripts/gold_ml_v1/audit/candidate_overlap_audit.py \
  --config config/gold_ml_v1/candidate_overlap_audit_20260624.json \
  --registry GML1-PROV-007=<csv> \
  --registry GML1-PROV-008=<csv> \
  --registry GML1-PROV-010=<csv> \
  --registry GML1-PROV-015=<csv> \
  --registry GML1-PROV-020=<csv> \
  --registry GML1-WATCH-014-A=<csv>
```

既知SHAとの照合を飛ばす`--skip-hash-check`は調査用に存在するが、正式なBatch015監査では使用しない。

## 9. 完了判定

次のすべてを満たすまでP0-1完了とはしない。

1. 6本すべてのexact registryを入力
2. SHA検査を有効にして正常終了
3. `manifest.json`で全入力・全出力hashを確認
4. all / pre-2026 / 2026 diagnostic / freshを分離確認
5. exact・fuzzy・concurrent・monthly correlation・concentrationを目視検査
6. 親子派生を独立edgeとして二重計上していないことを確認
7. 監査結果を新しいresult JSONへ固定

この段階では実装完了、実データ監査未完了である。
