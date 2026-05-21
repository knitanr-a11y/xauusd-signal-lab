# NEXT_CHAT_HANDOFF_GOLD_AI_TAG_COMBO_RULES_20260522

Last updated: 2026-05-22

この文書は、GOLD strict7 のAI推定タグに「タグ組み合わせ」判定を追加した作業の短縮引き継ぎです。

次チャットでは、まずこの文書だけ読めばよいです。
古い長いハンドオフは、必要になった時だけ参照してください。

---

## 0. 次チャットで最初に読むもの

最優先:

```text
docs/NEXT_CHAT_HANDOFF_GOLD_AI_TAG_COMBO_RULES_20260522.md
```

必要になった時だけ読む:

```text
docs/NEXT_CHAT_HANDOFF_GOLD_BTC_DISCORD_AI_TAG_DUPLICATE_GUARD_20260521.md
```

読む必要が出る条件:

```text
- Discord通知の重複再発を調べる時
- GOLD/BTC通知タイミングの+5秒設定を再確認する時
- GOLD strict7 浅いSL検証の過去結論を確認する時
```

読まなくていいもの:

```text
- 2026-05-21以前の古いNEXT_CHAT_HANDOFF系ドキュメント
- GOLD strict7以外の古いAIタグ設計メモ
- 旧方式のAIタグパッチ手順だけを書いたドキュメント
```

理由:

```text
今回の最新状態は、この文書と対象スクリプトの現在実装で確定しているため。
古い文書を読むと、ローカルパッチ方式や旧AIタグ表示に引っ張られる可能性がある。
```

---

## 1. 今回の結論

GOLD strict7 のDiscord通知に、単体AIタグだけでなく、タグの組み合わせから見た相対的な傾向を表示できるようにした。

表示イメージ:

```text
AIタグ: ✅ 好材料 1件 / ⚠️ 強め注意 1件 / 注意 1件 / 参考注意 2件
判定: 評価可 18/24・特徴不足 0・HIT 5

タグ組み合わせ: ✅ 複合好機 1件 / ⚠️ 複合警告 1件
- ✅ 複合好機: tag_a + tag_b / 過去類似=10件 / 勝率=50% / PF=2.90 / avgR=+1.20 / 戦略平均=勝率42%/PF2.09/avgR+0.81 / 差分=勝率差+8%/avgR差+0.40
- ⚠️ 複合警告: tag_c + tag_d / 過去類似=14件 / 勝率=21% / PF=0.80 / avgR=-0.20 / 戦略平均=勝率42%/PF2.09/avgR+0.81 / 差分=勝率差-20%/avgR差-1.01
```

重要:

```text
- 複合タグは発注ブロックではない
- あくまでDiscord通知上の参考情報
- strategy_idごとの平均と比較して、相対的に良い/悪い組み合わせを出す
- 単体タグがHITして、その組み合わせがcombo_rulesに登録されている時だけ表示される
```

---

## 2. 実装済みファイル

### 共通AIタグ表示ロジック

```text
scripts/ai_tag_numeric_rule_utils.py
```

主な変更:

```text
- combo_rules を読み込めるようにした
- score_signal_row() が combo_hits を返すようにした
- format_score_for_discord() が「タグ組み合わせ:」を表示するようにした
- 単体タグのヘッダーで「注意」と「参考注意」を分離した
```

### GOLD単体タグ生成 v3

```text
scripts/gold_strict_7_signals/build_gold_strict_7_ai_tag_numeric_rules_v3_no_patch.py
```

目的:

```text
- ローカルで既存ソースにパッチを当てない
- 好材料/注意/参考注意の分類を直接生成する
- positiveタグやtag_balance_auditを使えるようにする
```

注意:

```text
旧 apply_ai_tag_positive_balance_patch.py は、BATから呼ばない。
今後もローカルパッチ方式には戻さない。
```

### GOLD複合タグ生成

```text
scripts/gold_strict_7_signals/add_gold_strict_7_ai_tag_combo_rules.py
```

目的:

```text
- trade_feature_snapshot.csv と trade_ai_review_ledger.jsonl を読む
- strategy_idごとにタグ2個組/3個組を集計する
- strategy平均と比較して複合好機/複合警告/複合注意を作る
- ai_tag_numeric_rules.json に combo_rules として追記する
- 監査用CSV ai_tag_combo_rules_summary.csv を出力する
```

### GOLD生成BAT

