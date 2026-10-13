# 当前执行入口：I1 确认、A/B 预检与 512 块成本（2026-09-11）

用户要求重排未完工作，并加入相邻研究报告；规划已提交 `3a851256`；用户随后授权直接在 deinlab 执行新 CSV，灵活并行。执行授权和资源上限见新 Mission 的 `evidence/execution-authorization-v1.json`。新范围取代下方全六家族 CONF 推进安排，旧数据、失败、预约与未答问题保留。逐行状态只查新 CSV，不在 Trellis 镜像。

- [新 CSV](../../../.mission/20260911_19-55-51-afdm-i1-cost-adjacent-pivots/20260911_19-55-51-afdm-i1-cost-adjacent-pivots.csv)
- [实验与排程计划](../../../.mission/20260911_19-55-51-afdm-i1-cost-adjacent-pivots/plan.md)
- [前序成果、Git 节点与九项处置](../../../.mission/20260911_19-55-51-afdm-i1-cost-adjacent-pivots/legacy-disposition.md)
- [新研究来源与哈希](../../../.mission/20260911_19-55-51-afdm-i1-cost-adjacent-pivots/source-manifest.json)

2026-09-12 最终数值结果：I1 固定 G0 强参考门通过；A/B 当前方案不晋级；正式 COST 每 SNR 512 块、N=1024，全流程 65.81 分钟，I1/A2 成本门通过，B_star_1 相关组保留不确定。后续仅建议保持 I1 性能的完整计算降本，本轮不追加实验。详见[总报告与下一步边界](../../../.mission/20260911_19-55-51-afdm-i1-cost-adjacent-pivots/evidence/final-findings.md)。下方开发中记录保留为历史；父研究任务、旧 20/29 与论文主张未改，最终逐行闭环及审查独立性以新 CSV 为准。

已确认：COST 每 SNR 512 个独立计时块，物理 N 不变；10 小时仅限 COST，其他任务另排。保留 I1 独立强参考确认，A/B 用独立开发数据有限预检，COST 最后独占；最多建议一个后续主方向，C–F 不自动启动。规划不是新实验或旧全范围验收，D_test/v3 HOLD 和父任务科学验收边界保持。

2026-09-12：共享 I1 开发与 A 冻结态预检已完成原始审计；A 本次规则局部更新慢 34.34%，裁决 STOP_CURRENT_RULE。见[预检证据](../../../.mission/20260911_19-55-51-afdm-i1-cost-adjacent-pivots/evidence/route-a-precheck.md)。确认仍保持盲态，B 与最终成本继续按 CSV 推进；本记录不改变论文主张。

2026-09-12：B 新增 1280 F 与全部原始数组审计完成，固定留出池未满足晋级门；同时区间仍宽，不外推为整条路线无空间。见[B 预检](../../../.mission/20260911_19-55-51-afdm-i1-cost-adjacent-pivots/evidence/route-b-precheck.md)。A/B 输出在打开确认结果前锁定。

按 trellis-import-mission 的静态挂接契约复用本父任务。项目环境没有可导入的 personal_ai_workflow.bridge，使用现有 execution.md 手动挂接；未另建任务生命周期或逐行状态副本。

---

# 历史执行入口：全问题补充实验（2026-09-11，新范围已取代）

用户已确认执行完整补充 CSV，并要求主会话推进、保护 deinlab、保留 git/Trellis 回滚点。逐项状态只在 CSV；本文只挂接入口。旧 v3 HOLD 与 D_test 仍封存。

- CSV：[全问题补充实验](../../../.mission/20260909_09-01-15-afdm-comprehensive-supplement/20260909_09-01-15-afdm-comprehensive-supplement.csv)
- 协议：[plan.md](../../../.mission/20260909_09-01-15-afdm-comprehensive-supplement/plan.md)
- **当前检查点：** [supplement-takeover-20260910-codex.md](research/supplement-takeover-20260910-codex.md)
- 前序 Grok 检查点：[supplement-progress-20260910-a01-s01.md](research/supplement-progress-20260910-a01-s01.md)
- 前序检查点（DET 追加 runner / 16T 门）：[supplement-resume-20260910.md](research/supplement-resume-20260910.md)
- 当前执行：S-01六单元3456成功F已收齐，保留两次失败和192条旧记录的哈希缺口；H/M/DET-01R证据审查完成。A-01桥接自拟合退化、I-02时延/残差记录缺口待补。G1的B_star单元576F已完成、原始数组审计通过；S-01候选代表覆盖仍需核对和补齐。A-01正接回历史合法物理搜索。CONF及COST-02正式计时尚未准入；D1仅为开发参考，16T不重跑。

---

# 当前执行入口：方向判别（2026-09-08用户授权）

