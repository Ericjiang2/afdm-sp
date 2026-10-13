# F1-fast offline reader implementation receipt

Reader: `experiments/cstate_necessity_stageB_20260928/f1_analyze_stage_b.py`, SHA-256 `2682a2dbf3d7b16a766ca098c28791526066a8f4c3e193d66946bae40cb865d6`. It only reads sealed output and bound truth after consuming a SHA-bound local Git attestation for the observed seal. It imports Stage-A **analysis helpers** and the archived evidence codec; it does not import or call a receiver, decoder, generator, acquisition, or optimizer. No real truth or new observed output has been read by this implementation check.

Checks completed: CLI `--help`, Python compilation, Ruff E4/E7/E9/F/B, targeted mypy, reader/producer schedule equality on all 1,024 IDs and 2,112 arm calls, and a synthetic Git-failure injection showing that truth inventory is not read before the Git gate. The implementer independently checked current producer raw/ledger/checkpoint keys; the two gaps found were fixed: truth inventory moved after Git attestation, and the incomplete direct-Git branch was removed. Actual sealed-output statistics, source/observed Git commits, and an independent recount remain pending.

From the remote project root, after the main session has verified both Git blobs and ancestry locally, transferred the attestation, committed the observed seal, and supplied the two shell variables `F1_OBSERVED_COMMIT` (full 40 hex) and `F1_ATTESTATION_SHA256` (full SHA-256), the intended **offline-only** command is:

```sh
/home/guoyikun/.conda/envs/AFDM/bin/python experiments/cstate_necessity_stageB_20260928/f1_analyze_stage_b.py \
  --registration results/cstate_necessity_stageB_20260928/STAGE_B_MANIFEST.json \
  --stage-a-registration results/cstate_necessity_stageA_20260928/EXPERIMENT_MANIFEST.json \
  --observed results/cstate_necessity_stageB_20260928/observed_f1_matched_v1 \
  --population-observed results/tf_cstate_prospective_20260923/population_observed \
  --population-truth results/tf_cstate_prospective_20260923/population_truth \
  --stage-a-observed results/cstate_necessity_stageA_20260928/observed \
  --baseline experiments/sp_afdm_frozen_reviewed_20260921 \
  --out results/cstate_necessity_stageB_20260928/analysis_f1_matched_v1 \
  --git-attestation results/cstate_necessity_stageB_20260928/F1_OBSERVED_GIT_ATTESTATION.json \
  --git-attestation-sha256 "$F1_ATTESTATION_SHA256" \
  --observed-commit "$F1_OBSERVED_COMMIT" \
  --seal-repo-path 00_Inbox/AFDM-channel-estimation/results/cstate_necessity_stageB_20260928/observed_f1_matched_v1/observed_seal.json
```

The reader refuses an existing output directory, an invalid-partial run, a missing call, a wrong schedule, a SHA/identity mismatch, or a truth seal drift. Its tables/report are outputs to be generated only after the committed observed seal gate.