```text
scripts/build_gold_strict_7_ai_tag_numeric_rules.bat
```

現在の流れ:

```text
1. trade_feature_snapshot.csv の存在確認
2. trade_ai_review_ledger.jsonl の存在確認
3. build_gold_strict_7_ai_tag_numeric_rules_v3_no_patch.py を実行
4. add_gold_strict_7_ai_tag_combo_rules.py を実行
5. ai_tag_numeric_rules.json に rules + combo_rules が入る
```

ローカルパッチャーは呼ばない。

---

## 3. 生成結果の確認済み状態

ユーザーがアップロードした生成後ファイルを確認した結果:

```text
data/runtime_state/gold/strict_7/ai_tag_numeric_rules.json
```

確認結果:

```text
単体AIタグルール: 173件
複合タグルール: 194件
```

複合タグ内訳:

```text
✅ 複合好機:      70件
複合好機候補:     21件
⚠️ 複合警告:      51件
複合注意:         52件
合計:            194件
```

対象strategy_id:

```text
BUY_BB_RSI30_REJECTION65_NY_TP30_SL7P5
BUY_STOCH_BB_KTURN_NY_TP150_SL10
BUY_SWEEP_RECLAIM_RSI_TP150_SL10
SELL_DONCHIAN48_MACD_RANGE_NY_TP30_SL7P5
SELL_DONCHIAN96_MACD_RANGE_ALL_TP150_SL37P5_CD60
SELL_DONCHIAN96_MACD_RANGE_ALL_TP150_SL37P5_CD120
SELL_KC_CCI150_LONDON_TP100_SL10
```

重複確認:

```text
同じstrategy内で同じタグ組み合わせが重複登録されているものはなし。
```

---

## 4. 現在の運用方針

しばらく様子見する。

見るポイント:

```text
1. 通知に「タグ組み合わせ:」が出るか
2. 複合警告が出たシグナルの結果が実際に悪いか
3. 複合好機が出たシグナルが本当に取りやすい形か
4. 表示が多すぎないか
5. サンプル5件程度の複合好機/警告が軽すぎないか
```

最初は、複合好機よりも複合警告の精度を見る。

理由:

```text
警告が「避けたい場面」を拾えているなら、運用上の価値が高い。
好機は少数サンプルで過信しやすいため、最初は参考寄りで見る。
```

---

## 5. 次に調整するなら

もし表示が軽すぎる、または好機が出すぎる場合:

```text
min_combo_trades: 5 -> 8 or 10
```

おすすめ候補:

```text
複合好機/複合警告: 最低10件
複合好機候補/複合注意: 最低5件
```

現在は、まず見える化を優先して最低5件から出している。

---

## 6. BTC側について

BTC側は、共通表示ロジック `scripts/ai_tag_numeric_rule_utils.py` が combo_rules に対応したため、JSONに combo_rules が入れば表示できる。

ただし、BTC側の生成BATはGOLDとは構造が違う。

BTC:

```text
数値条件診断CSV -> rules JSON
```

GOLD:

```text
AIレビュー台帳 + feature snapshot -> rules JSON + combo_rules
```

そのため、BTCの複合タグ生成はまだ未実装。

BTCに追加する場合は、先にBTC側のAIレビュー元データ構造を確認してから、GOLDと同じ思想で別途 `add_btc_strict_5_ai_tag_combo_rules.py` を作るのが安全。

---

## 7. やってはいけないこと

```text
- ローカルで既存ソースへパッチを当てる方式に戻さない
- BAT内で apply_ai_tag_positive_balance_patch.py を呼ばない
- AIタグだけで発注ブロックやロット変更をしない
- 5件程度の複合好機を強い根拠として扱わない
- 古いハンドオフを大量に読んで、旧設計へ戻さない
```

---

## 8. 次チャットで確認すべき最小チェック

ユーザーが「AIタグ組み合わせの続き」と言った場合、まず以下だけ確認する。

```text
1. scripts/ai_tag_numeric_rule_utils.py
2. scripts/build_gold_strict_7_ai_tag_numeric_rules.bat
3. scripts/gold_strict_7_signals/build_gold_strict_7_ai_tag_numeric_rules_v3_no_patch.py
4. scripts/gold_strict_7_signals/add_gold_strict_7_ai_tag_combo_rules.py
5. data/runtime_state/gold/strict_7/ai_tag_numeric_rules.json がアップされていればその combo_rules
```

古いドキュメントは、上記で足りない時だけ読む。
