# Experiment Integrity Audit — AFDM SP-Joint Learned-Receiver Thesis (RETRY v2)

## IMPORTANT — READ FIRST

Files are delivered as a **single bundled archive attachment**. Before anything else:

1. List every file in the attachment bundle (in your sandbox; typical path `/mnt/data/...`).
2. If you see a `.zip`, `.tar`, `.tar.gz`, or any archive-like file, **unpack it** into your working directory and re-list.
3. Read each file you find. The bundle should contain approximately 20 files matching the list in the "Files expected" section below. If your listing disagrees, SAY SO — do not assume files are missing and fail out; attempt one more unpack / directory walk first.

If, after a genuine attempt to unpack and list, you truly cannot access the content, state this and STOP — do not speculate.

## Project briefing

UoG/UESTC BEng Final-Year-Project thesis on an AFDM (Affine Frequency Division Multiplexing) receiver with superimposed pilots (SP). Baseline: classical joint `joint_omp_mp_iterative` in `afdm_baselines.py` — OMP-once support init + LS/MP-BP inner loop (Algorithm 1). Contribution: 1,041-parameter learned "C2-rel F2-P" support-refinement head (pair-encoder MLP + order-invariant pool + scorer MLP), invoked twice at outer-iteration t=0 to append top-K_add off-support candidates, then the unmodified classical inner LS/MP-BP loop runs. Forward kernel `classical_joint_unrolled.py` is bit-exact against NumPy `joint_omp_mp_iterative` when superparameters are frozen (see `verify_classical_unrolled_matches_numpy.py`). Training: 4B cached trainer (N=512, UWA-like sparse DD channel, QPSK, ρ_p=0.5). BER reported against true transmitted bits at SNR ∈ {0,5,10,15,20,25} dB, 80–500 frames/SNR.

## Task

Judge experimental integrity ONLY. Do not re-score writing quality. Use the 6-point checklist (A-F below). Cite exact `file:line` refs.

## Files expected in the bundle

Scripts:
- `afdm_env.py` — channel simulator + true-bit injection
- `afdm_baselines.py` — classical `joint_omp_mp_iterative` (the teacher)
- `classical_joint_unrolled.py` — learned forward kernel
- `eval_classical_joint_unrolled.py` — main BER/NMSE eval
- `run_classical_baselines_python.py` — reproduces NumPy baseline
- `loop13_iter_convergence_probe.py` — §3 iter-convergence table
- `loop13_new_baselines_eval.py` — §3 new baselines
- `loop13_support_recall_probe.py` — §3 support recall
- `headroom_decomposition_probe.py` — §3 headroom decomposition
- `compute_heldout_metrics.py` — held-out metrics helper
- `_merge_snr20_300f.py` — mixed-frame-budget merge helper
- `verify_classical_unrolled_matches_numpy.py` — bit-exactness check

Result JSONs:
- `outputs_loop13_4B_full_results.json`
- `outputs_loop13_iter_convergence_4B_merged_results.json` (renamed from `outputs_loop13_iter_convergence_4B_merged/results.json`)
- `outputs_loop13_support_recall_recall_by_snr.json` (renamed)
- `outputs_loop13_headroom_4B_big_headroom_results.json` (renamed)
- `outputs_loop13_new_baselines_500f_results.json`
- `outputs_loop13_2B_snr0_5_results.json`

Paper claims:
- `Abstract.tex`
- `Section1.tex`
- `Section3.tex`
- `Section4.tex`
- `CLAIMS_FROM_RESULTS.md`

## Audit checklist

### A. Ground-Truth Provenance (CRITICAL)
For the eval scripts, trace `bits_sim → model → bits_hat → ber(bits_sim, bits_hat)`:
1. Are "true bits" the simulator's injected bits, or bits the model-under-test spat out?
2. For "support recall", is `true_support` the physical taps from `afdm_env.py`, or inferred from the model?
3. For NMSE, is reference `h_true` the simulator-drawn channel, or model's `h_hat`?
4. Any metric computed against a prior-round `h_hat` of the same model without being labelled "proxy"?

**FAIL** if any headline claim uses model-derived reference without proxy labelling.

### B. Score Normalisation
1. Any score divided by max/min/mean of the model's OWN output?
2. "Recall"/"precision" against top-K chosen from model's own confidence?
3. Raw counts (errs/bits, hits/total) reported alongside any ratio?

**FAIL** if normalisation denominator comes from prediction statistics.

### C. Result-File Existence & Number Matching
Open the thesis (`Abstract.tex`, `Section1.tex`, `Section3.tex`, `Section4.tex`) and `CLAIMS_FROM_RESULTS.md`. For each numeric claim (BER, NMSE, gain-in-dB, iter-convergence, mixed-frame-budget), trace to the specific JSON. Confirm:
1. File exists, non-empty, well-formed
2. Key path (arm → snr → iter → metric) exists
3. Number matches to 2 sig figs
4. `_merge_snr20_300f.py` does what §3 says

**FAIL** if any number doesn't match or any claim cites a missing file/key.

### D. Dead-Code Detection
1. Any metric/feature function defined but never called in the eval pipeline that produced the headline JSONs?
2. Training-time-only ranking (rank-hinge, BCE) vs deployment top-K_add — is the DEPLOYMENT path what produced the headline numbers?
3. Any fallback that silently bypasses the learned head yet still counts as "learned" arm?

**WARN** on unused functions; **FAIL** if learned-arm BER is actually classical-arm BER in disguise.

### E. Scope vs Language
Scan `Abstract.tex`, `Section1.tex`, `Section4.tex` for "comprehensive/extensive/robust/general/across-the-board":
1. How many channels/scenarios tested?
2. How many training seeds? Eval seeds per SNR? Frames per SNR?
3. Are 95% CIs reported at BER ≈ 1e-4? (500 frames × ~1000 bits ≈ 50 errors ≈ 14% relative σ)
4. Does wording exceed evidence?

**WARN** on scope inflation; **FAIL** if Abstract promises fundamentally broader than tested.

### F. Evaluation-Type Classification
Pick one: `real_gt` / `synthetic_proxy` / `self_supervised_proxy` / `simulation_only` / `human_eval`. One sentence evidence.

## Output format (exact)

```
### A. Ground-Truth Provenance: PASS | WARN | FAIL
Evidence: <file>:<line> — <1-2 sentences>
Details: <only if WARN/FAIL>
```
…same for B through F…

```
## Overall Verdict: PASS | WARN | FAIL
## Integrity Status: pass | warn | fail
## Evaluation Type: real_gt | synthetic_proxy | ...
## Claim Impact
- Abstract BER/NMSE: supported | needs_qualifier | unsupported
- §3 iter-convergence (mixed 80/300 frame): supported | needs_qualifier | unsupported
- §3 support-recall: supported | needs_qualifier | unsupported
- §3 headroom-decomposition: supported | needs_qualifier | unsupported
- §4 "classical joint is the data-detection bottleneck": supported | needs_qualifier | unsupported
## Action Items (ranked by severity)
1. ...
```

Honest PASS beats performative WARN. Do not truncate.
