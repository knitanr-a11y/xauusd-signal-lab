# GOLD V3 Stage262 定義固定
## live-resolvable exit ledger と新情報readiness監査

作成日: 2026-06-20  
状態: `GOLD_V3_262_DEFINITION_LOCKED_AUDIT_ONLY`

## 目的

Stage261で判明した二つの問題を分離して監査する。

1. entryはlive再現できるが、固定ホライズン結果の一部が将来のpath completenessで除外されていた。
2. OHLC＋bar-level tick_volumeだけでは方向と到達順序を十分に判別できなかった。

Stage262Aでは、entry時点で決定可能なsession calendarとforced-exit規則を使い、全candidateを後から削除しない共通exit ledgerを作る。

Stage262Bでは、新しい方向情報を得るために必要なデータが現在の入力に存在するかを監査する。

このStageでは候補閾値・entry・方向・固定TP/SLを変更しない。

## 絶対契約

- audit-only。
- GOLD V2、旧GOLD、DISC8、Stage41を読まない。
- Stage260 E5〜E8のcandidate poolを削除しない。
- candidate eventは全件ledgerへ残す。
- entry時点で結果経路の完全性を知ることはできないため、future completenessを理由にcandidateを除外しない。
- holiday、short session、daily closeをCSV欠損から後付け推定してlive判定に使わない。
- broker/source別の事前公開session calendarがない場合はfail-closed BLOCKED。
- MT5発注、通知、live hook、order payload、autotrade、final signal禁止。

# Stage262A live-resolvable exit contract

## 対象候補

- E5 fixed cell: horizon 240分、TP25、SL10
- E6 fixed cell: horizon 240分、TP10、SL15
- E7 fixed cell: horizon 240分、TP25、SL10
- E8 fixed cell: horizon 60分、TP20、SL15

entry時刻・方向はStage260 live-parity済み出力をそのまま使用する。

## 必須calendar schema

calendarはbroker、server、symbol groupごとに事前提供され、最低限次の列を持つ。

- `calendar_id`
- `broker_or_server_id`
- `symbol_group`
- `server_timezone`
- `session_date`
- `session_open_time`
- `session_close_time`
- `is_holiday_closed`
- `is_short_session`
- `published_at`
- `source_name`
- `source_version`

要件:

- calendar rowは対象session開始前に公開済みであること。
- `published_at <= entry_time`を満たすこと。
- regular weekly scheduleだけでholiday/short sessionを代用しない。
- CME calendarは参考情報であり、broker CFDの取引時間と一致する証拠がない限りbroker calendarの代用にしない。
- gold#とgoldsharpが同一server scheduleであるかを証明できない場合は別calendarとして扱う。

## pre-known forced exit

固定値:

- `FORCED_EXIT_BUFFER_MIN = 5`

candidate entry時点でcalendar rowを参照し、次を計算する。

- `nominal_exit_time = entry_time + fixed_horizon`
- `calendar_forced_exit_time = session_close_time - 5分`
- `planned_exit_time = min(nominal_exit_time, calendar_forced_exit_time)`

entry可否:

- calendar rowがない: `CALENDAR_MISSING_NO_ENTRY`
- calendarがentry時点で未公開: `CALENDAR_NOT_PREKNOWN_NO_ENTRY`
- holiday closed: `HOLIDAY_CLOSED_NO_ENTRY`
- `planned_exit_time <= entry_time`: `TOO_CLOSE_TO_SESSION_END_NO_ENTRY`
- それ以外: `TRADE_OPENED`

candidate自体は削除せず、trade eligibility状態を記録する。

## exit price contract

TRADE_OPENEDのみ評価する。

- entry価格: entry_timeに始まるM1 OPEN
- TP/SL: entry後のM1 high/lowで監視
- 同一M1 TP＋SL: SL優先
- TP/SL未到達の場合、`planned_exit_time`に始まるM1 OPENでforced exit
- `planned_exit_time`のM1が存在しない場合は価格を補間せず`DATA_MISSING_BLOCKED`
- 次のM1、直前M1、M5 closeへfallbackしない
- weekend/short-session跨ぎは禁止

planned_exit_timeはentry時点で固定し、後からsession closeを変更しない。calendar revisionがある場合は、revisionがentry前に公開済みだった場合のみ採用する。

## exit state machine

状態:

- `CANDIDATE_LOGGED`
- `NO_ENTRY_CALENDAR`
- `OPEN`
- `TP_EXIT`
- `SL_EXIT`
- `FORCED_EXIT`
- `DATA_MISSING_BLOCKED`

state snapshot必須項目:

- candidate_id / candidate_key
- entry_time / entry_price
- direction
- fixed_horizon / TP / SL
- calendar_id / source_version / published_at
- session_close_time
- planned_exit_time
- current state
- last_processed_m1_time
- exit_time / exit_price / exit_reason

## batch/live parity

別実装で次を完全一致させる。

- candidate eligibility状態
- planned_exit_time
- entry_price
- exit_time
- exit_price
- exit_reason
- gross_pnl
- cost2_pnl

必須監査:

- prefix invariance
- restart invariance
- same-M1 SL priority
- forced-exit M1 exact timestamp
- calendar published_at parity
- candidate pool count invariance
- resolved-only health: `exit_time <= current_entry_time`のみ使用

## Stage262A formal判定

- calendar schemaと全対象session rowが事前情報として存在し、全candidateがentry/no-entry/exitへ決定的に解決できる: `LIVE_RESOLVABLE_EXIT_LEDGER_READY`
- calendarはあるがM1価格欠損で全件解決不能: `EXIT_PRICE_DATA_BLOCKED`
- broker別pre-known calendarがない: `PREKNOWN_BROKER_CALENDAR_BLOCKED`

# Stage262B new information readiness

## 現在データで確認する項目

### tick arrival timing / sub-bar path

必要:

- tick timestamp
- bid
- ask
- lastまたはmid
- tick sequence

M1/M5 OHLCとtick_volume合計だけでは代用不可。

### bid/ask / spread path

必要:

- tickまたは秒単位bid/ask
- spreadの時間内最大・平均・終盤値

M5の単一spread列だけではpath判別不可。

### external synchronized markets

必要:

- DXYまたはUSD index
- 米2年金利
- 米10年金利
- COMEX GC futures
- 共通UTC timestamp
- source availability time

後から修正された終値だけでなく、当時利用可能だったtimestamp契約が必要。

### pre-known macro calendar

必要:

- event name
- scheduled UTC time
- importance
- first publication timestamp
- revision history

actual/surpriseをentry前filterへ使わない。scheduled timeのみ事前情報として使用可能。

### multi-broker robustness

必要:

- 独立broker/serverの同時間帯データ
- symbol mapping
- timezone mapping
- spread/tick-volume定義

同一価格feedの別symbol名は独立sourceと数えない。

## readiness判定

各カテゴリを次で分類する。

- `READY_NOW`
- `PARTIAL_NOT_DIRECTIONAL`
- `MISSING_EXTERNAL_DATA`
- `SOURCE_IDENTITY_UNPROVEN`

## Stage262全体判定

可能な正式状態:

- `GOLD_V3_262_EXIT_LEDGER_READY_NEW_INFORMATION_REQUIRED_AUDIT_ONLY`
- `GOLD_V3_262_PREKNOWN_CALENDAR_AND_NEW_DATA_REQUIRED_BLOCKED_AUDIT_ONLY`
- `GOLD_V3_262_EXIT_PRICE_DATA_BLOCKED_AUDIT_ONLY`

いずれもlive-readyではない。

## 運用状態

`NO_LIVE_PROMOTION_AUDIT_ONLY`
