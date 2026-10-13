# Structured inference execution contract — 2026-10-03

This run resumes the last unfinished request in session
`01a0f27b-e6d2-74b1-be7c-5f2995ea31dc`, not the completed causal-defects campaign.
The canonical task is the CSV under
`.mission/20261003_10-41-29-afdm-structured-inference-exploration/`.
The PLAN is the scientific contract; this file binds its executable context.

## Physical and statistical boundary

Reuse `experiments/sp_afdm_frozen_20260920/src/physical.py` (`Channel`, `daft`)
and native `TimePathOps`/`scalar_joint`; the path action contains the actual CPP
wrap phase and continuous Doppler. Data live in the AF domain, not an
independent time-domain QPSK model. Use the existing frozen loader in
`experiments/afdm_inference_causal_20261002/oracle_comparison.py`.

Production uses N=1024, superimposed pilot/data energies 0.5/0.5, QPSK with
all-I then all-Q bits and cached n=2048, dv=3, dc=6 LDPC (seed 20260726).
Small mathematical experiments must state their different N, code, pilot and
noise. The production code's C2 automorphism is existing evidence from
`results/afdm_deep_rethinking_20261003/research/operator_geometry.md`; do not
rerun its matrix check or describe a short code as the production code.

The actual scalar joint uses the working prior CN(0,I/P), including after
initialization (`twofft.py:41,65`). Native refinement compresses a delay to one
center; F1 `keep_slots.py` already permits multiple same-delay paths.
The upstream generator normalizes gain against its virtual channel; real-CPP
`supplement_g1.py` reuses gains. Therefore the physical generating prior is
not an independent Gaussian working prior, nor automatically unit physical
Frobenius norm per frame. Exact Gaussian elimination is exact only inside
its declared working model. Reparameterization must push that same prior
forward, not change the physical model to win a comparison.

## Assets and resource registration

`asset_manifest.json` in the Mission root hashes the real physical, message,
native, oracle, generator, F1 and production-code sources. `run_contract.json`
registers separate seed namespaces for each branch, learning train/validation/
test, and unopened production development/confirmation. Old 48 conditions
contained six exogenous clusters; no old condition is a fresh test sample.

The local arithmetic quote (`execution/quote_v1`) is 20 solve/Gram/FFT repeats
at (N,P)=(8,2),(1024,8), with effective one-thread binding. It bounds initial
engineering cost, not the full receiver runtime. Registered CPU caps are 90 s
for each algebra branch, 180 s for continuous message integration, 300 s for
small learning. These are local bounded development runs; no remote/GPU or
production calls are authorized by this registration. Each stage saves its
own fixed dimensions, sample allocation and configuration before calculation.
Training architecture, steps and splits must be frozen before training.

`common.run` reuses the existing real BLAS binding (including Apple Accelerate
thread-local control), freezes hashes/configuration, reserves an immutable
attempt directory, enforces wall caps and records CPU/elapsed time and failures.
Workers own disjoint mathematical modules. A result file is not a scientific
success flag; reports must state actual errors and limits. Shared-process
timings cannot establish isolated whole-chain latency advantages.

## Admission and remaining production work

An implementable finite prototype may be admitted on legal working-model
messages and an affordable scalable computation, followed by actual-state
relevance in TRANSFER/MECH. Production benefit is not a circular prerequisite
for constructing that prototype. A point score is not a marginal LLR, and
enumeration/quadrature can be an oracle without being deployable.

Production tests require their own candidate/endpoint/precision/power/cost
freeze. Common 0.5/0.75/1 budgets are measured against original full-chain
cost with initialization, LDPC, failures and saving included; an infeasible
low budget stays infeasible. New expensive or remote resource needs must be
made concrete before the applicable approval gate. No received-signal truth
may enter inference, and no accepted paper claim changes in this run.

## Recovery changes

The previous session had not written its two review fixes; PLAN and SELECT/
FRESH rows now contain the two-stage admission and minimum-cost provisions.
The configured `gpt-6-sol` workers returned API 404 (unsupported model); no
scientific work ran there. Replacement workers inherit the available main
model, keeping the original responsibilities and evidence intact.
