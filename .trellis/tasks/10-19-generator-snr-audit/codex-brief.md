# Codex brief — generator re-implementation and SNR/power definition audit

Active task: `.trellis/tasks/10-19-generator-snr-audit`. Read `prd.md` first, then the project rules (`CLAUDE.md` at the
project root, including the deinlab section), then `STATE.md` (TCOM main-line section only).

## Why
All TCOM comparisons share one channel generator and one set of SNR, power and noise definitions:
- P1 (F0, B, LOCAL, F1 front end C, D, true-H receiver A3);
- P2a (port of Zheng et al. GLOBECOM 2025) and P2b (embedded pilot, scenario S);
- the CRB tier and the genie-support audit;
- E-1, E-2 (families R and C), E-3, E-3b, E-3c, GSO and the 10-18 prospective test.

A recount of the saved rows already passed (`experiments/tf_covariance_audit_20261018/out/recount-01/README.md`). It cannot
detect an error that every arm shares. This task looks for exactly that kind of error. Do not fix anything; report.

## Deliverable A — definition-layer audit (no new receiver runs)
For every comparison listed above, build one table with these columns, each entry backed by file:line in the code that
actually ran:
1. SNR definition. Is σ² = 10^(−SNR/10) relative to the total transmitted symbol energy (pilot + data), the data energy
   only, or energy per complex sample after the channel? Where is the per-frame channel energy normalised (the gen_fixed
   flag A1: unit per-frame path power)?
2. Pilot/data power split. Check that ρ and 1−ρ are applied as stated. Explain the E-3 family's internal representation:
   `experiments/tf_covariance_audit_20261018/forensic_synthetic_local.json` reports internal data power .5 and a scale
   1.183 at ρ .3. Show that the physical SNR matches P1's, or quantify the difference in dB.
3. Constellation scaling (QPSK), and any Eb/N0 versus Es/N0 conversion. P2b uses a different code length and k; check
   that its SNR axis is defined consistently with P1.
4. The σ² that each receiver assumes, compared with the σ² the generator used. All receivers are stated to know σ².
5. Frames and seeds. Which comparisons share channel, noise and codeword, as each card claims?

**Numerical check.** On a small set of frames per comparison (≥ 50), recompute the realised per-frame signal energy and noise
energy from the stored or regenerated arrays. Report the empirical SNR next to the nominal value.

## Deliverable B — independent generator re-implementation
Specification sources:
- `experiments/tcom_reference_frame_20261015/S0_NOTES.md`: the runtime sampling path, constants, and the D1/D2/A1 fixes.
- `experiments/tcom_reference_frame_20261015/gen_fixed.py`: the code under test. **Do not import it, or any project
  generator or receiver, into your re-implementation.**
- The protocol `.trellis/tasks/archive/2026-10/10-15-tcom-reference-frame/protocol.md`.
- For family C: `experiments/tf_cstate_e2_20261017/e2_channels.py` (Jakes-4 rays per tap) and its PROTOCOL.

Checks to implement, each with a tolerance declared before running:
- **B1 — physical operator.** From the specification alone, write the AFDM transform (c1 = 5/(2N), c2 = (√2−1)/(2N²),
  N = 1024), the CPP of length 102, and the path operator for given (delay, Doppler, gain). Take the stored truth
  parameters of ≥ 200 P1 frames and ≥ 50 family-C frames, rebuild the noiseless y or H independently, and compare with the
  project generator's output. Target: relative error ≤ 1e-10. Cover both Doppler sign conventions only if the spec is
  ambiguous, and state which one matches.
- **B2 — parameter laws.** On ≥ 2000 P1 frames per scenario (U and G), compare the drawn delays, Dopplers, gains, the
  redraw rate (stated 48.6% for the main generator, 58.2% for scenario S) and the per-frame power against the written
  law. Use KS or χ² tests with a declared α. Check that no truth geometry in family R has two paths on one delay, and
  that family C has the stated rays per tap.
- **B3 — invariants.** Delays ≤ 102 after D1. Δf = fs/N (D2). Unit per-frame path power (A1). Determinism: the same
  seed gives the same frame bit for bit. Frames are shared across ρ and SNR where the cards say so.
- **B4 — scenario S** (P2b): delay law scaled by 25/102 and truncated, as stated in res-20261015-03.

## Procedure and constraints
- Use the `research-checkpoint` skill, moment 1, before running: write the tolerances, α and the severity rule into
  `experiments/generator_snr_audit_20261019/PROTOCOL.md`, then commit before the run. Commit again after the run.
- **Severity.**
  - BLOCKER: a mismatch that changes a number in an accepted card (SNR offset ≥ 0.1 dB between compared arms, a wrong
    power split, a wrong operator, a non-shared frame where sharing is claimed). Stop and report immediately.
  - MAJOR: affects scope or wording.
  - MINOR: documentation only.
  - OK.
- Frozen code and existing evidence are read-only. New code goes only under `experiments/generator_snr_audit_20261019/`.
- On deinlab:
  - Work under `/data/guoyikun/00inbox/AFDM-channel-estimation/`. Scratch goes in `/data/guoyikun/tmp/`; never write to
    `/tmp`.
  - Use `conda activate AFDM` through `bash -lc`, and tmux session names starting with `g_`.
  - Cost cap: 6 core-hours. Large arrays stay on deinlab, with their full path and md5 recorded in the report.
- No result card and no STATE edit. Return `REPORT.md` and `report.json` and stop. The user decides follow-ups.
