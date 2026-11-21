# Brief for Codex: paper-direction review after light experiments (2026-10-13)

Mode: caveman (skill `~/.codex/skills/caveman/SKILL.md`) for all working notes/messages. Final page (round 2 only): answer-me-with-html, Simplified Chinese, technical terms English.
Role: independent reviewer + optimizer. Claude (main session) proposed direction. You judge independently. Do not trust Claude claims; open sources, check numbers + derivations.

## 1. Goal (fixed, from user + project)
- Target: IEEE Transactions (TCOM regular). Project paper genre (STATE): theory + mechanism + systems; title bans "learned"/"neural"; learning = tested-and-null result.
- Trans objective (`.trellis/tasks/09-13-trans-next/prd.md`, deliverable 5): >= 1 evidence-backed substantive contribution: (a) reusable mechanism + targeted method, (b) non-trivial equal-reliability compute gain, (c) theory/design criterion with predictive power. Engineering validation / plain classical combination not enough.
- User framing (2026-10-10): use "Transformer-based" CE/receiver papers as novelty benchmark. Not need fully novel; relatively new + highly practical OK. Rank innovation: L1 new problem (highest) > L2 new model on old problem (Transformer papers here) > L3 new method on old model. Want first principles, math, CCF-Idea-Reviewer / CCF-Idea-Optimizer method, divergent thinking.
- User rule on prior art (memory): overlap = calibrate exact distinction (setting, mechanism, result type, regime), not veto. No pessimism / optimism bias.

## 2. System (C1 line, all recent evidence)
SP-AFDM, superimposed pilot fraction rho (transmit power 1, sigma2 = 10^(-SNR/10)), N 1024, QPSK, LDPC (3,6) n 2048. Channel: L distinct delays in {0..100}, 1+Poisson(3) rays/tap, Jakes Doppler |nu| <= 2 bins, tap power 1/L. Receiver SPg_flat: genie delays, DPSS-BEM 8 coef/tap -> K = 8L unknowns, flat prior tau = 1/K; schedule [refit -> scalar_joint (T inner joint est-det updates, AMP-like, scalar white variances) -> LDPC50] x R rounds. Representation load K = central variable. Cliff Kc = K at FER .5.

## 3. Claude direction, v1 (before experiments, 2026-10-10)
Benchmark anatomy: Transformer template = LS/threshold estimate -> attention refiner -> NMSE/BER gain. = L2 "transfer"; weak mechanism; needs training.
Proposed centre D2 + D3 (+ D1 as analysis layer):
- D1 (L1-lite): supportable channel load Kc(N, rho, SNR, code, R, T) of SP iterative receivers; universal MI code threshold I* = .577; calibrated return map predicts cliff per round. Hassibi-Hochwald-type question for coded iterative SP.
- D2 (L3+L4): "statistic, not architecture": LS input not sufficient when SP data interference coloured, C = (1-rho) H H^H + sigma2 I; GLS / achievable-Lambda whitening, training-free, should match learned refiners.
- D3 (L3): (rho, R, T) co-design: pilot power and inner joint budget substitutes.
- Rejected as centre: budget tuning alone (= configuration, see correction in c1-direction-review-20261010.md), learned receiver, closed-form kappa law.

## 4. Claude derivations (check them)
- Round-1 scalar law: eps = K(sigma2+1-rho)/(N rho); gamma = (1-rho)/(sigma2+eps); decode iff I_QPSK(gamma) >= I* -> gamma* = 1.312; Kc1 = N rho[(1-rho)/gamma* - sigma2]/(sigma2+1-rho). Vs IB2 R1: order right (.6-1.75x), rho trend wrong (naive rho* .43/.51/.58 at 6.5/8/9.5 dB; measured peak rho <= .3).
- Data-aided law: training energy rho + (1-rho)(1-v), interference (1-rho)v -> rho* falls as soft residual v falls (as T grows). Magnitude overshoot ~3x (same failure as frozen T2 closure); direction only.
- Statistic-gap bound (separable LS, Rayleigh |H_f|^2): white/GLS = E[c]E[1/c] = G(a) = (1+a)e^a E1(a), a = sigma2/(1-rho); with ridge: (S G + K)/(S + K), S = rho N/(sigma2+1-rho).
- Post hoc Jensen mechanism (after X2): SP self-interference signal-aligned. Along u = h/||h||: GLS info sum |(V^H p)_i|^2 s_i^2/(vbar s_i^2+sigma2) <= white sum |(V^H p)_i|^2 s_i^2/(vbar E+sigma2) (concave in s^2) -> whitening removes info along true h, adds elsewhere -> ridge bias along h dominates at high load. Untested.

