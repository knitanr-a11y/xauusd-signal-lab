# M7C Runtime Bootstrap and Log Folder Correction

作成日: 2026-07-20 JST  
repo: `knitanr-a11y/xauusd-signal-lab`  
branch: `feature/mochipoyo-alert-research`

## 1. 発生した問題

最初のM7C manifestは、M7B結果作成時刻をそのままprospective startに固定した。

```text
old prospective_start_utc = 2026-07-19T18:50:47Z
```

しかしCloudflare collectorはその後の未取得イベントを保持しており、2026-07-20T02:32Zの再開時にraw alert ID 43〜54をまとめて取得した。

そのうちBTCUSD ID 43〜50はold prospective start以前のbar timeを持っていた。このため、old bootstrap IDsと実際のpre-start IDsが一致しなくなり、M7Cは正しくfail closedした。

```text
old expected BTC IDs: ... 41, 42
actual pre-start BTC IDs: ... 41, 42, 43, 44, 45, 46, 47, 48, 49, 50
```

M3外部キー問題の修正後も、このbootstrap mismatchによりM7C loopは141 cycleすべてexit=2となり、successful cycleは0だった。

## 2. 判定

旧開始点を使ったM7C出力は正式な前向き再現結果として使用しない。

```text
latest_m7c_prospective_shadow.json built_at 2026-07-20T02:23:04Z
proxy decisions 46
proxy signals 3
```

上記はcollector backlogを回収する前の出力であり、M7C正式forward sampleには含めない。

凍結したtrigger式の失敗ではない。開始点をcollector catch-up前に固定したruntime設計ミスである。

## 3. 修正後の開始契約

GitHubの次のmanifestは式・gate・安全条件のtemplateとして維持する。

```text
config/mochipoyo_alert_research/m7c_prospective_shadow_manifest_v1.json
```

実際のprospective startとbootstrap IDs/stateは、ユーザーPC上でcollector catch-up後に一度だけ作るlocal runtime manifestへ固定する。

```text
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\m7c_runtime\
m7c_prospective_shadow_manifest_runtime.json
```

初期化条件:

1. M7C loopが停止している
2. collectorは稼働中
3. 最新3回のCloudflare collection runが連続`PASS_EMPTY`
4. collector cursorがSQLiteの最新raw alert IDと一致
5. M3 episode_eventsがeligible raw alertsと一致
6. M4 M15 alignmentがeligible raw alertsと一致
7. 初期化中に新しいraw alertが増えた場合はmanifestを作らずfail closed

初期化BAT:

```text
scripts\mochipoyo_alert_research\
run_initialize_m7c_prospective_shadow_runtime_once.bat
```

runtime manifestが既に存在する場合、再初期化は拒否する。forward結果を見た後に開始点をリセットしない。

## 4. fail-closed loop修正

M7C contract errorのexit code 2は、今後loopを停止する。

```text
FAIL_CLOSED_CONTRACT_BLOCK
```

同じ無効cycleを5分ごとに無期限反復しない。

一時的な実行errorと、開始契約・bootstrap・DSTなどのcontract blockを区別する。

## 5. ログフォルダ契約

次回起動から用途別に分ける。

### collector

```text
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\logs\collector
```

主なファイル:

```text
collector_forever.log
latest_loop_status.json
latest_collection_result.json
latest_collection_error.json
```

### M7C

```text
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\logs\m7c
```

主なファイル:

```text
m7c_shadow_forever.log
latest_m7c_shadow_loop_status.json
latest_m7c_prospective_shadow.json
latest_m7c_proxy_decisions.csv
latest_m7c_proxy_signals.csv
latest_m7c_source_event_comparisons.csv
latest_m7c_extra_proxy_signals.csv
m7c_runtime_start_receipt.json
```

### derived audit

```text
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\logs\derived
```

主なファイル:

```text
latest_episode_build_result.json
latest_mt5_closed_bar_alignment_result.json
```

一括で開くBAT:

```text
scripts\mochipoyo_alert_research\open_mochipoyo_monitor_folders.bat
```

## 6. 再開順序

1. old M7C loopを停止
2. collectorは稼働維持
3. feature branchをPull
4. collector BATを新コードで再起動し、collector logを専用folderへ移行
5. 最新3回のcollector cycleが`PASS_EMPTY`になるまで待つ
6. `run_initialize_m7c_prospective_shadow_runtime_once.bat`
7. `run_build_m7c_prospective_shadow_once.bat`
8. one-shotが`COLLECTING`なら`run_m7c_prospective_shadow_forever.bat`

## 7. 変更していないもの

- M7Bで凍結したPRIMARY LONG式
- M7Bで凍結したPRIMARY SHORT式
- LONG EXIT閾値
- SHORT EXIT閾値
- 120分grace
- exact / ±1 bar照合
- review gate件数
- REENTRY未採点
- audit-only
- Discord OFF
- MT5 order OFF
- entry gate OFF
- live-ready OFF
- final signal OFF
