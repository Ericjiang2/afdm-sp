# CSTATE Stage B 接续：阶段汇报

本轮恢复并完成了具体故障诊断、F2 数值修复和单帧完整验证。**完整 Stage B 尚未完成；F1/CSTATE 总体裁决仍为 UNRESOLVED。** 原 TF+CSTATE / Stage-A 结果与全部失败记录保留，无新 Monte Carlo，无新 truth 分析。

| 问题 | 本轮证据 | 允许的结论 |
|---|---|---|
| F1-fast 的995/1002计数差异 | [原顺序前缀](F1_PREFIX_RESULTS.md)：183秒，198帧、409/409 wrapper通过；旧差异未复现；[独立元数据重计数](independent/F1_PREFIX_RECOUNT.json) | 历史差异仍未解释，不能冒充1024帧等价通过 |
| 最小保守 F1 修复 | [候选](F1_COMPAT_CANDIDATE.md)：恢复 Stage-A 坐标/response/refit/接受残差路径，仅保留共轭缓存和重复项批量屏蔽；合成3/3与独立定向审查通过 | 代码候选就绪，真实1024帧门尚未执行 |
| F2 首次真实尺寸失败 | [失败](F2_PROBE_OUTCOME.json) → [捕获](F2_QP_CAPTURE_OUTCOME.json) → [离线诊断](F2_QP_OFFLINE_DIAGNOSIS.json)：第22个155维QP，条件数524.38，100次迭代未成功 | 数值坐标问题；不等于F2通信性能差 |
| F2 修复是否可执行 | [等价变量变换](F2_NUMERICAL_AMENDMENT.md) → [合成资格](F2_NUMERICAL_FIX_QUALIFICATION.json) → [真实v2](F2_PROBE_V2_OUTCOME.json)：完整1帧、2个checkpoint、79次QP成功，最大23次迭代 | 此输入的完整接收链可运行；不是总体误码率或整体收敛证明 |

F2 v2 实测：含一次性预检20.2746秒；接收及raw保存15.9764秒；估计器15.6718秒。主要组成：dense H 5.783秒、感知矩阵4.825秒、后验2.755秒、grid1.582秒、LMMSE0.510秒。EM有3/4轮触及上限，数据反馈也触及上限；所有79个QP按ftol退出，不能据此声称整体达到收敛阈值。最终 syndrome=323，仅是无truth的接收状态，不代替信息比特FER。

## 尚缺什么

- F1新候选：冻结完整runner/预算后，完成1024帧几何、参数、TF入口、最终比特等价与当前时钟检查。
- F2：真实P155的CSTATE/LOCAL交接、F2T资格，以及冻结后的F2E/F2EC/triggered-F2总体比较。
- 最终风险–成本前沿、总体FER/BER与deadline表。现有诊断不足以判定CSTATE被替代或具有独特必要性。

单帧16秒线性外推，F2E单臂1024帧约4.5小时；这只是量级，未覆盖额外分支且不构成完整预算。旧F1前缀外推原2112调用约16分钟；新保守实现可能更久。按用户优先快速阶段汇报的要求，本轮没有启动这些长批次；任务保持in_progress，长计算安排已询问，未收到回答不算批准新的安排。

## 检索路径

[当前入口](README.md) → 本报告 → 表中具体问题 → 冻结计划/源码与小收据 → 远端raw/checkpoint的SHA256与MD5。[F2单帧独立元数据复核](independent/F2_V2_RECOUNT.json)限定于小文件、调用数与时间记录，不冒充raw重算。原始NPZ保留deinlab；为离线对比短暂下载过的QP及f197副本已核对远端后清理。归档如实记录临时复制过程。旧失败不被覆盖，前缀不写人口封存，单帧不冒充总体。
