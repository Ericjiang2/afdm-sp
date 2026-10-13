# Research: CSTATE20 reference contract

- Query: Read the supplied CSTATE20 validation contract and reference implementation, then compare its structural traversal/tie/acceptance and shared local stage with the local `geometry_reopen.py` implementation.
- Scope: mixed (local code plus supplied reference package; external references only as named in the supplied derivation)
- Date: 2026-09-22

## Findings

### Fixed validation contract

- Reference: `/Users/guoyikun/Downloads/TF_GLOBAL_structural_state_investigation_20260922.zip`, members `tf_round3_research/CODEX_VALIDATION.md`, `structural_state.py`, `geometry_exchange_control.py`, `verify_and_probe.py`, `limiting_cases.py`, `DERIVATIONS.md`.
- `CODEX_VALIDATION.md:5-7` defines CSTATE20 as an exact classical GLOBAL20 control, forbids changing TF_J20_R2, candidate bank, scorer, path count, grid, prior, iteration budget, trigger, acceptance threshold or decoder, and forbids new observations/SNR points.
- `CODEX_VALIDATION.md:13` freezes exactly 75 IDs: 43 nonzero-syndrome 6.5 dB observations plus the first 32 zero-syndrome controls; truth cannot select frames, atoms, slots, priors, thresholds or decisions.
- Stage 0 is zero receiver calls (`CODEX_VALIDATION.md:15-25`): compare every valid slot×atom score, validity mask, accepted/no-improvement result and direct refit on 145 sealed GLOBAL entered states. If full-grid or decision qualification fails, stop before receiver calls.
- Stage 1 is exactly 225 wrapper calls over LOCAL20, GLOBAL20 and CSTATE20 (`CODEX_VALIDATION.md:27-35`). CSTATE20 is compact exchange with at most two replacements, followed by GLOBAL20's unchanged local-refit and fresh TF20/LDPC50 continuation.
- Exact realization acceptance requires the same discrete replacement sequence and qualified continuous outputs after the shared local stage, identical final decisions for all 75 observations, and mean complete added CSTATE20 branch time `<=0.6 s` over the 43 triggered observations (`CODEX_VALIDATION.md:56-63`). Expected replay checks are 31/43 triggered rescues, 15/23 old-witness rescues, and 32 successful controls; these are equivalence checks, not new performance claims.

### API and frozen objective

- `geometry_exchange_control.py:21-37` exposes `Path(delay:int, doppler:float)` and `ExchangeResult`; `reopen_geometry(...)` is the direct fixed-cardinality control (`:82-100`).
- `geometry_exchange_control.py:39-79` defines the positive-chirp IDAFT, CPP-aware path responses, Gamma cross terms, and system objective. The frozen normal system is `Q = BᴴB + Gamma + ridge I`, `b = BᴴY`, `h = Q⁻¹b`, with objective `||Y||² - bᴴh`.
- `DERIVATIONS.md:7-13` states the same contract in notation: `m=p+mu`, diagonal `V=diag(v)`, `A=BᴴB+Gamma+lambda I`, `b=Bᴴy`, `h=A⁻¹b`, and `Q_S=||y||²-bᴴA⁻¹b`. The inverse is an optimization sensitivity, not a posterior covariance or TF scalar gain variance.
- For a candidate atom, `DERIVATIONS.md:17-38` gives `k=Bᴴphi+Gamma_(S,a)`, `beta=phiᴴy`, `d=||m||²+sum(v)+lambda`, `u=Ck`, `s=d-kᴴCk`, `g=beta-kᴴh`, and the exact joint replacement score:

  `Q_(S-i+a) = Q_S - |g|²/s + |h_i-u_i g/s|² / (C_ii + |u_i|²/s)`.

  This is a joint add/delete score; an add-only gain followed by an independent deletion penalty is not equivalent.
- `structural_state.py:24-57` implements `CPPField`: exact CPP-aware FFT correlations for every declared delay/Doppler bank, delay-major then Doppler-major, with no rounding, truncation, circular-CPP shortcut or dense response dictionary.
- `structural_state.py:69-104` implements the compact state and all slot×candidate scores. `beta` is a length-M candidate vector and `K` is a P×M cross block; one `C@K` produces all candidate sensitivities.
- `DERIVATIONS.md:42-62` gives the extended waveform and finite CPP correlation identity; `DERIVATIONS.md:64-70` says beta remains fixed while m,V and the bank are fixed, only the changed K row is refreshed after a swap, and two accepted swaps require P+2 field calls (P+1 initial fields plus one refresh).

### Fallback and numerical qualification

- `structural_state.py:132-191` validates moments/geometry, builds the compact field/state, guards `cond(A)>1e8`, scores the full bank, applies the direct strict-improvement convention, refreshes only the changed K row after an accepted swap, and asserts compact/direct objective agreement at `1e-7*(1+abs(score))`.
- `structural_state.py:194-221` exposes `compact_exchange(...)`. It catches only `FloatingPointError` and `LinAlgError`, then calls the unchanged observed-only `reopen_geometry(..., local_passes=0)` and marks `numerical_fallback=True`; discarded compact work remains part of elapsed time. Assertion failures for algebra/direct-winner mismatch are deliberately not swallowed.
- `CODEX_VALIDATION.md:23,46` requires `atol=2e-9`, `rtol=1e-8` when confirmed by the source contract, explicit near-tie parity, and counting fallback calls/cost. The `1e8` condition threshold is an engineering guard, not a floating-point proof.
- The independent fixture assertions in `verify_and_probe.py:27-75` are tighter: field, Gamma and all-swap objective errors `<1e-10`, final gain error `<1e-9`; the saved run reports field `7.64e-15`, Gamma `7.26e-15`, all-swap objective `7.11e-14`, final gain `0`, 720 score comparisons, and six equal sequential-winner fixtures (`verification_stdout.txt`).
- `limiting_cases.py:9-50` and `limiting_case_results.json` show the boundary: normal same-delay and zero-mean cases pass (`1.08e-12` and `0` max objective discrepancy), while tiny ridge `1e-12` with nearly duplicate same-delay paths has condition `8.96e13` and unguarded discrepancy `0.04751`; guarded fallback reproduces control paths and gains exactly. Positive Schur slack alone is insufficient.

