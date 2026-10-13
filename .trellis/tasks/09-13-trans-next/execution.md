# Mission 执行入口

## 当前唯一入口：融合探索与条件验证

用户2026-09-14要求合并旧Trans与A/B探索CSV。新表接替两份来源表，Trellis仍复用本任务；此文件只挂静态引用，不镜像逐行状态。

- [唯一当前 CSV](../../../.mission/20260914_12-58-51-afdm-unified-exploration/20260914_12-58-51-afdm-unified-exploration.csv)
- [2026-09-17接续复核](research/tail-recheck-results-20260917.md)：原始264记录/3036数组、跨版本实际调用、三例CPU/CUDA资格与LLR描述；不替代候选/CONF/COST等科学门。
- [实际终端尾补全合同](research/tail-terminal-contract-v1.md)：接续已完成的TAIL/CWORD风险可行性，先原终端精确回放及工程报价，再按条件执行其余旧开发块；不替代原CONF/COST等后置门。
- [TAIL接续核验](research/tail-completion-recovery-review-v1.md)：新进程结果回执、累计计算账本及原文件回传限制。
- [新增理论与联合接收阶段合同](research/m3-final-plan-v1.md)：精简为追加11行；用户已于2026-09-14明确要求执行本CSV、deinlab GPU不可用则CPU，保留冻结预算。THEORY/PRED → 四oracle执行行及DICT/导频 → 共用状态分析 → 阶段review，不新开执行流。
- [当前融合计划](research/unified-exploration-20260914/plan.md)
- [迁移映射](research/unified-exploration-20260914/migration-map.json)
- [需求—证据合同](../../../.mission/20260914_12-58-51-afdm-unified-exploration/20260914_12-58-51-afdm-unified-exploration.claims.json)
- [来源哈希](research/unified-exploration-20260914/source-manifest.json)
- [工件校验](research/unified-exploration-20260914/validation.json)
- [Mission 决策日志](../../../.mission/20260914_12-58-51-afdm-unified-exploration/log.md)

用户现已明确授权执行融合CSV，GPU不可用时用CPU。当前按[冻结A/B合同](research/unified-exploration-20260914/ab-contract-v1.md)推进；正式CONF/COST、候选G1、跨场景和码配置依有效范围与预算授权启用。C及动态模型准备不研究。无候选可以阶段交接，不能关闭总研究。

阶段交接预定：融合目录 `stage-handoff.md`；最终审查与交接预定：同目录 `20260914_12-58-51-afdm-unified-exploration.handoff.md`。两者尚未产生，不冒称验收。生成后补静态链接，不提前归档。

## 冻结来源与科学依据

- [旧Trans来源CSV](../../../.mission/20260913_00-48-38-afdm-trans-next/20260913_00-48-38-afdm-trans-next.csv)：保留原始行、状态和证据，旧执行授权/continue_now仅为历史。
- [原A/B来源CSV](../../../.mission/20260914_11-44-58-afdm-two-direction-exploration/20260914_11-44-58-afdm-two-direction-exploration.csv)：规划来源，旧“另行执行流”安排已由融合替代。
- [A/B科学原因与文献](research/two-direction-exploration-20260914/analysis.md)：保留原文；路由以当前融合计划为准。
- [原Trans研究设计](design.md)、[原执行顺序](implement.md)：历史来源，未来按融合计划。
- [原始评审](../../../_archive/20260913_trans_reassessment/afdm_trans_research_reassessment.html)。

按 `trellis-import-mission` 静态挂接契约复用本任务；本项目此前缺少 `personal_ai_workflow.bridge`，本次沿用手工静态挂接，未声称调用bridge成功，未创建第二生命周期。
