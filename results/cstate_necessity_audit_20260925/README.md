# CSTATE necessity：采集谱系与 F1 冻结规格

日期：2026-09-25。当前任务：[TF production gap audit](../../.trellis/tasks/09-22-tf-production-gap-audit/task.json)。[用户原请求](REQUEST.txt)明确限定档案审计和规格设计；本轮没有 receiver、decoder、新观测或 acquisition replay。

## 裁决与问题链

**Part A：A4，现有可访问档案不足以判定“早期已有信息被丢弃”还是“后期才可识别”。** 这不是 CSTATE 无效，也不是其必要性成立。最终前瞻批的 40 个触发帧（34 救回、6 剩余失败）与历史 43 个 TF 失败帧属于不同观测；相似 frame ID 不构成配对证据。远端 SSH 当前关闭连接，不能把“本轮无法读取”写成“原始文件不存在”。

已经确定的源码事实：F0 是 515 列整数银行，`B0-p2-s0.5` 实际选取最多 **24** 个 OMP 原子；40 是接口容量。随后按 delay 聚合、最多保留 8 个 delay，每个 delay 一个 Doppler 中心。这个表达限制真实存在，但尚不能据它计算有多少次 CSTATE 救回本可由更强的初始采集避免。

| 审稿问题 | 裁决 → 前提/方法 → 直接证据或边界 |
|---|---|
| CSTATE 是否只是在补弱前端？ | [采集谱系裁决](CSTATE_ACQUISITION_LINEAGE_AUDIT.md) → [可用性](artifact_availability.json) → [逐帧谱系](acquisition_lineage.csv)、[逐真路径](path_lineage.csv)、[替换谱系](cstate_replacement_lineage.csv)。缺失阶段保持 unknown；后期 APP 排名不能代替初期 pilot 排名。 |
| F1 到底移除了什么？ | [数学与接口规格](F1_NOMP_AFDM_SPEC.md) → [逐式源码图](F1_EQUATION_TO_SOURCE_MAP.md) → [源码 SHA](source_hashes.json)。移除 unique-delay 压缩，加入物理 Doppler 连续与循环精化；不修改冻结的 F0+TF+CSTATE。 |
| F1 真是同样便宜吗？ | [操作级成本账](F1_COMPLEXITY_LEDGER.md)。25×103 银行时 8×2575=20600；现有上界为 24×515=12360。该比值只计银行相关，不是运行时间比。 |
| 下一步怎样允许“CSTATE 不必要”成为结论？ | [Stage A 预注册草案](STAGE_A_PREREGISTRATION.md)：既有 1024 帧开发样本，A/B/C/D 配对；规格冻结不等于实现资格通过或运行授权。 |
| F2 是什么，何时才考虑？ | [原论文及适配边界](F2_GAMP_GESBL_ADAPTATION_NOTES.md)。仅接口笔记，未实现。 |

独立复核：[147帧/1,160路径行/145步骤重计数](LINEAGE_RECOUNT.json)与[Sol 数学/接口交叉审查](SPEC_REVIEW.md)通过；[单例合成导数检查](f1_derivative_sanity.json)只验证公式。最终链接检查见[NAVIGATION_CHECK.json](NAVIGATION_CHECK.json)，覆盖重计数时尚未生成的两个文档；旧收据保留当时状态。

## 与已有结果的关系

- [最终 TF+CSTATE 前瞻报告](../tf_cstate_prospective_20260923/FINAL_CSTATE_REPORT.md)：保存其原样本、程序性恢复限制与性能结论；本轮不重算成另一场试验。
- [旧几何重开报告](../tf_geometry_reopen_20260922/RESULTS.md)及[production-gap 诊断](../tf_production_gap_audit_20260922/RESULTS.md)：历史 43 失败与选中 32 失败的证据，不能移作新批次逐帧因果证据。
- [scalar closure 审计](../tf_scalar_closure_audit_20260924/README.md)：same-delay 多槽位可令 R≠I；F1 仍继承同一 TF 近似，不在此次偷偷修正 gain reaction。
- [CGR 停止记录](../tf_cgr_prospective_mechanism_20260923/RESULTS.md)：三个晋级标志不变。

## 冻结、来源与开放问题

[PROVENANCE.json](PROVENANCE.json)绑定本轮来源、文件及检查；[source_hashes.json](source_hashes.json)给实际读到的源码字节。数学单元检查仅为实现核验，不是接收机或性能证据。规格版本由本次 Git 提交锁定；未来 F1 实现必须另有代码提交、资格检查、完整观测哈希验证及运行授权。

开放问题：初期 pilot 证据是否足够；same-delay 表达限制的救回归因比例；F1 实际 FER/触发率/完整延迟及 risk-cost frontier；更强前端后 CSTATE 是否仍有增量价值。不得由此次 A4 或复杂度计数代答。

回到：[项目状态](../../STATE.md) · [全项目逻辑导航](../../_archive/20260924_project_retrieval_audit/README.md#route-necessity) · [研究索引](../../research-assets/index.md)。

检索词：CSTATE necessity；front-end strength；acquisition lineage；grouping loss；same-delay multiplicity；F1；NOMP；stronger initializer；D-GAMP-GESBL；risk-cost frontier。