### Traversal, ties, acceptance, and local-stage comparison

- Reference control traversal is chunk-major then slot-major (`geometry_exchange_control.py:137-153`): for each candidate chunk, each slot selects its chunk argmin, then the global winner is updated only if `best - value > 1e-10*(1+abs(best))`. `structural_state.py:115-129` makes this same order explicit in `select_control_order` and warns that sorting or unconditional argmin changes near ties.
- The local implementation computes the same candidate bank (delay-major, Doppler-major) and score blocks (`experiments/tf_geometry_reopen_20260922/geometry_reopen.py:142-213`), and uses the same `1e-10` strict improvement guard (`:161-162`). It also uses the same duplicate rule (`:132-136` and `:209-212`) and preserves invalid duplicate scores behind a validity mask.
- The local implementation's actual accepted winner is selected by `np.lexsort((doppler, delay, slot_id, score))` and `ranked[0]` (`geometry_reopen.py:214-240`), whereas the reference winner is selected during chunk→slot traversal. These are equivalent away from ties, but can differ when two valid scores are equal or when a later score improves the incumbent by less than the strict threshold: lexsort prioritizes lower slot, then delay/Doppler, while the reference keeps the first traversal winner. This is the main near-tie qualification risk; compare full score/valid arrays and accepted slot/atom rather than relying on truth-rank/top-K ordering.
- Local `geometry_reopen.py:123-136` rejects essentially duplicate input paths up front. The reference contract allows repeated delays and excludes only essentially identical same-delay atoms as replacements (`geometry_exchange_control.py:9-12`; `CODEX_VALIDATION.md:39-42`). Confirm sealed production inputs contain no duplicate initial atoms before treating this API difference as harmless.
- The local code uses production `Channel`/`TimePathOps` responses and `projected_variance` (`geometry_reopen.py:43-77`), while the reference control uses explicit CPP response/Gamma identities (`geometry_exchange_control.py:39-79`). CSTATE parity therefore requires full observed-array qualification, not only fixture-level agreement.
- Shared local refinement is otherwise aligned: after structural edits, both freeze window centers at the reopened geometry, use two passes by default, per-slot Doppler bounds center ±0.75 clipped to [-3,3], duplicate rejection, `minimize_scalar(method='bounded', xatol=.002, maxiter=16)` (`geometry_reopen.py:275-323`; reference control `geometry_exchange_control.py:160-179`). CSTATE's compact function deliberately stops before local refinement (`structural_state.py:135-139`); the caller must pass compact or fallback paths through this unchanged local stage and then the fresh TF/LDPC continuation.

### Complete segmented timing contract

- `CODEX_VALIDATION.md:48-54` requires charging field construction, every candidate score and rejection, fallback work, local trials, TF, LDPC, message handling and serialization; ready time, branch completion and wrapper completion must be stored separately, with 0.5 s/1.0 s deadline outcomes using the same baseline origin/fallback convention. Retain path/score/validity/gain/local/final-state/LLR/decision/syndrome and per-stage durations.
- The supplied synthetic benchmark is only a timing reference, not production evidence (`benchmark_results.json` scope). At N=1024, P=8, max delay 102, bank size 2,575, two edits and 10 field calls, it reports direct structural mean `0.56523 s`, local `0.12039 s`, combined `0.68562 s`; compact structural `0.02968 s`, local `0.11248 s`, combined `0.14216 s`. It has no TF, decoder or production serialization, so these numbers cannot satisfy the production timing gate by themselves.
- Do not optimize or omit stages: no candidate pruning, top-K warm start, reduced logging, extra edits, changed tolerance, changed local schedule, or hidden fallback. `CODEX_VALIDATION.md:41-46,50-52` makes these exclusions explicit.

### Reusable points and named references

- Reusable: fixed-q compact sufficient state `(A,C,b,h,beta,K)`, exact CPP FFT field, one-row K refresh, full-bank validity mask, direct observed-only fallback, and unchanged shared local/TF/LDPC stages.
- `DERIVATIONS.md:72-87` places the construction in classical augmented cardinality-constrained least squares and names Leibovitz & Giryes, IEEE TSP 68 (2020), arXiv:2004.06661; JCCD-VALSE, arXiv:2107.07101; data-aided evolving-grid SBL for SP-AFDM, arXiv:2607.18881; and Tipping & Faul (AISTATS 2003). These are references cited by the supplied derivation, not independently checked here.

## Caveats / Not Found

- This was a read-only contract comparison. No receiver, decoder, CSTATE20 validation, production-array qualification, or new timing run was executed.
- The supplied fixture/benchmark proves reference algebra and synthetic behavior only. It does not establish production parity, FER, posterior calibration, or novelty.
- The local `lexsort` winner path must be resolved by an explicit near-tie parity check before claiming exact CSTATE20/GLOBAL20 realization; the validation contract says not to silently substitute one ordering for the other.
