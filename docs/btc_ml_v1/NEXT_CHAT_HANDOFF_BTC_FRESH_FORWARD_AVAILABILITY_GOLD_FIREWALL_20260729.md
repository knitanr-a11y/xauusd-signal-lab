# BTC ML V1 次チャット正式引き継ぎ — GOLD完全分離・fresh-forward availabilityのみ次

- repository: `knitanr-a11y/xauusd-signal-lab`
- required branch: `main`
- project: `BTC_ML_V1`
- symbol: `BTCUSD#`
- recorded date: `2026-07-29`
- formal status: `BTC_FIVE_CANDIDATES_REPRODUCED_FRESH_FORWARD_AVAILABILITY_NOT_YET_VERIFIED`
- next stage: `BTC_FF01_FRESH_FORWARD_DATA_AVAILABILITY_AUDIT_READ_ONLY`

この文書は、BTC4／BTC5／BTC6／BTC7R／BTC9Rの積み重ね候補研究を、GOLD・もちぽよアラート研究から完全に分離して再開するための最優先正本である。

古いBTCハンドオフは履歴・根拠確認用に限る。現在地、許可範囲、次アクション、停止条件はこの文書と次の3ファイルを優先する。

- `configs/btc_ml_v1/current_state_20260729.json`
- `configs/btc_ml_v1/next_action_20260729.json`
- `configs/btc_ml_v1/btc_gold_scope_firewall_20260729.json`

---

## 1. 最初に必ず読む順序

次チャットでは、GitHub `main`の次を順番どおり、最初から最後まで読む。

1. `START_HERE_BTC_ML_V1_NEXT_CHAT.md`
2. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_FRESH_FORWARD_AVAILABILITY_GOLD_FIREWALL_20260729.md`
3. `configs/btc_ml_v1/current_state_20260729.json`
4. `configs/btc_ml_v1/next_action_20260729.json`
5. `configs/btc_ml_v1/btc_gold_scope_firewall_20260729.json`
6. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_STACKING_2026_EVALUATED_20260702.md`
7. `docs/btc_ml_v1/BTC_STACKING_REPRODUCTION_FIX_AND_VERIFIED_RUN_20260702.md`
8. `docs/btc_ml_v1/BTC_STACKING_REPRODUCTION_AUDIT_AND_RUNBOOK_20260702.md`
9. `docs/btc_ml_v1/BTC_STACKING_PORTFOLIO_2026_EVALUATION_20260702.md`
10. `configs/btc_ml_v1/btc_candidate_master_catalog.json`
11. `configs/btc_ml_v1/btc_stacking_portfolio_2026_evaluation.json`
12. `configs/btc_ml_v1/btc_stacking_reproduction_reference.json`

ここに列挙されていない古いBTCハンドオフや旧entry-only文書は、上記の正本と矛盾する場合に使用しない。

---

## 2. 今回の引き継ぎを作った理由

別チャットでBTC研究を依頼した際、古いハンドオフを根拠にGOLD側の`M10W24B`へ触れる誤作業が発生した。ユーザーが元へ戻したが、BTCとGOLDの研究境界が守られなかったため、次の恒久対策を取る。

- BTC研究は`main`だけで行う。
- GOLD／もちぽよのfeature branchへ切り替えない。
- GOLD／もちぽよ／M10W関連ファイルを閲覧しない。
- BTC研究の実装をGOLD配下へ置かない。
- BTCの条件・結果をGOLDへ反映しない。
- GOLDの条件・runner・payoff・runtimeをBTCへ流用しない。

誤って作成された、または配置不適切だったBTC Stage 01一式は、cleanup commit

```text
0c23fd107680f0f323e956b5f7bbbddc6639243e
```

で`main`から削除済みである。このcleanup commitを含まない古い作業状態を基準にしない。

---

## 3. GOLD／もちぽよへの絶対禁止事項

BTCの作業中、次は**参照も変更も禁止**。

```text
docs/mochipoyo_alert_research/**
config/mochipoyo_alert_research/**
scripts/mochipoyo_alert_research/**
docs/gold_v3/**
docs/gold_ml_v1/**
config/gold_v3/**
config/gold_ml_v1/**
scripts/gold_v3/**
scripts/gold_ml_v1/**
```

