# Minimal staged development — prospective plan v1 (2026-09-21)

Authority: latest user request supersedes the old exhaustive development and full-array retention requirements for this new campaign only. Never run 59 × 5 × 32, confirmation, or new receiver modules. Existing screen and sources remain immutable engineering evidence. This is adaptive exploratory triage, not a powered/significance-controlled study or a confirmation lock. No hypothesis tests or population equivalence claims are used for stopping.

## Questions and constants

Determine whether physical refinement gives a useful complete-cost/error tradeoff against fair native competitors; whether mean/scalar/full Gamma can be simplified; and which of two SNR regimes distinguishes methods. Frozen N=1024, LDPC(2048,1024), rho=0.5, eight physical paths, all existing numerical receiver settings. Do not introduce pilot-fraction variation into this minimal campaign. This bounds conclusions to rho=0.5.

Use the reviewed receiver from commit `31d5ec0d`; call its existing `run`/`run_native` directly. No shared-front computational discount: each method pays its complete initializer/front/refinement/detection/LDPC/conversion/failure cost. Offline scoring and disk storage are separate. No truth enters receiver choices.

## Stage 1: paired fresh triage

Two existing cells: cell 1 / 6 dB and cell 3 / 8 dB. Ten independent frames per cell, all selected configurations on each observation. Do not pool repeated arm calls as independent observations. Different cells use distinct physical-channel seeds, as in the original generator.

Candidate configuration IDs (unmodified catalog entries):

- I1 reference: `I1_BP12_r0`; strongest simple I1: `I1_BP8_r1`.
- Existing actual-H/new-terminal `C_M24_I8` results remain engineering controls. Do not spend fresh calls on this control at this stage: the question is Gamma/refinement versus independently initialized external families. No E-JSG reproduction claim or new E-JSG module.
- Matched Gamma comparison: `ABL_mean`, `ABL_scalar`, `P_M24_I20` (all M24/I20). Cheap full-Gamma variant: `P_M16_I8`.
- Native structured EP: `N_ep_2_r2`, `N_ep_8_r2`.
- Native coded GAMP: `N_gamp_g1_i30_r2`, `N_gamp_g4_i40_r3`.
- Exact shared-start SBL control: `S_SBL1`.
- Coded PBiGaBP: `N_bilinear_8_r1` and `N_bilinear_8_r2` (cheap and strong round budgets).

13 arms × 2 cells × 10 frames = 260 receiver calls. The old single observation chooses engineering budgets only; none of its errors are pooled into new estimates. Do not add/drop arms until this stage's complete paired blocks are available, except integrity/resource failure.

Seed contract remains original SeedSequence([20260920,480017,1,cell,absolute_frame,component]). Stage 1 absolute frames 100000–100009. Stage 2 absolute frames 200000–200031. These are disjoint from original/smoke frames and each other. Save actual component entropy/channel seed and reject repeated channel seeds within the campaign. Deterministically rotate arm order across frame/cell; no cost-timed parallel processes. Warm selected arms before each stage; warmup stays phase 0 and is separately charged in process wall time.

## Frozen selection, dominance and stopping

Analyze only at completion of Stage 1 and Stage 2; no efficacy peeking within a stage. Numerical failures remain errors with actual costs; missing bits are not fabricated BER observations. Use worst-case missing-bit count only in ranking and label it explicitly.

For each cell fix the Stage-1 deadline to 1.5 × median complete I1_BP12_r0 time, including failed attempts. Report unrestricted errors and secondary 1/1.25/2 × reference deadlines too. Stage 2 retains these Stage-1 deadlines rather than optimizing its deadline after seeing new outcomes.

Ranking tuple, pooled with equal observations per cell: deadline frame-error count, unrestricted frame-error count, information-bit errors (explicit worst-case ranking for missing bits), median complete time, configuration ID. Select the best proposed candidate from the four registered refinement variants. When error counts are exactly tied and median time differs by at most 5%, prefer mean-only, then scalar, then full Gamma; within full Gamma prefer smaller graph/iteration allocation. Select the better of the two I1 configurations using the same ranking and retain that single I1 as the Stage-2 anchor. I1_BP12_r0 remains the Stage-1 timing-reference authority only.

Observed clear dominance: B has no more deadline errors, unrestricted frame errors, or information-bit errors than A in either cell, costs at most 80% of A's median complete time in both cells, and has at least two net paired deadline-frame rescues over A across the stage. Drop A from expansion (selected I1 anchor excepted). Also drop cost-only duplicates when both paired deadline and unrestricted frame-error vectors are identical, B's bit count is no worse in either cell, and B costs at most 75% in both cells. These are resource-allocation heuristics on observed data, not population dominance proofs. Preserve every eliminated arm and reason in the report.

