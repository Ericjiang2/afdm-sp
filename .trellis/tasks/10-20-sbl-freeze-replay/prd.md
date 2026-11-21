# SBL final-gain freeze replay

## Authorization
User approved the proposed two-control follow-up after the three-mode pilot. Obtain one useful bounded result; no expanded scenarios or tuning. Parent: 09-22-tf-production-gap-audit.

## Question
For scalar-Gamma outputs, does restarting fixed-gain detection with the gains from point step 20 recover decoding, and does simply continuing point to step 40 recover it?

## Acceptance
- Reuse exactly the prior 200 keys / 50 frame clusters (9100..9149, U/G, rho .3, SNR 7/8). Scalar Gamma only, since that is the harm to localize.
- Use saved support/h0/h20 from the three-mode raw rows. Reconstruct only the shared first-round check prior if required; do not rerun second-stage SBL.
- Add exactly two arms: point40 continuous from h0; point20-then-reset-fixed20 from saved h20 and the original round-1 check prior. No point20 decoder feedback enters the latter.
- Exact per-key check-prior hash and first-20-step point40 prefix parity against stored point20 gains/traces. A real gate must independently decode point20 and match its old decision.
- Score truth only outside the detector. Retain all errors/attempts and reject incomplete cohorts.
- Compare paired FER, transitions, final channel NMSE and raw extrinsic bit log loss; old fixed20 and point20 are baseline context. Bootstrap 50 frame clusters jointly across four cells, 10000 draws.
- CPU <=12 single-thread processes, all execution <=15 wall minutes / 3 core-hours. No automatic extension.
- Report reset+freeze as a combined intervention, not isolated freeze causality. Record actual runtime separately from logical 40 detector steps. Preserve frozen sources and raw data; no claim promotion or GitHub push.

## User-approved single-arm extension (2026-10-20)
Add RP, restart point20 from the exact same saved h20/prior as RF. The prospective addendum in protocol.md governs this extension. Preserve original scripts/raw/reports and run only the new arm plus representative engineering gates; compare against immutable run2 RF and P40. No other scope is added.

## User-approved saved-trajectory analysis (2026-10-20)
Analyze all six saved mode/Gamma trajectories without any new receiver or SBL execution. The trajectory analysis addendum in protocol.md fixes metric alignment, full-cohort paired statistics and interpretation boundaries. Deliver one plot and bounded readout; original results remain unchanged.

## User-approved representation probe (2026-10-21)
Derive and independently check uniform duplicate-atom physical/prior equivalence. If valid, run one synthetic algebra fixture and the predetermined saved real key, fixed/point only, under the latest protocol addendum. No SBL rerun or performance/generalization claim.

## User-approved soft-Gram block stage (2026-10-21)
Derive matched full/diagonal soft-Gram gain refits and perform minimal representation/dense-Gamma/native-replay gates only. The 200-key actual-support study remains a later decision. Latest protocol addendum and research/full-gram-gain-block.md define the objective, schedule and boundaries.

## User-approved actual-support cohort (2026-10-21)
Execute only the same200 keys and both saved upstream variants, new full/diag20 with matched old six native replays. Preserve all old sources/results. Qualify source/prior/old outcome parity, report all arms and paired frame-cluster FER/log-loss contrasts with compute cost; exploratory only. Protocol defines exact arms, stopping and budget. No automatic new frames/Gemini/claim promotion/archive.


## User-approved Gamma-only ablation (2026-10-21)
Add only full-BHB + diag-Gamma20 for both saved upstream variants on the same200keys. Compare with immutable gram_cohort1/full using primary paired logloss and secondary FER/NMSE/compute; all50sharedframes/all4cells retained. The latest protocol addendum fixes exact intervention, counts, gates, budget and decision boundaries. No SBL/newframes/claim promotion; return one useful bounded result.


## User-approved new-frame validation (2026-10-21)
Validate the frozen full-gain candidate on50fresh shared P1 frame IDs /200keys in the same4cells. Freshly fit both E3 upstreams; evaluate their two full candidates and the old best L-cov/native-joint control only. Primary paired logloss, secondary FER/quality/cost; latest protocol fixes reserved frame range, source/input/old-key gates, counts and bounded budget. No further scenario search, tuning, mechanism/novelty claim or automatic expansion.

## User-approved uniform-symbol-variance Gamma comparison (2026-10-21)
Add one terminal arm using Gamma(mean(v_pre)*ones), retaining full BHB and all frozen receiver settings on the original200 saved keys/both upstreams. Compare to saved full and Gamma-only diagonal scores. The user accepted the proposed90% benefit-retention criterion; the latest protocol fixes its joint-frame bootstrap, qualification and scope. No SBL/new frames/optimization claim or automatic follow-up.
