Active task: .trellis/tasks/09-22-tf-production-gap-audit

# Codex Astra brief — does the co-delay uncertainty block generalize beyond AFDM? (fixed mathematical question)

Written 2026-11-18 by Claude for Eric. Working directory:
`/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation`. Read-only: write nothing to the repo. Your final
message is the deliverable; Eric saves it as `.trellis/tasks/09-22-tf-production-gap-audit/research/astra-generality-20261118.md`.
Model: `gpt-6.2-astra`. Pass `-m` on any resume and check the log `model:` line.

## Role and limits
Answer only the questions below. No research directions, paper framing or experiment proposals. Zero receiver simulation; symbolic work
and small in-memory numerical checks are allowed. Mark every claim **derived**, **numerically checked** or **assumed**. If a question is
ill-posed, say so in one paragraph and answer what can be answered.

## Background (established; cite, do not re-derive)
- Your own earlier answer, `.trellis/tasks/09-22-tf-production-gap-audit/research/astra-producer-consumer-20261118.md`, Part B:
  - For AFDM with integer delays, sufficient CPP, even N, 2Nc₁ ∈ ℤ and diagonal symbol-error covariance V = diag(v), the projected
    uncertainty Γ_ij = Σ_n v_n ⟨U_i a_n, U_j a_n⟩ satisfies Γ_ij = u·D_N(ν_j − ν_i) for same-delay pairs, for any v (u = Σv).
  - Cross-delay entries are e^{2πi c₁(ℓ_i² − ℓ_j²)} D_N(z) v̂[d], with z = Δν + 2Nc₁d.
  - Claude re-checked both numerically against the frozen `experiments/sp_afdm_frozen_20260920/src/physical.py`.
- Your decision-boundary chain (`astra-idea-dialogue.md` Eqs. (3), (8)–(10), (12)–(14)) is written in terms of Γ only.
- Relevant prior work sits on integer delay–Doppler grids, where same-delay atoms are orthogonal: Wang et al. TCOM'22 (OTFS-type DD grid,
  full expected Gram), Mishra TWC'21 (OTFS), Kanazawa (OTFS), Zheng (AFDM). See
  `literature-uncertainty-model-check-20261118.md`.

## Candidate claims (Claude's quick sketch, unverified — prove or refute each)
- **C1.** For any orthonormal modulation basis {a_n} and time-domain path operators U_p = (cyclic delay ℓ_p)·(Doppler modulation ν_p),
  constant variance v ≡ v̄ gives Γ = (u/N)·[tr(U_iᴴU_j)]. By completeness (Σ_n a_n a_nᴴ = I) this is independent of the modulation.
  So the same-delay block u·D_N(Δν) appears under constant variance in **any** such system: OFDM with Doppler, OTFS, AFDM,
  single-carrier, ODDM.
- **C2.** Exactness for **heteroscedastic** v on same-delay pairs requires the basis to be flat in time, |a_n[t]|² = 1/N for all n and t.
  This holds for AFDM chirps and for OFDM subcarriers (time-domain complex exponentials). It fails for OTFS with a rectangular pulse,
  whose DD basis functions are not constant-modulus in time. Under OTFS the same-delay entries then depend on how v is distributed
  over the DD grid.
- **C3.** On integer Doppler grids (Δν ∈ ℤ \ {0}), D_N(Δν) = 0, so the same-delay block vanishes regardless of modulation. This is why
  integer-grid treatments (Wang TCOM'22) see a diagonal uncertainty term.

## Questions
- **G1.** Prove or refute C1. State the exact operator model (CP or CPP, cyclic or linear delay, where the Doppler phase is applied)
  under which it holds. Note any modulation-specific phase factors, such as AFDM's chirp-periodic prefix.
- **G2.** Prove or refute C2.
  - For OFDM with Doppler (time-domain basis a_n[t] = e^{2πi nt/N}/√N, CP ≥ ℓ_max), give Γ_ij for same-delay and cross-delay pairs with
    heteroscedastic v, in the same form as your B1/B2.
  - For OTFS (M×N grid, rectangular pulse, CP per frame), give the same-delay Γ_ij and say what replaces u·D_N(Δν) when v is
    heteroscedastic. Is there still a single-scalar sufficient form, or a bound on the deviation?
  - Numerically check at small sizes (e.g., N = 64 for OFDM; M = 16, N = 8 for OTFS) with random heteroscedastic v and fractional
    Doppler.
- **G3.** Prove or refute C3 for OFDM and OTFS. Does the cross-delay resonance you found for AFDM (|d| = 1, Δν = −5) have an analogue
  in OFDM or OTFS?
- **G4.** Given G1–G3, which parts of your decision-boundary results (split reward Eq. (3), window Eq. (8), finite-spacing Eqs. (12)–(14))
  transfer unchanged to OFDM-with-Doppler and to OTFS? Which need the heteroscedastic exactness of G2? One table.

## Output format (final message, English, ≤ 150 lines)
- `## G1` … `## G4`.
- `## Verdicts`, one line each: C1 proved / refuted (with conditions); C2 proved / refuted per modulation; C3 proved / refuted.
- `## Limits`.
