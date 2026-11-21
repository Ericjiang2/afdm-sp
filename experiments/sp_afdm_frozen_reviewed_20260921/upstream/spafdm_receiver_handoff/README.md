# Frozen I1 handoff pack — v3 (2026-09-17)

Self-contained runnable subset of the SP-AFDM project (working-tree snapshot, repo HEAD
`cdc4daac` on `trans/tcom-main`).

## Why v3 (v2 gap)

v2 shipped `run_frozen_i1_smoke.py` but NOT `budgeted_support_eval.py` — the module that defines
`build_receiver` / `make_frame` / **`run_frame`** — and its code lived in category folders rather
than an importable `afdm_sp_joint_unrolled/` package. v3 fixes both: the complete import closure
(85 files: top-level modules + baseline subpackages + `__init__.py`) ships as a real package next
to the smoke.

## Layout

- `run_frozen_i1_smoke.py` — one-command CPU smoke (fixed seeds/checkpoint, FER/LLR output, `--check` mode)
- `frozen-i1-smoke-fixture-v1.json` — known-input → known-output fixture (8 frames @ 7 dB, replicate 30)
- `afdm_sp_joint_unrolled/` — complete import closure of the smoke + frozen adapter, e.g.
  `budgeted_support_eval.py` (build_receiver / make_frame / run_frame), `direction_receiver.py`
  (`ObservedReceiver`, `terminal_decode`, `CHECKPOINT_HASH`), `supplement_pilots.py`,
  `supplement_feedback.py` + `supplement_messages.py`, `classical_joint_unrolled.py`,
  `mp_detect_bp_torch.py`, `e1_ldpc.py` + `e1_ldpc_coded_eval.py`, `supplement_timing_catalogue.py`
  (formal I1 adapter) + deps, support-exchange / transaction modules, and the classical baseline
  subpackages pulled by that chain (`cao_baseline/`, `lmmse_baseline/`, `drce_baseline/`, `pbigabp_baseline/`).
- `07_checkpoint/frozen-c2rel-checkpoint.pt` — the frozen receiver checkpoint
  (sha256 `052ecfab8eff7780c49038d9bb4f16f92272ee22322fa05b6f65029cc3112a91`; hash-checked by the receiver and the smoke)
- `01_theory_and_state/`, `05_recent_evidence/` — context documents
- `MANIFEST.txt` (sha256 + sizes) and `RUNTIME_CLOSURE.txt` (module list)

## Run (works directly from the extracted pack)

    python run_frozen_i1_smoke.py                                        # 4 frames @ 8 dB
    python run_frozen_i1_smoke.py --frames 8 --snr 7                     # matches the fixture
    python run_frozen_i1_smoke.py --frames 8 --snr 7 --check frozen-i1-smoke-fixture-v1.json

Requires numpy / scipy / torch / matplotlib. Checkpoint auto-discovery: repository path
(`.mission/.../frozen-c2rel-checkpoint.pt`) or pack path (`07_checkpoint/...`); `--checkpoint`
overrides. CUDA is hidden before the torch import (project convention for CPU runs).
Verified from the extracted pack: every shipped module imports cleanly (85/85), and `--check`
reproduces every input hash, LLR hash and integer field of the fixture exactly (~11 s for 8 frames).

## Fixture semantics

Receiver identity: arm `a0` (support repair disabled), shell `direct40` / `active_cap=40`,
actual 10 outer iterations / 20 BP detection iterations / LDPC maxiter 50, frozen checkpoint and
frozen 2048-bit LDPC (`code_g_sha256 bfd4247263adedc9a095b87603c2a7a4c2f2e8cb83f7e78bad721c5b06eaa6af`).
Per frame: `input_hashes` (y / H / noise / info / coded / pilot via the project `array_hash`),
`info_errors`, `raw_errors`, `decode_ok`, `fer`, `final_bit_nll`, `final_bit_brier`, `nmse`,
`final_llr_sha256`, `final_bp_mu_sha256`, `final_bp_var_sha256`, `output_h_sha256`,
`output_x_sha256`, `decoded_bits_sha256`. Truth (H) is used for offline scoring only; the
receiver never reads it.