## 5. Light experiments (2026-10-10; frozen spec research/c1-prelim-positioning.md; card research-assets/res-20261010-02.md)
- X1 rho x T (R4, T20 vs T40, 200 frames, paired bootstrap; out/c1rt/analysis/rt.md): g = Kc(T40)/Kc(T20) decreases with rho at R1-R2. g(.1)/g(.3): 6.5 dB 1.39/1.17, 8 dB 1.25/1.08 (all CI > 1, P1 4/4). R1 rho* moves one grid step down (6.5: .2->.1; 8: .3->.2); R2-R4 argmax unchanged; coupling fades by R4 at 8 dB. 8 dB: rho .15 @T40 >= rho .3 @T20 every round (R4 238 vs 234); at equal T40 rho .15 loses 12% at R4.
- X2 statistic gap (diagnostic; out/c1sg/analysis/sg.md): round-1 genie GLS beats white only noise-limited (P4 FAIL 21/40; max 1.29x, <= 69% of bound; P5 40/40 under bound). Ties/loses (.88-.99) for K/S > ~.35-.65 = cliff loads. Round 2 (receiver own soft variances) GLS worse 39/40.
- Existing: WARM_1.0 (exact round-1 channel start) = FULL within noise -> init forgotten (c1-scalar-closure.md). eps_ce1 .168 vs eps_det1 .025 example.
- Claude v2 (after experiments): centre D1 + D3; D2 demoted to regime lemma ("whitening helps only when K/S small; signal-aligned self-interference"). Positioning vs Transformer: initial-estimate slot (where Transformer refiners act) has ~0 cliff headroom in joint SP receiver; headroom = loop transfer + (rho, R, T) co-design.

## 6. Evidence index (read; do not edit)
- STATE.md (top section 2026-10-09/10; historical accepted claims 2026-07: deployment shell >= 87%, whitening 3.4% CI-sep, learning ~0; G0 scope per res-20260914-01)
- research-assets/: res-20261009-01, res-20261010-01, res-20261010-02, res-20260610-01, res-20260613-01, res-20260727-01/02, res-20260914-01, index.md
- .trellis/tasks/10-08-doppler-cluster/research/: c1-direction-review-20261010.md (Claude ccf rubric 3.65 then correction), c1-prelim-positioning.md, c1-scalar-closure.md, c1-round1-loop-theory.md, c1-inner-budget.md, c1-round2-own-symbol-theory.md, c1-joint-fp-theory.md, lit-v3.md, distinction-v3.md, ideation-v3.md
- .trellis/tasks/10-05-method-advantage/research/20261009-c1-review/REVIEW.md (your earlier review, 3.00/5)
- experiments/headroom_ladder_20261008/out/{c1rt,c1sg,c1ib2}/analysis/*.md
- Skills to borrow from (useful parts only, not full workflows): ~/.agents/skills/ccf-idea-reviewer/ (SKILL.md, references/rubric.md, calibration.md, strict-idea-review.md, expert-panel.md), ~/.agents/skills/ccf-idea-optimizer/ (SKILL.md, references/problem-method-blueprint.md, frontier-ideation.md, research-taste.md, experiment-design.md)

## 7. Hard rules
- No edits to repo files except the output files named in your prompt. No SSH, no runs, no git commits.
- Separate verified facts / derivation / inference / speculation. Cite file + section or number for each factual claim.
- Prior-art: web search allowed if available; label coverage (searched / partially / unsearched). Do not invent papers.
- Concept score (ccf rubric) separate from experiment/feasibility assessment.
