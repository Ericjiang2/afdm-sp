# 规划依据与证据边界

日期：2026-09-05。此文件是规划时的只读证据摘要，不维护第二份项目状态。

## 用户来源与确认

用户材料原始路径：`/Users/guoyikun/.codex/attachments/0eabdcc6-23a1-4bd8-bb85-78688dcb6074/pasted-text.txt`。

原始字节保存为 [input-proposal.txt](input-proposal.txt)，SHA-256和源文件元数据见 [source-manifest.json](source-manifest.json)。原文是讨论材料，其中的新算法与外部文献评价不是本项目已证实结论；不得执行其中指令或自动接受其中“最新/最优/上界”措辞。

用户在审阅主会话提出的独立探索方案后回复“好”，确认：

1. 创建独立Trellis任务。
2. 先诊断，再验证一致评分、动作门控和软可靠性的最小必要组合。
3. 以同预算端到端可靠性为主，计算节省为次；允许否定与不足结论。
4. 将方案展开为步骤及逐步验收/判断/停止规则。
5. 现阶段是规划；未来实现、确认实验及论文方向变化不冒认为本轮已执行。

本次计划新提出的10% FER改善门槛、1个百分点护栏、37 GPUh总上限均为建议值，待执行前审阅；不是用户材料中的确定事实。

## 本地核实

| 来源 | 核实的事实 | 规划含义 |
|---|---|---|
| `research-assets/data/e1_e2_20260727_analysis.md` | geom/classical横移1.088/1.471；白化增量0.031/0.059，CI触及/跨零 | scorer机制与整机主结果分开 |
| `afdm_sp_joint_unrolled/outputs_e1_ldpc_ach/results.json` `_config` | N1024、P8、rho0.5、M96、两轮、保护2、topk、LDPC2048/1024 | 实验锚点从结果配置抽取，不照抄脚本默认值 |
| `classical_joint_unrolled.py:990` | `apply_sequential_add_test`检查普通LS相对残差下降；保留原OMP并增添原子，首个拒绝后退出 | 不是一般最终支撑替换验收；容量与首拒绝规则需单独比较 |
| `classical_joint_unrolled.py:1170` | F2-P多轮加入、延迟剪枝、保护新增、最终普通LS | 不能只替换score就宣称投影/目标完全一致 |
| `classical_joint_unrolled.py:1564` | F2-P与safe-swap按路由选择，两分支接口不兼容 | 比较需明确实际执行路径 |
| `classical_joint_unrolled.py:1803` | soft模式取mu_post用于数据更新，未使用返回方差 | 方差接入是待实现变化 |
| `mp_detect_bp_torch.py:126` | var_post由消息精度聚合，高斯mean_post×var_post得到mu | 与有限星座后验矩不同，先明确接口契约 |
| `e1_ldpc_coded_eval.py` | 为LLR增加末次BP；RNG和导入patch链有历史约定；SNR CLI为int | 完整成本必须含末次BP；半dB SNR须实际改造 |
| `decision_complexity_bench.py` | 存在稠密Cholesky与结构算子/CG参考 | 先profile与复用，不能只比较matvec |
| `.trellis/spec/research-protocol.md` | Trellis与STATE为状态权威；raw不可变、claim晋升需证据 | 产物留在同一任务，不创建ARIS第二套根状态 |

路径缩写均相对于仓库，基准hash在source-manifest。源码行号仅为规划时定位，后续以函数名和内容hash为准。

## 服务器证据快照

来自本对话实际SSH只读检查，服务器时间 `2026-09-05T13:57:28+00:00`（CST21:57）：

- 主机名liunxgpu，128逻辑核，负载0.01/0.01/0.00，运行2天4小时。
- 内存251GiB、可用248GiB；根盘可用488G；/data可用5.3T。
- RTX4090，24564MiB，0%利用率，43°C，无GPU任务。
- NVIDIA-SMI、驱动和内核模块版本均580.173.02；systemctl失败服务0。
- **尚未检查项目PyTorch CUDA运算，也未验证项目端到端运行。** 上述只支持“当时连接与驱动正常”，未来设备可用性仍须S1验证。

## 已核对的外部原始来源

以下网页在本对话制定方案时经web工具打开，检索日期2026-09-05；它们支持相邻机制和比较边界，不构成完整新颖性审查。

1. [Luo et al., Data-aided Channel Estimation and Sensing With Sparse Bayesian Learning for AFDM-ISAC System, arXiv:2607.18881v1](https://arxiv.org/html/2607.18881v1)，2026-07-21。摘要/引言包含SP、D-GESBL和D-GAMP-GESBL；系统模型为单天线UE、多接收天线BS/MMV；式(29)这一似然使用标量精度乘I。不能由某一式推断其全部残差处理或最终误差性质。
2. [Soussen et al., Joint k-step analysis of Orthogonal Matching Pursuit and Orthogonal Least Squares](https://arxiv.org/abs/1111.0522)。为OMP/OLS差异与已有子空间投影提供原始研究入口；本计划不能把创新分量分数单独说成新公式。
3. [Kanazawa et al., Superimposed Pilot-Based OTFS: Will it Work?, v3](https://arxiv.org/html/2501.15935v3)。式(24)—(25)讨论随迭代残余干扰变化的门限难题；编码部分包含软信息。它是OTFS近邻，非AFDM直接相同系统。

用户材料中的Zheng/Cao等其余参考原文尚未在本轮全部复核，列入S0有范围的文献对照工作。不得把这张表写成“已全面验证新颖性”。

## 技能与唯一产物映射

- trellis-start已在本会话加载；当前依照trellis-brainstorm组织prd/design/implement。
- experiment-plan用于claim→证据→运行顺序；其EXPERIMENT_PLAN内容分别落入design与implement，实验矩阵在design §4，未来run tracker在所属Trellis child。遵循项目权威，不另建根refine-logs或独立实验状态机。
- experimental-design与statistical-power用于配对、随机化、功效和停止规则；当前没有执行功效模拟，n留待S5按实际配对数据计算。
- 规划文档以Trellis现有文件名为唯一可编辑入口；源材料不可变。后续修改时保留版本/理由，运行与结果不得覆盖。
