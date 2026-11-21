# Inner-loop convergence acceleration: headroom screen — FROZEN PROTOCOL (Claude, 2026-10-14, before any run)

Why: every C1 method/criterion candidate failed its gate; the strongest lever in all data is plain inner-loop convergence
(B screen: pooled risk BASE40 .131 vs T20 variants ~.19; IB/IB2: T 20 -> 40 moves the cliff +10-40%). A method contribution
(Trans deliverable 5(b)) must reach T40 quality at clearly lower compute than simply running more inner updates.
Last bounded attempt (user, 2026-10-14). Fail -> stop method search for C1; inner budget stays a configuration finding.

## Harness and cells
Reuse the B mechanism-screen harness (driver_c1B.py / c1B_rx.py, same metric definitions, same receiver, R = 1, same refit/tau,
genie delays): the six cells M1-M6 of codex-B-derivation-20261013.md (8 dB rho .2 L8/L24, 8 dB rho .5 L24, 6.5 dB rho .3 L16/L28,
11 dB rho .2 L32), frames 0-31 (same observations as the B screen; this is a headroom screen, not a confirmation).

## Arms (hyperparameters fixed here; no tuning on these cells)
References (frozen kernel, damping .3): BASE20, BASE25, BASE30, BASE40. Tuned-damping control: DAMP20 with damping .5.
Candidates at T = 20, update equations unchanged, acceleration applied to the kernel's iterate state (the damped channel and data
means the next update consumes), safeguarded (if the residual norm grows, discard the extrapolated step and take the plain step):
- AA2: Anderson acceleration, memory 2, mixing 1, Tikhonov 1e-8 on the least-squares system.
- AA4: Anderson acceleration, memory 4, same settings.
- ADPT: adaptive damping, start .3; after each step multiply by 1.25 if the residual decreased (cap .9), else halve (floor .1).
The implementer defines the exact state vector and residual (document it); no truth enters any algorithm.

## Metrics (same definitions as the B screen)
Round-1 risk (orthogonal channel error as in B), round-1 FER, inner updates, measured seconds per frame (same host, shuffled arm
order, single-thread), plus per-step overhead of the acceleration.

## Gate (pre-registered)
PASS iff at least one candidate X satisfies, in >= 4 of 6 cells: risk_X <= 1.10 * risk_BASE40, FER_X <= FER_BASE40 + .02, and
seconds_X <= .80 * seconds_BASE40; AND X beats DAMP20 and BASE25 on risk in >= 4/6 cells. Pooled numbers are reported but the
cell count decides. PASS -> next step is a load screen (cliff at R = 2-4, compute-matched against BASE30/BASE40 with early stop),
designed separately. FAIL -> KILL acceleration route; no hyperparameter re-tuning on these cells.

## Result (2026-10-14 00:34; Codex, out/c1ACC/screen/analysis.md)
KILL. Joint-pass cells AA2/AA4/ADPT = 0/1/1; beat-both-references cells 0/0/3 (needs >= 4/6). Pooled risk / FER / s per frame
(192 frames each): BASE20 .147/.818/.459; BASE25 .141/.797/.515; BASE30 .137/.745/.565; BASE40 .131/.677/.686; DAMP20(.5) diverged
numerically (retained)/.833/.467; AA2 .147/.818/.559; AA4 .147/.818/.558; ADPT .137/.938/.470. Anderson adds time without gain;
adaptive damping lowers channel risk to the BASE30 level at BASE20 cost but worsens FER sharply (channel accuracy and decoding decouple).
Per the frozen rule: C1 method search stops; the inner budget remains a configuration finding.
