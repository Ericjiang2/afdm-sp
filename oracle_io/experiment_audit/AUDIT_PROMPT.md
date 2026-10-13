# Experiment Integrity Audit — AFDM SP-Joint Learned-Receiver Thesis

You are an independent experiment-integrity auditor (cross-model reviewer: you are GPT-5.5 Pro, the executor is a different model). Your job is to READ the attached files line-by-line and judge whether the experimental evidence backing the thesis claims is REAL, or whether it contains any of the well-known LLM-agent fraud patterns (fake ground truth, score self-normalisation, phantom result files, dead-code metrics, scope inflation).

## Project briefing (one paragraph)

This is a UoG/UESTC BEng Final-Year-Project thesis on an AFDM (Affine Frequency Division Multiplexing) receiver with superimposed pilots (SP). The baseline is a classical joint receiver (`joint_omp_mp_iterative` in `afdm_baselines.py`) that does **OMP-once** support initialisation + **LS/MP-BP** inner iterations (Algorithm 1 in `Section2.tex`). The contribution is a **1,041-parameter learned "C2-rel F2-P" support-refinement head** (pair-encoder MLP + order-invariant pool + scorer MLP) that is invoked TWICE at outer-iteration t=0 to append top-K_add off-support candidates, then the classical inner LS/MP-BP loop takes over unchanged. The forward kernel is `classical_joint_unrolled.py::ClassicalJointUnrolledReceiver` which, when superparameters are frozen, is bit-exact against the NumPy `joint_omp_mp_iterative` (verified via `verify_classical_unrolled_matches_numpy.py`). Training is on a 4B cached trainer (N=512, UWA-like sparse DD channel, QPSK, rho_p=0.5). BER is reported against TRUE transmitted bits — NOT against a model-generated proxy — at SNR ∈ {0,5,10,15,20,25} dB, 80–500 frames/SNR depending on sweep. The thesis is currently rated A5 (weighted 86.7/100) by a prior Oracle GPT-5.5 Pro panel review.

## Your task: audit integrity, not quality

Do NOT re-score the thesis. Do NOT give writing feedback. ONLY judge whether the experimental results can be trusted. Use the 6-point checklist below. Cite exact `file:line` references for every finding.

## Audit checklist

### A. Ground-Truth Provenance (CRITICAL)
Open the evaluation scripts and follow the data flow:
- `eval_classical_joint_unrolled.py`
- `run_classical_baselines_python.py`
- `loop13_iter_convergence_probe.py`
- `loop13_new_baselines_eval.py`
- `loop13_support_recall_probe.py`
- `headroom_decomposition_probe.py`
- `compute_heldout_metrics.py`

For each, answer:
1. Where do the "true bits" / "ground truth" come from? Are they the bits the simulator put INTO the channel, or are they bits the MODEL THE SCRIPT IS EVALUATING spat out?
2. For "support recall" metrics, is the "true support" the physical channel taps the simulator put in (AFDM environment / `afdm_env.py`), or is it inferred from the model's own estimate?
3. For NMSE / h-recovery metrics, is the reference `h_true` the simulator-drawn channel, or the model's own recovered `h_hat`?
4. Are any metrics computed against `h_hat` from a PRIOR round of the same model (iterative-consistency proxy) without being clearly labelled as a proxy?

**FAIL** if any headline claim in the paper (paper/sections/Section3.tex, Section4.tex, Abstract.tex) uses a model-derived reference without labelling it a proxy.

### B. Score Normalisation
For every metric in the evaluation scripts:
1. Is any score divided by `max(own_output)`, `min(own_output)`, or any statistic of the model's own prediction distribution?
2. Are "recall" / "precision" computed against a top-K window whose K is chosen from the model's own confidence?
3. Are raw counts (errs/bits, hits/total) reported alongside any ratio?

Pay particular attention to `loop13_support_recall_probe.py` and its output `outputs_loop13_support_recall/recall_by_snr.json`.

**FAIL** if any normalised score uses the model's own output as its own denominator.

### C. Result-File Existence and Number Matching
Open the thesis text (`paper/sections/Section3.tex`, `Section4.tex`, `Abstract.tex`) and the `CLAIMS_FROM_RESULTS.md`. For each numeric claim (BER value, NMSE value, SER gap, gain-in-dB, iteration-convergence number, 300-frame vs 80-frame bootstrap), trace it back to the specific JSON result file I have attached:

