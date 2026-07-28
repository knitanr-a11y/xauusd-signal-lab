# MOCHIPOYO Alert Research 次チャット引き継ぎ

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/mochipoyo-alert-research`
- scope: `XAUUSD_GOLD_ONLY`
- mode: `AUDIT_ONLY`
- current formal status: `ALL_NINE_FORWARD_LOOPS_RUNNING_M10P_PRESERVED_START_RECOVERY_HEALTH_PASS_AUDIT_ONLY`
- next formal status: `ALL_NINE_FORWARD_LOOPS_FRESH_ACCUMULATION_AND_REVIEW_GATE_WATCH_NEXT`
- recorded date: `2026-07-29`

この文書は、M10W29以降の研究、M10W34 fresh shadow開始、9本一括dashboard導入、M10Pのoperational incident、preserved-start recovery、現在の監視状態と次の操作を一つにまとめた正式引き継ぎです。

---

## 1. 次チャットで最初に読む順序

必ず次の順番で、最初から最後まで読むこと。

1. `docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_ALL_NINE_RUNNING_M10P_RECOVERY_PASS_REVIEW_GATE_WATCH_20260729.md`
2. `config/mochipoyo_alert_research/current_state_20260729.json`
3. `config/mochipoyo_alert_research/next_action_20260729.json`
4. `config/mochipoyo_alert_research/m10p_preserved_start_recovery_health_user_local_result_20260729.json`
5. `config/mochipoyo_alert_research/m10p_blocked_user_local_diagnostic_result_20260729.json`
6. `config/mochipoyo_alert_research/m10p_preserved_start_recovery_implementation_audit_20260729.json`
7. `config/mochipoyo_alert_research/m9v_plus_read_only_dashboard_implementation_audit_20260729.json`
8. `config/mochipoyo_alert_research/m10w34_user_local_initial_health_result_20260728.json`
9. `config/mochipoyo_alert_research/m10w33_user_local_result_20260728.json`
10. `config/mochipoyo_alert_research/m10w32_scale_normalized_entry_preregistration_20260728.json`
11. `config/mochipoyo_alert_research/m10w31_user_local_result_20260728.json`
12. `config/mochipoyo_alert_research/m10w30_independent_covariate_shift_result_20260728.json`
13. `config/mochipoyo_alert_research/m10w29_user_local_result_20260728.json`

必要な場合のみ、その文書から参照される実装ファイルを読むこと。古いinitializerを実行判断の根拠にしないこと。

---

## 2. 現在の正式状態

現在、次の9本のfresh prospective shadow loopはすべて稼働状態へ戻っている。

- M9V
- M9Y
- M10B
- M10E
- M10P
- M10P2
- M10W19
- M10W26
- M10W34

M10Pは旧画面ではなく、次のpreserved-start recovery画面が現在の正式なM10P loop画面である。

```text
scripts\mochipoyo_alert_research\m10p_incident\bat\02_recover_m10p_preserved_start_once.bat
```

このBATは既に1回成功済みであり、**再実行は禁止**。画面だけを稼働継続する。

collector、M7C、M8Cも変更せず稼働継続する。

---

## 3. 絶対に保持する不変start

時刻基準はすべてMT5サーバー時刻。M7CのみUTC記録。

| loop | immutable start |
|---|---|
| M7C | `2026-07-20T14:54:15Z` |
| M9V | `2026.07.24 11:04:00` |
| M9Y | `2026.07.24 12:45:00` |
| M10B | `2026.07.24 20:54:00` |
| M10E | `2026.07.24 22:06:00` |
| M10P | `2026.07.24 23:56:00` |
| M10P2 | `2026.07.27 01:39:00` |
| M10W19 | `2026.07.28 02:31:00` |
| M10W26 | `2026.07.28 15:58:00` |
| M10W34 | `2026.07.28 18:19:00` |

これらを変更、再作成、reset、backfillしてはならない。

---

## 4. 永久禁止事項

次は明示的なincident対応契約がない限り永久禁止。

- M9V以降の既存loop BAT01／initializerを実行しない。
- M10W26 BAT01を実行しない。
- M10W34 BAT01を実行しない。
- M10P BAT01を実行しない。
- M10P preserved-start recovery BAT02を再実行しない。
- M10P recovery health BAT03を再実行しない。
- 健康なloopを停止・再起動しない。
- `taskkill`、強制終了、force-closeをしない。
- lock、runtime、state、start receipt、prestart audit、snapshot、adapter journalを手動削除・編集しない。
- prospective startを変更・resetしない。
- start以前をhistorical backfillしない。
- nearest M1 fallbackを使わない。
- formula、threshold、session、ATR境界、horizon、exit、runner semanticsを事後調整しない。
- Discord送信、MT5注文、live-ready、final signal、automatic promotionを行わない。
- dashboardの`REACHED`表示だけでcheckpointや昇格を自動実行しない。
- M10Vは、M10PとM10P2の両方が`resolved >= 20`かつintegrity PASSになるまで禁止。

CSV最新行は契約上closed。open/as-of扱いは禁止。

---

## 5. M10W29までの低ATR候補評価

M10W27でlow-ATR bullish causal NEITHERのoutcome-blind情報監査を実施。

- rows: 7480
- 2023: 1562
- 2024: 2078
- 2025: 3193
- 2026: 647
- timing violation: 0
- outcome/future read: 0
- source feature SHA256: `03f0185694485eab2b5e50ab93c2f354a91cdd8b0706f7710b66c2b1173648cd`
- package SHA256: `e9f63f4e8a83e35c5c1274edf41b5abcacb9a65e90280382077955491b80ce1b`

M10W28で3候補を事前登録し、M10W29で固定評価。

### LMVI1

- classification: `REJECT`
- test PF: `0.8792`

### LMWR1

- classification: `WEAK_OR_INCONSISTENT`
- test PF: `1.0486`

### LMMO1

- classification: `REJECT`
- test PF: `0.5806`

正式判定:

```text
PASS_NO_ADVANCING_LOW_ATR_MICROSTRUCTURE_ENTRY_FAMILY_AUDIT_ONLY
```

3候補はすべてadvanceなし。救済、threshold変更、再調整は禁止。

正式結果:

- `config/mochipoyo_alert_research/m10w29_user_local_result_20260728.json`
- user package SHA256: `9584283d1a7079d50f33f360a616d1ff9b91dcf1e6a69797ef366f5e57919840`
- result commit: `b5c777548248823474890bcb7d27c944a18502f4`

---

## 6. M10W30 covariate shift診断

M10W29失敗後、候補救済ではなくcovariate scale shiftだけを診断。

正式判定:

```text
PASS_MATERIAL_2026_COVARIATE_SCALE_SHIFT_DIAGNOSTIC_ONLY
```

2026で大きなPSI:

- `spread_bps`: `10.7827`
- `m5_range3_bps`: `1.4680`
- `m1_range5_bps`: `1.3350`
- `m5_ret3_bps`: `0.3340`

formula trigger densityの崩壊ではなかった。M10W29候補を救済する根拠ではない。

正式結果:

- `config/mochipoyo_alert_research/m10w30_independent_covariate_shift_result_20260728.json`
- commit: `c87893f9f61d6147be35a8b262180ba7c01c1f64`

---

## 7. M10W31 scale-normalized情報監査

7480行の同一decision setで、scale-normalized causal informationが利用可能と確認。

正式判定:

```text
PASS_SCALE_NORMALIZED_CAUSAL_INFORMATION_AVAILABLE_AUDIT_ONLY
```

- rows: 7480
- source feature SHA256: `8ad229791f1fb1a14760e715c65d03b4431bcea5f261155cd49dfb028175cc52`
- package SHA256: `7483f46087c5ed8cfb673dc0c34976a57387885738e5ecaa6a568f89b6612120`
- selected normalized features: test PSIすべて`< 0.05`
- absolute ATR/spread系のsevere drift特徴は除外

正式結果:

- `config/mochipoyo_alert_research/m10w31_user_local_result_20260728.json`
- commit: `b4b8c5d16324e76050bf9b1f14e9408647287877`

---

## 8. M10W32事前登録した3候補

実行契約はexact M1 entry、decision時のactual spread、+240分exact M1 bid exit、one-position、chronological overlap skip、fixed $0.20と+1/+2bps cost sensitivity。

### SNRI1

```text
m5_range3_over_h1_atr14 >= 0.40
m5_ret3_over_h1_atr14 > 0.0
m5_close_location >= 0.6666666666666666
```

### SNRC1

```text
m15_close_minus_ema20_over_h1_atr14 >= 0.0
m15_close_minus_ema20_over_h1_atr14 <= 0.50
m5_ret3_over_h1_atr14 > 0.0
m5_close_location >= 0.60
```

### SNDX1

```text
m5_range3_over_h1_atr14 >= 0.40
m1_range5_over_h1_atr14 >= 0.20
m1_ret5_over_h1_atr14 > 0.0
m1_close_location >= 0.60
```

正式契約:

- `config/mochipoyo_alert_research/m10w32_scale_normalized_entry_preregistration_20260728.json`
- commit: `fe99cb77a88fe2450b363ce763d58cdfae96f83c`

---

## 9. M10W33固定評価結果

user package SHA256:

```text
fa41d4717e32e5f02cade9043928e27d2d023b13148f7d80b53cdd84edb33a13
```

独立ledger検証:

- trade rows: 1126
- overlap rows: 1633
- split counts/PF/netはsummaryと一致
- actual/fixed/+2bps metricsも一致
- formula/threshold/horizon変更なし
- M10W29救済なし
- M10W26変更なし

### SNRI1

- classification: `REJECT`
- resolved: 398
- train PF: `1.152486`
- validation PF: `2.275403`
- test: 32
- test PF: `0.860648`
- test net: `-90.8876 bps`
- all PF: `1.482758`
- +2bps all PF: `1.296400`
- advance: false

### SNRC1

- classification: `REJECT`
- resolved: 342
- train PF: `1.722462`
- validation PF: `1.248178`
- test: 31
- test PF: `0.720876`
- test net: `-186.9362 bps`
- all PF: `1.350331`
- +2bps all PF: `1.164788`
- advance: false

### SNDX1

- classification: `ROBUST_CANDIDATE`
- candidates: 914
- accepted: 365
- resolved: 361
- overlap: 549
- train PF: `1.604068`
- validation PF: `1.774648`
- test: 32
- test PF: `1.187205`
- test net: `+106.2531 bps`
- all PF: `1.625336`
- all net: `+2803.8644 bps`
- fixed all PF: `1.614485`
- +2bps all PF: `1.434675`
- advance: true

正式判定:

```text
PASS_ONE_ROBUST_SNDX1_CANDIDATE_FRESH_SHADOW_AUTHORIZED_AUDIT_ONLY
```

重要: historical supportはfresh supportではない。SNDX1は独立fresh shadowへ進めるだけで、live/final昇格ではない。

正式結果:

- `config/mochipoyo_alert_research/m10w33_user_local_result_20260728.json`
- commit: `ab602d24108529cd7677f7499473a03d9387f96f`

---

## 10. M10W34 SNDX1 fresh prospective shadow

目的:

- low-ATR bullish prefix-causal NEITHER内でSNDX1だけを独立fresh shadow
- 既存8本を変更しない
- exact formula維持
- exact M1 actual-spread entry
- exact M1 bid exit +240分
- one-position、chronological overlap skip
- fixed $0.20、+1/+2bps cost sensitivity
- review gates: resolved 20/60/120
- audit-only

対象regime:

```text
D1 EMA20 > EMA30 > EMA40
H4 EMA20 > EMA30
H1 MACD line(6,13) > 0
H1 ATR percentile100 < 0.33
causal coverage = NEITHER
```

契約:

- `config/mochipoyo_alert_research/m10w34_sndx1_fresh_prospective_shadow_contract_20260728.json`
- contract commit: `34d3d55b4ed61f9fb22bd83e1fa011e4d40731fa`

不変start:

```text
2026.07.28 18:19:00
```

initial health正式判定:

```text
PASS_M10W34_INITIAL_HEALTHY_RUNNING_AUDIT_ONLY
```

initial health package SHA256:

```text
dfee3076f45e53e31ccbb097e88416702aff53c650348d0e9fe3531cb6c799c4
```

initial health確認:

- exactly one process
- exactly one lock
- successful cycles: 7
- transient waiting: 0
- terminal failures: 0
- runtime/state/start/prestart一致
- private snapshot 6ファイル整合
- shared journal 6本整合
- runtime/start変更なし
- initial candidate/resolved 0は正常

M10W34 BAT01は永久禁止。現在はBAT03画面を継続稼働。

20/60/120件でのみ、review後に次のread-only checkpointを使う。

```text
scripts\mochipoyo_alert_research\m10w34\bat\06_audit_checkpoint_read_only.bat
```

---

## 11. M9V以降一括dashboard

9本を一画面で確認するread-only dashboardを追加。

実行BAT:

```text
scripts\mochipoyo_alert_research\dashboard\bat\01_watch_all_forward_status.bat
```

表示:

- loop health
- lock/PID
- immutable start
- loop固有progress
- review gate
- update age

60秒ごとに更新。dashboardだけは`Ctrl+C`で閉じてもloopに影響しない。

### V1 incident

最初のV1ではM10PのPIDがstatusにもlockにもない場合に、`None > 0`を評価してdashboardだけが停止。

```text
TypeError: '>' not supported between instances of 'NoneType' and 'int'
```

monitor、runtime、start、lock、journalへの影響なし。

### V2修正

- PID不明を`pid=-`表示
- null countを0として安全表示
- 1行の欠損で全体停止しない

### V3修正

M10P operational incidentの再発防止として、Windows status JSON読取で`FILE_SHARE_DELETE`を許可。

- active implementation: `scripts/mochipoyo_alert_research/dashboard/python/forward_status_dashboard_v3.py`
- dashboardはread-only
- status JSONのatomic replaceを妨げない

正式監査:

- `config/mochipoyo_alert_research/m9v_plus_read_only_dashboard_implementation_audit_20260729.json`

`REACHED`または`FORMAL`が表示された場合、checkpointを先に実行せずdashboard全体を提出する。

---

## 12. M10P operational incident

V2 dashboardで次を検出。

```text
M10P BLOCKED lock=N pid=-
```

検出時点の表示:

- start: `2026.07.24 23:56:00`
- accepted: 1
- resolved: 0
- open: 1
- status age: 約47分

M10Pだけfail-closed停止。他の8本はRUNNING。

### 読取専用診断

診断BAT:

```text
scripts\mochipoyo_alert_research\m10p_incident\bat\01_collect_m10p_blocked_diagnostic_read_only.bat
```

診断package SHA256:

```text
365941e42fd9fdd73b0ac1d30febb85c7640b92f7308e5acb7882d75d45d5a30
```

正式診断:

```text
PASS_OPERATIONAL_STATUS_PUBLICATION_RACE_PRESERVED_START_RECOVERY_AUTHORIZED_AUDIT_ONLY
```

原因:

- M10P計算cycle 251は正常PASS
- その後、dashboard用status JSONのatomic replaceでWindows一時アクセス拒否
- `PermissionError [WinError 5]`
- research failureではない
- integrity failureではない
- runtime/start/evidence破損なし

停止直前の正常metrics:

- candidate_match_count: 2
- accepted_count: 1
- resolved_count: 0
- open_count: 1
- overlap_skip_count: 1
- entry_data_gap_count: 0
- exit_data_gap_count: 0

runtime SHA256:

```text
7c175a4262deb0c0e5889fc5c5a77b225b04ec8e83ff6fab4fefc74ab87cbc66
```

LATEST runtime copyと完全一致。

正式結果:

- `config/mochipoyo_alert_research/m10p_blocked_user_local_diagnostic_result_20260729.json`

---

## 13. M10P preserved-start recovery

BAT01やinitializerを使わず、既存start・runtime・state・receipt・LATESTを検証して同じstartのまま再開。

回復BAT:

```text
scripts\mochipoyo_alert_research\m10p_incident\bat\02_recover_m10p_preserved_start_once.bat
```

実装上の再発防止:

- status publicationを最大15秒再試行
- status publicationだけの共有競合ではresearch loopをterminal停止させない
- dashboard V3は`FILE_SHARE_DELETE` read
- formula、threshold、horizon、entry、exit、cost、startは変更しない

回復BAT02は既に1回成功済み。再実行禁止。

---

## 14. M10P recovery health結果

user package:

- filename: `99_UPLOAD_PACKAGE(78).zip`
- SHA256: `5cc7e2ab4c6432ba019969a37452b7c58df38cf1a31b82ba009c0a13d457a92f`
- built UTC: `2026-07-28T19:01:07Z`

正式判定:

```text
PASS_M10P_PRESERVED_START_RECOVERY_HEALTHY_RUNNING_AUDIT_ONLY
```

health確認:

- status: RUNNING
- process alive: true
- lock present: true
- PID: 16252
- lock PID一致
- recovery cycles: 1
- successful recovery cycles: 1
- waiting transient: 0
- failed terminal: 0
- start全フィールド: `2026.07.24 23:56:00`で一致
- runtimeとLATEST runtime copy: 完全一致
- state/summary/health counts: 一致
- entry data gap: 0
- exit data gap: 0
- runtime/start変更: false

health監査時metrics:

- candidate_match_count: 2
- accepted_count: 1
- resolved_count: 0
- open_count: 1
- overlap_skip_count: 1

open trade:

- trade ID: `M10P_T000001`
- decision: `2026.07.28 19:00:00`
- entry: `2026.07.28 19:00:00`
- scheduled exit: `2026.07.28 23:00:00`
- audit時latest M1: `2026.07.28 21:58:00`
- OPEN判定はcausally consistent

正式結果:

- `config/mochipoyo_alert_research/m10p_preserved_start_recovery_health_user_local_result_20260729.json`

M10Pはfresh accumulationへ復帰済み。回復画面をそのまま稼働継続する。

---

## 15. 現在のreview gate

動的な現在件数は、この文書ではなくdashboardの最新表示を正とする。

| loop | gate判定に使う値 | review gates |
|---|---|---|
| M9V | V0/V1/V2のmaximum accepted | 20 / 60 / 120 |
| M9Y | Y0 accepted | 20 / 60 / 120 |
| M10B | M5 accepted | 20 / 60 / 120 |
| M10B | H1 accepted | 5 / 10 / 20 |
| M10B | H4 accepted | descriptive 5 |
| M10E | E0 accepted | 5 / 10 / 20 |
| M10P | resolved | 5 / 10 / 20 |
| M10P2 | resolved | 5 / 10 / 20 |
| M10W19 | filtered resolved | 20 / 60 / 120 |
| M10W26 | resolved | 20 / 60 / 120 |
| M10W34 | resolved | 20 / 60 / 120 |

M10PとM10P2の両方がformal 20 resolvedかつintegrity PASSになるまでM10Vは禁止。

---

## 16. 現在の即時アクション

今すぐ新しい研究BATやuploadは不要。

1. collector、M7C、M8Cを継続。
2. 9本のloopをすべて継続。
3. M10Pはpreserved-start recovery画面を継続。
4. dashboard V3を任意で継続。
5. dashboardで初めて`REACHED`または`FORMAL`が表示されたら、checkpointを実行せず全画面を提出。
6. review後に指示されたread-only checkpointだけを実行。
7. 自動昇格は行わない。

---

## 17. incident発生時の原則

- `BLOCKED`、lock欠損、PID欠損、age長期停止を見つけてもBAT01を実行しない。
- lockを手動で作成・削除しない。
- runtime/state/startを編集しない。
- まずdashboard全体を提出する。
- 必要なら専用read-only diagnosticを作成・実行して原因を確定する。
- research/integrity failureとoperational telemetry failureを混同しない。
- preserved-start recoveryは、診断で明示承認されたincidentだけに限定する。

---

## 18. 次チャット開始用プロンプト

```text
repo: knitanr-a11y/xauusd-signal-lab
branch: feature/mochipoyo-alert-research

