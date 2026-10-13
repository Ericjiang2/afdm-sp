# Part B remote execution handoff (pending explicit payload/destination approval)

No Part B files have been transferred and no new receiver calls have run. The local producer must be frozen in Git by the main session before these commands are used. They are recorded here for review, **not executed**.

Destination: `deinlab:/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_pd1q_part_b_20260921/`. Transfer exactly `campaign/`, `approved_ticket.md`, `statistical_contract.json`, and `qualification_reference_manifest.json` from the local Part B root. Do not transfer `paper_design_reference.md` or prior raw observations. Verify SHA256 of the three contract/provenance files after upload, plus the committed campaign file inventory.

The exact reduced transfer command rejected by automatic review, recorded for use only after explicit payload/destination approval, is:

```bash
tar -C results/sp_afdm_pd1q_part_b_20260921 -cf - campaign approved_ticket.md statistical_contract.json qualification_reference_manifest.json | ssh -o BatchMode=yes -o ConnectTimeout=8 deinlab 'mkdir -p /data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_pd1q_part_b_20260921 && tar -C /data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_pd1q_part_b_20260921 -xf -'
```

Run the zero-receiver synthetic test on deinlab after transfer, with every cache/temp/log under `/data`:

```bash
ssh deinlab 'set -u; ROOT=/data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_pd1q_part_b_20260921; mkdir -p "$ROOT/tmp" "$ROOT/cache" "$ROOT/matplotlib" "$ROOT/launch_pretest"; export CUDA_VISIBLE_DEVICES="" OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 TMPDIR="$ROOT/tmp" XDG_CACHE_HOME="$ROOT/cache" TORCH_HOME="$ROOT/cache" MPLCONFIGDIR="$ROOT/matplotlib"; cd "$ROOT/campaign" || exit 90; /home/guoyikun/.conda/envs/AFDM/bin/python -B -m unittest -v test_analyze > "$ROOT/launch_pretest/stdout.log" 2> "$ROOT/launch_pretest/stderr.log"; rc=$?; printf "%s\n" "$rc" > "$ROOT/launch_pretest/exit_code.txt"; exit "$rc"'
```

If and only if that test exits zero and the committed files/hashes match, launch the authorized unified chain once. Its script runs read-only preflight/seed collision audit, exactly 9,696 receiver calls on 3,072 new frames, full saved-array recount, frozen statistical analysis, and remote inventory. A failed stage writes `blocked.json`/`RESULTS.md` and stops; do not auto-retry or resume:

```bash
ssh deinlab 'tmux new-session -d -s g_pd1q_partb "bash /data/guoyikun/00inbox/AFDM-channel-estimation/results/sp_afdm_pd1q_part_b_20260921/campaign/run_chain.sh"'
```

Remote read-only checks already showed host `liunxgpu`, frozen E1 stage D present, and frozen LDPC cache present. They did not constitute the pending zero-receiver synthetic test or preflight result. No overnight polling is needed; the server-side chain writes PID, argv, whitelist environment, deadline, per-stage time, exit codes and logs.
