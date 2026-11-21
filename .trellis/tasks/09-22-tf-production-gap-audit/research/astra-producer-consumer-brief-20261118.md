Active task: .trellis/tasks/09-22-tf-production-gap-audit

# Codex Astra brief — two fixed mathematical questions (no direction-setting)

Written 2026-11-18 by Claude for Eric. Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`. Read-only: write nothing to the repo. Your final
message is the deliverable; Eric saves it as `.trellis/tasks/09-22-tf-production-gap-audit/research/astra-producer-consumer-20261118.md`.
Model: `gpt-6.2-astra` (pass `-m` on any resume and check the log `model:` line).

Role and limits: answer only the two questions below. Do not propose research directions, paper framing or experiments beyond the
falsification test asked in A4. If a question is ill-posed, say so in one paragraph and answer what can be answered. Zero receiver
simulation; symbolic work and small in-memory numerical checks are allowed. Mark every claim **derived**, **numerically checked** or
**assumed**.

## Part A — is "producer–consumer split invariance" a valid formal statement?

### Candidate (Claude's synthesis, untested, confidence L–M)
Pipeline steps fall into two roles.
- A **producer** outputs a support with gains, for example scalar-Γ or full-Γ SBL, or a CSTATE support exchange.
- A **consumer** takes that support and updates the gains and symbols: the detector gain interface.

The candidate says the split bias of the scalar uncertainty approximation causes damage only when **both** the producer emits split
representations **and** the consumer is not invariant to splitting. Either end being invariant suffices.

### Established facts (cite, do not re-derive unless you find an error)
- Exact uniform duplication with coordinate prior 1/(kP) leaves the initial H and the aggregated prior unchanged. Under it:
  - fixed-gain and expected-Gram (`eG`) gain updates are exactly invariant (400/400 cases, LLR difference ~1e-13);
  - native `point` and `joint` updates are not invariant (0/400; first-update relative H difference median 0.4–1.1).

  Sources: `experiments/sbl_split_diagnostic_20261118/out/deinlab_main_retry/RESULTS.md`, `experiments/sbl_freeze_replay_20261020/REPRESENTATION_SUMMARY.md`,
  `.trellis/tasks/10-20-sbl-freeze-replay/research/representation-invariance.md`. The `eG` ridge is α = σ²P; it becomes kα under duplication, so the
  aggregated normal equations are invariant (`experiments/sbl_freeze_replay_20261020/gram_block.py::solve_gain`).
- FER on 200 old keys (`experiments/sbl_three_mode_20261020/SUMMARY.md`; `eG` from the diagnostic G2):

  | upstream SBL | fixed | point | joint | eG |
  |---|---|---|---|---|
  | scalar Γ (`L-diag`) | .020 | .200 | .115 | 0 errors |
  | full Γ (`L-cov`) | .075 | .055 | .010 | 0 errors |

  The full-Γ fixed-gain loss is attributed to gain over-shrinkage (`research-assets/res-20261018-02.md`), not to splitting.
- **Natural producer outputs are not exact duplicates.**
  - On-grid E-3 SBL (0.25-bin Doppler grid): 99.9% of scalar-SBL co-delay pairs lie on true delays, with median |Δν| = .25, i.e. one grid step
    (`research-assets/res-20261017-03.md`). These pairs may be interpolating an off-grid Doppler rather than duplicating.
  - Off-grid E-3b: 58% of scalar-SBL co-delay pairs have |Δν| < .1 (`research-assets/res-20261017-04.md`).
  - Merging co-delay atoms changes the operator by a median 24% (scalar) and 15% (full).
- CSTATE: the scalar-score discrete argmax exchange both produces the support and consumes the split reward; your 11-11 chain
  (`astra-idea-dialogue.md` Eqs. (3), (8)–(10), (12)–(14)) gives its decision boundary. Mainline = `CODELAY` support scoring + native
  `scalar_joint` downstream.

### Questions
- **A1.** State the candidate as a precise proposition: what "invariant producer" and "split representation" mean, and what "no split damage"
  means — relative to which reference representation? Is it trivially true for exact duplicates once the consumer is invariant? If so, say
  where the non-trivial content lies.
- **A2.** For **near-duplicates** (Δν > 0), does an invariant consumer stay approximately invariant? If so, give a bound on the change of
  its output in terms of the coherence 1 − |D_N(Δν)| or your Eqs. (12)–(14). Separate genuine local-basis interpolation of an off-grid
  path (the .25-bin on-grid pairs) from spurious splitting. Can the proposition distinguish them at all?
- **A3.** Fill this table: for each producer × consumer cell, does the proposition predict "no split damage", "split damage possible", or
  is it silent (e.g., differences in fitted-H quality such as full-Γ over-shrinkage)? Producers: scalar on-grid SBL; scalar off-grid SBL;
  full SBL; CSTATE scalar; CSTATE `CODELAY`. Consumers: fixed, point, joint, eG, native `scalar_joint`. Then check the table against
  the FER facts above and list any cell that contradicts it.
- **A4.** Which estimand would falsify the proposition on fresh frames? (Expected: the interface interaction "scalar upstream's improvement
  joint → eG minus full upstream's improvement joint → eG".) What result would refute it? Note the confound: the 10-21 fresh-frame
  validation found `eG` improves log-loss by ~12.7% for **both** upstreams (`experiments/sbl_freeze_replay_20261020/FRESH_COHORT_SUMMARY.md`).
- **A6. Hardest-card check.** Run this check before the proposition is adopted. Answer for each card what the proposition says,
  or state explicitly that the card lies outside its scope.
  - **Card 1.** The SBL ranking reversal (above).
  - **Card 2.** At ρ = .3, with **true delays given**, the channel-estimate MSE remains 4.5–5.3 dB above the constrained MCRB
    (accepted `research-assets/res-20261016-02.md` / `res-20261016-03.md`). Its FER cost is only 0.12–0.55 dB to genie CSI.
  - **Card 3.** The slot-mismatch Q2 result (`research-assets/res-20261118-04.md`, draft). With spare slots (cap 12 vs 8, same
    common-trigger units) the full-vs-scalar rescue gap shrinks to D12/D8 = .763 [.716, .811]. That is neither the "no change"
    nor the "vanishes" case.
    - The narrowing saturates: cap 8 → 10 gives .851, cap 10 → 12 gives .998 (secondary reads).
    - It is concentrated at ρ = .5, where the gap is small (D8 ≈ 7 pp, ratio ≈ .52–.55). At ρ = .3 (D8 ≈ 43–50 pp) the ratio is ≈ .87–.95
      (per-cell descriptive values, no per-cell CI).
    - In the stratum where cap 12 already holds a true delay that cap 8 missed, the ratio is .696; elsewhere it is .796.
    - Scalar phantom-first share: 93.8% at cap 8, 99.8% at cap 12.

    Source: `experiments/slot_mismatch_20261019/out/RESULTS.md`. What does your Eq. (8)-based answer to A1–A3 imply for these
    numbers, and could pre-emption alone account for them?

  State the resulting scope in one sentence, e.g. "support acquisition only".
- **A5.** Only if confident: is this a restatement of known results (reparameterization or representation invariance in Bayesian
  inference; identifiability)? Name the closest known result, or say "unsure".

## Part B — the `CODELAY` exactness proposition (verify or refute)

Source of the claim: `tcom-narrative-skeleton-20261118.md` lines 29–40 (Proposition 1), from another session; never machine-verified.
Parameters: same directory, line 73 (N = 1024, CPP length 102, c₁ = 5/2048, c₂ = (√2 − 1)/(2N²)).
Claim:
1. Because DAFT basis columns have constant modulus 1/√N, every diagonal and same-delay entry of the projected uncertainty matrix
   satisfies Γ_ij(v) = u·D_N(ν_j − ν_i) **for any non-uniform v ∈ ℝ₊ᴺ**, with u = Σ v_n.
2. The difference Γ(v) − Γ_codelay(u) is confined to different-delay pairs, with magnitude |D_N(ν_j − ν_i + 2Nc₁Δℓ)|·|v̂[Δℓ mod N]|
   ("double suppression"); state the precise bound.

Context: res-20261118-03 reports 0:0 FER discordance between `CODELAY` and heteroscedastic `FULL` on 13,600 keys. Its synthetic parity
gate was checked against **constant-variance** `FULL`, and there were 155 decoded-hash changes on jointly failed frames.

- **B1.** Prove or refute claim 1. State all premises (error decorrelation across symbols, CPP, parity of N, 2Nc₁ ∈ ℤ, integer delays).
  Numerically check at N = 1024 with random heteroscedastic v and fractional ν.
- **B2.** Prove or refute claim 2 and give the bound. Evaluate it numerically for the project's delay range (0..102) and Doppler range
  ([−3, 3]). Do the 155 hash changes fit "cross-delay residual only"? Answer qualitatively; you do not have the rows.
- **B3.** Which premises fail for fractional delays? One paragraph; no new derivation required.

## Output format (final message, English, ≤ 180 lines)
- `## A` — A1–A5, including the A3 table.
- `## B` — B1–B3.
- `## Verdicts` — one line each:
  - producer–consumer proposition: valid as stated / valid with stated restrictions / invalid;
  - Proposition 1 claim 1: proved / refuted;
  - Proposition 1 claim 2: proved with bound / refuted.
- `## Limits`.
