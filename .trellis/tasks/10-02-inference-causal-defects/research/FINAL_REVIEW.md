# 独立愿景审查：AFDM 主推断因果缺陷

- review_result: vision_met
- claim_supported: no（对象：新实用主推断机制及同预算收益）
- review_agent_mode: direct-spawn-agent
- review_independence: strong
- review_actual_model: runtime identifier unavailable; inherited parent model without override
- validation_limited: model parity unknown by runtime identity；配置指定的 gpt-6-sol 不可用，本次使用主会话继承模型，未选择弱模型替代
- claim_coverage: 8/8
- claim_coverage_status: complete
- explicit_requirement_coverage: 7/7（5 个问题 + 2 个推导约束）
- handoff_contract: passed（内容合同；机械排版检查由主会话执行）
- gaps: []
- 审查日期：2026-10-03

## 结论及其范围

批准计划允许前置模型/消息门失败后，以证据化 no-go 关闭后续性能行（PLAN.md:52）。此次交付满足这条明确允许的完成路径，因此为 **vision_met**。这个词只表示批准的诊断、反馈、候选准入判断和交付合同完成；不表示提出了成功的新算法。新主检测器未实现或准入，完整同预算因果/FER 比较及独立性能确认未运行，对这些实用主张的独立 result-to-claim 为 **no**。

直接检查最终 CSV：14 个非 REVIEW 行的开发、初审、回归均为已完成，Git 为已提交；各 notes 引用的 commit 均可解析为真实提交。所有 required_mcp 为空。REVIEW-01 此时处于本次审查流程中，其提交和关闭由主会话在收到本报告后执行，不在这里伪称已经完成。

未发现需追加实现或实验的可证伪缺口。生产困难帧的真实联合余项、完整新接收闭环及同预算效用确实没有证据；交付明确披露这些限制，而批准计划的准入失败分支并不要求绕过前置门去强造后续实验。

## 独立性、输入和实际验证

本审查先读 PLAN、全部 CSV 验收条件和初始 claims，再独立读诊断源码、测试及原始结果，最后才核对主会话最终映射与交接。未把主会话总结或其他研究代理的结论作为唯一证据。实际读取范围包括本任务 8 个 Python 诊断模块、5 个直接读取的测试文件以及其余测试收据/哈希、原 twofft 的增益/方差/反应/CE 实现、模型合同、联合消息推导、准入说明、最近邻文献映射及各诊断报告。模型和分支事实主要经静态源码核对；本审查不声称重放了完整级联。

独立数值核验没有调用已有 remainder/slr 计算函数：对保存的每个 d 条件高斯 h 后验，构造对二次多项式精确的对称确定性求积点，直接计算物理响应 f、切线及余项；再对全部加权中心化实坐标与响应做 `numpy.linalg.lstsq`，独立重建最优仿射投影。给定 d 后 f 对 h 是仿射的，因此这些求积点精确覆盖此处所需二阶矩，既没有随机抽样，也没有新似然/后验推断调用。

实际结果：

| 独立检查 | 结果 |
|---|---|
| oracle/remainder/SLR 注册源码、输入和原始 NPZ 哈希 | 214 项匹配 |
| 96 条 oracle 保存记录：归一化、LLR 概率、h/d 均值、h 协方差、概率 MSE 与 sharpness | 最大差 ≤ 8.89e-16 |
| 48 个条件：直接求积余项能量、均值能量、线性—余项交叉项 | 最大差 3.219646771412954e-15 |
| 48 个条件：独立加权最小二乘仿射残差 | 最大差 6.661338147750939e-16 |
| 有 pilot 的最优仿射残差门 | 1/24 通过，保持原门 0.1 N sigma2 |
| 256 条状态表与 256 条先验干预记录摘要 | 文件绑定及报告均值复算一致 |
| 本次数值复算 CPU / 实际线程 | 0.267652 秒；Accelerate calling-thread mode 1，五个线程变量均为 1 |
| 新 receiver / oracle 调用 | 0 / 0 |

另外核对 `execution/checks/suite_v1.json` 与 `oracle_suite_v1.json`：10 + 26 项通过，当前所有列出的源码/测试哈希匹配。这里是核验现存运行收据，没有重复运行这 36 项测试。原始线性极限中的数据因子替换被明确标为严格已知输入诊断，未冒称合法生产 QPSK 接收。整体没有专门的 EXPERIMENT_AUDIT.json，因此 result-to-claim 保留 provisional integrity 标签；本次有强独立源码/原始数值审查，不等于全范围外部实验完整性审计。

## 八项声明逐项覆盖

下列“覆盖”是审过承诺与证据，并不表示每个正向科研猜想成立。execution/reviews 路径按任务根解析；未带前缀的诊断源码/文档按 experiments/afdm_inference_causal_20261002/ 解析；研究文件位于本 Trellis 任务 research/。