- `outputs_loop13_4B_full_results.json` — 4B full headline BER-vs-SNR
- `outputs_loop13_4B_retrain_eval_results.json` — retrain eval
- `outputs_loop13_4B_retrain27k_snr25_eval_results.json` — SNR=25 retrain
- `outputs_loop13_iter_convergence_4B_merged/results.json` — mixed 80/300 frame iter-convergence (the one currently cited in §3 Table + Fig 3)
- `outputs_loop13_iter_convergence_4B/results.json` — original 80-frame (superseded by merged for SNR=20)
- `outputs_loop13_iter_convergence_4B_snr20_300f/results.json` — the 300-frame SNR=20 rerun
- `outputs_loop13_iter_convergence_v2_results.json` — v2 convergence (earlier)
- `outputs_loop13_new_baselines_500f_results.json` — 500-frame new baselines
- `outputs_loop13_new_baselines_4B_results.json` — 4B new baselines
- `outputs_loop13_headroom_4B_big/headroom_results.json` — headroom 4B-big
- `outputs_loop13_headroom_4B/headroom_results.json` — headroom 4B
- `outputs_loop13_support_recall/recall_by_snr.json` — support-recall probe
- `outputs_loop13_2B_snr0_5_results.json` — 2B SNR∈{0,5}

For each claim:
1. Does the referenced file exist? (It's attached, so yes — but confirm the file is non-empty and well-formed.)
2. Does the specific key path (arm → snr → iter → metric) exist in the file?
3. Does the NUMBER in the paper match the NUMBER in the file to at least 2 significant figures?
4. If the thesis cites an "80-frame + 300-frame mixed budget", does the merge helper `_merge_snr20_300f.py` actually produce what §3 says it produces?

**FAIL** if any numeric claim references a file that doesn't exist, a key that doesn't exist, or a number that disagrees with the file by more than rounding.

### D. Dead-Code Detection
For the eval scripts above and the feature-extraction code in `classical_joint_unrolled.py`:
1. Are there defined metric functions or feature extractors that are **never called** in the actual eval pipeline that produced the result files above?
2. Are there training-time auxiliary losses (rank-hinge, BCE) or training-time-only ranking strategies that differ from deployment-time ranking? Is the DEPLOYMENT path the one that actually produced the headline numbers?
3. Is there any "fallback" or "default" branch in the inference path that would silently bypass the learned head and yet still count toward the "learned" arm's BER?

**WARN** if metric functions exist but aren't called; **FAIL** if the learned-arm numbers in the paper are actually classical-arm outputs in disguise.

### E. Scope vs Language
Open `paper/sections/Abstract.tex`, `paper/sections/Section1.tex`, `paper/sections/Section4.tex`, `paper/sections/Section5.tex`. For each "comprehensive", "extensive", "robust", "general", or "across-the-board" claim:
1. How many channel scenarios were actually tested? (UWA-like sparse DD only? MSML? per-path time-scaling?)
2. How many training seeds? How many evaluation seeds per SNR? How many frames per SNR?
3. Are confidence intervals / 95% CIs reported for BER at 10^-4 level? (At BER = 1e-4 with ~500 frames × ~1000 bits/frame, you get ~50 errors which is ~14% relative 1-sigma.)
4. Is any claim using wording that exceeds the actual evidence base?

**WARN** if scope language is inflated; **FAIL** if the abstract promises something fundamentally broader than what was tested.

### F. Evaluation-Type Classification
Classify the thesis's headline evaluation as ONE of:
- `real_gt` — uses simulator-drawn ground truth (true transmitted bits, true channel taps)
- `synthetic_proxy` — reference is model-generated
- `self_supervised_proxy` — no GT by design
- `simulation_only` — simulated channel only, no hardware/ocean measurements (this is the honest default for AFDM UWA thesis work)
- `human_eval` — not applicable here

Give one classification and one sentence of evidence.

## Output format

For each check A–F, report exactly:

```
### A. Ground-Truth Provenance: PASS | WARN | FAIL
Evidence: <file>:<line> — <what you found, in one or two sentences>
Details: <only if WARN/FAIL — what specifically is wrong and what would need to change>
```

Then finish with:

```
## Overall Verdict: PASS | WARN | FAIL

## Integrity Status: pass | warn | fail

## Evaluation Type: real_gt | synthetic_proxy | self_supervised_proxy | simulation_only | human_eval

## Claim Impact
- Abstract's BER/NMSE headline: supported | needs_qualifier | unsupported
- §3 iter-convergence claim (mixed 80/300 frame): supported | needs_qualifier | unsupported
- §3 support-recall claim: supported | needs_qualifier | unsupported
- §3 headroom-decomposition claim: supported | needs_qualifier | unsupported
- §4 "classical joint is the data-detection bottleneck" claim: supported | needs_qualifier | unsupported

## Action Items (ranked by severity)
1. ...
2. ...
3. ...
```

Be thorough. Read every eval script. Trace `y_sim, bits_sim → model → bits_hat → ber(bits_sim, bits_hat)` end-to-end. If the loop is broken anywhere, flag it. If everything is clean, say PASS confidently with evidence. Do NOT hedge just to seem rigorous — honest PASS is more useful than performative WARN.
