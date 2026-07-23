M9H_RESIDUAL_STATE_BRANCH_AUDIT

Purpose:
- P2 is rejected as a forward candidate.
- Compare a very small set of natural residual-state avoid observations on the same 852 Tier-B first-turn sample.
- Preserve frequency and report PF, DD, losing streak, monthly counts, and ticker/direction results.

Run:
1. Keep M8C / M7C / collector running.
2. Run 01_run_residual_state_branch_audit.bat ONCE.
3. Success marker: [M9H PASS]
4. Run 02_open_latest_results.bat.
5. Submit 99_UPLOAD_PACKAGE.zip from the opened M9H LATEST folder.

Important:
- One-time audit only.
- Do not run Python directly.
- H1-H3 are exploratory same-sample policies, not validated live gates.
- Do not reset any prospective start.
- M7C formula/threshold remain unchanged.
