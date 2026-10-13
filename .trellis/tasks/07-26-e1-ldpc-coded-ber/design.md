# E1 Design — LDPC coded BER (paired, 3-arm)

## 目标

验证白化优势（achievable-Λ vs geom）在信道编码后是否存活。coded-BER ratio(ach/geom) 帧级 bootstrap CI。

## 关键设计决策（已定，实现时不再改）

1. **码**：**自包含纯 numpy 实现**（2026-07-26 变更：pyldpc 在远程 AFDM 环境 wheel build 失败，弃用，改为零依赖自写）。Gallager (d_v=3, d_c=6) 正则 LDPC，n=2048，rate≈1/2：H 由分块列置换构造（固定 seed），G 由 GF(2) 高斯消元系统化（k = n − rank(H)，≈1024）。每帧 2048 个数据比特 = 恰好一个码字。H/G 固定 seed 生成一次并缓存 npz，跨臂/跨运行同码。正确性由 selftest 把关（零噪声 roundtrip + AWGN 编码增益）。
2. **软译码**：用 `afdm_baselines.py` 的 `return_soft=True`（mp_detect BP 后验 μ/var，constellation space）构造每比特 LLR。QPSK Gray：bit_I=sign(Re)，bit_Q=sign(Im)；高斯近似 LLR = 4·Re(μ)·a/var 与 4·Im(μ)·a/var 形式（a=星座幅度含 data_scaling，实现时以代码中实际星座缩放为准推导，写注释）；LLR clip ±20。pyldpc 的 decode 接口若只吃信道输出形式，则自写标准 sum-product/min-sum BP over H（maxiter=50，早停 syndrome=0）——**以能吃任意 LLR 为准，不迁就库接口而降级成硬判**。
3. **TX 注入**：帧内数据符号不再是随机 QPSK，而是 LDPC 码字映射。信息比特 (k bits) 由 seed_fi 派生的 RNG 生成 → encode → 2048 coded bits → QPSK 映射，替换原 data_qam 生成处（paired_learned_eval 的帧生成路径，data_qam / data_pos 附近）。除此之外帧协议（导频、ρ、功率、信道 RNG）逐字不动。
4. **臂与配对**：harness 一次运行只有一个 gateA scorer 槽 → 跑两次（--gateA-scorer geom / achievable），同 seed 20260601 → 帧序列逐位相同。**硬性验收**：两次运行的 classical 臂每帧未编码 errs 向量必须逐元素相等（写进 results.json 并在分析脚本 assert），否则配对不成立、全部作废。
5. **指标**：每臂每帧记录 (a) 未编码 raw data-bit errs（与现有口径一致，兼作配对校验）(b) 译码后 info-bit errs (c) 是否译码成功（syndrome）。results.json 含 `_argv`/`_config`（QA #26 规矩）+ 每帧 per-frame 数组（bootstrap 用）。
6. **规模**：SNR15 主口径 800 帧；SNR20 顺带跑（方向性）。CPU 可跑（全臂无 NN）。
7. **输出**：`outputs_e1_ldpc_geom/`、`outputs_e1_ldpc_ach/` + 运行 log 同目录约定。

## 不做

- 不改 BP 检测器内部；不引入 sionna/重依赖；不做码型扫描（一个码，rate 1/2，够回答审计问题）；不做交织优化（QPSK+单码字/帧，天然无需）。

## 风险

- pyldpc 的 systematic G 可能给出 k≠1024 的边角（以实际 k 为准，帧内 2048 coded bits 不变即可）。
- 若 return_soft 在 F2-P 壳的调用路径没透出（壳包装层丢posteriors），fallback：壳外重跑最后一次 mp_detect 取软信息（同支撑/同增益，成本 +1 次 BP）。
