# POST HOC (not frozen, not a decision input): decomposition of the T1 oracle headroom at L16 (6.5 dB, rho .3, frames 0-299)
Computed 2026-10-13 after the frozen T1-T3 run, inline script on deinlab (same rows, same timing reference, same matched-FER
oracle logic as c1on_analyze.py; FER-feasibility not enforced by the inline script, checked by hand below).
- Best fixed: T40, Rc 7, FER .097, cost .698 s.
- Full oracle (T and Rc per frame, give-up): S1 .337.
- Oracle restricted to T40 (give-up + Rc per frame): S1 .201 at matched FER (26 frames fail under every T40 option; 3 extra
  give-ups to reach FER .097).
- Oracle restricted to T20: printed S1 .418 is NOT FER-feasible (50 frames fail under every T20 option -> FER .167 > .10);
  excluded.
- Per-frame T choice without give-up: S1 .045 (FER .087).
- Frames: decode only at T40 24, only at T20 0, both 250, neither 26.
- Mean per-round cost (s): T20 .234 (round 1 incl. pilot front), then ~.134; T40 .317, then ~.229.
Reading: of the 34% oracle headroom, ~20 points come from give-up/round-cap at fixed T40 (deployable syndrome rule realised 11%
on test frames), ~14 more need per-frame T choice combined with give-up. A switching policy (e.g. start T20, escalate to T40 on
a syndrome trigger) changes trajectories and cannot be evaluated from stored fixed-T rows; it needs new runs.
