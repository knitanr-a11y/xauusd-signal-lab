# GOLD V3 Stage329 — Persistent Router Prospective Shadow Runtime（Audit-only）

## 1. 目的

Stage329は、Stage328で凍結済みの契約とbootstrap stateを変更せず、将来のclosed dataだけを対象に、固定routerを永続状態付きでprospective shadow運用するruntimeである。

このStageは発注機能ではない。Stage329の`live_ready`とfinal signal emissionはOFFであり、MT5自動発注、Discord通知、partial close、automatic promotionもすべてOFFのままとする。

## 2. 固定契約

- source candidate: `M5_H4|MOCHI_UNION|SHORT|RR1_5|ATR_GE_1_AND_NO_ROUND`
- lane: `BALANCED_OR_PREMIUM`
- router policy: `RELATIVE_TRAILING_MEAN_R_N2`
- cost view: `1p0x spread-adjusted R`
- decision cutoff: `decision_dt > 2026-06-23 13:55:00`
- time basis: MT5 server time
- latest CSV row: closedとして扱う
- parity tolerance: `1e-12`
- same-M1 TP/SL priority: SL
- maximum hold: 720 minutes
- source portfolio: one-position / no-preemption

Stage329は次の凍結ファイルを読み取り専用で検証する。

- `stage328_persistent_router_prospective_shadow_contract.json`
  - SHA256: `cfdfdd74050d33d68dcaa97dcb14b9c812f0cad00807870c922d0d13c6e050f9`
- `stage328_persistent_router_bootstrap_state.json`
  - SHA256: `90824803f7bb3992e73f8e0727760ffba6c31f68f77e771884a099a2cc26178e`
  - internal state SHA256: `6b165f518f67212ca217f41dc40b7e24228a5c9e3eabd2cf5a517869bb19dbaf`

SHA、status、policy、lane、cost view、cutoff、bootstrap内部stateが一致しない場合はfail closedする。Stage328ファイルへのwrite、delete、recreate、rename、moveは行わない。

## 3. 候補処理順序

処理順序は固定で、並べ替えない。

1. Stage311の凍結対象4 MOCHIPOYO trackからraw signalを生成する。
2. SHORT、ATR ratio 1.0以上、round-number除外、cutoffより後だけを残す。
3. 同一`decision_dt`をStage319と同じparity項目でcanonical dedupする。
4. immutable source identityと`decision_dt`だけからstable event IDを生成する。
5. Balanced / Premium membershipを判定する。
6. Premium membershipを優先してrouter subgroupを割り当てる。
7. Stage314のexact next-M5 entry、structural stop、0.75–2.0 ATR risk、RR1.5、M1 SL-first、spread adjustment、720分horizonを再利用する。
8. Stage314のsource one-position/no-preemption policyをrouterより先に適用する。
9. `ACCEPTED`だけをrouter observation streamへ入れる。
10. entry時点では、以前に解決済みで永続化済みのACCEPTED source candidateだけからrouter判定する。
11. selectedはselected shadow lane、filteredはsource-only shadow laneとして記録する。
12. selected/filteredを問わず、ACCEPTED candidateが解決した後だけsubgroup historyを更新する。

## 4. Membershipとsubgroup

Balanced:

`pooled_track_count >= 2 OR (1.10 <= atr_ratio_signal <= 1.45 AND 0.70 <= range_atr_signal <= 1.05)`

Premium:

`compression_ratio_signal >= 0.95`

subgroup precedence:

- Premium member: `PREMIUM_INVOLVED`
- PremiumではなくBalanced member: `BALANCED_WITHOUT_PREMIUM`
- どちらでもない行: `OUTSIDE_FIXED_LANE`

lane外の行をrouter observationへ変換しない。

## 5. Router判定

各subgroupは、解決済みspread-adjusted Rの直近2件だけを保持する。

- どちらかのsubgroupが2件未満: `WARMUP_TAKE_ALL`
- 両方2件以上: candidate subgroupの平均Rが他方以上ならselected
- 同値はcandidate subgroupをselected

Stage328 bootstrapでは両subgroupのwarmupは完了済みである。

## 6. State更新対象

更新するのは、canonicalかつsource portfolioで`ACCEPTED`となり、`RESOLVED`になったcandidateだけである。

更新する:

- router-selected ACCEPTED source candidate
- router-filtered ACCEPTED source candidate

更新しない:

- pending
- `REJECTED_OVERLAP`
- `RISK_REJECTED`
- invalid entry alignment / M1 gap / invalid hold window
- `NOT_TRADABLE_YET`
- `OUTSIDE_FIXED_LANE`

pending行の`spread_adjusted_pnl`と`spread_adjusted_r`は必ず空のままとする。

## 7. Mutable runtime state

初回だけ、凍結bootstrapの`initial_state`を別ファイルへコピーする。

