# MANIFEST

## 00_prompt
- PROMPT_claim_reconstruction.md

## 01_adjudication_html (secondary)
- GateAB_covhead_report.html                 # 2026-06-12 Gate A/B + cov-head writeup
- suppl_tests_report_20260613.html           # 2026-06-13 complexity / rho / self-supp writeup
- Adjudication_Report_20260610.html          # 2026-06-10 earlier “why learn” adjudication

## 02_theory_architecture_html (hypothesis)
- Paper_Architecture.html
- Theory_Detection_and_Turbo.html
- Conclusions and Open Questions.html
- ana_Paper_Architecture.html
- ana_Theory_Detection_and_Turbo.html

## 03_raw_results (primary)
- gateA/                                     # early gate runs
- gateA_s15firm/                             # SNR15 firm
- gateA_s20firm/                             # SNR20 firm (often low-power / heavy-tail)
- gateA_artifacts/                           # bootstrap JSONs, covhead comparisons
- mech/                                      # rho sweep + integer-Doppler control
- selfsupp/                                  # SNR20 pooled self-suppression shards
- f2p_firm/s07|s08|s09/results.json          # 3-seed F2-P firm
- complexity/                                # runtime / Cholesky vs receiver tables

## 04_analysis_scripts (definitional)
- decision_gateA.py
- decision_gateA_bootstrap.py
- decision_mech_analyze.py
- decision_complexity_bench.py
- decision_covhead_harvest.py
- decision_covhead_train.py
- decision_harvest.py
- decision_bound.py
- decision_metrics.py
- decision_ber.py
- decision_firmup.py
- decision_review.py
- decision_c1_sweep.py
- paired_learned_eval.py
- classical_joint_unrolled.py

## 05_old_narrative_for_contrast
- NARRATIVE_REPORT.md
- PROOF_SKELETON.md
- PROOF_AUDIT.md
- main.tex
- TCOM_PLAN.md
- findings.md
- progress.md
- task_plan.md
- PAPER_PLAN.md

## 06_qa_and_logs
- _QA_Index.md
- _Log.meta.json (if present)
- REPRODUCTION.md
- outputs_3seed_POOL_SUMMARY.md

## 07_direction_context_optional
- report2_divergent_directions.html
- report3v2_PhD_blueprint_updated.html