用户明确要求执行新CSV直到完成，服务器运行及心跳获准。Trellis保持研究生命周期权威；逐行状态仅在下列CSV。旧v3 HOLD与封存D_test保持。

- CSV：[方向判别CSV](../../../issues/2026-09-08_21-06-44-afdm-direction-decision/2026-09-08_21-06-44-afdm-direction-decision.csv)
- 协议与账本：[目录说明](../../../issues/2026-09-08_21-06-44-afdm-direction-decision/README.md)
- 源计划：[字节快照](../../../issues/2026-09-08_21-06-44-afdm-direction-decision/source-plan.md)
- 交接：[方向判别施工交工单](../../../issues/2026-09-08_21-06-44-afdm-direction-decision/2026-09-08_21-06-44-afdm-direction-decision.handoff.md)
- 独立验收：[最终审查](../../../issues/2026-09-08_21-06-44-afdm-direction-decision/evidence/vision-review.md)。研究父任务及科学主张仍需用户验收；逐行结案状态只查CSV。

---

> 当前授权更新：用户要求执行v3 CSV直到完成。下方仅规划说明为生成时历史，现由新CSV维护执行状态；不继续旧v2 CSV。

# 当前入口：v3诊断完成 / HOLD（2026-09-08）

用户已直接确认「允许上传并执行 v3 CSV」和「采用增广实 Gaussian 修订」。v3诊断已完成，旧v2结果与未提交工作保留，旧v2 CSV不继续执行。远端自动审批引用旧planning-only的阻塞已由用户新确认解除。

- 交接报告：[v3施工交工单](../../../.mission/20260907_23-36-31-afdm-causal-plan-v3/20260907_23-36-31-afdm-causal-plan-v3.handoff.md)
- 科学裁决：[findings](research/findings.md)
- 当前方案：[v3研究计划](research/next-execution-plan-20260907-v3.md)
- 新任务CSV：[v3 CSV](../../../.mission/20260907_23-36-31-afdm-causal-plan-v3/20260907_23-36-31-afdm-causal-plan-v3.csv)
- 使用与验收说明：[README](../../../.mission/20260907_23-36-31-afdm-causal-plan-v3/README.md)
- 旧任务处置：[59项范围映射](../../../.mission/20260907_23-36-31-afdm-causal-plan-v3/v2-disposition.md)

子代理GPT-6默认low，普通最多medium，仅纯数学必要时可high；主会话承担主要推导及inline实现/检查。Trellis仍为父任务生命周期权威，新CSV维护当前逐项状态。本轮真实计算和分析已完成；研究路线HOLD，Dtest和原G1/G2/G3不变。最终实现审核按批准方案由主会话完成，独立性weak；不将GPT-6 low的科学解释复核冒称独立实现审计。

---

# Mission执行入口：AFDM计划v2

本记录只挂接静态执行产物。Trellis保留父任务生命周期；CSV是逐项任务状态唯一权威。

- 源方案：[下一轮v2](research/next-execution-plan-20260906-v2.md)
- 执行CSV：[2026-09-06_13-47-38-afdm-plan-v2.csv](../../../issues/2026-09-06_13-47-38-afdm-plan-v2/2026-09-06_13-47-38-afdm-plan-v2.csv)
- 承诺账本：[2026-09-06_13-47-38-afdm-plan-v2.claims.json](../../../issues/2026-09-06_13-47-38-afdm-plan-v2/2026-09-06_13-47-38-afdm-plan-v2.claims.json)
- 使用说明：[README](../../../issues/2026-09-06_13-47-38-afdm-plan-v2/README.md)
- 生成结构检查：[2026-09-06_13-47-38-afdm-plan-v2.validation.json](../../../issues/2026-09-06_13-47-38-afdm-plan-v2/2026-09-06_13-47-38-afdm-plan-v2.validation.json)
- 最终愿景验收：CSV的REVIEW-01；未来handoff目标为同目录`2026-09-06_13-47-38-afdm-plan-v2.handoff.md`，当前未生成。

本次授权是按v2生成完整CSV；没有启动其中实验、打开Dtest、接受新增S1计时预算或修改论文。今后逐行执行进度只更新CSV与证据账本，不在Trellis复制一份任务状态。

挂接方式：遵循trellis-import-mission静态契约手动关联已有父任务。当前项目没有`src/personal_ai_workflow`，skill辅助脚本依赖的项目模块不可用；未另建生命周期、安装依赖或复制任务清单。

## 2026-09-06执行授权增补

用户当前目标明确要求执行本CSV并完成、灵活并行；上文“本次仅生成”属于生成时历史范围。今后以CSV真实证据更新执行状态；S1追加预算、Dtest预登记和研究主张门不变。
