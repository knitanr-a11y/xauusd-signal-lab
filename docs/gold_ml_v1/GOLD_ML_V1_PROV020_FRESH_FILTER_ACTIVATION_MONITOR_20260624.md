# GML1-PROV-020 fresh filter activation monitor

更新日: 2026-06-24

## 状態

- monitor ID: `GML1-PROV-020-FRESH-FILTER-ACTIVATION-MONITOR-V1`
- audit-only
- candidate logic変更なし
- 実装・合成テスト完了
- exact prospective `GML1-PROV-015` parent-event CSVによる実監視は未実行
- live signal / final signal / MT5 / DiscordはOFF

## 目的

MT5 server close `2026-06-23 18:15:00`より後に、PROV-020の追加除外filterが実際に発火したかを記録する。

このmonitorはPROV-015の検出済みparent eventだけを入力にし、次のentry時点既知情報だけを読む。

- `decision_close_time`
- `H1_DECISION_CLOSE_SERVER_HOUR`
- `H1_SPREAD_PRICE_DIV_ATR14`

exit、TP/SL、realized R、MAE/MFE、将来horizonは読まない。入力CSVに存在しても出力ledgerへコピーしない。

## 固定filter

PROV-015 parent eventについて、次を両方満たす場合に`filter_activation=true`とする。

1. MT5 server hourが8以上16以下
2. `H1_SPREAD_PRICE_DIV_ATR14 >= 0.0308778597897866`

これは既存のPROV-020条件を監視用に再現するだけで、閾値変更や新候補作成ではない。

- `filter_activation=true`: PROV-020では除外される想定
- `prov020_expected_emit=true`: 追加filterを通過する想定

## cutoff

- cutoffと同時刻のeventはfreshへ含めない
- `decision_close_time > 2026-06-23 18:15:00`だけをfreshとして扱う
- timestampはtimezone変換しないMT5 server naive time

## fail closed

- required column不足・alias曖昧
- duplicate decision close
- 非単調event順
- spread/ATRの非有限値
- timestampから導出したserver hourと提供hourの不一致
- 既存append-only ledgerと同じ時刻の内容不一致
- execution boundaryがOFFでないconfig

## 出力

- append-only `filter_activation_ledger.jsonl`
- deterministic `filter_activation_summary.json`

ledger keyは`decision_close_time`。同じ入力の再実行は追記せず、既存内容が同じことを確認する。

## 実行

```bat
scripts\gold_ml_v1\prospective\run_prov020_fresh_filter_activation_monitor.bat path\prov015_parent_events.csv
```

実監視結果を確定するには、cutoff後を含むexact prospective PROV-015 parent-event CSVを投入し、summaryとledgerを目視確認する必要がある。
