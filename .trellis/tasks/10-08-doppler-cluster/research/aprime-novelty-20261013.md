# A' novelty judgment (Opus extraction + distinction, 2026-10-13)

Inputs: aprime-lit-candidates-20261013.md (Haiku, 35 items, keyword pass), aprime-lit-candidates-v2-20261013.md (Sonnet,
43 new items, concept-aware pass + shortlist), aprime-lit-packets-20261013.md (Sonnet, partial packets). Decisive sources
re-checked by the main session: verbatim abstracts via OpenAlex for Lee & Yang (TCOM 2010), Ylioinas et al. (TCOM 2013),
Chen-Maunder-Hanzo (TVT 2011 x2); Kanazawa et al. full text (local pdftotext, lines 479-480, 713-733, 789-791, 895-897);
Realtek US 11431440 claims (Google Patents). Coverage: partial (IEEE full texts closed; no exhaustive search).
Stance: overlap calibrates the distinction; it does not veto.

## Idea decomposed into mechanisms
| ID | mechanism in A' | closest prior work (verified level) | overlap |
|---|---|---|---|
| M1 | syndrome early stop | classic LDPC practice; Thaj & Viterbo OTFS turbo DFE (full text, Sonnet) | complete: this is our baseline |
| M2 | give up on predicted failure | Shin 2008 / Amador 2010 satisfied-check thresholds tuned by false-alarm vs missed detection (Amador full text); Mohsenin 2011; Samsung WCNC 2021 ML early termination; Strodthoff JSAC 2019 early-HARQ with FNR working point for a target BLER 1e-5 (full text) | high |
| M3 | per-block decision whether to run another inner estimation/equalization pass | Lee & Yang TCOM 2010 (abstract verbatim): "monitors the status of its iterative process and determines whether additional equalization is needed or not"; Ylioinas TCOM 2013 (abstract verbatim): EXIT-based activation scheduling of APP detector, decoder and decision-directed LS channel estimator, "adapted to prevailing channel circumstances"; Intel US 9210012 per-block iteration control by MSE | high for continue/stop; channel estimator as a scheduled block already exists (Ylioinas, condition-level) |
| M4 | escalate inner effort | Realtek US 11431440: inner LDPC iterations in a predetermined strictly increasing sequence over outer IDD iterations (fixed); failure-triggered escalation in decoding (Li-Shen-Tse adaptive SCL; Wang-Yedidia-Draper multistage); Chen-Hanzo deferred iterations until the EXIT tunnel opens | medium: fixed escalation and failure-triggered escalation exist separately; failure/risk-triggered escalation of a joint channel-estimation-detection inner loop not found |
| M5 | action-conditional failure risk with an explicit FER constraint (calibrated thresholds) | Strodthoff (threshold moving to a BLER target, single action: early NACK); ML risk-controlled early exit (Jazbec NeurIPS 2024; Learn-then-Test; conformal risk control) outside communications; Akyildiz-Mahdavifar 2026 cost-weighted OSD stopping (no hard constraint) | medium-low in iterative receivers; the methodology exists in ML |
| M6 | receiver class: SP joint CE-detection loop whose inner budget sets a load-dependent cliff; per-frame failure heterogeneity | Kanazawa SP-OTFS TVT 2026 (closest same class): global r_unc/r_cod/r_end (r_end = 4 chosen by simulation), and states as future work "an adaptive stopping criterion ... early termination based on LLR variance or residual interference power"; Zheng SP-AFDM and Huang SP-OTFS fix iteration counts (uncoded) | low: no per-frame control found in SP/OTFS/AFDM receivers |

## Distinction (calibrated)
- Shared core concept, well established in TCOM itself since 2010-2013: adapt an iterative receiver's per-block effort
  (including channel-estimator activations) from convergence/decoder-state metrics to save complexity at near-equal error rate.
  So "online per-frame scheduling" as such is NOT the contribution.
- What remains ours:
  (a) the action set includes risk-triggered escalation of the joint channel-estimation-detection inner budget, tied to a
      mechanism we measured: in SP receivers the inner budget sets the load cliff (res-20261010-01) and failures are
      frame-heterogeneous (A5, T3);
  (b) action-conditional failure risk with an explicit FER constraint and calibration (possibly a finite-sample
      risk-control guarantee), new to iterative receivers as far as searched; Strodthoff is the closest (one action, HARQ);
  (c) evidence so far for the novelty-relevant delta: in the frozen A' table on fresh test frames at L16, give-up only
      (prior-art-like rule) costs .585 s at FER .100, escalation + give-up .496 s at the same FER .100, i.e. escalation adds
      ~15% at equal realised FER over the prior-art-like rule (test frames, one condition; selection on dev).
- Substantiveness: (a)+(b) together are a moderate, honest increment (L3: known components, new receiver class, new trigger
  and guarantee). A' alone at "saves X% vs fixed schedules" would read as a rerun of Lee & Yang / Ylioinas in SP-AFDM.
  It becomes TCOM-worthy only with the mechanism link (A) and/or a calibrated reliability guarantee.

## Consequences
1. Ordering judgment (2026-10-13 reconsideration) refined: neither A nor A' alone is the paper. One object: a load-cliff-aware,
   risk-controlled per-frame scheduler for SP joint receivers. A gives the state and the mechanism (why the inner budget binds,
   which features carry risk: decoder state + elapsed rounds); A' gives the practical gain. Run order stays A'-test first
   (cheap, decisive), A-transfer next.
2. Criterion change for (b): baselines must include prior-art ADAPTIVE rules, not only fixed schedules: (i) convex hull of
   tuned fixed schedules (stands for offline EXIT/condition-level scheduling, Ylioinas/Haddad/Chen-DI); (ii) a tuned
   satisfied-check / syndrome-trajectory give-up rule (Shin/Amador/T2 type) with the same calibration margin; (iii) a
   stall rule (stop or give up when the syndrome stops improving, Lee & Yang type). The novelty-relevant gate is the gain of
   the risk-controlled escalation policy over the best of (i)-(iii) at equal realised FER.
3. Positioning: cite Lee & Yang, Ylioinas, Chen-Hanzo, Amador/Shin, Strodthoff, Kanazawa (future work), Realtek patent;
   distinction sentence = receiver class + inner CE-detection escalation + action-conditional calibrated risk + mechanism.

## Correction (2026-10-13, after Codex R3 codex-aprime-check-20261013.md)
- Retracted: "(c) escalation adds ~15% at equal realised FER over the prior-art-like rule". The two policies differ in arm
  (E0 -> E3), round cap (7 -> 10) and give-up rule (r1/>264 -> r2/>284) at once; E1-E3 are fixed clock schedules, not adaptive
  escalation. The arithmetic (1 - .496/.585 = .152) stands; the attribution does not. Baselines must include all five arms x Rc.
- Added closest work: Alves, Guimaraes, Pinto 2015 (IET Commun.) online switching of turbo-receiver computation mode from a
  channel-estimate/soft-symbol quality test with a false-alarm-controlled threshold (downgrade direction); Liu, Guan, Gonzalez
  Turbo BEM OTFS (TCOM 2024) is same-class SP+BEM soft-feedback (scheduler not checked); Huang & Ritcey 2005 (TWC) open lead.
- Narrowed: the remaining distinction is a target to implement, not an existing result: predict the action value
  Delta_e(z) = q20(z) - q_e(z) (rescue by extra inner budget), not only failure risk, and beat strong generic adaptive
  controllers (learned failure predictor, generic promotion) at the same reliability.
