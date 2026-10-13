# 存档证据复算：DATA / VALUE / DIAG

本次完成了 **6.5 dB、1,024 个原有模拟观测的只读复算**。未调用接收机、未生成新观测、未写远端文件。它能裁决已存动作的上界和部分机制诊断，不能代替 DEV 的完整链实验或独立确认。

## 输入与完整性

- 原观测：`/data/guoyikun/00inbox/AFDM-channel-estimation/results/tf_cstate_prospective_20260923/population_observed`，现场确认 3,076 文件，包含三个 SNR 共 3,072 个观测。
- Stage-A：同项目 `results/cstate_necessity_stageA_20260928/observed`，现场确认 16,501 文件。分析读取 A/C 各 1,024 个 raw；所有 raw 的 SHA、seal、frame、input SHA、observation hash、stream IDs 一致后，才载入旧 truth。
- 本地 `archived_population_diagnostics.json` 保留每帧输入、raw 和 truth SHA；2,048 个 raw、1,024 个 truth 全部通过绑定，缺失观测 **0**。两臂 raw 重新计算的最终 coded-error 数逐帧等于旧表。
- VALUE 使用 five-policy 的全部 5,120 行；逐帧输入 SHA 一致。F0/B 最终 decoded SHA 与另一 campaign 的 Stage-A A/B 对齐。只有其 outcome 对照跨 campaign；成本始终只用同一 five-policy campaign。
- 首次提取在 truth schema 解包时失败：本 campaign 存 `uint8[2048]`，不是早期 packed dict。失败记录 `extraction_attempt1_failure.json` 保留；检查真实 dtype/shape 后重算成功，没有复用失败的部分结果。

本次原始来源仍在远端，不改历史档。脚本：`extract_archived_population.py`（服务器 stdin 只读运行）、`recount_action_value.py`、`summarize_archived_diagnostics.py`。本地统计环境 `/opt/anaconda3/envs/CE/bin/python`；服务器读取环境原 AFDM Python，单线程。

## VALUE：动作空间的已测上限很小

|动作|错误 / 1024|FER|同 campaign 完整均值 s|
|---|---:|---:|---:|
|F0 / STOP|40|0.039063|0.354328|
|F0 + LOCAL|29|0.028320|0.362873|
|F0 + CSTATE|6|0.005859|0.364990|
|F2T|39|0.038086|0.986837|
|F2E|1021|0.997070|15.630672|

1. STOP、LOCAL、CSTATE 的正确集并集恰好等于 CSTATE 正确集：**最终 FER oracle 仍错 6 帧，新增正确 0**。换路由不能突破当前已测动作的最终 FER；需产生新的有效动作或候选。
2. 按逐帧正确标签与已测时钟做全知最小成本选择，平均为 **0.362833 s**，比 CSTATE 少 **2.158 ms/帧（约 0.59%）**。这里不计选择器成本且使用真值，属于该档案的乐观上界，不是可部署收益证明。选择 STOP 990、LOCAL 10、CSTATE 24 次；STOP 包含所有动作都错的 6 帧。
3. 0.5 s deadline：STOP / LOCAL / CSTATE 正确 **984 / 987 / 986**，全知并集 **988**。相对 CSTATE 仅有 **2 帧**时限覆盖空间；1 s 时并集与 CSTATE 均为 **1,018**。该 oracle 也不是已实现调度器。
4. 原有“native syndrome 非零才 CSTATE”就是合法可观测 B 策略；本轮没有在旧标签上训练或调参后冒称新门控。F1 的 12 次 LOCAL 触发中救回 11，但不存在全群体独立计时的 F1+LOCAL 臂。

**决策**：当前动作集合内，VALUE 可支撑成本/时限边界分析，尚不足单独成为新的 FER 方法贡献。优先把实验资源用于能改变候选覆盖的新动作。

## DIAG：近碰撞具有发生率与残余错误关联

以下阈值是本次读取前脚本固定的描述分箱，不是物理可辨识阈值，也不允许使用真实路径门控接收机。

|真实物理分组|帧数 / 1024|F0 错误 / 组内|CSTATE 错误 / 组内|F1 错误 / 组内|
|---|---:|---:|---:|---:|
|存在同延迟路径对|236|27 / 236|6 / 236|3 / 236|
|无同延迟路径对|788|13 / 788|0 / 788|9 / 788|
|存在同延迟 Doppler 间隔 ≤ 0.25|201|24 / 201|5 / 201|2 / 201|
|不存在上述 ≤ 0.25 对|823|16 / 823|1 / 823|10 / 823|

