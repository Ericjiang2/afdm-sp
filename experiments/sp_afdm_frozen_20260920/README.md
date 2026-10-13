# SP-AFDM scientific design freeze — 20 September 2026

Read `docs/DESIGN.md` for the verdict, equation-level novelty boundary, derivations, baseline adaptations and executed evidence. Read `docs/LOCAL_PROTOCOL.md` for exact commands and the return-file contract. The primary receiver is fixed; local development selects only registered resource settings and primary operating points before creating an immutable confirmation lock.

The work establishes executable algorithms and numerical consistency, not a publication-level FER or runtime advantage. In particular, partial soft cancellation/weak-edge aggregation is known, scalar uncertainty ties full Gamma on the small new screen, structured EP remains a strong competitor, and already-cached dense moment calculations are faster than the matrix-free kernel in the recorded fixtures.

## Layout

- `src/physical.py`: inherited physical refit plus cache optimization, exact fractional-path statistics, full mean action, selected diagonals, weak row variance/pseudo-variance, actual-I1-matrix projection.
- `src/messages.py`: grouped-I/Q QPSK posterior/extrinsic contracts, sparse proper/noncircular BP, conditional SP moments.
- `src/structured_ep.py`: declared proper-complex coded dual-domain EP with exact cyclic-band Gaussian solves and selected inverse diagonals.
- `src/offgrid.py`: declared coded grid-evolution Gaussian-SBL / GAMP adapters, evolving dictionary, covariance-aware grid objective and effective CE-noise treatment.
- `src/bilinear.py`: declared SP parametric bilinear Gaussian-factor BP adaptation.
- `src/receiver.py`: formal I1 preterminal interface, single terminal stage, native competitor starts, recorded message boundaries.
- `src/run_local.py`, `seal.py`, `analyze.py`: paired local study, development-only selection/source lock, fixed-sample confirmation analysis.
- `protocol/`: finite configuration catalogue and statistical/resource contract.
- `tests/`, `results/`: executable exact/small-model checks and saved small screens. These are not a long confirmation campaign.
- `upstream/spafdm_receiver_handoff/`: original user-supplied receiver closure plus one optional,
  observation-only `decoder_observer` hook in `direction_receiver.py`. With the hook omitted,
  the original terminal decoder path is retained. The hook captures the result of the existing
  decoder call once; it does not add an inference pass or change decoder mathematics.

## Source identity boundary

`SHA256SUMS` describes the preserved original frozen delivery. It must not be used to verify this
corrected working tree. Each corrected run records the complete current `src/`, `tests/`, `docs/`,
`protocol/`, and `upstream/` hash map in its `manifest.json`; that run manifest is the corrected
source authority. The preserved original snapshot remains byte-for-byte separate from corrected
qualification and run directories.

## Quick start

```bash
export CUDA_VISIBLE_DEVICES=''
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python tests/test_core.py
python tests/test_baselines.py
python tests/test_integration.py
python tests/test_native.py
python src/run_local.py --phase development --out runs/development
python src/seal.py --development runs/development --out runs/confirmation_lock.json
python src/run_local.py --phase confirmation --lock runs/confirmation_lock.json --out runs/confirmation
python src/analyze.py --run runs/confirmation --lock runs/confirmation_lock.json --out runs/confirmation_analysis.json
```

The last five commands require substantial local computation; they were not executed as a campaign here. A reduced smoke can use `--frames 1 --arms P_M24_I20 I1_BP12_r0 --cell 2`, but cannot create a valid confirmation lock. Dependencies are recorded in `environment.json`; the code does not install packages or access the network.

Do not regenerate/overwrite `results/` while trying to preserve this delivered evidence; copy the package first. Do not compare results from modified sources under an old lock. Native baselines are honest method-family adaptations with explicitly listed differences, not asserted author-code reproductions.
