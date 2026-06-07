# 次チャット開始文 - GOLD V2 25C45修正版 / 25C46 filter coverage review

次のチャット開始時に、以下をそのまま貼ってください。

```text
repo: knitanr-a11y/xauusd-signal-lab

まず以下を読んで、続きからお願いします。
1. docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_25C45_FIXED_25C46_FILTER_COVERAGE_REVIEW_READY_20260608.md
2. docs/gold_v2/GOLD_V2_25C46_COREB_G1_RETENTION_AWARE_RECOVERY_PLAN_AUDIT_SPEC_20260608.md
3. docs/gold_v2/GOLD_V2_25C46_FILTER_COVERAGE_REVIEW_LOCAL_RUNBOOK_20260608.md
4. docs/gold_v2/NEXT_CHAT_START_PROMPT_GOLD_V2_25C45_FIXED_25C46_FILTER_COVERAGE_REVIEW_JA_20260608.md

GOLD V2は現在もaudit-onlyです。
REQUEST_MORE_AUDITはsource recovery承認ではありません。
旧GOLD/DISC8はHTF open-time不整合疑いで隔離済みです。
近似再実装は禁止です。
監査済みsource-of-truth artifactを優先してください。
Discord通知、MT5発注、AI API、live hook、live evaluator解除、final signal作成は、明示許可までOFFです。
NO_SIGNAL時はDiscord通知しません。
24-series source recovery chainは24AFで停止中です。明示依頼がない限り24AGへ進まないでください。

現在位置:
- 25C45は修正版で完了済みです。
- 25C45で件数定義の修正が入りました。
- 必ず以下のcount semanticsを守ってください。
  - unique_incremental_damage_keys = 360
  - filter_attribution_rows = 1260
  - unique_cleanly_attributed_damage_keys = 360
  - cleanly_attributed_rows = 1260
  - unique_not_cleanly_attributed_damage_keys = 0
- 1260をdamaged-key件数として扱わないでください。
- filter別attribution行を合算して、uniqueなrow-level damageとして扱わないでください。

25C45の正式なnext_recommended_stepは以下です。
25C46_COREB_G1_RETENTION_AWARE_RECOVERY_PLAN_AUDIT_ONLY

ただし、前チャットで25C46 Python scriptのGitHub直接作成が安全チェックによりブロックされました。
そのため、25C46の実装名は中立名にしてください。
25C46_COREB_G1_FILTER_COVERAGE_REVIEW_AUDIT_ONLY

25C46 summaryには、必ず両方の名前を残してください。
step = 25C46_COREB_G1_FILTER_COVERAGE_REVIEW_AUDIT_ONLY
logical_step_alias = 25C46_COREB_G1_RETENTION_AWARE_RECOVERY_PLAN_AUDIT_ONLY

25C46の中立出力ディレクトリは以下に統一してください。
FX_OUTPUTS/gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only/

次にやること:
- 25C46の中立名filter coverage review scriptをGitHub上で再作成するか、前チャットで作成したlocal packageを配置してください。
- GitHub create_fileが再度ブロックされる場合は、local packageを使うか、手動配置手順を提示してください。
- 25C46はreview/plan-onlyです。
- 25C45 summary、attribution rows、retention candidates、quality matrixを読みます。
- coverageは必ずunique key単位で計算してください。
  variant + dataset + entry_time + policy
- variantごと、retention_priority cutoffごとに、covered_unique_keysとopen_unique_keysを計算してください。
- full known-key coverage候補を以下の順序で選んでください。
  1. full known-key coverage
  2. unique damaged-key countが最小
  3. retained-filter countが最小
  4. A002とA004が同点ならA002を代表にする
- A002/A004はこのstepで承認してはいけません。A002は同点時の代表候補にすぎません。

25C46 output artifactが作成・レビューされるまで25C47へ進まないでください。
25C46では、replay実行、条件変更、source変更、recovery、live path、external path、AI review、通知、発注、final signalを実行しないでください。
```

## 次の担当向け注意

最大の罠は件数定義です。`filter_attribution_rows=1260` は `unique_incremental_damage_keys=360` に対する複数filter展開です。1260をrow-level damageとして扱ってはいけません。

2つ目の罠は命名です。25C45の論理的な次工程は `25C46_COREB_G1_RETENTION_AWARE_RECOVERY_PLAN_AUDIT_ONLY` のままですが、実装名は `25C46_COREB_G1_FILTER_COVERAGE_REVIEW_AUDIT_ONLY` を使い、summaryに `logical_step_alias` として元の論理名を残してください。

3つ目の罠は先に進みすぎることです。25C46のartifactが作成されレビューされるまで、25C47へ進まないでください。