明示的に禁止する対象:

- `M10W24B`
- その他すべての`M10W*`
- GOLD／XAUUSDの候補、契約、current state、next action、handoff
- GOLD／もちぽよのcollector、loop、BAT、lock、PID、runtime、state、journal、snapshot、checkpoint
- 稼働中のGOLDプロセスの停止、再起動、`taskkill`
- GOLD feature branchへのcheckout

BTCの調査中にGOLDを読む必要があるように見えた場合、その判断は誤りとして停止する。古いハンドオフからGOLD操作の許可を推測しない。

正式な機械可読契約:

- `configs/btc_ml_v1/btc_gold_scope_firewall_20260729.json`

---

## 4. BTC側で許可された主要範囲

主要な読み書き対象:

```text
START_HERE_BTC_ML_V1_NEXT_CHAT.md
docs/btc_ml_v1/**
configs/btc_ml_v1/**
scripts/btc_ml_v1/**
```

BTC FF01で、既存機能を再利用できるか確認するための読取専用support path:

```text
scripts/run_btc_youtube_candidates_dry_run_cycle.py
scripts/run_btc_youtube_candidates_operational_forever.py
scripts/btc_ml_v1/research/reproduce_btc_stacking_portfolio.py
RUN_BTC_STACKING_REPRODUCTION.bat
```

support pathは、既存のBTCファイル解決、broker-server-time変換、正本candidate engineの所在を確認するためだけに読む。FF01では変更しない。

repository全体を無差別検索せず、まず許可範囲に限定する。

---

## 5. 正式な最低基準と再現性

BTC6 CLI修正を含む正式な最低基準コミット:

```text
dc29fbf5345e26c7890b5ab836a0dd3182e99fe9
```

この基準以降で、2つの元データpackageから5候補をend-to-end再生成し、次を確認済み。

```json
{
  "reproduction_pass": true,
  "metric_errors": {},
  "fingerprint_errors": {},
  "unresolved_post2026": 0,
  "maximum_simultaneous_positions": 3
}
```

実物再現report SHA256:

```text
45fcde35def8d82e2ff67f11fc7131fbf8f3112eeccb761706bfb3e37f4e1989
```

必要な固定入力package:

```text
BTCUSD_HISTORY_CHAT_PACKAGE.zip
SHA256: 9b0b74e9937eca05e895047f5737c6794332af7ec25f2a30b64d9440c9e0dd22

BTCUSD_H4_WARMUP_PACKAGE.zip
SHA256: d150eaee0c126e2eb4c4aecb667ff0ad181a9a0a6e060cc5c1613b60e0a8019a
```

これらは2026-07-02時点までの固定再現用であり、fresh行を追加して固定reference再現を行う用途ではない。

---

## 6. 凍結済みの積み重ね5候補

| candidate ID | 主時間足 | lot | 状態 |
|---|---|---:|---|
| `BTC4_RISK_CAP_400` | H4 | 0.02 | ADOPTED_STACKING_CANDIDATE_NOT_LIVE |
| `BTC5_TWO_PIVOT_P2_CLEAN_N_382_786` | M5 | 未設定 | ADOPTED_STACKING_CANDIDATE_NOT_LIVE |
| `BTC6_M15_TWO_PIVOT_P3_BROAD_N_236_886` | M15 | 未設定 | ADOPTED_STACKING_CANDIDATE_NOT_LIVE |
| `BTC7R_M15_IMPULSE_HIGH_WIN_24_96_M22_R110` | M15 | 未設定 | ADOPTED_STACKING_CANDIDATE_NOT_LIVE |
| `BTC9R_M15_PREVDAY_BREAKOUT_HIGH_WIN_R080` | M15 | 未設定 | ADOPTED_STACKING_CANDIDATE_NOT_LIVE |

BTC10R、デモruntimeの候補、後から設定された運用lotは、この5候補研究へ混ぜない。

BTC4の0.02 lotを他候補へ横展開しない。

---

## 7. 確定済み成績

2026年以前:

- 142取引
- 104勝38敗
- 勝率73.239437%
- PF 2.786708
- 合計 +5768.321236 pips
- 最大DD 345.176061 pips

開封済み2026評価、データ終端`2026-07-02 02:15:00 UTC`:

