# GOLD V3 引き継ぎ
## Stage263 architecture reset June pseudo-holdout REJECT

正式状態:

`GOLD_V3_263_JUNE_PSEUDO_HOLDOUT_REJECTED_AUDIT_ONLY`

## 結論

- setup探索を停止し、M15→60分return予測の意思決定modelへ根本変更した。
- 2025-07〜2026-05 expanding OOFでthresholdを固定。
- Ridge＋HistGradientBoostingの符号一致＋OOF強度上位15%のみをtrade。
- OOF prediction Pearson -0.0477、Spearman 0.0059。
- OOF 304 trades、cost2 expectancy -2.156、PF0.807。
- 6月600 eligible decisions、20 raw signal、one-active後8 trades。
- 6月 cost2 PnL -65.56、expectancy -8.195、PF0.185。
- LONG 6件 -49.82、SHORT 2件 -15.74。
- prefix/prediction parity 12/12 PASS。
- baselineよりPnL損失は小さいが、8件しか取引しないため。expectancy/PFは全baselineより悪い。

## 禁止

- 同じ6月を使ったthreshold緩和
- SHORT only化
- 時間帯選択
- horizon変更
- feature/model連続探索
- E2〜E8の後付け追加

6月pseudo-holdoutは開封済みであり、これ以降は開発データ扱い。

## 推奨

現在のOHLC＋bar tick_volumeでdirectional autotradeを作る研究は停止する。

次に進むなら二択:

1. `VOLATILITY_ONLY_PIVOT`: directionを出さず、将来値幅・activity・取引禁止判定だけを予測。
2. `NEW_INFORMATION_RESTART`: tick/bid-ask/external marketsを追加し、新しい未来paper holdoutで再開始。

現在データだけで別方向modelを続けない。

## 主要参照

- `docs/gold_v3/GOLD_V3_STAGE263_RESEARCH_ARCHITECTURE_RESET_JUNE_PSEUDO_HOLDOUT_DEFINITION_AUDIT_ONLY_20260620.md`
- `docs/gold_v3/GOLD_V3_STAGE263_JUNE_PSEUDO_HOLDOUT_REJECTED_AUDIT_ONLY_20260620.md`
- `docs/gold_v3/stage263_final_summary_20260620.json`
- `docs/gold_v3/stage263_key_results_20260620.csv`
- `docs/gold_v3/stage263_reproducibility_manifest_20260620.json`
- `tests/gold_v3/test_stage263_architecture_reset.py`

完全runnerは生成artifact `stage263_architecture_reset.py`として保存し、SHA256をreproducibility manifestへ固定済み。

運用状態:

`NO_LIVE_PROMOTION_AUDIT_ONLY`
