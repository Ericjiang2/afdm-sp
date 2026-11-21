Active task: .trellis/tasks/11-19-unified-cov-prospective

# Codex Sol brief: unified-covariance prospective test, Phase 1 (arms, gates, leverage, cost), then STOP

Written 2026-11-19 by Claude after Eric approved the run ("Yes, run it"). Eric delegated approvals and the freeze to Claude, so
**treat this brief as the design approval** and do not stop to ask. You are the executor (GPT-6.2 Sol). Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`
(the git root is the vault, two levels up; branch `main`). Confirm `model:` is `gpt-6.2-sol`; if it is not, stop and say so.

## Hard rules
- Phase 1 only. Do not run the main block and do not freeze anything.
- **Blindness.** Never simulate any arm on the fresh frame block (4400–4599, or the block selected under DRAFT §2). Phase 1 uses only
  old keys (frames 4000–4399, whose outcomes are archived), synthetic inputs, and a previously used smoke block (for example
  frames 8400–8411). Do not interpret smoke FER.
- Before any simulation, verify that the fresh block is unused by every archived run in `experiments/*/out/` and the historical
  `afdm_sp_joint_unrolled/outputs_*` configs. Record the method and the result.
- Frozen sources are read-only (`FROZEN_DEPENDENCIES.md` and the source manifests of E-3c, spectral split and Stage 3). New code goes
  in `experiments/unified_cov_prospective_20261119/`. Import the existing modules wherever possible. If a frozen function must be
  copied, put one line at the top of the copy stating its source, the change, and why it cannot be called directly.
- Do not edit `STATE.md`, any result card or the skeleton.
- deinlab: test reachability with `ssh -o ConnectTimeout=15 deinlab true`. CPU only, one thread per process, at most 32 processes, tmux
  session `g_unified`, outputs under `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/unified_cov_prospective_20261119/out/`.
  Run bit-exact parity gates on deinlab. Phase 1 cap: 3 core-hours.
- Git: stage only this task's files and the new experiment directory (small files only). HEREDOC message, no push, no amend. On
  `index.lock`, wait 30 s and retry, up to 10 times.

## Read first
1. `.trellis/tasks/11-19-unified-cov-prospective/research/protocol-DRAFT.md` (definitions, arms, verdicts, hypotheses) and `design.md`.
2. `experiments/sbl_spectral_split_20261119/` (`PROTOCOL.md` §7, `spectral_receiver.py`, `main_receiver.py`, `run_main.py`,
   `aggregate.py`), and `research-assets/res-20261119-02.md`.
3. `experiments/cstate_codelay_sbl_stage3_20261118/` (`PROTOCOL.md`, `codelay.py`, `run.py`), `research-assets/res-20261118-03.md`,
   and the E-1 geometry `experiments/tf_cstate_e1_20261017/geometry_reopen_variant.py` (and its validation variant with
   `strategy='direct'`).
4. `.trellis/spec/backend/covariance-experiment-evidence.md`.

## Deliverables
1. **`experiments/unified_cov_prospective_20261119/PROTOCOL.md`**, marked DRAFT, copied from the task DRAFT. Give a written reason for
   every change.
2. **Arms** exactly as DRAFT §3:
   - SBL leg: R0, R1, S-lo, S-hi, S-isolo, U2. U2's refinement adds `u·Π_lo` built at the start of each continuous pass on that pass's
     atom set and held fixed within the pass.
   - CSTATE leg: F0, A2, CD, U. Γ_U must be exact for every trial support in exchange scoring, local passes and the final refit. The
     route is your choice (design.md).
   - Per key and arm, log: decoded SHA, information errors, NMSE (SBL), atom and co-delay counts, β, iterations and convergence (SBL),
     first-edit type (CSTATE: new delay or existing delay), and the Π_lo census.
     - The census covers the CSTATE trials with a nonempty Π_lo, the keys where U and CD exchange decisions differ, and whether such a
       key has a true co-delay pair within .5 bin. Truth is used only for this diagnostic.
   - Configs carry `_argv` and `_config`.
3. **Gates G1–G3** as in `design.md`, with receipts. Defect rule: fix your own-code defects, log them and rerun. A frozen-source or
   archive mismatch is a gate failure: stop and report.
4. **Leverage readouts** (from old rows only):
   - (a) The cluster-bootstrap 95% half-width of φ_lo on the 1,200 E-3c / spectral-split keys, then extrapolated to 2,400 keys.
   - (b) The archived A2 − A1 (or A2 − CODELAY) whole-grid FER difference with a cluster CI on a comparable P1 F0+CSTATE grid, naming
     the archive used. If no archive pairs these arms on this harness, run A2 on old Stage 3 keys (frames 4000–4399; old keys are
     allowed) within the Phase 1 cap, and report the result.
5. **Verdict code** for DRAFT §4, with synthetic tests covering each verdict branch and the not-evaluable rules.
6. **Cost**: smoke timing per key and arm, projected main cost × 1.3 for 2,400 SBL keys and 6,800 CSTATE keys. If the projection exceeds
   25 core-hours, apply the DRAFT §8 reduction and recompute.
7. **Commit and stop.** Append a dated Phase 1 paragraph to `.trellis/tasks/11-19-unified-cov-prospective/implement.md`.

## Final message
English, ≤ 15 lines, containing:
- commit hash;
- the fresh-block check result;
- the gate table;
- the leverage readouts (a) and (b);
- the CSTATE Γ_U route and why it is exact;
- the projected main cost;
- the DRAFT changes and their reasons;
- the confirmed `model:`.
