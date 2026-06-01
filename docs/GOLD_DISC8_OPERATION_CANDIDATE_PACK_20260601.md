# GOLD DISC8 SAFE group-tag-filtered operation candidate pack

作成日: 2026-06-01

## 目的

`data/gold_disc8/source_of_truth/group_tag_filtered/` に固定した SAFE group-tag-filtered DISC8 を、通知・運用候補へ渡すための manifest / runtime gate rules / Discord preview を作る。

この段階では、実運用送信や発注はしない。

## 入力 source of truth

```text
data/gold_disc8/source_of_truth/group_tag_filtered/selected_disc8_group_tag_filtered_strategies.csv
data/gold_disc8/source_of_truth/group_tag_filtered/group_tag_filtered_source_trade_ledger.csv
data/gold_disc8/source_of_truth/group_tag_filtered/group_tag_filtered_source_trade_audit.json
data/gold_disc8/config/disc8_ai_group_tag_filter_rules_20260531.json
```

## 出力

```text
data/gold_disc8/operational_candidate/group_tag_filtered/gold_disc8_operational_strategy_manifest.csv
data/gold_disc8/operational_candidate/group_tag_filtered/gold_disc8_operational_strategy_manifest.json
data/gold_disc8/operational_candidate/group_tag_filtered/gold_disc8_runtime_group_tag_gate_rules.json
data/gold_disc8/operational_candidate/group_tag_filtered/gold_disc8_discord_notification_templates.csv
data/gold_disc8/operational_candidate/group_tag_filtered/gold_disc8_discord_notification_templates.json
data/gold_disc8/operational_candidate/group_tag_filtered/gold_disc8_discord_preview_messages.md
data/gold_disc8/operational_candidate/group_tag_filtered/gold_disc8_operational_candidate_audit.json
```

## 安全条件

- OpenAI APIを呼ばない
- MT5 order_sendしない
- Discord送信しない
- OHLCから再検出しない
- source of truth固定CSV以外を評価対象にしない

## runtime gate 方針

運用時は、候補シグナルに対して通知前タグ判定を行い、以下の条件で処理する。

```text
strategy_id が対象DISC8に含まれる
かつ AI/タグ判定結果に strategy-specific block tag が含まれる
=> BLOCK / 通知しない / 監査に残す
```

watch_onlyタグは通知を止めない。ただし監査ログに残す。

## 注意

現在のgroup tag filterは、過去AIレビューから得たタグを用いたフィルタである。
ライブ運用では、候補シグナル生成時点の特徴量から同じタグ判定を得る必要がある。
そのため、このpackは「通知・運用候補の仕様固定」であり、実送信へ接続する前に pre-send tagger との結合監査が必要。