| 声明 | 对账结论 | 主要证据 |
|---|---|---|
| CLAIM-MODEL | 模型/分支及先验区别已定位；同接口干预隔离了初始化因素，未证明主要 bug | `LINEAR_LIMITS.md`、`PRIOR_INTERVENTION.md`；`execution/prior_intervention/{registration,result}.json` 与 `records.jsonl`；研究 model-contract |
| CLAIM-IDENT | 方向表达缺口成立；实际失败关联不足且存在选择/阶段混杂 | `STATE_DIAGNOSTICS.md:27`、`:41`；`execution/state_diagnostics/states.jsonl`、`summary.json` |
| CLAIM-ORACLE | 独立生成模型下精确枚举/增益积分及真实 scalar 对照成立；受限 N=2/3 | `exact_oracle.py`、相关测试；`execution/oracle/comparison_v1/results.json` 和全部 96 个 raw |
| CLAIM-JOINT | 完整仿射 Gaussian 均值/协方差与合法因子删除可核验；原双线性实用闭环未成立，标 conditional_no_go 合理 | `gaussian_blocks.py`、4 项合同测试、研究 joint-message-theory；remainder/SLR 原始证据 |
| CLAIM-NOVEL | 最近邻公式映射扣除了标准工具和旧贡献；无新颖性过度宣称 | 研究 literature-neighbors 的原文链接、公式定位、读取限制；本地 twofft 已有 P·vh·vx |
| CLAIM-CORE | 准入失败，未实现生产替换；production_path_required 保持 true，记录条件性不适用而非通过 | `ADMISSION.md:5`；PLAN.md:52；SLR 全正支撑与门失败 |
| CLAIM-CAUSAL | 无合格候选，按依赖关闭 MECH/FRESH；无同预算/新鲜性能结果，未借诊断成本包装性能 | `ADMISSION.md:13`、`:19`；`reviews/result-to-claim.json` |
| CLAIM-CLAIMS | 最终因果证据表和人类交接保留阴性结论、替代解释及未验证空间 | `FINDINGS.md`；同名 handoff；最终 claims JSON |

## 用户五个问题与两个推导要求

1. **同一统计模型？** 固定已知输入下 CE 的 sigma2 I 与 joint 有限固定点的 P sigma2 I 不同；源码将 CE 定义为初始化。固定反馈接口的干预支持扰动通常衰减，不支持将目标切换直接定性为错误、发散或 FER 根因。
2. **标量是否丢信息？** 条件 covariance 通常非标量，null 方向保留先验方差；物理与人工例子的适用性区分清楚。实际 256 帧包含成功和失败，没有失败挑选。六失败全在 f1_cstate、该阶段无成功，不能得出阶段调整后的因果估计。
3. **耦合遗漏是否造成过度自信？** 实际 joint 与 point/plug-in/精确边缘乘积对照的含义明确。有 pilot 时 joint 概率 MSE 约 .006657，平均 sharpness gap 为负；这反对 blanket overconfidence，而不是证明 joint 精确。精确边缘乘积保持 LLR，直接反驳“少交叉矩必然导致 LLR 错误”的无条件推理。
4. **新推导是否修复？** Gaussian 仿射参照恢复所声明极限与协方差块，但原双线性候选在余项门失败，故不能给出新检测器修复成功结论。最佳仿射修订也失败，排除了仅换切线中心/斜率即可满足本门的解释。
5. **有无同预算实际价值？** 未证实。没有完整新主检测、同总耗时/FFT/算子/求解/LDPC/内存曲线或独立 FER 结果；这些项依据原先条件门关闭，未被小模型误差和短运行时间替代。
6. **Ch 来源及合法外信息。** 推导采用原始独立先验或明确存储 site 的 cavity 除法，不将任意同 y 后验重用为新先验。Gaussian 删除与 partial Jacobian 被核验；完整 coded/relinearized EP 的稳定性和全局目标未被证明，也未声称已部署。
7. **双线性余项。** 不仅有独立误差公式，还对真实小模型混合后验保留均值、能量和交叉项，再作全实仿射投影及正支撑检查。对 N1024 六个真实失败帧的真实后验余项未计算，最终 FINDINGS、ADMISSION 和 handoff 均明确披露；小模型困难条件没有被当成这些生产帧的直接证据。

## 科学范围、成本和依赖判断

- 48 条件与两初始化形成 96 记录，但只有 6 个独立外生随机簇；不允许按 96 独立样本做显著性推断。256 个旧帧已揭盲，六失败的探索 bootstrap 未经多重校正且混杂严重，不能转成独立确认。
- 1024 次固定接口 scalar 调用与 192 次小模型 scalar 调用是真实诊断工作。两种先验臂在对应 20/40 步内匹配工作；这没有测出新方法完整预算效用，20 对 40 也不是创新收益比较。
- no-go 仅针对“单一全局仿射并忽略残差”候选与预设工程 screen。最优仿射残差高于阈值不证明仿射方法必然有坏 LLR，更不排除显式残差、非线性或模式条件化方法。阈值 .1 不是所有可用算法的数学必要条件。
- 精确 posterior SLR 系数属特权诊断量，不是合法可部署 cavity。全正支撑结果强化了这个特定候选门失败证据，没有制造实用机制。
- 普通任务之间的依赖通过推导、诊断及显式不准入传递；允许最多两次修订并不强迫用完额度。一次有针对性的修订失败后关闭此分支符合 PLAN，并非降标用“未运行”冒充成功。
- 最近邻检索范围是有原文公式依据的定向核对；未复做网络全文检索，也不据此宣称文献穷尽或首创。报告本身保持了这个限制。

## 交接与后续动作

同名 handoff 能独立说明任务目标、实际新增内容、五加二对账、关键负结果、36 项测试、独立数值复核、未运行性能实验、统计范围与复现入口，不需要靠 CSV 猜出科学结论。指定候选关闭与仍未验证的其他推断空间分开，符合施工交工单的诚实交付要求。

没有需要追加 follow-up issue 的 factual gap。本审查未修改生产源码、旧结果或 CSV，也没有新仿真/远程调用。主会话剩余动作仅为持久化本审查、完成机械 handoff 检查并提交/关闭 REVIEW-01；不得把本次 vision_met 改写为 practical claim_supported=yes。
