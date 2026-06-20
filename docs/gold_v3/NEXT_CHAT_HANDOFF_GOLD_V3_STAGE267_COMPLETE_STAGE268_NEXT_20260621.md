# GOLD V3 Stage267 handoff

正式状態: `GOLD_V3_267_RESEARCH_ARCHITECTURE_RESET_COMPLETE_AUDIT_ONLY`

## 完了

- observed M1 session calendar作成
- daily maintenance / weekend / holiday-like closure / rare gapを分離
- 全H1/H4確定足decision universe作成
- closure中decisionを次のtradable M1へ繰越
- 4/8/12/24/48/72/120取引時間forward path作成
- C1/F12をREFERENCE_ONLY_NOT_VALIDATEDへ格下げ
- 旧8時間lossのlater-positive率を診断

## 主要確認

- H1 source-covered 8479件、activation 100%
- H4 source-covered 2216件、activation 100%
- H1 closure後activation 369件
- H4 closure後activation 341件
- 旧H4対象時刻00/04/08は全H4の49.86%
- 00時がmaintenanceでほぼ失効し、実効対象は04/08の33.30%
- 旧C1 8h-lossの48h後プラス率64.71%、72h後73.53%
- 旧F12短期lossの48h後プラス率78.95%
- regression 4/4 PASS

## 次

Stage268: path ledgerを用いて、時間帯・volatility・trend/range・horizon別のforward distributionを診断する。まだentry/exitルールは作らない。

禁止:
- 旧C1/F12をcomponentとして扱う
- 固定8時間labelでloss gateを学習
- session休止をdata gapとして失効
- 一部H4時刻だけを先に除外
- Stage268前に新entry候補を作る

運用: `NO_LIVE_PROMOTION_AUDIT_ONLY`