もちぽよアラート研究の続きです。

最初に次を順番どおり、最初から最後まで読んでください。

1. docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_ALL_NINE_RUNNING_M10P_RECOVERY_PASS_REVIEW_GATE_WATCH_20260729.md
2. config/mochipoyo_alert_research/current_state_20260729.json
3. config/mochipoyo_alert_research/next_action_20260729.json
4. config/mochipoyo_alert_research/m10p_preserved_start_recovery_health_user_local_result_20260729.json
5. config/mochipoyo_alert_research/m10p_blocked_user_local_diagnostic_result_20260729.json
6. config/mochipoyo_alert_research/m10p_preserved_start_recovery_implementation_audit_20260729.json
7. config/mochipoyo_alert_research/m9v_plus_read_only_dashboard_implementation_audit_20260729.json
8. config/mochipoyo_alert_research/m10w34_user_local_initial_health_result_20260728.json
9. config/mochipoyo_alert_research/m10w33_user_local_result_20260728.json

現在、M9V/M9Y/M10B/M10E/M10P/M10P2/M10W19/M10W26/M10W34の9本はすべて稼働中です。
M10Pは2026.07.24 23:56:00の不変startを保持したpreserved-start recovery画面が正式loopです。
M10P BAT01、M10P recovery BAT02、M10W26 BAT01、M10W34 BAT01、その他既存loop initializerは永久禁止です。

今はdashboard V3でreview gateを待っています。
どれかがREACHED/FORMALになったら、checkpointを実行する前にdashboard全体を確認してください。
憶測でreset、再初期化、threshold変更、runner変更をしないでください。
```

---

## 19. 現在の正式参照

- current state: `config/mochipoyo_alert_research/current_state_20260729.json`
- next action: `config/mochipoyo_alert_research/next_action_20260729.json`
- M10P recovery health: `config/mochipoyo_alert_research/m10p_preserved_start_recovery_health_user_local_result_20260729.json`
- M10P diagnostic: `config/mochipoyo_alert_research/m10p_blocked_user_local_diagnostic_result_20260729.json`
- dashboard audit: `config/mochipoyo_alert_research/m9v_plus_read_only_dashboard_implementation_audit_20260729.json`
- M10W34 health: `config/mochipoyo_alert_research/m10w34_user_local_initial_health_result_20260728.json`
- M10W33 result: `config/mochipoyo_alert_research/m10w33_user_local_result_20260728.json`

この文書より古い引き継ぎは経緯参照に限定し、現在地・次アクション・禁止事項はこの文書と20260729 current state／next actionを優先する。