- mutable file: `stage329_persistent_router_runtime_state.json`
- frozen contract/bootstrap lineage hashをwrapperに保存する
- 以後はbootstrapへ戻さず、runtime stateを継続使用する
- runtime fileが存在するのにlineage、schema、policy、lane、state hashが不一致ならfail closedする
- runtime fileが消失し、journalだけ残っている場合はbootstrapから再作成せずfail closedする

## 8. Append-only journalとcrash recovery

journal:

`stage329_persistent_router_state_journal.csv`

journalには、解決後にstateへ適用したACCEPTED source eventだけを保存する。

- event IDはstableかつduplicate禁止
- logical append-only
- file更新はtemporary fileへ完全write、flush、`fsync`後にatomic replace
- journalを先にcommitし、その後runtime stateをatomic replaceする
- journalがruntime stateより先に進んだ状態で停止した場合、次回はbootstrap initial stateとjournal全件を検証replayしてruntime stateを復旧する
- runtime stateがjournalより先に進んでいる場合はfail closedする
- 件数が同じでstate hashまたはjournal hashが一致しない場合もfail closedする
- journal replayでは、各eventのrouter decision、before-entry score/history count、適用後state count/timestamps/state SHAを再検証する

この順序により、途中停止後の二重state更新を防止する。

## 9. 出力

すべて `FX_OUTPUTS\gold_v3\289_training_history` 配下に出力する。

- `stage329_persistent_router_prospective_shadow_watch.json`
- `stage329_persistent_router_runtime_state.json`
- `stage329_persistent_router_state_journal.csv`
- `stage329_persistent_router_raw_signals.csv`
- `stage329_persistent_router_canonical_source_signals.csv`
- `stage329_persistent_router_source_pending.csv`
- `stage329_persistent_router_source_resolved.csv`
- `stage329_persistent_router_selected_signals.csv`
- `stage329_persistent_router_selected_pending.csv`
- `stage329_persistent_router_selected_resolved.csv`
- `stage329_persistent_router_rejected_overlap.csv`
- `stage329_persistent_router_health.csv`

`canonical_source_signals.csv`にはportfolio判定後のcanonical全行を残すため、ACCEPTEDだけでなくlane外、risk/invalid/not-tradable、overlap rejectionも監査できる。

## 10. 分離して報告する件数・成績

次を混ぜずに別々に報告する。

- raw pooled signals
- canonical deduplicated signals
- fixed lane canonical signals
- source portfolio ACCEPTED
- rejected overlap
- risk rejected
- invalid alignment/gap
- not tradable
- router selected
- router filtered
- source pending / resolved
- selected pending / resolved
- 今回のstate update数
- duplicate ignored数
- subgroup score/state
- resolved-only source成績
- resolved-only selected成績

raw、canonical、source accepted、router selected、pending、resolvedを単一成績として集計しない。

## 11. Future review gate

Stage328の固定gateをそのまま使う。

- resolved source candidates 20件以上
- resolved selected trades 10件以上
- selected WR 60%以上
- selected PF 1.25以上
- selected total R > 0
- selected DD 4R以下
- largest winner share 35%以下
- state integrity pass

passしてもhuman audit eligibilityを開くだけであり、自動昇格しない。

## 12. 初回ゼロ候補

cutoff後に候補がないことは正常である。

期待動作:

- mutable runtime stateをbootstrapから初回作成
- journalをheader-onlyで作成
- stateはbootstrapと同一
- raw/canonical/source/selected/pending/resolvedは0件
- frozen contract/bootstrap hashは有効
- decision: `WAIT_FOR_FIRST_POST_FREEZE_SOURCE_CANDIDATE`

ゼロ候補runから将来成績の有効性を主張しない。

## 13. 変更しない対象

- Stage280 exact recovery: `BLOCKED_UNCHANGED`
- Stage281 exact model: unchanged
- Stage292 candidate pool: unchanged
- Stage307 registered candidate: unchanged
- Stage314 contract: unchanged active
- Stage319 contract/cutoff: unchanged frozen
- Stage328 contract/bootstrap: unchanged frozen
- final signal logic: unchanged
- MT5 order: OFF
- Discord: OFF
- partial close: OFF
- automatic promotion: forbidden

## 14. 実装時監査

GitHub commit前に次を実施する。

- Python syntax compile
- import source audit
- prohibited source name/reference audit
- first mutable-state creation helper test
- journal先行/runtime未更新のcrash recovery helper test
- duplicate event idempotency helper test
- router-filtered ACCEPTED resolutionのstate更新helper test
- pending no-PnL/no-R/no-state-update helper test

実市場CSVを使ったruntime出力は、BAT実行後に生成物を別途監査する。生成物未確認の段階ではStage329のprospective runtime結果を完了扱いにしない。

## 15. 実行BAT

`scripts\gold_v3_runtime\bat\run_gold_v3_329_persistent_router_prospective_shadow_runtime_audit.bat`
