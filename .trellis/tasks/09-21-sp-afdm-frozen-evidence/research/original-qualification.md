# Original frozen package migration and qualification — 2026-09-21

## Scope and identity

This record covers only the byte-preserved package delivered as
`SP_AFDM_Design_Freeze_20260920.zip` and its original qualification commands. It does not treat
historical result files as fresh experimental evidence and does not qualify later corrected source.

- Local imported package: `experiments/sp_afdm_frozen_20260920`
- Source archive SHA-256: `e27c1fe6edee494d476d0e8431b027cde4c16afbad0b71c59bdfa527cb9029d7`
- Import manifest: `research/original-import-manifest.json` (279 files)
- Compliant remote source: `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_20260920`
- Isolated qualification copy: `/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_frozen/qualification_original_20260921/worktree`
- Delivered `SHA256SUMS` file SHA-256: `03210be1c654b483d11aa359305b583b9e30f8365e0f4de45c3d269a7b5a6e3c`

The remote migration inventory contains 279 files. All 278 entries named by the delivered
`SHA256SUMS` passed after migration, before qualification, and after qualification when generated
`results/` were excluded. The full pre-test 279-file inventory is in
`results/sp_afdm_frozen/qualification_original_20260921/pretest_full_tree.sha256`.
No original source, test, protocol, documentation, or imported result byte was changed in this
qualification copy before the commands ran.

The earlier home-directory copy was later moved without deletion to
`/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_frozen/recovered_home_source_20260921`.
Its 279-file relocation receipt is `results/sp_afdm_frozen/remote_home_relocation.json`. The
prohibited `/home/guoyikun/experiments/sp_afdm_frozen_20260920` source path no longer exists.

## Runtime contract

The qualification ran on host `liunxgpu`, Intel Xeon Platinum 8336C, using
`/home/guoyikun/.conda/envs/AFDM/bin/python` with Python 3.10.20, NumPy 1.26.4,
SciPy 1.10.1, PyTorch 2.5.1+cu121, and Matplotlib 3.7.1. CUDA was hidden and unavailable.
`OPENBLAS_NUM_THREADS`, `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, and `NUMEXPR_NUM_THREADS` were all
one. `TMPDIR`, Matplotlib, Torch, and XDG caches were explicitly placed under the task's `/data`
result directory. Each numerical command ran alone with a server-side timeout and recorded argv,
PID, deadline, stdout, stderr, `/usr/bin/time -v`, and exit code.

The standalone environment probe observed PyTorch inter-op default 64, then explicitly set and
verified intra-op/inter-op one inside that probe. The original receiver `build()` is the binding
authority in actual test processes. The exported thread variables apply to each separate test
process; the probe's explicit PyTorch setters do not propagate across processes.

## Fresh original qualification

The eight commands required by `docs/LOCAL_PROTOCOL.md` ran sequentially and all returned zero:

| Command | Fresh result | Wall time |
| --- | --- | ---: |
| `tests/test_core.py` | PASS 134 checks; max error `1.4547e-09` | 0.29 s |
| `tests/test_baselines.py` | PASS 22 checks | 0.41 s |
| `tests/test_bilinear.py` | PASS | 0.23 s |
| `tests/test_cache.py` | PASS | 0.36 s |
| `tests/test_fallback.py` | PASS | 1.73 s |
| `tests/test_integration.py` | PASS, one production-size frame | 7.76 s |
| `tests/test_native.py` | PASS, reduced native smoke | 7.92 s |
| `tests/benchmark_kernels.py` | PASS | 1.71 s |

The production-size integration front took 1.0472 s. Recorded incremental terminal times were
I1 0.0550 s, proposed mean 0.2000 s, proposed soft 0.2004 s, EP 0.1939 s, and active GAMP
0.1593 s. The reduced native smoke recorded complete times GAMP 0.7092 s, EP 0.5408 s, and
bilinear 2.2306 s. These are qualification fixtures, not 59-arm development or confirmation.

`tests/verify_saved_decisions.py` then returned zero and recounted 104 imported saved decisions.
That check verifies internal consistency of saved arrays; it does not make those historical arrays
fresh evidence. The largest process RSS observed by `/usr/bin/time -v` was 1,134,092 KiB during
the native test. This is a whole-test-process qualification bound, not a per-arm online-memory
measurement.

## Evidence locations

- Complete local evidence: `results/sp_afdm_frozen/qualification_original_20260921/`
- Per-command logs: `results/sp_afdm_frozen/qualification_original_20260921/commands/`
- Fresh outputs: `results/sp_afdm_frozen/qualification_original_20260921/fresh_outputs/`
- Evidence archive SHA-256: `1a10bbd3de5f8265526343a9b68249ea8c162eb5e0d68865569c50070c41f097`
- Remote evidence archive: `/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_frozen/qualification_original_20260921_evidence.tar.gz`

The original source import boundary was committed separately as `70dd0077`. This report does not
claim that the later corrected working tree matches the delivered `SHA256SUMS`.
