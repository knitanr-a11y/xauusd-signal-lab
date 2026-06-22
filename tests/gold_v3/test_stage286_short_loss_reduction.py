from pathlib import Path
import json
import pandas as pd
ROOT=(Path(__file__).resolve().parents[2]/"docs"/"gold_v3")
if not ROOT.exists(): ROOT=Path("/mnt/data")
def test_losses_reduced_in_all_years():
 d=pd.read_csv(ROOT/"gold_v3_stage286_short_loss_reduction_yearly.csv")
 raw=d[d.variant=="RAW"].set_index("year"); strict=d[d.variant=="STRICT_RISK_SCORE"].set_index("year")
 assert (strict.losses < raw.losses).all()
 assert (strict.sl_count < raw.sl_count).all()
def test_2024_selection_and_2025_confirmation():
 d=pd.read_csv(ROOT/"gold_v3_stage286_short_loss_reduction_yearly.csv")
 q=d[d.variant=="STRICT_RISK_SCORE"].set_index("year")
 assert q.loc[2024,"pf_cost100"]>1
 assert q.loc[2025,"pf_cost100"]>1
 assert q.loc[2025,"pf"]>2
def test_safe_portfolio_does_not_raise_dd():
 d=pd.read_csv(ROOT/"gold_v3_stage286_short_selected_portfolios.csv")
 e=d[d.portfolio=="EXISTING"].set_index("year"); s=d[d.portfolio=="PLUS_STRICT_SAFE"].set_index("year")
 assert (s.dd <= e.dd + 1e-9).all()
 assert (s["sum"] > e["sum"]).all()
def test_no_active_and_flags_off():
 c=json.loads((ROOT/"gold_v3_stage286_short_loss_reduction_final_contract.json").read_text())
 assert c["active_addition"]=="NONE"
 assert c["flags"]["audit_only"] is True
 assert all(v is False for k,v in c["flags"].items() if k!="audit_only")
