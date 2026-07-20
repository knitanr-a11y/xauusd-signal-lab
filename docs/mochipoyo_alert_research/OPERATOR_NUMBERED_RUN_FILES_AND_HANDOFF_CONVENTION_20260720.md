# Mochipoyo operator run-file numbering and handoff convention

## Status

Mandatory operator-facing convention for all future stages and handoff documents.

## Numbered run-file rule

Every user-executed BAT file introduced or renamed in a future operator workflow must have a two-digit numeric prefix that matches the required execution order.

Canonical M7C operator order:

1. `01_run_collect_events_cloudflare_forever.bat`
2. `02_run_initialize_m7c_prospective_shadow_runtime_once.bat`
3. `03_run_build_m7c_prospective_shadow_once.bat`
4. `04_run_m7c_prospective_shadow_forever.bat`
5. `05_stop_m7c_prospective_shadow_forever.bat`
6. `06_open_mochipoyo_monitor_folders.bat`

The number is part of the physical filename, not only a numbered instruction list.

Existing unnumbered files must not be silently mixed with numbered replacements. A migration must either:

- rename all affected operator BAT files and update every caller and document in the same change, or
- keep the existing files temporarily and state clearly that physical renaming is still pending.

## Required handoff section

Every future Mochipoyo handoff must contain a clearly visible section titled `実行ファイルと実行順` and must state all of the following:

- the exact numbered filename;
- whether it is one-shot, continuous, stop-only, or folder-opening;
- the exact execution order;
- which files must run simultaneously in separate windows;
- which file must be run only once;
- the exact local output folders;
- the exact files the user may need to upload;
- the stop and fail-closed conditions;
- whether any old unnumbered filename remains valid;
- the old-to-new filename mapping when a rename occurred.

## Required user-facing pre-run checklist

Before asking the user to execute files, provide one complete checklist containing:

1. numbered run files;
2. execution order;
3. files that stay running;
4. files that run once;
5. output folder locations;
6. required upload files and when they are needed;
7. expected success text;
8. exact error text or exit code that requires stopping.

Do not reveal required files piecemeal after the user has already started monitoring.

## Prohibited ambiguity

- Do not refer to a BAT file only as “the collector” or “the M7C file.”
- Do not present an unnumbered filename when a numbered replacement exists.
- Do not omit required upload files from the initial instructions.
- Do not make the user search a shared log directory without naming the dedicated subfolder.
- Do not claim a physical rename has occurred unless the repository filename was actually changed and all references were updated.

## Audit-only safety

This convention changes operator usability only. It does not change frozen formulas, prospective start rules, source matching, review gates, raw alerts, MT5 CSVs, Discord, MT5 orders, entry gates, live-ready, or final-signal settings.
