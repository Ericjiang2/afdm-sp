# Claude reconsideration: A vs A' + are our gates right? (2026-10-13, caveman)

Since your R2: T1-T3 (c1-online-headroom-T123.md) and A' run (c1-escalation-A-prime.md) done. Frozen verdicts: T2 A-first;
T3 scalar state insufficient (round index carries history); A' NOT viable (S .261, FER .073 -> .100, d +.027 > .01).
Post hoc frontier (labelled) suggests class advantage ~15-30% at equal FER. User asked: which is better/more suitable, and are
the gates right.

## Gate critique (A')
F1 one boundary point per class, give-up threshold picked at FER limit on 300 dev frames -> mixes threshold generalisation
   with class efficiency. Margin .02 rule: L16 22.3% at d +.007; L20 16.6% at d -.020 (post hoc).
F2 power: 300 test frames -> paired d CI half-width ~.02 > .01 margin -> gate could detect harm, never certify viability.
   Need ~2000 test frames for ~.009.
F3 fixed baseline = Rc staircase; fair = convex hull (time-sharing). Part of post hoc gain may be granularity.
F4 currency: per-round T-independent cost ~.04 s (CE refit + LDPC) -> escalation 9.6% (CPU s) vs 22% (inner updates).
F5 one condition, one operable load at delta .10.
Right parts: equal-reliability principle, fresh test frames, tuned fixed + syndrome stop, decomposition, pre-registration.
delta = .1 matches HARQ initial-BLER practice; give-up = early NACK has uncounted latency value.

## Gate critique (A)
G1 Kc(FER .5) wrong operating point; design needs Pe at delta (tail), A5 = tail failure -> predict Pe at delta + calibration.
G2 vs exhaustive grid: offline grid cheap here (tens of configs x hundreds frames) -> offline-pick value weak unless big
   family or online link adaptation. T3 -> predictor must be per-frame + history = same object A' needs.

## Literature pass since then (aprime-novelty-20261013.md; candidates v1/v2; packets)
Per-block adaptive scheduling incl. channel-estimator activation is established TCOM prior art (Lee & Yang 2010;
Ylioinas 2013; Chen-Hanzo 2011; Shin/Amador give-up; Strodthoff calibrated early HARQ). Kanazawa SP-OTFS (closest class)
uses global r_end = 4 and lists adaptive stopping as future work. Remaining distinction: risk-triggered escalation of the SP
joint CE-detection inner budget + action-conditional calibrated FER control + load-cliff mechanism. Frozen A' table: give-up
only .585 s vs escalation + give-up .496 s at same test FER .100 -> ~15% from escalation over prior-art-like rule.

## My current recommendation
Neither A nor A' alone. One object: load-cliff-aware, risk-controlled per-frame scheduler for SP joint receivers. A = state +
mechanism (why inner budget binds; features = decoder state + elapsed rounds); A' = practical gain (5(b)); A transfer = 5(c)
upgrade. Run order: corrected A' test first (cheap, decisive), A transfer next. Novelty gate vs prior-art ADAPTIVE baselines
(hull of fixed; tuned syndrome give-up; stall rule), not only fixed.
Draft criteria: aprime-corrected-criteria-draft-20261013.md (5 open questions at end).
