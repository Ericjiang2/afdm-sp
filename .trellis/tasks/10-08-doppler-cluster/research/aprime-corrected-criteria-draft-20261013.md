# A' corrected evaluation criteria — DRAFT for Codex check (2026-10-13; not frozen, not run)

Why a redraft: the frozen A' test (c1-escalation-A-prime.md, verdict "not viable", kept on record) compared one boundary point
per class, selected a give-up threshold at the FER limit on 300 frames, used a staircase fixed baseline, had a paired FER CI
half-width ~.02 (cannot certify a .01 margin), one condition, one operable load. Post hoc frontier (analysis_frontier/,
labelled): online ~15-30% cheaper at equal FER; dev-selected with a .02 margin: L16 22.3% at d +.007, L20 16.6% at d -.020.
This redraft changes the criterion before any new data; old verdict unchanged.

## Object
Per-frame action policy after each outer round r of the SP joint receiver (genie delays, K = 8L, rounds <= 10):
stop (syndrome 0) / continue at current T / escalate T 20 -> 40 (allowed at r in {0,1,2,3}; r = 0 = start at 40) / give up.
Action-conditional failure risk from deployable features z_r = [log(1 + syndrome_r), decoder iterations_r, r, syndrome change]:
q_cont(z_r) = Pr(final failure | z_r, continue at T20), q_esc(z_r) = Pr(final failure | z_r, escalate now) (logistic, fitted on
calibration frames per cell; pooled-across-cells fit reported as secondary). Policy: escalate at first r <= 3 with
q_cont > tau_e; give up at round r when the risk under the chosen continuation > tau_g; round cap Rc.
Exactly evaluable from five fixed-schedule arms per frame (E10, E0, E1, E2, E3: before escalation the trajectory equals E10;
after escalation at round e it equals E_e), as in driver_c1esc.py.

## Cells (two conditions x two loads; loads chosen from stored R4 data so the R10 FER sits near the targets)
6.5 dB rho .3: L16 (target l = .10), L20 (l = .20). 8 dB rho .3: L28 (l = .10), L32 (l = .20).
If on calibration frames no fixed schedule reaches the cell target, the cell moves to the next level in {.10, .20, .30}
(rule fixed now).
Frames: calibration 0-599 (6.5 dB reuses stored c1esc rows; 8 dB new), test 600-2599 (new, 2000 per cell).
Cost: quiet timing reference per (T, L, round) (6.5 dB from c1ib2_time; 8 dB L28/L32 new 10-frame reference run alone);
secondary unit inner updates.

## Selection (calibration frames only)
tau_e, tau_g, Rc: minimise calibration cost subject to calibration FER <= l - m, m = .02.

## Test criterion (test frames)
Baseline = lower convex hull of the fixed class {T in {20, 40}} x {Rc 1..10} with syndrome early stop, computed on the test frames
themselves (in-sample for the baseline -> conservative for A'); time-sharing between two fixed schedules makes every hull point
achievable. ratio_c = cost_online / hull_cost(at the online policy's realised test FER).
Cell passes iff realised test FER <= l + .01 AND ratio_c <= .85 AND the paired-bootstrap 95% CI upper end of ratio_c < 1.
Primary: A' viable (development level) iff >= 3/4 cells pass. Power: 2000 test frames -> paired FER-difference CI half-width
~.009 at FER ~.1.
Report-only: secondary unit; pooled risk model; each component (escalation-only, give-up-only); oracle headroom; reliability
diagrams of q on test frames.

## Revision after the literature pass (aprime-novelty-20261013.md)
Per-block adaptive scheduling is established prior art (Lee & Yang TCOM 2010; Ylioinas TCOM 2013; Shin/Amador give-up;
Chen-Hanzo MI stopping / deferred iterations). The novelty-relevant gate is therefore against prior-art ADAPTIVE baselines,
each tuned on calibration frames with the same FER margin:
(i) convex hull of tuned fixed schedules (stands for offline / condition-level EXIT scheduling);
(ii) syndrome-threshold give-up (Shin/Amador/T2 type) on the best fixed schedule;
(iii) stall rule: stop or give up when the syndrome weight fails to decrease by > theta between rounds (Lee & Yang type).
Primary metric becomes ratio_c = cost_online / min over baselines (i)-(iii) of cost at the online policy's realised test FER;
pass iff realised test FER <= l + .01, ratio_c <= .85 and the CI upper end < 1, in >= 3/4 cells. Gain over fixed schedules
alone is report-only. Note from the frozen A' table (test frames, L16): give-up only .585 s and escalation + give-up .496 s at the
same realised FER .100, i.e. ~15% from escalation over a prior-art-like rule.

## Open questions for Codex
1. Is the hull computed in-sample on test frames the right conservative baseline, or should it be calibration-selected too?
2. Per-cell calibration (600 frames) vs pooled: which should be primary for a method claim?
3. Margin m = .02 fixed vs m = 1.64 x calibration SE?
4. Is .85 (15%) at equal FER a reasonable "non-trivial" bar for TCOM 5(b), given the novelty assessment?
5. Anything that would make a pass uninformative (leakage, selection optimism, cost model)?
