Active task: .trellis/tasks/11-19-unified-cov-prospective

# Codex Sol brief: Phase 1b (pre-freeze revisions §9–§10), then STOP

Written 2026-11-19 by Claude. Continue in this session; the Phase 1 rules still apply (blindness, read-only frozen sources, deinlab
limits, git rules). Treat this brief as the approval. Phase 1b cap: 3 core-hours. Confirm `model:` is `gpt-6.2-sol`.

Read `protocol-DRAFT.md` §9 and §10 first (committed `27a23bd7`, `d7eb02e4`), and `astra-design-review.md`. Where they conflict with
§4, they take precedence.

## Deliverables
1. **CSTATE arms C-hi and C-lo** (§9), built with the same exact per-support construction as U.
2. **Construction rules** (§10.7):
   - name the projector's construction support at each stage;
   - rescore the incumbent whenever the projector changes, before any accept or reject comparison;
   - check monotone descent inside each fixed-projector pass;
   - R1 refinement is full Γ + σ²I, so U2 with an empty refinement projector is bit-identical to S-lo;
   - at u = 0, use the Doppler kernel directly or skip the zero ridge.

   Revise any Phase 1 code that does not satisfy these, and re-run the affected gates.
3. **New G2 item**: on isolated admission-law slices, compare the phantom net reward under A2, CD, U, C-hi and C-lo at δ = .25 and .5 bin
   with Astra's closed form, using two separately optimised supports. Relative error ≤ 1e-8. Include C-hi and C-lo in the τ = 0
   reduction checks:
   - C-hi with an empty Π_lo reduces to CD;
   - C-lo with an empty Π_lo reduces to A2.
4. **Unit-level mirror readout V5-adm** (§10.6): code that, from a saved first-exchange state, evaluates the designated A2 phantom and the
   best new-delay candidate under the five covariances with the deletion slot fixed. Test it on old keys and smoke keys only.
5. **Leverage for the frozen rules** (old data only):
   - margin m = min(.5 pp, .25 × the archived A2 − CD whole-grid FER gap);
   - the expected 95% half-width of ψ at the FER level, with the V5 primary chosen by the §10.5 rule;
   - on old keys, the expected count of V5-adm units per 200 frames.
6. **Verdict code** updated to §10:
   - three-layer conclusion, with premises evaluated first;
   - V3 non-inferiority with the rare-event rule;
   - V5 and V5-adm;
   - the H contrast;
   - synthetic tests for every branch.
7. **Fresh-block check** extended to frames 4600–4699. Project the cost for the SBL leg at 200 and 300 frames, the CSTATE leg with six arms
   (F0, A2, CD, U, C-hi, C-lo) at 200 frames, and V5-adm. Apply the §10.9 rule and report the choice.
8. Update the experiment `PROTOCOL.md` (still DRAFT) so that it carries §9–§10 with your implementation notes. Commit and stop.

## Final message
English, ≤ 15 lines, containing:
- commit hash;
- gate table (G1–G3, the new G2 items);
- m;
- ψ half-width and the chosen V5 primary;
- expected V5-adm units;
- SBL frame count and its cost;
- total projected main cost;
- any revision you made with its reason;
- the confirmed `model:`.

## Addendum after reading the Phase 1 report
- G1 matched A2 against only one archived key. Strengthen it: compare A2 with every archived A2 row on the same harness that is
  available on old keys (split-prospective K keys), up to 8 triggered keys. If fewer than 8 exist, report the count and the reason.