- 43取引
- 26勝17敗
- 勝率60.465116%
- PF 2.023410
- 合計 +1199.423358 pips
- 最大DD 247.839574 pips
- 43件すべて決着済み

全評価期間:

- 185取引
- 130勝55敗
- 勝率70.270270%
- PF 2.583416
- 合計 +6967.744594 pips
- 最大DD 345.176061 pips
- 最大同時保有3ポジション

この結果を見て既存候補条件を再調整しない。

---

## 8. 固定契約

- symbol: `BTCUSD#`
- CSV `time`: bar open
- closed bars only
- $10 price movement = 1 pip
- primary spread: $30
- entry: decision後の正確な下位足open
- same lower barでSL／TP両方成立: 原則SL優先
- BTC4はTP1後、TP2より先にbreak-even判定
- BTC4 EMA applied price: Close
- BTC4 risk cap: 400 pips
- BTC4 H4 warmup: 2017年開始の長期データが必要
- BTC6 entry／exit判定: M15、M5ではない
- 完全一致時刻の別候補取引を重複除外しない
- global one-position capなし
- 最大同時保有実測3
- BTC7R／BTC9RのH1 EMA200傾斜は、M15 as-of結合後の`shift(4)`で前の確定H1値と比較
- orders disabled
- Discord disabled
- live-ready false
- final-signal false

---

## 9. fresh-forward境界

正式なexclusive cutoff:

```text
entry_dt > 2026-07-02 02:15:00 UTC
```

`2026-07-02 02:15:00 UTC`以前は開封済み評価期間であり、今後holdoutと呼ばない。

次の未使用forwardは、この時刻より後。

現時点では、ローカルにあるM5／M15／H1／D1／H4がcutoff後まで存在することを正式確認していない。

現在の判定:

```text
FRESH_FORWARD_DATA_NOT_YET_VERIFIED
```

---

## 10. 時刻契約

固定再現referenceのcutoffはUTC。

一方、現在の`Files`等にあるライブCSVのnaive timestampは、MT5 broker server wall-clockとして扱う。CSV時刻をそのままUTCとみなしてcutoff比較しない。

最新`main`のBTC freshness処理は、broker UTC+2またはUTC+3を推定し、UTCへ変換する。FF01ではその正本処理を再利用する。

禁止:

- 固定で2時間または3時間を引く独自実装
- 同じ目的の別UTC変換を新設
- 推定が曖昧なのに都合のよいoffsetを採用

availability結果には少なくとも次を残す。

- raw MT5 broker-server latest closed-bar time
- selected broker UTC offset
- offset inference evidence
- UTC-converted latest closed-bar time
- cutoff後の行数
- ambiguous／errorの明示

---

## 11. 現在の次StageはBTC FF01だけ

```text
BTC_FF01_FRESH_FORWARD_DATA_AVAILABILITY_AUDIT_READ_ONLY
```

目的は、候補条件を実行することではなく、ローカルに必要なclosed-barデータが存在するかを確認すること。

FF01完了前に次へ進まない。

- fresh performance evaluation
- candidate engine実行
- fresh trade生成
- portfolio成績計算
- lot設計
- monetary DD計算
- 新候補探索
- collector／常駐loop／dashboard
- Discord／MT5 order
- live化

---

## 12. FF01のphase 0 — 書込み前確認

新チャットは最初に次を行う。

1. repoと`main`を確認。
2. cleanup commit `0c23fd...`がcurrent mainのancestorであることを確認。
3. 本handoff、current state、next action、scope firewallを読む。
4. GOLD／もちぽよ／M10Wを検索しない。
5. 許可されたBTC範囲だけで、現在有効なavailability監査が既に存在するか確認。
6. 既存BTC support codeから、ファイル解決とbroker-time変換の正本を確認。
7. 既存の同等機能があれば重複実装しない。

phase 0の確認中はファイルを変更しない。

---

## 13. FF01の最小実装が必要な場合

現在有効な同等監査が存在しない場合だけ、次の範囲へ最小実装することを許可する。

```text
scripts/btc_ml_v1/fresh_forward_availability/
  python/
    audit_btc_fresh_forward_availability.py
  bat/
    00_READ_ME_FIRST.txt
    01_run_availability_audit.bat
    02_open_latest_results.bat

docs/btc_ml_v1/BTC_FF01_FRESH_FORWARD_AVAILABILITY_AUDIT_CONTRACT_20260729.md
configs/btc_ml_v1/btc_ff01_fresh_forward_availability_contract_20260729.json
```

