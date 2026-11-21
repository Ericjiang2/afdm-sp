# Implement
1. **Phase 1 (Sol, ≤ 1 core-hour).** Fresh-block check; U in the MIXED8 harness; G1–G3; SNR selection by DRAFT §1 using F0/CD on old
   frames only; verdict code with synthetic tests; cost. Commit; the protocol stays DRAFT.
2. **Freeze (Claude).** Freeze record and commit.
3. **Main (Sol).** One chain with a cost stop of 4 core-hours; frozen verdict; small files back; commit.
4. **Report (Claude).** Independent check, draft card, STATE, log.

**2026-11-19 — Phase 1 complete.** [DRAFT and Phase 1 amendments](../../../experiments/doublet_conflict_20261119/PROTOCOL.md) and [receipts](../../../experiments/doublet_conflict_20261119/out/phase1_20261119_attempt03/results.json) record G1–G3 passing, 7 dB selected (CD 4/96), and 0.2534 projected core-hours for 600 frames with the 1.3 multiplier. An independent raw-row read confirmed the SNR counts, paired inputs, zero old-frame U rows, and zero fresh-frame rows. Raw rows and digests remain in the deinlab attempt03 receipt directory. Two startup attempts stopped before frame generation due to the output-path contract and duplicate Torch thread initialization, respectively. The corrected attempt consumed 0.0901 core-hours. Phase 2 freeze and main execution are pending.

**2026-11-19 — Phase 2 complete.** The [frozen main run](../../../experiments/doublet_conflict_20261119/out/main_20261119/RESULTS.md) finished `DONE` at 0.2073 CPU core-hours for 600 MIXED8 frames at 7 dB. The unchanged verdict code returned **uncertain**, with Δ = +1.00 pp and a paired-bootstrap 95% interval of [−0.17, +2.17] pp. The freeze commit is `3360add4` and the pre-run launch commit is `7a0c11d9`. Independent checks reproduced the raw counts, paired support readouts, scope and bootstrap endpoints. Raw rows stay at `/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/doublet_conflict_20261119/out/main_20261119/rows.jsonl` (MD5 `3fb82ceaba80cac43c307b19f95c489e`).


## 关闭说明（2026-11-19，Eric 在收官时接受）
结果见 res-20261119-04；FER 代价不确定，若要定量需加大样本（开放项）。
