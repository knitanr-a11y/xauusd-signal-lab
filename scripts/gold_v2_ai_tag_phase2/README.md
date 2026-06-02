# GOLD V2 AI tag Phase 2

This folder is intended to be pulled into the clean GitHub clone.

Run order:

1. `bat/01_INSTALL_REQUIREMENTS_PHASE2.bat`
2. `bat/02_RUN_AI_TAG_PHASE2.bat`
3. `bat/03_EVALUATE_AI_TAG_PHASE2.bat`

Runtime outputs are written outside the repository to:

```text
Files\FX_OUTPUTS\gold_v2_ai_tag_phase2\
```

The scripts read the existing env file from:

```text
Files\xauusd-signal-lab\.env
```

Only `OPENAI_API_KEY` and optional `OPENAI_MODEL` are used. Discord and MT5 are not used.

Safety status:

```text
MT5 order_send: disabled
Discord send: disabled
dispatch_ready: false
```