リポジトリ直下へ新BATを置かない。GOLD／もちぽよ配下へ置かない。

ユーザーが実行するBATには実ファイル名で番号を付ける。

---

## 14. FF01で読むデータ

対象:

- M5
- M15
- H1
- D1
- H4 fresh tail
- BTC4用H4 long warmup

既知のBTCデータ場所と、ユーザーが明示したpathだけを確認する。

PC全体を再帰検索しない。

ファイルが見つからない場合、似た名前や別symbolのCSVを勝手に代用しない。

source CSVは読取専用。

- 追記しない
- 上書きしない
- copyしない
- mergeしない
- renameしない
- deleteしない
- 並べ替えて保存しない

---

## 15. FF01の必須出力項目

各timeframeについて次を記録。

- actual file path
- file size
- row count
- first raw timestamp
- latest raw closed-bar timestamp
- selected broker UTC offset
- offset inference evidence
- latest UTC timestamp
- `2026-07-02 02:15:00 UTC`より後の行数
- non-ascending timestamp count
- duplicate timestamp count
- read error／ambiguity

H4は別々に判定。

1. BTC4のwarmupが2017年開始またはそれ以前を満たすか
2. fresh H4 tailがcutoff後まで存在するか

warmupとfresh tailが別ファイルでもFF01では許容する。ただし、この段階で結合・再生成しない。

---

## 16. 候補別readiness

5時間足すべてがそろわないことを理由に、評価可能な候補まで一括BLOCKしない。

| candidate | FF01 readinessに必要な入力 |
|---|---|
| BTC4 | H4 long warmup + cutoff後H4 fresh tail + cutoff後M5 |
| BTC5 | cutoff後M5 |
| BTC6 | cutoff後M15 |
| BTC7R | cutoff後M5 + M15 + H1 |
| BTC9R | cutoff後M5 + M15 + H1 + D1 |

各候補を独立して次のどちらかに分類。

```text
READY
BLOCKED
```

BLOCKEDの場合は、不足または曖昧なtimeframeと理由を明記する。

---

## 17. FF01の出力構成

```text
%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\01_fresh_forward_availability\
  LATEST\
    00_READ_ME_FIRST.txt
    01_availability_summary.json
    02_availability_report.txt
    99_UPLOAD_PACKAGE.zip

  archive\
    <UTC execution timestamp>\
```

ZIPへ生CSVを含めない。

FF01の実行が完了したら、ユーザーには`LATEST\99_UPLOAD_PACKAGE.zip`だけを提出させる。

---

## 18. FF01完了時の強制停止

availability packageを作成した時点、または明確なBLOCKED reportを作成した時点で停止する。

次を自動で始めない。

- FF02 fresh performance evaluator
- candidate engine実行
- reproduction再実行
- `--skip-input-hash-check`
- lot決定
- portfolio monetary DD
- new candidate search
- operational runtime変更
- Discord／orders

ユーザーがZIPを提出し、結果をreviewし、明示許可するまでFF02は未承認。

---

## 19. reproduceスクリプトに関する禁止

`reproduce_btc_stacking_portfolio.py`は、2026-07-02時点の固定data SHA、行数、期間、entry fingerprint、期待metricsを照合する正本再現用。

fresh行を追加したCSVへ実行しない。

`--skip-input-hash-check`をfresh evaluatorの代用にしない。

固定referenceとの不一致を発生させるだけの無駄な実行をしない。

---

## 20. FF01で変更禁止のBTC資産

- BTC4／BTC5／BTC6／BTC7R／BTC9Rの条件
- threshold
- TP／SL
- exit order
- spread
- pip definition
- timeframe semantics
- H1 EMA200 slope semantics
- global overlap policy
- lot
- candidate adoption status
- existing operational runtime
- existing persistent state
- orders／Discord／live flags

既存runtimeを整理目的でrename・移動・再生成しない。

---

## 21. FF02はまだ未承認

将来のFF02候補名:

```text
BTC_FF02_FROZEN_FIVE_CANDIDATE_FRESH_FORWARD_PERFORMANCE_EVALUATION
```

