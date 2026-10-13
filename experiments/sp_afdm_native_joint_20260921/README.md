# Native tensor-free joint SP-AFDM continuation — 21 September 2026

This is a research reference and bounded Codex specification, not a validated submission-ready performance claim. Read `docs/RESEARCH_VERDICT.md` and `docs/CODEX_HANDOFF.md` first. The previous full-physical/sparse-inference campaign remains stopped.

## Dependencies and source boundary

The user already owns `SP_AFDM_Design_Freeze_20260920.zip`. Point to its extracted root (the directory containing `src/receiver.py`, `src/physical.py`, and `upstream/`) using:

```bash
export SPAFDM_BASELINE_ROOT=/absolute/path/to/SP_AFDM_Design_Freeze
export CUDA_VISIBLE_DEVICES=''
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD/src:$SPAFDM_BASELINE_ROOT/src:$SPAFDM_BASELINE_ROOT${PYTHONPATH:+:$PYTHONPATH}"
python tests/test_twofft.py
python tests/test_contractions.py
python tests/test_checkpoint_contract.py
python tests/audit_outputs.py
```

The delivered numerical sources were tested against the original frozen package. The corrected local numerical source `31d5ec0d` and remote Stage-2 arrays were NOT available in this session. Codex should retain its corrected evidence/timing interfaces and audit numerical compatibility before new local observations. The original numerical package and third-party papers are not redistributed here.

Core implementation:

- `src/twofft.py`: `TimePathOps`, exact path norms, two-/four-transform same-map scalar joint inference, optimized equivalent physical refit.
- `src/native_twofft.py`: observed-input-only native two-round pipeline, no I1 outer loop.
- `tests/test_twofft.py`: independent dense and unitary checks, refit equivalence, production-size interface.
- `tests/screen_fair_controls.py`: reference integration for EP/PBiGaBP with the shared optimized refit.
- `tests/screen_point_clean.py`: same-soft-CE gain adaptation/variance controls.
- `tests/benchmark_fourfft.py`: strong same-map four-transform timing control.

`fast_bilinear.py`, `block_bilinear.py`, `joint_tangent*.py`, and their screens are rejected/diagnostic research alternatives, NOT additional proposed arms to sweep.

## Existing results

`results/` contains 28 exploratory radio observations, many paired/reused method calls, 292 audited saved decisions, and independent algebraic comparisons. The final native screen has only four observations at each of 6 and 7 dB. Do not pool these with the user's 84 staged observations. The serialized user RESULTS.md is represented by its hash/provenance in the manifest, not relabeled as a new replication.

Screen scripts reproduce historical exploratory namespaces; they are NOT the new local experiment driver. Follow the new prospective namespace and bounded 70/112-call plan in `docs/CODEX_HANDOFF.md`. Preserve interrupted and failed-launch logs as implementation evidence, not scientific samples.

The audit script reads the old upstream LDPC cache and the archived arrays. It does not import a receiver or use the true channel to make decisions. Runtime measurements are specific to their process and host. The late competent four-FFT control produces identical decisions and nearly the same kernel runtime; no large two-versus-four FFT headline is supported.

No convergence, true posterior, first-ever-FFT, complete-process O(NP)-memory, or universal superiority claim is made. The remaining experiment is whether the native tensor-free joint implementation has a useful complete-cost operating regime against strong coded EP and PBiGaBP.
