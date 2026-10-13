# RUN-02 legacy fixedcap40 历史回放参考

只读检索，2026-09-06。没有发车、改代码/CSV、访问Dtest或validation观测。范围为本地已归档status、开发/smoke frames与batch源码路径元数据。

## 结论：有完整逐帧错误计数向量，无逐bit错误向量

最小冻结参考是 `.trellis/tasks/09-06-minimal-repair-mechanism/research/runtime/capacity-smoke40/` 下的 `status.json`、`frames.jsonl`、`calibration.json`。

该记录 `active_cap=40`、`nomination_cap=8`；旧receiver扩展2。因此它正是关闭direct40新路径后的legacy fixedcap40参考。两帧均完整保存了各arm逐帧raw/info错误计数、译码标志、输入hash、H_est/x_soft hash、支撑及F2P轮次记录。

| arm | raw错误计数向量（frame0,1） | info错误计数向量 | decode_ok向量 |
|---|---|---|---|
| baseline | [226, 237] | [0, 0] | [true, true] |
| covariance | [216, 223] | [0, 0] | [true, true] |

上述是**完整逐帧计数向量**，不是两帧总错误数。历史文件没有raw_bit_error_mask、info_bit_error_mask、decoded_bits或完整每bit判决向量。`output_x_sha256`可证明对应soft输出字节一致，仍不能代替没有存下的LDPC decoded-bit向量。若RUN-02“完整错误向量”要求逐bit mask，现有档案不足；只能在冻结旧source-v3另做独立参考与当前legacy配对重放并保存逐bit向量，不能从计数反推，也不能将新生成参考冒称历史已存。

`budgeted_support_replay.py`既有VECTOR_KEYS也是perframe错误计数/seed/decode标志；compare_prefix明确scope为“integer error counts and decoder flags only”。该脚本的E1 results.json格式不能直接用于这里的budgeted frames.jsonl，且不能声称验证逐bit等价。

## 身份、温度、prior与冻结源码

- N1024、SNR8、split=`cal`（split2）、rep997、frame0…1；channel_seed分别1612805481、66232847。
- arms参数顺序为`baseline covariance`；实际frame0顺序`covariance,baseline`，frame1顺序`baseline,covariance`。保持这组arms和顺序，不随意删成baseline-only再声称同一历史算术序列。
- baseline mean/T1；covariance模式/T1。不开soft-observe、不设uncoded、不使用新a0。
- checkpoint `/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk`，hash `052ecfab8eff7780c49038d9bb4f16f92272ee22322fa05b6f65029cc3112a91`。
- prior `/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_budgeted_support_repair/s4_20260906/prior-cap40/cache_snr8.pt`，hash `2037a0a6f2179a7ca2630ee8be08bcc536775c8024f2ee7c9f58c597e52c6c03`。这是旧nomination8 prior，不能换成新direct40 prior。
- 温度 `/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_budgeted_support_repair/s4_20260906/identity-temperature.json`，hash `add8e80917851686c435a21ef597c859f69ddd4f4c568e52593e0c5fd31ef34d`。
- LDPC hash `7be530177c11b398d4f362ae81a663e83dd03de0ffdcd9bf2dd42eb1418f08be`；N2048,dv3,dc6,seed20260726。
- `.trellis/tasks/09-06-minimal-repair-mechanism/research/runtime/capacity-smoke-batch.json:5`记录冻结source `/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_budgeted_support_repair/s4_20260906/source-v3`。
- 历史 `budgeted_support_eval.py` hash `1a06c9ec49dc93528cbf3b219410d9f9b8b973cd5199d3afb0d6f57340f18284`；`classical_joint_unrolled.py` hash `59af54ccdc830e5dfa69e8c88a004e7d0703f24793e7d6af0b26b6e81c282489`；`budgeted_support_diagnostics.py` hash `93c3ad09a09835d7b8321b3efac097b081fdb98b1f4a2c6ae783e3d2fb294054`。完整源码hash表在status。
- 历史PyTorch2.5.1+cu121、OMP/BLAS各4线程、CPU affinity24…27。当前远端路径是否仍存在未在本子任务验证；本地只持有记录，不持有可直接运行的完整source-v3/checkpoint/prior。

注意另有名为 `capacity-legacy-replay` 的两帧目录：split dev/rep998、active_cap=null、prior来自s2 calibration-snr8。它是历史不限制容量锚点，**不是fixedcap40/nomination8参考**，不能混用。

## 当前代码关闭新路径的最小重放命令

发车前由主会话核验资源、当前源码快照与上述文件hash。新输出目录不得已存在，不能覆盖历史目录。命令在当前已验收源码根运行，而不是旧source-v3；这样才检验新代码的legacy关闭模式。

```bash
AFDM_ROOT=/data/guoyikun/00inbox/AFDM-channel-estimation
AFDM_OLD="$AFDM_ROOT/outputs_budgeted_support_repair/s4_20260906"
AFDM_PY=/home/guoyikun/.conda/envs/AFDM/bin/python
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
cd "$AFDM_ROOT"
"$AFDM_PY" -u -m afdm_sp_joint_unrolled.budgeted_support_eval \
  --ckpt "$AFDM_ROOT/afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk" \
  --calibration "$AFDM_OLD/prior-cap40/cache_snr8.pt" \
  --feedback-calibration "$AFDM_OLD/identity-temperature.json" \
  --snr 8 --split cal --replicate 997 --start-frame 0 --frames 2 \
  --n-total 1024 --device cuda --active-cap 40 --receiver-shell legacy \
  --arms baseline covariance \
  --out "$AFDM_ROOT/outputs_budgeted_support_repair/legacy_fixed40_replay_20260906"
```

如果必须新生成逐bit旧参考：另在冻结source-v3下运行同参数，仅去掉旧CLI不支持的`--receiver-shell legacy`；当前源码和旧源码须用不同输出目录。旧参考新增观察器不得改变算术路径，先验证其开关不改变已存H/x hash及逐帧计数。该额外工作未在本研究执行。

## 比较字段与边界

按固定frame0…1顺序，首先比较 `split,replicate,frame_index,snr,channel_seed,coding,bits_per_frame,nomination_cap,active_cap,arm_order`，以及`input_hashes`全部六项（y,H,noise,info,coded,pilot）。不允许只按seed或从更多帧挑匹配子集。

每arm比较长度为2的raw_errors/info_errors/decode_ok完整向量；保留逐帧差异索引。进一步比较output_h_sha256/output_x_sha256、support（raw/final_nomination/expanded）、rounds（support/candidate_ids/scores）、sigma2_final和finite。时间字段应排除相等断言。若GPU浮点路径改变导致hash差异，应如实记录并区分bit错误计数与浮点字节，不以误差总和相同抵消差异。

若需要包含译码失败帧的较强补充，旧 `capacity-dev-rep0/frames.jsonl` 有完整64帧，baseline info_errors首帧149、raw334，第二帧info0/raw161。对应完整设置是split dev/rep0/frame0…63、arms baseline temperature_mean covariance、soft-observe开启、fixed-feedback-calibration.json（不是identity-temperature），仍nomination8。此64帧记录是已用开发数据，不能误标独立验证。最小两帧smoke的info向量全0这一限制必须保留，不能声称覆盖译码失败回放。