FF02で将来使用する境界:

```text
entry_dt > 2026-07-02 02:15:00 UTC
```

ただし、FF01結果で候補別READYが確認され、ユーザーが明示許可した場合だけ設計する。

FF02でも凍結済みcandidate engineを再利用し、新規に条件を写経・再解釈しない。

未決済tradeは未来結果で埋めず、OPENとして扱う契約を別途作る。

---

## 22. 次チャットで期待する最初の回答

新チャットは文書を読んだ後、作業を始める前に次を簡潔に報告する。

```text
- repositoryとbranch
- 読んだ正本一覧
- BTC5候補ID
- exclusive fresh cutoff
- 現在の正式status
- 次StageがFF01 availability-onlyであること
- GOLD/Mochipoyo/M10W24Bを参照・変更しないこと
- phase 0では書込みをしないこと
- 同等監査がない場合だけ最小実装すること
- FF01 package作成後に停止すること
```

GOLDの状況説明やM10Wの読み込みは不要であり、行った場合はscope violation。

---

## 23. 新しいチャット開始用プロンプト

```text
repo: knitanr-a11y/xauusd-signal-lab
branch: main

BTC積み重ね候補研究を、GOLD／もちぽよ研究と完全分離して続けます。

最初にGitHub mainの次を順番どおり、最初から最後まで読んでください。

1. START_HERE_BTC_ML_V1_NEXT_CHAT.md
2. docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_FRESH_FORWARD_AVAILABILITY_GOLD_FIREWALL_20260729.md
3. configs/btc_ml_v1/current_state_20260729.json
4. configs/btc_ml_v1/next_action_20260729.json
5. configs/btc_ml_v1/btc_gold_scope_firewall_20260729.json
6. docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_STACKING_2026_EVALUATED_20260702.md
7. docs/btc_ml_v1/BTC_STACKING_REPRODUCTION_FIX_AND_VERIFIED_RUN_20260702.md
8. docs/btc_ml_v1/BTC_STACKING_REPRODUCTION_AUDIT_AND_RUNBOOK_20260702.md
9. docs/btc_ml_v1/BTC_STACKING_PORTFOLIO_2026_EVALUATION_20260702.md
10. configs/btc_ml_v1/btc_candidate_master_catalog.json
11. configs/btc_ml_v1/btc_stacking_portfolio_2026_evaluation.json
12. configs/btc_ml_v1/btc_stacking_reproduction_reference.json

絶対条件:

- mainだけを使用してください。
- GOLD／もちぽよ／M10W／M10W24Bのファイルは参照も変更もしないでください。
- docs/config/scriptsのmochipoyo_alert_research、gold_v3、gold_ml_v1配下を検索しないでください。
- GOLD側のcollector、loop、BAT、runtime、state、lock、journal、snapshot、processを一切触らないでください。
- cleanup commit 0c23fd107680f0f323e956b5f7bbbddc6639243eを含むmainを基準にしてください。

現在は5候補の再現と2026-07-02までの評価が完了済みです。
次はBTC_FF01 fresh-forward data availability read-only auditだけです。

最初に書込みなしで、許可されたBTC範囲に同等の監査が現存するか確認してください。
同等機能がない場合だけ、handoffとnext_actionに書かれた正確なBTC専用pathへ最小実装してください。

FF01では候補条件、threshold、TP/SL、exit、spread、pip、lot、採否、runtimeを変更しないでください。
reproduce_btc_stacking_portfolio.pyや--skip-input-hash-checkをfresh評価へ使用しないでください。
BTC10Rやデモruntimeのlotを混ぜないでください。

availability packageを作成した時点で停止し、fresh performance evaluatorや次Stageへ進まないでください。
憶測で実装範囲を広げず、不明点が実装判断へ影響する場合だけ質問してください。
```

---

## 24. 最終優先順位

1. `START_HERE_BTC_ML_V1_NEXT_CHAT.md`
2. 本handoff
3. `current_state_20260729.json`
4. `next_action_20260729.json`
5. `btc_gold_scope_firewall_20260729.json`
6. 2026-07-02の再現・評価正本
7. その他の古いBTC文書

GOLD文書は優先順位に含まれない。BTC研究で読まない。
