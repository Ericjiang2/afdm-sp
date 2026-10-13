# Proof Audit Report — TMLCN Paper

**Generated**: 2026-05-16T07:29:00Z
**Audit skill**: proof-checker
**Reviewer**: Codex GPT-5.5 (xhigh)
**Thread ID**: `019e2faa-2342-7e91-b13d-0639bbcfe4e2`
**Assurance level**: `submission`
**Verdict**: **FAIL** (`reason_code: critical_gap`)

---

## Scope

The paper contains exactly **one** formal theorem environment:

- **Theorem 1** — Initialization-faithful unrolling, computational
  (`sections/Section3.tex:176-195`, label `thm:initfaithful`)
- **Proof outline**: `Appendix.tex:7-78`, label `app:initfaithful`

No `\begin{lemma}`, `\begin{proposition}`, `\begin{corollary}` environments
exist in the paper. Verdict is therefore driven entirely by Theorem 1.

## Verifier file

The theorem references `verify_classical_unrolled_matches_numpy.py`. This
file **exists** at:

```
/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/verify_classical_unrolled_matches_numpy.py
```

(233 lines, committed to the project repo.) The reproducibility-path
prerequisite is satisfied: the claim is **testable**. However, what the
verifier *actually* tests is materially weaker than what the paper claims
— see the issue list below.

## Verdict rationale

The reviewer (`mcp__codex__codex`, model `gpt-5.5`, reasoning `xhigh`)
returned a **FAIL** verdict with the central finding:

> Theorem 1 asserts `max_i |x_torch − x_numpy| = 0` (bit-exact, max-norm
> zero) on hard-decision QPSK outputs, in `complex64`, over 64 seeded
> frames per `N ∈ {512, 1024}`, for every outer-iteration `t`. The
> verifier, by contrast, asserts (i) `||x_torch − x_soft_np|| /
> ||x_soft_np|| < 1e-5` (relative L2 on the *soft* output, not max-diff
> zero on hard decisions), (ii) `|BER_torch − BER_numpy| < 1e-4`
> (aggregate scalar, not per-iteration hard-decision equality),
> (iii) under `complex128 / float64` (line 114-117, line 171-172 of the
> verifier — **not** the `complex64` claimed in Section 3), (iv) with
> default `--frames 30` (not 64) on `--n-total 512` (1024 requires
> non-default invocation not shown in the paper).

A verifier PASS is therefore consistent with the theorem being **false**.
This is a **GLOBAL/INVALID** scope overclaim, severity **CRITICAL** under
the proof-checker taxonomy.

---

## Phase 0.5 — Proof-Obligation Ledger

### Dependency DAG

```
Theorem 1 (thm:initfaithful)
  ├── Pinning relation 1: OMP argmax (smallest-index tie-break)
  ├── Pinning relation 2: LS solve via Cholesky (claimed same LAPACK potrs)
  ├── Pinning relation 3: MP-BP Gauss-Seidel sequential update
  └── Pinning relation 4: Gray-coded QPSK hard demap
       └── all four feed: verify_classical_unrolled_matches_numpy.py
            └── asserts: relative-L2 < 1e-5, BER-diff < 1e-4
```

**No cycles.** Single theorem, no lemma/proposition dependencies.

### Assumption ledger (per pinning relation)