## Auto file listing
```
00_prompt/PROMPT_claim_reconstruction.md
00_prompt/STARTER_MESSAGE.txt
01_adjudication_html/Adjudication_Report_20260610.html
01_adjudication_html/GateAB_covhead_report.html
01_adjudication_html/suppl_tests_report_20260613.html
02_theory_architecture_html/Conclusions and Open Questions.html
02_theory_architecture_html/Paper_Architecture.html
02_theory_architecture_html/Theory_Detection_and_Turbo.html
02_theory_architecture_html/ana_Paper_Architecture.html
02_theory_architecture_html/ana_Theory_Detection_and_Turbo.html
03_raw_results/DATA_DICTIONARY.md
03_raw_results/complexity/runtime_table.csv
03_raw_results/complexity/runtime_table.json
03_raw_results/complexity/runtime_table.md
03_raw_results/f2p_firm/s07/results.json
03_raw_results/f2p_firm/s08/results.json
03_raw_results/f2p_firm/s09/results.json
03_raw_results/gateA/achievable/perframe_snr15.npz
03_raw_results/gateA/achievable/perframe_snr20.npz
03_raw_results/gateA/covhead/perframe_snr15.npz
03_raw_results/gateA/covhead/perframe_snr20.npz
03_raw_results/gateA/gateA_bootstrap_snr15.json
03_raw_results/gateA/gateA_bootstrap_snr20.json
03_raw_results/gateA/genie/perframe_snr15.npz
03_raw_results/gateA/genie/perframe_snr20.npz
03_raw_results/gateA/geom/perframe_snr15.npz
03_raw_results/gateA/geom/perframe_snr20.npz
03_raw_results/gateA/head/perframe_snr15.npz
03_raw_results/gateA/head/perframe_snr20.npz
03_raw_results/gateA/white/perframe_snr15.npz
03_raw_results/gateA/white/perframe_snr20.npz
03_raw_results/gateA_artifacts/gateA_bootstrap_snr15.json
03_raw_results/gateA_artifacts/gateA_bootstrap_snr15_200f_covhead.json
03_raw_results/gateA_artifacts/gateA_bootstrap_snr15_200f_fullladder.json
03_raw_results/gateA_artifacts/gateA_bootstrap_snr15_800f_covhead.json
03_raw_results/gateA_artifacts/gateA_bootstrap_snr15_800f_covhead_v2.json
03_raw_results/gateA_artifacts/gateA_bootstrap_snr20.json
03_raw_results/gateA_artifacts/gateA_bootstrap_snr20_200f_covhead.json
03_raw_results/gateA_artifacts/gateA_bootstrap_snr20_200f_fullladder.json
03_raw_results/gateA_s15firm/achievable/perframe_snr15.npz
03_raw_results/gateA_s15firm/covhead/perframe_snr15.npz
03_raw_results/gateA_s15firm/gateA_bootstrap_snr15.json
03_raw_results/gateA_s15firm/geom/perframe_snr15.npz
03_raw_results/gateA_s15firm/head/perframe_snr15.npz
03_raw_results/gateA_s20firm/achievable/perframe_snr20.npz
03_raw_results/gateA_s20firm/gateA_bootstrap_snr20.json
03_raw_results/gateA_s20firm/genie/perframe_snr20.npz
03_raw_results/gateA_s20firm/geom/perframe_snr20.npz
03_raw_results/gateA_s20firm/head/perframe_snr20.npz
03_raw_results/mech/intdopp_achievable.log
03_raw_results/mech/intdopp_achievable/perframe_snr15.npz
03_raw_results/mech/intdopp_geom.log
03_raw_results/mech/intdopp_geom/perframe_snr15.npz
03_raw_results/mech/mech_rho_snr15.json
03_raw_results/mech/rho0.25_achievable.log
03_raw_results/mech/rho0.25_achievable/perframe_snr15.npz
03_raw_results/mech/rho0.25_geom.log
03_raw_results/mech/rho0.25_geom/perframe_snr15.npz
03_raw_results/mech/rho0.375_achievable.log
03_raw_results/mech/rho0.375_achievable/perframe_snr15.npz
03_raw_results/mech/rho0.375_geom.log
03_raw_results/mech/rho0.375_geom/perframe_snr15.npz
03_raw_results/mech/rho0.625_achievable.log
03_raw_results/mech/rho0.625_achievable/perframe_snr15.npz
03_raw_results/mech/rho0.625_geom.log
03_raw_results/mech/rho0.625_geom/perframe_snr15.npz
03_raw_results/mech/rho0.75_achievable.log
03_raw_results/mech/rho0.75_achievable/perframe_snr15.npz
03_raw_results/mech/rho0.75_geom.log
03_raw_results/mech/rho0.75_geom/perframe_snr15.npz
03_raw_results/selfsupp/selfsupp_snr20_pooled.json
03_raw_results/selfsupp/shard20260602/achievable.log
03_raw_results/selfsupp/shard20260602/achievable/perframe_snr20.npz
03_raw_results/selfsupp/shard20260602/genie.log
03_raw_results/selfsupp/shard20260602/genie/perframe_snr20.npz
03_raw_results/selfsupp/shard20260603/achievable.log
03_raw_results/selfsupp/shard20260603/achievable/perframe_snr20.npz
03_raw_results/selfsupp/shard20260603/genie.log
03_raw_results/selfsupp/shard20260603/genie/perframe_snr20.npz
03_raw_results/selfsupp/shard20260604/achievable.log
03_raw_results/selfsupp/shard20260604/achievable/perframe_snr20.npz
03_raw_results/selfsupp/shard20260604/genie.log
03_raw_results/selfsupp/shard20260604/genie/perframe_snr20.npz
03_raw_results/selfsupp/shard20260605/achievable.log
03_raw_results/selfsupp/shard20260605/achievable/perframe_snr20.npz
03_raw_results/selfsupp/shard20260605/genie.log
03_raw_results/selfsupp/shard20260605/genie/perframe_snr20.npz
03_raw_results/selfsupp/shard20260606/achievable.log
03_raw_results/selfsupp/shard20260606/achievable/perframe_snr20.npz
03_raw_results/selfsupp/shard20260606/genie.log
03_raw_results/selfsupp/shard20260606/genie/perframe_snr20.npz
03_raw_results/selfsupp/shard20260607/achievable.log
03_raw_results/selfsupp/shard20260607/achievable/perframe_snr20.npz
03_raw_results/selfsupp/shard20260607/genie.log
03_raw_results/selfsupp/shard20260607/genie/perframe_snr20.npz
03_raw_results/selfsupp/shard20260608/achievable.log
03_raw_results/selfsupp/shard20260608/achievable/perframe_snr20.npz
03_raw_results/selfsupp/shard20260608/genie.log
03_raw_results/selfsupp/shard20260608/genie/perframe_snr20.npz
04_analysis_scripts/classical_joint_unrolled.py
04_analysis_scripts/decision_ber.py
04_analysis_scripts/decision_bound.py
04_analysis_scripts/decision_c1_sweep.py
04_analysis_scripts/decision_complexity_bench.py
04_analysis_scripts/decision_covhead_harvest.py
04_analysis_scripts/decision_covhead_train.py
04_analysis_scripts/decision_firmup.py
04_analysis_scripts/decision_gateA.py
04_analysis_scripts/decision_gateA_bootstrap.py
04_analysis_scripts/decision_harvest.py
04_analysis_scripts/decision_mech_analyze.py
04_analysis_scripts/decision_metrics.py
04_analysis_scripts/decision_review.py
04_analysis_scripts/paired_learned_eval.py
05_old_narrative_for_contrast/NARRATIVE_REPORT.md
05_old_narrative_for_contrast/PAPER_PLAN.md
05_old_narrative_for_contrast/PROOF_AUDIT.md
05_old_narrative_for_contrast/PROOF_SKELETON.md
05_old_narrative_for_contrast/TCOM_PLAN.md
05_old_narrative_for_contrast/findings.md
05_old_narrative_for_contrast/main.tex
05_old_narrative_for_contrast/progress.md
05_old_narrative_for_contrast/task_plan.md
06_qa_and_logs/REPRODUCTION.md
06_qa_and_logs/_Log.meta.json
06_qa_and_logs/_QA_Index.md
06_qa_and_logs/outputs_3seed_POOL_SUMMARY.md
07_direction_context_optional/report2_divergent_directions.html
07_direction_context_optional/report3v2_PhD_blueprint_updated.html
MANIFEST.md
README.md
```
