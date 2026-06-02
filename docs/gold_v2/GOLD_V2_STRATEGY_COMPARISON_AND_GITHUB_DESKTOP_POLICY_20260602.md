# GOLD V2 strategy comparison and GitHub Desktop handling

Created: 2026-06-02

## 1. Comparison target

This snapshot compares the major GOLD V2 candidates and validation stages produced so far. It intentionally does not commit large CSV/ZIP outputs to GitHub.

## 2. Key comparison

| strategy | status | count | win_rate | pf | total_r | max_loss_streak | avg_monthly_count | notes |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| candidate-universe WF baseline | 基準 | 166 | 63.25% | 2.44 | 195.0 | 3 | 41.50 | 既存候補744本から各foldで候補/TP/SL/filter/policy再選定。 |
| combined_strict_safe_nonstacked | 安全重視候補 | 143 | 64.34% | 2.76 | 179.5 | 3 | 35.75 | nonstacked寄り。利益は落ちるが保守的。 |
| combined_strict_capped_or_rep | 現実寄り候補 | 166 | 64.46% | 2.74 | 210.0 | 4 | 41.50 | LOW_VOL_RANGEだけ専用候補/policy。capped/representativeのみ。 |
| combined_strict_foldbest_uncapped | 参考上限・runtime禁止 | 174 | 64.37% | 2.99 | 263.0 | 3 | 43.50 | LOW_VOL_RANGEだけ専用候補/policy。uncapped stackedを含むため上限参考。 |
| regime gate skip_low_vol_range | 参考 | 143 | 64.34% | 2.76 | 179.5 | - | 35.75 | baselineクラスタをregimeで後段フィルタ。専用再選定なし。 |
| regime gate only_high_vol | 参考 | 72 | 68.06% | 3.94 | 103.0 | - | 24.00 | high-volだけに絞るwhat-if。綺麗だがTotalRと件数が落ちる。 |
| low-vol TP/SL replacement best | 不採用寄り | 166 | 63.25% | 2.63 | 182.5 | 3 | 41.50 | baseline低ボラ部分だけTP/SL再価格付け。専用候補ではない。 |
| policy-level WF top1 confluence | 参考上限 | 172 | 72.67% | 4.11 | 421.0 | 3 | 43.00 | 候補ユニバース固定。過去月でpolicy選択、翌月テスト。楽観寄り。 |
| HIGHWIN_TOP20_ALL strict no-overlap TEST | 参考 | 132 | 75.00% | 3.59 | 85.5 | - | 77.14 | 固定選定後の後半holdout。WFではない。 |

## 3. Practical conclusion

Current practical baseline should be:

```text
candidate-universe WF baseline:
  count 166
  win rate 63.25%
  PF 2.44
  total R +195.0
  max loss streak 3
```

Current preferred upgrade candidate is:

```text
LOW_VOL_RANGE dedicated branch + non-low baseline, capped/representative:
  count 166
  win rate 64.46%
  PF 2.74
  total R +210.0
  max loss streak 4
```

A safer but lower-return variant is:

```text
skip/avoid low-vol or nonstacked-safe interpretation:
  count 143
  win rate 64.34%
  PF 2.76
  total R +179.5
  max loss streak 3
```

The uncapped stacked result is an upper-bound reference only:

```text
combined_strict_foldbest_uncapped:
  PF 2.99
  total R +263.0
```

It must not be used directly for runtime because uncapped stacking can enlarge single-cluster losses.

## 4. GitHub Desktop / repository-size handling

Do not commit generated CSV/ZIP artifacts from exploratory runs into the repository by default.

Recommended repository policy:

```text
Commit:
  docs/gold_v2/*.md summary documents
  scripts needed to reproduce audits
  small config files only after selection is stable

Do not commit by default:
  large generated CSV ledgers
  ZIP output bundles
  raw exploration output directories
  temporary audit artifacts
```

Reason:

```text
GitHub Desktop becomes slow when many generated files are added because it must scan, diff, fetch, and present them.
The current workflow should keep heavy outputs in /mnt/data or local artifacts and store only concise markdown summaries in GitHub.
```

If GitHub Desktop remains slow:

```text
1. Do not add output folders to the repo.
2. Add output patterns to .gitignore if not already covered.
3. Keep one markdown summary per audit in docs/gold_v2/.
4. Commit only scripts/configs after they are stable.
5. Use direct GitHub commits for small docs if Desktop is stuck.
```

## 5. Recommendation matrix

| item | recommendation | reason | risk |
|---|---|---|---|
| 短期の暫定基準 | candidate-universe WF baselineを基準線にする | 各foldで候補/TP/SL/filter/policyを選び直しており、固定policyより現実寄り。 | まだ既存候補ユニバース由来の選択バイアスあり |
| 低ボラ対応 | LOW_VOL_RANGEだけ専用候補へ切替。ただしcapped/representativeを優先 | baseline低ボラPF1.47→専用capped PF2.82、全体PF2.74/TotalR+210。 | 2026-06サンプルが少なく、uncappedは危険 |
| ロット重ね | uncapped禁止。まずmax stack 2〜3、同方向・no conflictのみ | uncappedはTotalR上限が大きいが、誤認時の単発損失が拡大。 | DD/最大単発損失の追加監査が必要 |
| 高ボラ対応 | 専用候補は後回し。通常候補を継続 | HIGH_VOL系はbaselineでPF3.43〜4.92と強い。 | 将来ボラ構造が変わる可能性 |
| BTC展開 | GOLDの閾値はコピーせず、BTC用TP/SL・曜日/週末・24/7特徴量で再探索 | BTCは価格水準・ボラ・週末構造が異なる。 | BTCはスプレッド/スリッページ/急変に別監査が必要 |
| GitHub Desktop対策 | CSV/ZIP成果物はGitHubに入れず、docsのMarkdown要約だけcommit | 大量成果物をrepoに入れるとFetch/Pull/差分表示が重くなる。 | 成果物はsandbox/ローカル保存なので、必要時にzipだけ個別共有 |

## 6. Runtime status

```text
MT5 order_send: disabled
Discord send: disabled
dispatch_ready: false
AI/API: not used
uncapped stacking: prohibited for runtime
```

## 7. Local comparison output bundle

Generated local files:

```text
gold_v2_final_strategy_comparison_summary.csv
gold_v2_final_strategy_comparison_key_summary.csv
gold_v2_final_strategy_comparison_monthly.csv
gold_v2_final_strategy_recommendations.csv
gold_v2_final_strategy_comparison_report.md
gold_v2_final_strategy_comparison_outputs.zip
```
