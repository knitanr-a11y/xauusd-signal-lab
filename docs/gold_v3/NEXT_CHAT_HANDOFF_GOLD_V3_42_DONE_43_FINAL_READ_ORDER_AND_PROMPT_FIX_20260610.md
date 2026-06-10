# GOLD V3 42 -> 43 final read order and prompt fix

Created JST: 2026-06-10

## Why this file exists

The three handoff documents were re-read after creation. One issue was found:

- `NEXT_CHAT_HANDOFF_GOLD_V3_42_DONE_43_NEXT_EXACT_ENTRY_PRUNE_HONMEI_20260610.md` still contains an older embedded next-chat prompt that only names that single handoff file and omits the later addenda.
- That embedded prompt is now superseded by this file.

Do not use the older embedded prompt from the first handoff file.

## Correct read order for the next chat

Read these four files in this order:

```text
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_42_DONE_43_NEXT_EXACT_ENTRY_PRUNE_HONMEI_20260610.md
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_42_DONE_43_MUST_READ_SOURCE_CHECK_ADDENDUM_20260610.md
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_42_DONE_43_STAGE01_40_READCHECK_ADDENDUM_20260610.md
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_42_DONE_43_FINAL_READ_ORDER_AND_PROMPT_FIX_20260610.md
```

This file is the final override for read order and start prompt.

## Correct next-chat start prompt

```text
repo: knitanr-a11y/xauusd-signal-lab

まず以下4本を読んで、続きからお願いします。

docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_42_DONE_43_NEXT_EXACT_ENTRY_PRUNE_HONMEI_20260610.md
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_42_DONE_43_MUST_READ_SOURCE_CHECK_ADDENDUM_20260610.md
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_42_DONE_43_STAGE01_40_READCHECK_ADDENDUM_20260610.md
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_42_DONE_43_FINAL_READ_ORDER_AND_PROMPT_FIX_20260610.md

GOLD V3はsource-of-truth constrainedです。
GOLD V2 / 旧GOLD / DISC8は隔離中で、読まない・使わない・参照しない・fallbackにしないでください。

近似live entry実装は禁止です。
Stage41 feature-only snapshotをtrading sourceにしないでください。
MT5実行は有効化しないでください。

次はStage43:
GOLD_V3_43_EXACT_ENTRY_AND_PRUNE_CONTRACT_FOR_HONMEI_SET_AUDIT_ONLY

本命セット:
- R03_P1_R1_ONLY_CD60_PRUNE_111
- R04_P4_R1_ONLY_CD60_PRUNE_115
- R1_ONLY_CD90_PRUNE_050__R1_ONLY_CD90_PRUNE_050_S030__R1_ONLY_CD90_PRUNE_050_S024

Stage15でbase entry family、Stage21/22/30/35/36で削り条件、Stage42で人間判断を確認してください。
Stage43ではexact entry/prune contractとレポートだけ作成してください。
live code、Discord live enablement、MT5 BAT、MT5発注は作らないでください。

重要:
Stage15/21/22/30/35/36の成果物はGitHub docs内に無い場合があります。
その場合は存在しないと決めつけず、FX_OUTPUTS/gold_v3側成果物を探すか、必要ファイルのアップロード依頼、またはBLOCKERで停止してください。
```

## Correct source stages for Stage43

Use the following source stages:

- Stage15: base entry family, source_rank, direction, profile, replay ledger.
- Stage21: initial selected prune filters.
- Stage22: within-candidate prune filters and `R1_ONLY_CD90_PRUNE_050` restore candidate.
- Stage30: all-retained filter contract for retained rows, especially R03/R04.
- Stage35: cumulative selected band pruning context, especially why P7/P8 PF improved but retained negative-month concerns.
- Stage36: final ranked active candidate contract and final filters for R03/R04.
- Stage42: human decision to add R03/R04/CD90 restore candidate to honmei review.

## Confirmed issue status after re-read

The following were checked:

1. First handoff: structurally useful, but its embedded next-chat prompt is outdated and superseded by this file.
2. Source-check addendum: useful and consistent; emphasizes that FX_OUTPUTS runtime artifacts may not be committed to repo.
3. Stage01-40 addendum: useful and consistent; records Stage1-13 availability limit and Stage14-40 status/log context.

## Final safety statement

Until Stage43 exact entry/prune contract is created and reviewed:

- no live code
- no live signal enablement
- no MT5 BAT
- no MT5 order action
- no Stage41 feature-only trading source
- no approximation from OHLC alone
