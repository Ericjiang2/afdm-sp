# GLOBAL20 continuation: compact classical structural state, no cleared new-inference claim

22 September 2026.

## Verdict

The new production report establishes useful structural-recovery headroom: GLOBAL20 recovers 31/43 selected triggered failures versus LOCAL20 10/43, with 15 rescues among 23 old iteration-resistant witnesses. This package does **not** independently replay those remote observations. It uses the attached RESULTS(20260922-132047).md as the production evidence source.

The independently derived compact state can evaluate the **same full all-slot replacement objective** without separate per-slot refits and without constructing candidate response columns one by one. A CPP-aware FFT correlation field and exact Schur add/delete algebra reproduce the reference decisions. This is potentially a substantial receiver-cost improvement, not a new posterior law.

Closest OLS-with-replacement literature already owns the inverse-Gram and add/delete-state mechanism. I do not recommend promoting this as the stronger new inference contribution. The findings do not establish that no future inference innovation exists; they show that the currently demonstrated structural headroom does not itself require additional posterior information.

## New numerical evidence (not production)

`verify_and_probe.py`:
- 720 independently refitted candidate scores in 6 fixtures (N=16,31,64; repeated delays; trivial/nontrivial CPP).
- Maximum FFT field discrepancy 7.64e-15.
- Maximum Gamma discrepancy against dense independent physical operators 7.27e-15.
- Maximum all-swap objective discrepancy 7.11e-14.
- All two-step structural decisions match the previous reference; final gain discrepancy zero.
- An orthogonal-active-model counterexample shows that the best added atom need not yield the best replacement.
- A separate 80-snapshot N96/P4 AFDM fixture uses synthetic truth-aligned means, NOT actual decoder APPs. An add-first heuristic matches the best candidate on 77/80 snapshots. Its objective is worse on 3/80, maximum regret .105404, and it never stalls when the full exchange improves in this set. This is not evidence of a large production benefit from the coupling correction, and contains no FER measurement.

`limiting_cases.py`:
- Known-waveform, nearly duplicate same-delay case: condition 1036.7, score discrepancy 1.08e-12.
- Zero mean case: no geometric score differentiation, as predicted.
- Extremely ill-conditioned, tiny-ridge case: unguarded score discrepancy .04751. The guarded API falls back to the direct control and matches its paths/gains. No numerical universal-stability claim.

`benchmark_reference.py`, final guarded source:
- One fixed synthetic N1024/P8 observation, max delay102, 25 Dopplers (-3 to3, step.25), 2575 candidate atoms, 2 accepted replacements.
- Seven warmed interleaved timing pairs, OPENBLAS_NUM_THREADS=1, OMP_NUM_THREADS=1.
- Mean structural work: direct reference .56523s; compact .02968s.
- Median structural work: direct .54286s; compact .02895s.
- Mean structural-plus-common-local-refinement: direct .68562s; compact .14216s.
- Median structural-plus-common-local-refinement: direct .65811s; compact .13346s.
- Both replacement geometries and the final local-refit geometry/gains match.
- Stored beta/K fields have 23175 complex entries (370800 bytes), plus the active state and FFT workspace. This is not process peak memory.
- These timings exclude TF, LDPC, production initialization, evidence serialization, and hardware differences. They cannot be subtracted directly from the reported production .718s.

The result files retain the individual synthetic-snapshot records and the interleaved timing pairs. Timings from a preliminary source version were not used to choose a configuration; the final benchmark was rerun after the numerical guard was added. See experiment_incidents.md.

## Files

- `DERIVATIONS.md`: exact model-space equations, CPP field, augmented-LS equivalence, and novelty boundary.
- `structural_state.py`: compact kernel; high-level guarded entry point `compact_exchange`.
- `geometry_exchange_control.py`: unchanged copy of the previous classical reference, for direct comparison/fallback.
- `verify_and_probe.py`, `limiting_cases.py`, `benchmark_reference.py`: reproducible independent calculations.
- `CODEX_VALIDATION.md`: one bounded equivalence-and-complete-cost validation, explicitly not a new-inference performance campaign.
- `*_results.json`: measured reference outcomes, not remote receiver outputs.
- `experiment_incidents.md`: retained unsuccessful or cautionary checks.
- `manifest.json`: content hashes and source evidence identity.

## Running

Requires Python, NumPy and SciPy. From this directory:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python verify_and_probe.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python limiting_cases.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python benchmark_reference.py
```

Example structural call:

```python
from structural_state import compact_exchange
from geometry_exchange_control import Path
result = compact_exchange(
    Y, pilot_plus_APP_mean, APP_variance,
    [Path(int(l), float(nu)) for l, nu in observed_geometry],
    c1=c1, c2=c2, ridge=noise_variance, max_delay=max_delay,
    max_edits=2,
)
# Feed result['paths'] through the unchanged GLOBAL20 local-refit schedule,
# then the same fresh TF20 / LDPC50 continuation. Do not regroup delays.
```

No true path, gain, codeword or error-count input is accepted by the structural algorithm. APP-derived mean/variance are working moments; no calibrated confidence is claimed. The original TF path-count-dependent prior, code-extrinsic interface, and fresh-round initialization must remain unchanged in production.
