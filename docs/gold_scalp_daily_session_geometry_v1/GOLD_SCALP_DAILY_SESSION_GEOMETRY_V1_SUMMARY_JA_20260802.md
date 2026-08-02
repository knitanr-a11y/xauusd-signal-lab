# GOLDスキャルピング 日次／session水準geometry V1 結果

正式状態: **`AUDIT_COMPLETE_NO_FORMAL_PROMOTION`**

## データ

- M1統合: 1,167,591行（2023-01-03 01:00:00 ～ 2026-07-31 23:56:00）
- M5統合: 253,557行（2023-01-03 01:00:00 ～ 2026-07-31 23:50:00）
- M1の重複は後から追加されたチャンクを優先し、goldsharp重複部分は完全一致を確認しました。
- 2024H1・2024H2はexact M1 coverage不足のため、正式な擬似forward対象から除外しました。

## 研究した独立family

- 前日高値／安値のsweepとclose-back
- server時刻01・08・15時のopening range拡張と初回retest
- daily reopen gapの保持と順方向継続

## 段階別成績

- CATALOG / RAW_SELECTED_EXACT_M1: 33件、勝率45.45%、PF0.7812、損益-15.75、DD32.25
- CATALOG / GLOBAL_DEDUP_EXACT_M1: 33件、勝率45.45%、PF0.7812、損益-15.75、DD32.25
- CATALOG / HEALTH_GATE_1_PRIOR_POSITIVE_BLOCK: 0件
- CATALOG / HEALTH_GATE_2_PRIOR_POSITIVE_BLOCKS: 0件
- CATALOG / RESOLVED_ONLY_LIVE_REPLAY_1BLOCK: 0件
- BALANCED / RAW_SELECTED_EXACT_M1: 33件、勝率45.45%、PF0.7812、損益-15.75、DD32.25
- BALANCED / GLOBAL_DEDUP_EXACT_M1: 33件、勝率45.45%、PF0.7812、損益-15.75、DD32.25
- BALANCED / HEALTH_GATE_1_PRIOR_POSITIVE_BLOCK: 0件
- BALANCED / HEALTH_GATE_2_PRIOR_POSITIVE_BLOCKS: 0件
- BALANCED / RESOLVED_ONLY_LIVE_REPLAY_1BLOCK: 0件

## 後付けで見えた小標本（不採用）

全engine確認後には `GAP_HOLD_CONT_G1_H0.5_UP_BASE` / `P67_TP5_TP10_SL5_H240` が、exact M1で21件・勝率80.95%・PF3.8948・+57.90ドル・DD5ドルでした。

ただし21件中13件が2026H1に集中し、月中央値は0件、LONGしかなく、厳格な擬似forward選択では一度も採用されていません。結果確認後に選んだ行でもあるため、統合レジストリへ追加せず `POST_RESULT_DESCRIPTIVE_TRACE_NOT_RETAINED` とします。

## 判定

- 同一engine・同一固定exitで、2つ以上の擬似forward target blockを通過した観察候補はありませんでした。
- live_ready / final_signal / Shadow / Discord / MT5発注はすべてOFFです。
- V19・Challenger C1・P75 State Survival Shadow・統合レジストリは変更していません。
