# GOLD V3 Stage276 handoff

正式状態: `GOLD_V3_276_NO_DISCOVERY_LEAD_AUDIT_ONLY`

## Stage276完了

- 81,781 M15 decision times
- 163,562 direction-expanded rows
- 48 sequence/state features
- 2 expanding monthly SGD families
- 32 model cells
- 40 event patterns × 2 exits = 80 event cells
- total 112 fixed cells
- prefix feature parity 64/64 PASS、max diff 0.0
- model score parity 4/4 PASS
- candidate replay parity 16/16 PASS
- 2024 discovery lead 0
- 2025 confirmation 0
- 2026 final 0

## 重要結論

Stage275 static snapshotだけでなく、Stage276 sequence/state transitionでもstrong candidateは作れなかった。

Stage276最上位:

`SGD_A5E4_Q95_M03_C4H_WIDE_225_40_3H`

- 2024 n98
- PF0.831
- mean -0.315 USD/oz
- LONG小幅プラス、SHORTマイナス
- 2025 PF0.503
- 2026 n9だけ高成績

2026を見て救済しない。

## 次Stage277

`GOLD_V3_277_EXTERNAL_CAUSAL_CONTEXT_DATA_AVAILABILITY_AUDIT_ONLY`

目的:

- 同一brokerのMT5で利用可能な外部context symbolをinventory化
- GOLDとの時刻・欠損・history range・spread契約を監査
- sourceが無いものを推測・補間・別broker fallbackしない
- まずデータ可用性のみ。成績探索を同時に行わない

優先inventory:

1. XAGUSD
2. USDJPY
3. EURUSD
4. US500 / NAS100
5. USD index proxy
6. yield / real-yield proxy
7. economic calendar event proximity

## 維持する禁止事項

- GOLD V2、旧GOLD、DISC8、Stage41を読まない
- 形成中HTF禁止
- future情報禁止
- candidate poolの手動除外禁止
- 2026だけの選択禁止
- live、final signal、MT5注文、Discord通知、partial close禁止

現行Specialist Health Router V3は変更しない。
