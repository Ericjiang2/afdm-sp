# E-3：外部有效性——在 Luo 式数据辅助 SBL 接收机中检验同时延协方差修正

## Goal

E-1/E-2（[res-20261017-01](../../../research-assets/res-20261017-01.md)、[res-20261017-02](../../../research-assets/res-20261017-02.md)）只在我们自己的接收机（F0 + CSTATE 支撑交换）里证明了 H*。新颖性检查（`archive/2026-10/10-17-codelay-novelty/research/novelty-verdict.md`）发现，SP-OTFS/AFDM 的数据辅助文献全部使用标量数据干扰模型。本任务回答一个问题：**在一个按文献风格搭建、与 CSTATE 无关的数据辅助稀疏信道估计器中，是否也出现同时延幻影原子？把它的标量数据模型换成投影协方差 Γ 后，幻影是否消失、FER 是否改善？**

用户 2026-10-17 选择先做本项（"先做1"）。

## Requirements

- R1：外部接收机采用 Luo et al. arXiv:2607.18881（D-GESBL，SP-AFDM，作者自述 TCOM 接收）的两级 EM-SBL 结构：导频级 SBL，加上用检测数据重建字典的数据辅助级 SBL。它不能复用 CSTATE 或 F0 的支撑搜索。与原文的偏差（细网格 on-grid 代替 Taylor off-grid、下游检测/译码用本项目的检测器与 LDPC）必须逐条写进协议。
- R2：四个第二级变体只改数据模型，其余一律相同：Luo 原样（硬判决、各向同性噪声）、软均值 + 对角 Γ、软均值 + 完整 Γ、真数据（genie）对照。
- R3：协议必须先冻结、提交，之后才能跑校准或主跑。冻结源码一律不改，新代码放在 `experiments/tf_e3_sbl_20261017/`。
- R4：帧使用此前从未用过的 P1 帧，执行者需查证。SNR 网格由冻结的校准规则决定，只看 Luo 原样变体。
- R5：行数据留在 deinlab；小文件回传并入 git；跑前、跑后各 commit 一次。成本上限 40 core-hours。
- R6：结果只出 draft 卡，验收由用户决定。

## Acceptance Criteria

- [ ] 门全部通过（见 design §6），协议在跑前提交。
- [ ] 主跑 0 失败；判定 X1–X3 按冻结规则给出，带 CI。
- [ ] 同时延普查口径与 E-1/E-2 一致，并扣除 genie 基线。
- [ ] draft 卡链接 res-20261017-01/-02。

## Boundaries

- 不调 SBL 超参来"救"任何一个变体，所有变体共用同一组冻结超参。
- 不做 Taylor off-grid 精化，不做 Kanazawa 门限检测器。
- 结论只限本移植、P1 信道、N = 1024、QPSK、本 LDPC 码。
