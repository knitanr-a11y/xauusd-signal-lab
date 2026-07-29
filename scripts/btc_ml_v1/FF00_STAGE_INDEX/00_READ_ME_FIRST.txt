BTC fresh-forward stage index
=============================

User-facing folders are sorted by FF number.

FF01_data_availability
  Check whether the required fresh CSV timeframes exist and are usable.

FF02_performance_evaluation
  Evaluate the frozen five candidates after the fresh cutoff.

FF03_btc7r_causality_audit
  Audit BTC7R prefix causality and historical selection provenance.

FF04_bar_time_audit
  Confirm that CSV time is BAR OPEN time and verify causal M5/M15/H1 timing.

FF05_candidate_rebuild_search
  Evaluate all 108 preregistered causal rebuild cells with familywise correction.
  Current submitted run is not final because OOS01/OOS02 lacked raw M5/M15 coverage.

RECOVERY_FF05_historical_coverage
  Exact frozen historical package and required CSV hashes were recovered successfully.

RECOVERY_FF05_time_domain
  Prove whether recovered history is UTC and current terminal history is broker-server UTC+2/+3 DST before any FF05 rerun.

Use only the numbered FF folders for normal manual execution.
The older unnumbered folders are retained as internal compatibility paths.

Recovery and incident material begins with RECOVERY_, INCIDENT_, or FORENSIC_
so that it cannot be buried among normal stage numbers.

Do not rerun FF05 until RECOVERY_FF05_time_domain has been reviewed.
Do not run a later FF stage unless ChatGPT explicitly instructs you to do so after reviewing the previous ZIP.