同延迟碰撞与 F0 错误相关（描述性 Fisher p = 1.17e-9），但 F1 中没有类似关联（p = 1）。全部 6 个 CSTATE 残余错帧有同延迟碰撞，5 个含 ≤ 0.25 对。不能据此断言“碰撞造成全部失败”，也不能把这 6 帧称独立确认。

F0 保存的两轮估计几何均无重复 delay；F1 两轮均有 **96 / 1024** 帧保留同延迟多槽。F1 第二轮中，间隔 ≤ 0.25 / 0.5 / 1 的帧数仅 **3 / 31 / 66**。真实碰撞数与估计多槽数不能逐项相减成“遗漏率”：未冻结匹配、增益或可辨识阈值；合并路径也可能准确表达可观测通道。

**决策**：CLUSTER 有真实发生率和针对强弱前端的机制差异，值得合法完整链干预。当前证据优先支持“以可观测通道簇为估计对象”的试验，不支持真实双路径恢复率或自动压缩自由度的主张。

## DIAG：闭合缺陷并非现成错误风险分数

用保存的 CE 矩阵与 CE gain 定义

\[
s=\operatorname{tr}(\Gamma)/P,\quad E=\Gamma-sI,\quad
r_F=\|E\|_F/\|\Gamma\|_F,\quad
r_h=\|Eh\|/(s\|h\|).
\]

这只是 **CE 阶段**精确矩阵和方向量。没有把它当作 TF 状态扰动、正规方程解差或 FER 证书。

|前端/CE轮|r_F 中位 / 最大|r_h 中位 / 最大|r_h 越大预测 native 错误的 AUC|
|---|---:|---:|---:|
|F0 第0轮|0 / 0|0 / 0|0.500|
|F0 第1轮|0.00408 / 0.08182|0.00409 / 0.06136|0.081|
|F1 第0轮|0 / 0.53768|0 / 0.82790|0.537|
|F1 第1轮|0.00612 / 0.49785|0.00555 / 0.73882|0.225|

第二轮是明显逆向关联：**不能沿用“闭合缺陷越大越危险”的直觉门控**。后验置信度、支持遗漏等混杂因素可能影响该量；当前未识别其因果来源。翻转分数再调阈值同样不能产生独立验证。

**决策**：DECISION 必须直接对接真正的 TF 更新与候选判决，或给出有假设约束的敏感性条件。单纯报告 Γ 非标量程度不能成为误码改善论据。

## DIAG：已存单点决策的覆盖已经嵌套

|前端|第0轮正确|第1轮正确|第0轮独有正确|两轮 + APP符号 oracle正确|
|---|---:|---:|---:|---:|
|F0|701|984|0|984|
|F1|727|1012|0|1012|

保留历史单点输出、再从其中选一个，不能新增正确帧。真正的 OSD/码字列表、模式权重及码字—几何联合候选没有在这套 raw 中保存；因此**真多模式覆盖未知**，不是零，也不能据此淘汰整个 MODES 方向。

后续最有区分力的最小试验：在旧开发观测上产生一个合法新候选，并完整计入候选生成、CE、TF、LDPC成本；共同参考为 CSTATE。是否进入新观测确认由该试验信号及概念差异决定。

## 可执行入口

远端完整源：`experiments/sp_afdm_native_joint_reviewed_20260921/src/native_twofft.py::receive`，调用现有 F0 pilot front、两轮 `time_refine -> scalar_joint -> decoder_messages`；接收输入只接受 `y/pilot/sigma2`。CSTATE 分支：`experiments/tf_cstate_validation_20260922/run_validation.py::_branch`。F1：`experiments/cstate_necessity_stageA_20260928/native_f1.py::receive_f1`。

依赖由原环境提供 numpy / scipy / torch 和冻结 LDPC cache；cache 位于 `experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz`。本地也有 `results/tf_cgr_mechanism_20260923_v2/qualification/local_v1/archived_reference_copy/frozen_reference/{native,baseline}` 副本。DATA 的新 namespace 完整链 smoke 由主代理执行，本报告不声称已完成它。
