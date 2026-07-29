# START HERE — BTC候補研究 次チャット固定入口

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- current status: `BTC_REDESIGN_D0_COMPLETE_D1_M7C_EVIDENCE_PACKAGE_PENDING_READ_ONLY`
- updated: `2026-07-30T06:31:00+09:00`

## 1. branchを先に固定する

このファイルを含むすべての読取りは、必ず次のbranchを明示指定する。

`feature/btc-fresh-forward-research`

`main`、default branch、別branchの同名ファイルは使用しない。branchが取得できなければ停止し、推測やfallbackをしない。

## 2. 最新版handoff

現在の唯一の最新版handoff:

`docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_REDESIGN_D0_COMPLETE_D1_M7C_EVIDENCE_PACKAGE_PENDING_20260730.md`

上記以外の過去handoffは、固定入口から明示されない限り`AUDIT_HISTORY_ONLY`であり、再開根拠にしない。

## 3. 読む順番

次の順番で、最初から最後まで読む。

1. `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`
2. `docs/btc_ml_v1/NEXT_CHAT_HANDOFF_BTC_REDESIGN_D0_COMPLETE_D1_M7C_EVIDENCE_PACKAGE_PENDING_20260730.md`
3. `configs/btc_ml_v1/btc_candidate_research_current_state_20260730.json`
4. `configs/btc_ml_v1/btc_candidate_research_next_action_20260730.json`
5. `configs/btc_ml_v1/btc_candidate_research_handoff_policy_20260730.json`
6. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_REDESIGN_MOCHIPOYO_DERIVED_AND_INDEPENDENT_20260730.md`
7. `configs/btc_ml_v1/btc_candidate_research_redesign_contract_20260730.json`
8. `docs/btc_ml_v1/BTC_D1_M7C_COLLECTOR_SOURCE_INVENTORY_PRELIMINARY_20260730.md`
9. `docs/btc_ml_v1/BTC_CANDIDATE_RESEARCH_HANDOFF_MAINTENANCE_POLICY_20260730.md`

この順番を終える前にrepo全体検索、code search、古いhandoff探索をしない。

## 4. 読んではいけないもの

このBTC研究の入口として、次を読まない・使わない。

- `AGENTS.md` — 現在GOLD_ML_V1用であり、このBTC研究の権威ではない
- `START_HERE_GOLD_ML_V1_NEXT_CHAT.md`
- `docs/gold_v3/**`
- `docs/gold_ml_v1/**`
- `config/gold_v3/**`
- `config/gold_ml_v1/**`
- `scripts/gold_v3/**`
- `scripts/gold_ml_v1/**`
- GOLD V2、旧GOLD、GOLD V3、GOLD_ML_V1、DISC8、Stage41関連
- 旧BTC stacking handoff
- 旧BTC YouTube候補handoff
- FF05 recovery V3〜V11の再開資料
- この固定入口から参照されていない旧current state、旧next action、旧handoff

MOCHIPOYO branchも一般探索しない。M7C/collectorはBTCUSDを含む一次証拠だが、最新版handoffが正確に許可した契約文書またはユーザー提出物だけを読み取り専用で扱う。

## 5. 現在の目的

- Track A: M7C/collectorの実source alertを一次証拠にする、もちぽよ由来BTC候補研究
- Track B: もちぽよと異なる相場原理から作る独立ベクトルBTC候補研究

完全複製や単発バックテストの見栄えではなく、将来の収益性、安定性、損失制御、候補間補完性、shadow parity、監視・停止まで含むシステムを作る。

## 6. 現在の次作業

次はD1だけ:

`D1_M7C_COLLECTOR_SOURCE_INVENTORY_READ_ONLY`

ユーザーから、既存M7C 7ファイルを一つにまとめたZIPを受け取り、schema、timestamp、event provenance、clock domain、event class、outcome exposureを監査する。

候補式、WR/PF/DD/MFE/MAE性能評価、新BAT、FF06、shadowには進まない。

## 7. 実行中システムの保護

M7C、collector、M8C、M9、M10系列を停止・再起動・初期化・変更しない。GOLD/MOCHIPOYO側へBTC研究結果を書き込まない。

## 8. fail-closed

branch、最新版handoff、current state、next actionのいずれかが矛盾する場合は作業を停止する。似たファイル、古いhandoff、記憶、default branchで補わない。
