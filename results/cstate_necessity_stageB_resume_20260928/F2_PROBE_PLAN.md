# F2E first-frame operational probe — closed until manifest commit

One sealed developmental observation only: `s650_f0000`, 6.5 dB, N=1024, original 1024-frame Stage-A population. At most **one complete F2E wrapper call** (four estimator passes cap, two TF20/LDPC50 coded rounds), no generator, truth, F2T, CSTATE, F1 or additional receiver probe. The result is an interface/cost diagnostic, **not** a population FER estimate. A timeout or numerical failure remains a charged failed attempt; no automatic retry or reduced iteration cap.

Before launch, main freezes a new `f2e-first-frame-probe/1` JSON run manifest in Git. Its required fields are `status=locked`, `observation_id=s650_f0000`, `maximum_complete_calls=1`, `maximum_wall_seconds=120`, `truth_used=false`, SHA-256 of the observed population seal and exact first-frame artifact, `code_g_sha256`, full `native_source_hashes` and `baseline_source_hashes`, plus `dependency_source_hashes` including `tf_production_gap_audit_20260922/audit_io.py`. The separately frozen launcher SHA is recorded as `launcher_sha256` by main. The exact new Python producer source map is:

| Source | SHA-256 |
|---|---|
| `f2_estimator.py` | `f86321834db43dc860e39f63143cdecd66c17c2af37f8bee1413daf40124a432` |
| `f2_receiver.py` | `4e0a2e902e784860aa542bf1e1a4ce5def6acfe4737f5a2a30832ae1ebe00841` |
| `f2_probe.py` | `5dfff25c1a1df2069d6cfa9bd784a017d7fbff6bcb25d5ec5d229c00567547f5` |

Run only after the manifest is committed and independently checked. Remote paths remain under `/data/guoyikun/00inbox/AFDM-channel-estimation`; `--source` is the reviewed native source root bound by the manifest and `--baseline` the reviewed baseline root. Main's bound launcher fills the committed manifest SHA, uses CPU 64 and task-local scratch/cache directories, then runs GNU timeout at **115 seconds plus 5 seconds kill-after**, a 120-second total ceiling:

```sh
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  TMPDIR='<task-scratch>' XDG_CACHE_HOME='<task-scratch>' MPLCONFIGDIR='<task-scratch>' TORCH_HOME='<task-scratch>' \
  timeout --signal=INT --kill-after=5s 115s taskset -c 64 \
  /home/guoyikun/.conda/envs/AFDM/bin/python \
  experiments/cstate_necessity_stageB_resume_20260928/f2_probe.py \
  --manifest results/cstate_necessity_stageB_resume_20260928/F2_PROBE_MANIFEST.json \
  --manifest-sha256 '<committed-manifest-sha256>' \
  --source experiments/sp_afdm_native_joint_reviewed_20260921 \
  --baseline experiments/sp_afdm_frozen_reviewed_20260921 \
  --population-observed results/tf_cstate_prospective_20260923/population_observed \
  --out results/cstate_necessity_stageB_resume_20260928/probe_f0000_v1
```

The script checks source/observed hashes and runtime binding before a receiver call, fsyncs one pre-call attempt journal, runs an in-process 110-second guard, stores ready checkpoints and source-bound raw/receipt or a failure receipt, and charges matrix/posterior/grid/dense-H/LMMSE/serialization in the complete wall time. The outer 115+5-second timeout handles a blocked native library. No production or probe call has run at the time this plan was written.
