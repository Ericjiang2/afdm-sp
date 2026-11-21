Active task: .trellis/tasks/09-22-tf-production-gap-audit

# Codex Astra brief: sum-mode / difference-mode dichotomy (fixed question, zero-receiver probe)

Written 2026-11-18 by Claude after Eric's decision ("Yes, run the probe"). Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`.
Read-only: write nothing to the repo. Your final message is the deliverable; it is saved by the CLI as
`.trellis/tasks/09-22-tf-production-gap-audit/research/astra-dichotomy-20261118.md`.
Model: `gpt-6.2-astra`.

## Role and limits
- Answer only the questions below. Do not propose research directions or paper framing.
- No receiver simulation, and no reading of any per-unit rows. Symbolic work and in-memory numerical toy models are allowed
  (small N, synthetic channels, simulated soft symbols).
- Mark every claim as derived, numerically checked or assumed.

## The candidate (from an external review; untested)
Consider a same-delay pair of atoms with operator coherence D = D_N(Δν). Assume phases are aligned and |D| < 1.
- The uncertainty block `u[[1, D],[D*, 1]]` has eigenvalues u(1 ± |D|):
  - a **sum mode**, the composite channel, with eigenvalue ≈ 2u;
  - a **difference mode**, a derivative/contrast direction, with eigenvalue `u(1 − |D|) → 0`.
- **CSTATE side (proved):** the scalar `uI` halves the sum-mode penalty. This creates the split reward that produces phantoms.
- **SBL side (the candidate):** exact Γ assigns almost no penalty to the difference mode. The mean-response Gram is also near-singular
  there (κ ≈ D). The precision along the difference mode is therefore about `(E+u)(1 − |D|) + λ` under full Γ, but
  `E(1 − |D|) + u + λ` under the scalar. With fixed-gain output, the near-collinear atoms then get large antiphase gains.
  The scalar "accidentally" regularises the contrast.

The candidate is consistent with existing evidence:
- `research-assets/res-20261018-03.md`: the "over-shrinkage" explanation was refuted; "Γ supplies needed regularisation".
- `research-assets/res-20261018-01.md`: an isotropic ridge added to full Γ recovers 92% of the SBL scalar/full FER gap. With the same
  uncertainty diagonal, keeping the off-diagonal term is worse.
- `experiments/sbl_split_diagnostic_20261118/out/deinlab_main_retry/RESULTS.md`: the expected-Gram update `eG` (ridge σ²P) gives 0 errors
  with both upstreams.

## Claude's design prediction (derived informally; to be checked)
A **difference-mode ridge** penalises only contrasts within co-delay groups and leaves the sum mode exact. For an exact uniform
duplicate, the equal split has zero contrast, so the ridge should **not** create a split reward. It should still regularise
near-collinear contrasts. Predictions:
- (i) In fixed-gain estimation, "full Γ + difference-mode ridge" matches or beats the scalar.
- (ii) In discrete support decisions, "`CODELAY` + difference-mode ridge" behaves like `CODELAY`: no added phantom preference.
- (iii) An isotropic ridge of size ~u helps (i) but re-introduces a split reward of order of the ridge in (ii).

## Questions
1. **Formalise.**
   - For a co-delay group of k atoms with block `u·[D_N(ν_j − ν_i)]`, define the sum and difference subspaces precisely, including for
     k > 2 and non-equal spacings.
   - Give the precision matrix `B̄ᴴB̄ + Γ + λI` restricted to a co-delay group under scalar, full and `CODELAY`. State where κ ≠ D matters.
   - Is the "difference-mode under-regularisation" statement correct as written? If not, give the correct version.
2. **Define the ridge.** Give a closed-form, cheap difference-mode regulariser R_dm ⪰ 0 for co-delay groups, with a scale (e.g., u or
   u|D|). Prove or refute:
   - (a) for exact duplicates with matched prior pushforward it leaves the profiled objective split-invariant, so the duplicate reward
     in your Eq. (3) stays at the full-Γ value δ = λ;
   - (b) it restores difference-mode precision to the order of the scalar's.
   - Also state what it does at finite spacing (Eqs. (12)–(14)).
3. **Toy model, in memory.** Build a small model: N ≈ 64–256, AFDM or a generic Doppler-shift dictionary, one strong path, one weak path
   at another delay, and one or two grid atoms near the strong path at Δν ∈ {0.05, 0.1, 0.25} bins. Simulate soft symbols as
   x̄ = x − e with e ~ CN(0, diag(v)) and heteroscedastic v, then average over random draws. Compare four variants: scalar `uI`;
   full/`CODELAY`; full + isotropic ridge u; full + R_dm.
   - **Task A, support decision:** in the first exchange, measure the duplicate-versus-weak preference and the split reward.
   - **Task B, fixed-gain estimation:** with all near-neighbour atoms active (SBL-like overcomplete support), estimate gains once with
     the variant's precision. Report the composite-channel error ‖Ĥ − H‖_F/‖H‖_F, the antiphase magnitude (|ĥ₁| + |ĥ₂|)/|ĥ₁ + ĥ₂|, and a
     detection proxy of your choice.
   - **Report:** does the toy reproduce the reversal (scalar better than full in Task B; full better in Task A)? Do predictions (i)–(iii)
     hold? Give numbers per Δν.
4. **Receiver-level predictions** (to be pre-registered before any replay). For a later replay on the saved 200 SBL keys and the CSTATE
   units, which arm ordering do you predict under fixed-gain and joint SBL detectors and in CSTATE? Give a point value and a range where
   the theory can fix one; otherwise say it cannot.
5. **Prior art.** Only if confident: is this dichotomy, or the difference-mode ridge, a known result (e.g., in EIV regression, grouped
   ridge, or super-resolution with near-collinear atoms)? Otherwise answer "uncertain".

## Claude's predictions (written before your answer)
- The toy reproduces the reversal: .65.
- In the toy, prediction (i) holds (R_dm matches or beats the scalar in Task B): .60.
- (ii) holds (R_dm leaves Task A equal to full/`CODELAY`): .80.
- (iii) holds (an isotropic ridge re-introduces a split reward in Task A): .75.

## Output format (final message, English, ≤ 160 lines)
`## Q1` … `## Q5`, then `## Verdicts`, one line each:
- dichotomy statement: correct / corrected / wrong;
- R_dm: split-invariant (yes / no);
- toy reversal: reproduced (yes / no);
- predictions (i)–(iii): holds / fails.

Then `## Limits`.
