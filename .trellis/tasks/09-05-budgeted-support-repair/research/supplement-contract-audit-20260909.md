# Supplement receiver contract audit — 2026-09-09

Source identity and actual generator checks confirm g=L(eta)h for normalized physical gains. The raw gains include gain-dependent Frobenius normalization; that map is not unconditionally linear. Independent-atom OMP/DA-LS does not impose the path relation. Optional physical refit must be distinguished from the baseline.

The transmitted pilot already includes sqrt(rho). Cancellation is y-H@pilot. Sigma is variance, updated with the residual after outer work and consumed by the next outer/terminal stage. Default terminal cancellation and data detection use the same final H; covariance transforms and factorial diagnostic H interventions have separate explicit consumers. LDPC is terminal-only; no coded extrinsic information currently enters the original outer loop.

Actual source entry points: afdm_env.py:505/618; budgeted_support_eval.py:114; classical_joint_unrolled.py:2196; direction_receiver.py:33/127; direction_factorial.py:69; direction_cancel.py:31. Full source hashes and detailed findings: `.mission/20260909_09-01-15-afdm-comprehensive-supplement/evidence/audit-01.json`.

Fresh remote evidence: `afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/physical-map.json`, `pilot-geometry.json`, `preflight-status.json`, `unit.log`. Seven real generator cases passed at the existing 1e-10 tolerance; 28 unit tests passed. This is source/algebra evidence, not new FER evidence. CPP, stronger detectors, coding feedback and new data admission are separate pending contracts.

Read-only source map by gpt-5.6-luna low; main-session review matched actual source content and fresh bounded tests. No paper claim or parent scientific acceptance changed.