Stop the proposed direction after Stage 1 if the selected I1 anchor or an external family representative satisfies either dominance rule against the selected best proposed variant. Also stop with an **uninformative-regime** outcome if no cell has either (a) a selected-proposed/best-ranked-external paired deadline disagreement or (b) that same best-ranked external competitor with 1–9 unrestricted frame errors out of 10. All-zero/all-one comparisons without disagreements do not license favorable claims or an ad hoc SNR search.

For an unresolved/non-dominated proposed candidate, collapse EP, GAMP and PBiGaBP to their best configuration. Rank the external family representatives (structured EP, coded GAMP, exact SBL, PBiGaBP) using the same tuple after dominance exclusion. Retain the two strongest non-dominated families; retain a third only if it contributes at least one paired deadline rescue not achieved by either of the first two on Stage 1. If fewer than two remain, keep only the genuinely surviving families and disclose this narrower-than-requested set rather than reintroducing an explicitly dominated arm. No other configuration tuning.

Select at most two informative cells by descending paired deadline disagreement between the best proposed variant and the best-ranked external competitor, then proximity of that competitor's unrestricted FER to 0.3, then cell ID. A cell must satisfy the informative rule above. If only one qualifies, expand only one.

## Stage 2: independent survivor expansion

Only the selected I1 anchor + selected proposed variant + 2–3 external competitors (or fewer if explicit dominance leaves fewer), on the selected 1–2 cells. Exactly 32 new independent frames per cell; no automatic extension to 64 in this minimal campaign. Stage-1 counts remain separate from Stage-2 evaluation of selected methods. Maximum 320 calls (5 × 2 × 32), maximum campaign 580 calls vs 9440 previously.

At completion, stop. A provisional further-development signal requires at least four net paired deadline rescues (>=12.5 percentage points) over the strongest external competitor in one cell, at most two net harms in the other, and complete median cost no more than 1.2× that competitor; alternatively, at least 20% lower cost with no more than one extra deadline error per cell. Here strongest external means the surviving external configuration ranked best on Stage-2 observations by the same frozen ranking tuple; this reporting comparison does not change experimental allocation. Require also no more than two additional deadline errors per cell versus the selected I1 anchor. Report counts/uncertainty and whether this heuristic is met; do not label it significant/equivalent or confirmation-ready. Otherwise recommend stop/defer, with explicit ambiguity where n is inadequate. No module rescue or post-result retuning.

## Compact evidence and audits

Always retain per-frame input hash/seed, small truth physical path parameters, packed truth information/code bits and decoded/checkpoint bits with original lengths; configurations, receiver/campaign source hashes, environment, exact commands, error counts/FER/BER, full-channel NMSE, stage/round/complete timings, failure/fallback events, decoder counts/syndromes, selected-support counts, and small final fitted path parameters where available. Record per-call process RSS/high-water snapshots honestly as shared-process memory, not isolated peaks. Link exact-configuration existing isolated-memory probes; run additional survivor-only isolated probes if required, not the entire catalog.

Heavy input/messages/moments/full matrices are saved only on absolute frame 100000 (Stage 1) and 200000 (Stage 2), in each participating cell, for all participating arms, plus every numerical exception/fallback or integrity exception. Ordinary radio frame errors are NOT exceptional-storage triggers. Audit subset fixed before observations. Store actual I1 H only there; its other NMSE values are producer-side offline scores with matrix hashes, explicitly not fully reconstructible from compact storage. Physical-parameter NMSE remains independently reconstructible where parameters are retained. Recount all saved packed bits; fully audit only the heavy subset. Do not fake compatibility with the old full-array validator.

Heavy/storage hard cap 512 MiB; if approaching it, persist the triggering exception then stop with a resource-limit status. Never silently suppress exceptional evidence or delete old raw data. Target routine output below 100 MiB. Report actual bytes and separate receiver vs generation/scoring/storage wall time.

## Execution / delivery

All remote writes/code/logs/tmp/cache under `/data/guoyikun/`; SSH alias deinlab, existing AFDM Python, CPU-only, OMP/BLAS/Torch 1. Single timed numerical process, persistent g_ tmux, PID/deadline/exit logs, no installs. Stage 1 timeout 40 minutes; Stage 2 timeout 60 minutes. Stop on evidence integrity/qualification failure. User already authorized this bounded campaign; do not add a new approval loop.

Before scientific execution: focused compact-schema/recount/selection-rule tests plus one real audit-frame validation (its observation stays part of Stage 1, not a duplicate sample). Freeze new runner/plan hashes. Old package tests need not be repeated. One independent check of the changed orchestration/selection boundary; no broad review.

Update RESULTS.md with six requested answers, survivor/elimination reasons, stage-separated counts, informative regime, Gamma simplification limits, mandatory future rivals and actual/extrapolated next-stage costs. No `confirmation_lock.json`, no call to old seal/confirmation entry points, no accepted scientific STATE promotion.
