# A' test: does syndrome-triggered T escalation make online scheduling worth >= 15%? (2026-10-13, FROZEN before the run)

Context: T1-T3 (c1-online-headroom-T123.md): oracle headroom .337 at L16; a deployable give-up rule realised .111 on held-out
frames (< .15 gate, A-first). Post hoc: ~14 of the 34 oracle points need per-frame T choice, which stored fixed-T rows cannot
evaluate. User chose a small new run (2026-10-13) to test this one policy family. Development evidence, one condition.

## Run (driver_c1esc.py, out/c1esc)
6.5 dB, rho .3, L {16, 20}, frames 0-599, rounds 10. Arms E<e> = T 20 in rounds 1..e, T 40 afterwards: E10 (all 20), E0 (all 40),
E1, E2, E3. With syndrome early stop a frame decoded by round e never escalates, so "escalate if not decoded by round e" equals
the fixed schedule E<e>. Inner trace length per round asserted equal to the schedule.
Closure: E10 rows = stored FULL_R10 rows, E0 rows = stored R10T40 rows (frames 0-299; ierr/syn/dsha per round exact).

## Analysis (c1esc_analyze.py)
- Per-round cost: increments of the quiet timing reference (out/c1ib2_time, frames 0-9) by (T, L, round); a schedule's cost
  through round r = sum of the increments of the T actually used in rounds 1..r (round 1 includes the pilot front). Secondary unit:
  inner updates (sum of T). Measured t_cum of this run reported only.
- Stop round = min(first round with syndrome 0, round cap Rc, give-up round). Failure = ierr > 0 at the stop round, or given up.
- Policy spaces. Fixed F: arm in {E10, E0}, Rc in 1..10. Online O: F with give-up rule G, plus escalation arms E1-E3 with
  Rc in e+1..10, with or without G. G = give up at the end of round r_g (1..4, r_g < Rc) if not stopped and syndrome > theta
  (theta over syndrome values seen on dev frames).
- Dev = frames 0-299 (used in T1-T3), test = frames 300-599 (fresh). On dev: B* = cheapest F member with FER <= delta = .10;
  P* = cheapest O member with FER <= .10 (ties: lower FER, then simpler).
- Test: S = 1 - cost(P*)/cost(B*), d = FER(P*) - FER(B*); paired frame bootstrap (B = 1000) CI for S and d.
- Primary (L16): A' viable iff S >= .15 and S CI lower end > 0 and d <= +.01. Otherwise A' is demoted to a remark and the
  direction is A only (no further A' runs without a new idea).
- Report-only: components (escalation without G; G without escalation) selected the same way; L20 at delta = .20; full-frame
  oracle headroom; inner-update-unit version.

## Limits (stated before results)
One condition; cost from a 10-frame reference; dev/test 300/300 frames, so S has a few-point CI; escalation family limited to a
single switch 20 -> 40 at rounds 1-3; a positive result is development evidence for A' as a method exit, not a Trans claim.

## Results (2026-10-13; out/c1esc/analysis/esc.md; frozen commit d9a8c97a; 6000 rows, 0 errors)
- Closure: E10 = stored FULL_R10, E0 = stored R10T40 (600 + 600 pairs, 0 mismatches).
- L16 primary (delta .10, cost = timing-reference seconds): B* = E0 (all T40), Rc 7, syndrome early stop. Best online
  P* = E3 Rc10 + give-up after round 2 if syndrome > 284: test cost .671 -> .496 s, S = .261 [.215, .307], but FER .073 -> .100,
  d = +.027 [+.007, +.050] > +.01 -> **A' NOT viable by the frozen rule; demoted to a remark; direction A only.**
- Components on test: escalation only (E2 Rc8) S = .096 [.075, .119], d = -.007 (FER-safe, below gate); give-up only
  (E0 Rc7, r1, syndrome > 264) S = .128, d = +.027. Inner-update unit: S .399 / .221 / .148. Oracle headroom (all 600 frames,
  matched FER) .349. Measured run time (load-noisy) S = .301.
- L20 report-only (delta .20): P* = E3 Rc9 + give-up(r2, > 306) S = .226 [.179, .276], d = -.010 [-.030, +.013] (FER-safe there).
- POST HOC (c1esc_posthoc.py, out/c1esc/analysis_posthoc; not a decision input): re-selecting online policies under
  dev FER <= dev FER(B*) + .01 yields the same P* (B* dev FER >= .09), so the FER overshoot is not a gate-asymmetry artefact;
  it is dev -> test generalisation of a give-up threshold chosen at the FER boundary (B* test FER fell to .073).
- Reading: online per-frame scheduling has real headroom (oracle .35); escalation alone is reliability-safe but worth ~10% wall
  time (per-round fixed CE/decoder cost dilutes the T saving: T20 .134 s vs T40 .229 s per round); give-up carries most of the
  gain but needs a reliability margin rule. Any future A' claim needs that margin pre-registered on fresh frames.
- POST HOC frontier diagnostic (c1esc_frontier_posthoc.py, out/c1esc/analysis_frontier; written after the verdict, not a
  decision input): comparing classes across target FER levels instead of one boundary point. In-sample test frontier (optimistic,
  more so for the larger online class): online cheaper by .21/.24/.29 at test FER <= .075/.10/.125 (L16) and .21/.27/.34 at
  .15/.20/.25 (L20). Dev-selected with a .02 selection margin for the online policy: L16 level .125 -> online .490 s / FER .100 vs
  fixed .631 / .093 (saving .223, d +.007); L20 level .20 -> .828 / .180 vs .993 / .200 (.166, d -.020). Caveats: the fixed family
  is a coarse staircase (time-sharing hull not used), many more online policies (selection optimism), 300 test frames cannot
  certify a .01 non-inferiority margin (paired CI half-width ~.02). Reading: the frozen single-point gate mixed threshold
  generalisation with class efficiency; the class advantage looks real (~15-30% at equal FER) but needs a corrected,
  pre-registered test on fresh frames before any claim.
