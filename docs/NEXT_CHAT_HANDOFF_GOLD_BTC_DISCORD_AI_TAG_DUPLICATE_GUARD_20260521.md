# NEXT_CHAT_HANDOFF_GOLD_BTC_DISCORD_AI_TAG_DUPLICATE_GUARD_20260521

Last updated: 2026-05-21

## 0. 2026-05-22追記: まず読むべき最新短縮版

GOLD strict7 のAI推定タグ、特に「タグ組み合わせ」「複合警告」「複合好機」の続きなら、この長い文書を読む前に以下だけ読んでください。

```text
docs/NEXT_CHAT_HANDOFF_GOLD_AI_TAG_COMBO_RULES_20260522.md
```

この文書を読む必要があるのは、主に以下の場合だけです。

```text
- Discord通知の重複通知ガードを再確認する時
- GOLD/BTC通知タイミングの +5秒 設定を確認する時
- GOLD strict7 の浅いSL探索結果を確認する時
- 2026-05-21時点の背景を詳しく追う時
```

読まなくてよいケース:

```text
- AIタグ組み合わせの現在実装だけ確認したい時
- 最新のGOLD AIタグ生成BATの流れだけ確認したい時
- combo_rules の表示・運用方針だけ確認したい時
```

理由:

```text
2026-05-22に、GOLD AIタグ組み合わせ専用の短縮ハンドオフを追加済み。
古い記述にはローカルパッチ方式や旧AIタグ表示の説明が含まれるため、最新作業では短縮版を優先する。
```

---

この文書は、2026-05-21時点で実施した以下の内容を、次チャットへ正確に引き継ぐための最新版メモです。

```text
- GOLD strict7 / BTC strict5 official の通知タイミング調整
- GOLD strict7 の浅いSL探索結果
- GOLD AIタグの負けタグ/勝ちタグの見直し
- GOLD/BTC Discord通知の毎分重複通知問題とhotfix
- 現時点での運用確認ポイント
```

---

## 1. 最重要結論

### GOLD strict7 のSLは現行維持

GOLD strict7では、浅いSLを深くする探索を実施した。

結論:

```text
SLを深くすると勝率は少し上がるが、PF / Total R が大きく低下する。
したがって、現時点ではGOLD strict7のSLは変更しない。
```

特に `BUY_BB_RSI30_REJECTION65_NY_TP30_SL7P5` は、SLを深くしても勝率改善が弱く、Total Rの悪化が大きかったため現行維持。

`SELL_DONCHIAN48_MACD_RANGE_NY_TP30_SL7P5` は SL10 も妥協案としてはあり得たが、PF/Total Rでは現行SL7.5が最良だったため、こちらも現行維持。

### EA/BATタイミング

EA側:

```text
InpExportSecond = 2 推奨
```

GOLD/BTC通知・自動売買BAT側:

```text
run-delay / offset = +5秒
```

対象:

```text
GOLD strict7 Discord通知: +5秒
GOLD strict7 guarded demo autotrade: +5秒
BTC strict5 official Discord通知: +5秒
BTC strict5 guarded demo send: +5秒
```

理由:

```text
EAが+2秒でCSVを書き、Pythonが+5秒で読むことで約3秒の余裕を確保する。
0秒/1秒ぴったり取得はMT5 OnTimerや新バーtick依存で1分遅れや更新前読込の原因になる。
```

---

## 2. GOLD AIタグの最新方針

### 旧問題

以前のAIタグは、実質的に以下の見え方だった。

```text
負けタグらしきものがHIT
  -> ⚠️ 注意
```

しかし監査の結果、負けタグとして付いたものでも、勝ちトレードにも普通に出ているタグがあった。

そのため、単純に「負けタグ = 悪い」と扱うと、勝ちパターンまで過剰警告するリスクがあった。

### 新方針

AIタグ通知は以下の分類で表示する。

```text
✅ 好材料
  勝ちトレードに寄っているタグ。

好材料候補
  勝ち寄りだがサンプルや安定性はまだ確認中。

⚠️ 強め注意
  負け側に明確に偏っているタグ。

注意
  やや負け寄りのタグ。

参考注意
  気になるが、勝ちにも出るため強警告にしないタグ。

参考
  サンプル不足、または弱い材料。
```

通知例:

```text
AIタグ: ✅ 好材料 1件 / ⚠️ 強め注意 1件 / 参考注意 2件
判定: 評価可 18/24・特徴不足 6・HIT 4

- ✅ 好材料: GOLD短期反発の形（gold_fast_mean_reversion） / タグ実績avgR=11.23 / 勝率=78%
- ⚠️ 強め注意: 高ボラ追いかけ気味（high_volatility_chase） / タグ実績avgR=-0.78 / 勝率=10%
- 参考注意: 伸びた後のエントリー（entry_after_extended_move） / 勝ちにも出るため参考扱い

注: AIタグは過去レビュー類似の注意/好材料ラベルで、勝敗確定ではありません。
```

### 最新AIタグJSONの確認結果

ユーザーが貼った `data/runtime_state/gold/strict_7/ai_tag_numeric_rules.json` は新形式で生成済み。

確認済み内容:

```text
schema_version: gold_strict_7_ai_tag_numeric_rules_v3_positive_balance_audit
cycle_ok: true
rules_count: 173
tag_balance_audit_rows: 157
```

内訳の目安:

```text
risk系ルール: 135
positive系ルール: 38
好材料: 29
好材料候補: 5
強め注意: 12
注意: 61
参考注意: 50
参考: 16
```

重要:

```text
- tag_role: positive が入っている
- display_level_suggestion: 好材料 が入っている
- verdict: not_loss_specific_also_on_wins が入っている
```

したがって、GOLD AIタグJSON自体はOK。

### 関連スクリプト

共有ユーティリティ:

```text
scripts/ai_tag_numeric_rule_utils.py
```

GOLD AIタグ監査:

```text
scripts/gold_strict_7_signals/audit_gold_strict_7_ai_tag_win_loss_balance.py
```

GOLD AIタグ生成:

```text
scripts/gold_strict_7_signals/build_gold_strict_7_ai_tag_numeric_rules.py
scripts/build_gold_strict_7_ai_tag_numeric_rules.bat
```

GOLD AIタグ生成パッチャー:

```text
scripts/gold_strict_7_signals/apply_ai_tag_positive_balance_patch.py
```

---

## 3. Discord通知が毎分来続けた問題

### 発生した問題

GOLD Discord通知で、シグナル検出後、新しいローソク足が出るまで毎分通知が来続けた。

自動売買は毎分されなかった。

理由:

```text
自動売買側は order ledger / position guard で重複発注を防いでいた。
一方、Discord通知側は CSV ledger 依存で、同じ足の再通知を完全には止めきれていなかった。
```

### 原因

GOLD通知本体は当初、以下の構造だった。

```text
notification_key = GOLD|STRICT7|strategy|direction|close_time
重複判定 = discord_notification_ledger.csv のみ
ledger追記 = 最後にまとめてappend
```

このため、以下の条件で同じシグナルが毎分通知され得る。

```text
- ledger追記が次ループに見えない
- ledger追記前に落ちる
- close_timeが同一M5足内で微妙にズレる
- 同じシグナルが新しいM5足まで検出され続ける
```

BTC official Discord通知にも同じ構造のリスクがあった。

### hotfix方針