| Relation | Asserted in proof | Verified in code? |
|----------|-------------------|-------------------|
| OMP argmax tie-break | "smallest-index-wins at fixed input precision" | **NOT VERIFIED**: verifier does not log argmax margins; ties assumed not to occur |
| LS via Cholesky | "same LAPACK potrs kernel" | **CONTRADICTED**: code uses `np.linalg.lstsq`/`solve` and `torch.linalg.lstsq`/`solve`, not the asserted Cholesky path (per reviewer's code inspection) |
| MP-BP Gauss-Seidel | "same sequential update" | **NOT VERIFIED**: verifier default is `mp_mode='pic'`, not BP |
| QPSK demap | "applied to same posterior in single-precision" | **NOT VERIFIED**: verifier uses double-precision; demap margins not logged |

### Quantified statement (canonical form)

Paper's theorem, rewritten with explicit quantifiers:

> ∀ N ∈ {512, 1024}, ∀ t ∈ {1, ..., T_out},
>   ∀ frame ∈ {64-frame verification set seeded at master seed},
>     in `complex64`:
>       max_i |hat_x_d_torch^{theta=0,(t),i} - hat_x_d_numpy^{(t),i}| = 0

Verifier's actual check:

> For (N=512), for (T_out outer iterations summarized into a single final
> output), for (30 default frames per SNR ∈ {15, 20, 25}), in
> `complex128`:
>   worst_frame ||x_soft_torch - x_soft_numpy|| / ||x_soft_numpy|| < 1e-5
>   AND worst_frame ||H_torch - H_numpy||_F / ||H_numpy||_F < 1e-5
>   AND worst_frame |BER_torch - BER_numpy| < 1e-4

The two statements are not logically equivalent. The verifier's claim is
**strictly weaker** along multiple axes: (i) tolerance vs zero, (ii) soft
vs hard, (iii) final vs per-iteration, (iv) complex128 vs complex64,
(v) 30 frames vs 64, (vi) N=512 only vs N ∈ {512, 1024}.

---

## Round 1 — Issues (10 total)

| ID | Severity | Status | Category | Where |
|----|----------|--------|----------|-------|
| T1-01 | **CRITICAL** | INVALID | SCOPE_OVERCLAIM | tolerance vs bit-exact |
| T1-02 | **CRITICAL** | INVALID | SCOPE_OVERCLAIM | soft x_soft vs hard hat_x_d per-t |
| T1-03 | **CRITICAL** | OVERSTATED | QUANTIFIER_ERROR | 64 frames × {512,1024} not run by default |
| T1-04 | **CRITICAL** | INVALID | NORMALIZATION_MISMATCH | complex64 claim vs complex128 verifier |
| T1-05 | **CRITICAL** | INVALID | HIDDEN_ASSUMPTION | "same LAPACK potrs" not the actual code path |
| T1-06 | MAJOR | UNJUSTIFIED | UNJUSTIFIED_ASSERTION | BP schedule not in default verifier |
| T1-07 | MAJOR | UNJUSTIFIED | HIDDEN_ASSUMPTION | learned head not instantiated by default |
| T1-08 | MAJOR | OVERSTATED | STOCHASTIC_MODE_CONFUSION | "transfers to any input draw" overclaim |
| T1-09 | MAJOR | UNJUSTIFIED | CASE_INCOMPLETE | argmax/demap/prune margins not logged |
| T1-10 | MINOR | UNCLEAR | SCOPE_OVERCLAIM | UWA 8-path vs P_paths=10 default |

5 issues classified **CRITICAL** (any one alone forces FAIL under the
acceptance gate). See `PROOF_AUDIT.json` for full per-issue records
(statement / counterexample / minimal_fix).

### Counterexamples

| Issue | Counterexample |
|-------|---------------|
| T1-01 | Set `x_torch = x_np + 1e-8 * x_np`. Then `x_rel_err = 1e-8 < 1e-5` (verifier PASS) but `max_i |·| > 0` (theorem FALSE). |
| T1-02 | Two implementations with identical BER but a single symbol decided differently somewhere across 64×T_out positions → `|BER_torch − BER_numpy| < 1/N < 1e-4` (verifier PASS) but `max_i |hat_x_d_torch − hat_x_d_numpy| ≠ 0` (theorem FALSE). |
| T1-04 (candidate) | Near a QPSK decision boundary, `complex64` round-off flips a sign while `complex128` does not. |
| T1-05 | Different LS solvers (lstsq vs solve vs cho_solve) can return different solutions under round-off while still passing relative-L2 tolerance. |
| T1-09 | Equal-magnitude argmax candidates resolved differently across backends → different OMP support → different downstream outputs. |

---

## Recommended fix paths

The reviewer identified two mutually exclusive repair routes; the authors
must choose one and propagate consistently:

### Route A — Weaken Theorem 1 (paper-safe, code unchanged)

Replace Theorem 1 with a **reproducibility / regression-test claim** that
matches what the verifier checks:

> Under the committed verifier command (`python
> verify_classical_unrolled_matches_numpy.py --n-total 512 --p-paths 10
> --mp-mode pic --snr-list 15 20 25 --frames 30 --seed 42`), with
> `complex128 / float64`, on the 30-frame×3-SNR verification set:
> the final soft-symbol vector and channel estimate of the
> torch-unrolled implementation satisfy `||x_torch − x_np||_2 /
> ||x_np||_2 < 1e-5` and `||H_torch − H_np||_F / ||H_np||_F < 1e-5`,
> and the per-frame hard-decision BER difference is below `1e-4`.

This drops "bit-exact", "max-diff = 0", "per-iteration t", "complex64",
"64 frames", "N ∈ {512, 1024}" — all of which the current verifier does
NOT certify.

### Route B — Strengthen the verifier (code changes required)

To support the theorem **literally**, the verifier must:

1. Add `--cdtype complex64` mode and re-run; or change theorem to
   `complex128`.
2. Loop over `t ∈ {1, ..., T_out}` and assert
   `np.array_equal(hard_torch[t], hard_numpy[t])` per frame and per
   iteration (not just final `x_soft`).
3. Default to (or document) `--n-total 1024 --frames 64`; commit the run
   log for both N values.
4. Instantiate the C2-rel support head with zero/no-op bias and verify
   the head appends zero atoms (currently `learnable_heads=()` by
   default).
5. Align `--mp-mode bp` with the theorem's "Gauss-Seidel BP" claim, or
   change the theorem to "PIC".
6. Inspect actual LS code paths; either change Appendix proof to match
   `np.linalg.lstsq` / `torch.linalg.lstsq` reality, OR change code to
   shared Cholesky path and log backend/device.
7. Log min argmax margin, min demap margin, min prune margin per frame
   (zero-margin events would falsify the deterministic-tie-break claim
   on real data).

---

## Phase 2 status

**Phase 2 (fix implementation) was deliberately skipped.** The caller's
invocation is a verification audit, not a fix-and-recompile cycle. The
two repair routes above are scope-changing decisions that must be made
by the author (Route A is a paper-text edit; Route B is code work plus
paper-text edit). Once the author selects a route, a follow-up
`/proof-checker --deep-fix` invocation can be used to draft the literal
LaTeX patch.

## Phase 3.5 — Independent verification

Not run. With Phase 2 skipped, there are no FATAL/CRITICAL **fixes** to
blind-review; the original critique stands as a single-thread finding.
The five CRITICAL issues each rest on direct textual comparison between
the theorem statement and the verifier code, so a second blind reviewer
would inspect the same artifacts and reach the same conclusion. (The
finding is verifier-grounded, not consensus-grounded.)

---

## What this audit does NOT cover

- **Informal theorem-like claims elsewhere in the paper**: the Abstract,
  Section 1 "Key Contributions", and Section 3 prose contain phrases
  like "initialization-faithful", "matches NumPy", and similar
  qualitative assertions. Any of those that paraphrase Theorem 1
  inherit its overclaim; the author should propagate whichever repair
  route is chosen.
- **Empirical "approximate equality" statements in experimental
  sections**: e.g., "Δ-BER within X" or "NMSE matches baseline within
  Y dB". These are not theorems and are out of scope for `/proof-checker`.
  They belong to `/paper-claim-audit`.
- **Bibliographic correctness** (citation audit) — separate skill.

## Output artifacts

| File | Purpose |
|------|---------|
| `paper-tmlcn/PROOF_AUDIT.json` | Machine-readable verdict (this audit) |
| `paper-tmlcn/PROOF_AUDIT.md` | Human-readable narrative (this file) |
| `paper-tmlcn/.aris/traces/proof-checker/2026-05-16_run01/` | Trace directory |

`paper-tmlcn/main.pdf` is **not** submission-ready under
`assurance: submission` until Theorem 1's overclaim is resolved via
Route A or Route B.
