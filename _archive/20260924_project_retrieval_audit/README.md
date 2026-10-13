# AFDM 研究历史与证据导航（2026-09-24）

本页回答“当时问了什么、得到什么答案、证据在哪里”。它是**检索导航，不是新状态系统、结果晋级或重新裁决**；当前任务状态只查 [`STATE.md`](../../STATE.md) 和对应 Trellis/Mission 任务。历史稿、外部 Pro 材料和无效尝试按原时点保存，不因后来结论被抹去。表内“答案”只概括所链权威记录；精确样本、门槛、负结果和成本以原报告为准。

## 按审稿问题进入

新增问题：[Q10 CSTATE必要性与更强前端](#route-necessity)。

阅读顺序固定为**裁决 → 比较合同 → 方法/源码 → 直接封存证据与复核 → 限制/修正**。下列“外部来源”只是问题或假设输入；“导航”仅指路；“直接证据”是运行记录/封存结果；跨记录综合句标为“审计推论”。需要复算前先看该路由的分母、接收机阶段和真值开放时间。重型 raw 若只留远端会显式标明，不能把本地摘要当成已回收全部 raw。

| 稳定问题入口 | 先读哪条证据链 |
|---|---|
| <a id="q1"></a>Q1 最终 TF+CSTATE 性能/成本证据是什么？ | [接收机选择与前瞻链](#route-receiver)，再读 [CSTATE 合同](#route-cstate) |
| <a id="q2"></a>Q2 为什么 TF 取代旧 learned 主叙事？ | [接收机选择与前瞻链](#route-receiver) |
| <a id="q3"></a>Q3 CSTATE 触发、额外计算和 APP/check 接线在哪里？ | [CSTATE 合同](#route-cstate) |
| <a id="q4"></a>Q4 CGR 为何停止；BLOCK 伤害能否归因？ | [CGR 固定门与隔离](#route-cgr) |
| <a id="q5"></a>Q5 scalar closure 式 (3)/(4) 假设与可写结论？ | [理论/源码/数值链](#route-scalar) |
| <a id="q6"></a>Q6 旧40/1024 与新0/256是否矛盾？ | [同阶段比较链](#route-reconciliation) |
| <a id="q7"></a>Q7 G0/G1 物理外推为何受限？ | [历史分支与未晋级门](#route-alternatives)，优先看 G0 披露卡 |
| <a id="q8"></a>Q8 TAIL 有哪些完成与开放门？ | [历史分支与未晋级门](#route-alternatives)，优先看 TAIL v5/接续复核 |
| <a id="q9"></a>Q9 旧 learned 增益数字与归因如何并读？ | [接收机选择与前瞻链](#route-receiver)第一句同时连旧卡和7月终裁 |

<a id="route-receiver"></a>
### 为什么从旧 learned/候选路线转向 TF+CSTATE？

**裁决**：[旧 learned headline 卡](../../research-assets/res-20260610-01.md)保存当时数字；[7月 canonical claim audit v4](../claim_audits_20260726_20260727/AFDM_claim_audit_v4_20260727.html)重新限定其中“architectural learning contribution”的归因，两者须并读；[native 接收机结果](../../results/sp_afdm_native_joint_20260921/RESULTS.md)回答 TF 计算路线取舍。**合同**：[PD1-Q Part A](../../results/sp_afdm_pd1q_part_a_20260921/RESULTS.md#numerical-qualification)是数值/成本资格，[Part B](../../results/sp_afdm_pd1q_part_b_20260921/RESULTS.md#primary-reliability)才是当时 TF 前瞻性能；两者的样本和结论不相互替代。**方法/源码**：冻结 [twofft.py `scalar_joint`](../../experiments/sp_afdm_native_joint_20260921/src/twofft.py) 定义 TF20 数据/增益更新；[CSTATE 分支入口](../../experiments/tf_cstate_validation_20260922/run_validation.py)定义后续结构重开。**直接证据 → 复核**：[Part B 成本与原始证据边界](../../results/sp_afdm_pd1q_part_b_20260921/RESULTS.md#provenance-and-retention) → [TF+CSTATE 恢复后前瞻报告](../../results/tf_cstate_prospective_20260923/recovery_20260923/analysis/RESULTS.md) → [恢复核验收据](../../results/tf_cstate_prospective_20260923/recovery_20260923/verification/receipt.json)。**程序资格/修正**：[最终 CSTATE 报告](../../results/tf_cstate_prospective_20260923/FINAL_CSTATE_REPORT.md)说明原 unattended pipeline 无效、经授权的离线恢复后数值门通过，但不是 clean one-shot；需追原失败与恢复合同再从该报告走向 [failure READOUT](../../results/tf_cstate_prospective_20260923/failure/READOUT.md) 和 [RECOVERY_PROTOCOL](../../results/tf_cstate_prospective_20260923/RECOVERY_PROTOCOL.md)。**限制**：Part B 的大型原始证据 **remote-only** 于报告所记 deinlab 根；旧 TF 不等于最终 TF+CSTATE。旧 Pro [交接](imports/downloads/AFDM_GPT_Pro_Handoff_20260923.md)是外部来源，不是性能证据。

<a id="route-cstate"></a>
### CSTATE 为什么触发、多算了什么，几何与 APP/check 如何接线？

**问题/裁决**：[production gap 七问](../../results/tf_production_gap_audit_20260922/RESULTS.md#七个核心问题)区分有限增轮、几何与评分，指向可观测 syndrome 入口；[几何资格](../../results/tf_geometry_reopen_20260922/RESULTS.md)和[CSTATE 验证](../../results/tf_cstate_validation_20260922/RESULTS.md)说明 compact 重开与额外 TF20 的合同。**方法/源码**：[逐字段接线表](../../results/tf_campaign_reconciliation_20260923/receiver_audit.md)直接链接旧 [`_branch` APP→moments/compact refit、check→fresh TF20](../../experiments/tf_cstate_validation_20260922/run_validation.py)及新封装同构路径，避免从结果表猜先验时序。**直接证据 → 复核**：[前瞻恢复后报告](../../results/tf_cstate_prospective_20260923/recovery_20260923/analysis/RESULTS.md)给最终信息错误、期限与完整成本 → [验证收据](../../results/tf_cstate_prospective_20260923/recovery_20260923/verification/receipt.json)核对封存。**限制**：A+B+C 真值干预是诊断，不可当部署收益；其 B 批较大 raw/检查点在[原报告所记远端路径](../../results/tf_production_gap_audit_20260922/RESULTS.md#a来源与可追溯证据)，本地链接不是全部 raw。

<a id="route-cgr"></a>
### 为什么 CGR 已停止，BLOCK 是否能解释伤害？

**假设来源（外部）**：[原 CGR investigation 包](../20260923_tf_cgr_investigation/MANIFEST.json)与[冻结25帧合同](../20260923_tf_cgr_investigation/CODEX_TEST.md)提供问题和四臂约束，不是新贡献。**直接证据**：[历史 v2 配对结果与五门](../../results/tf_cgr_mechanism_20260923_v2/RESULTS.md#physical-diagnosis-and-the-fixed-gates)得出4/8救回、原机制门不获证明；[离线 BASE-only 与 BLOCK 面板](../../results/tf_cgr_offline_mechanism_20260923/RESULTS.md#block-source-map-and-mechanism-limit)给出相位传输与 BLOCK 域混配。**方法/源码 → 复核**：[receiver 审计表](../../results/tf_campaign_reconciliation_20260923/receiver_audit.md)显示新三臂只注册 BASE/CGR/SHAM、没有 BLOCK 导入；[离线独立 review](../../results/tf_cgr_offline_mechanism_20260923/review/final_review.md)限定 BLOCK 因果解释。**新前瞻与停止**：[256帧 Decision Packet](../../results/tf_cgr_prospective_mechanism_20260923/RESULTS.md)与[独立重计数](../../results/tf_cgr_prospective_mechanism_20260923/independent/recount_receipt.json)说明机制资格仅3、三臂最终全对，`bounded_continue=false`。此路由的“CGR 尚未晋级为正面新方法贡献、本分支停止”是固定门与前瞻的**审计推论**；原负结果和 TF+CSTATE limitation 仍可按其证据边界如实描述，离线 JVP 或外部假设不充当 FER 证据。

<a id="route-reconciliation"></a>
### 旧 TF 40/1024 与新 BASE 0/256 是否矛盾？

**裁决（审计推论）**：[同阶段法证总审计](../../results/tf_campaign_reconciliation_20260923/AUDIT.md)判定旧纯 TF 与新 post-CSTATE BASE 不同，正确旧比较臂是 TF+CSTATE 6/1024。**比较合同/源码**：[receiver identity](../../results/tf_campaign_reconciliation_20260923/receiver_audit.md)逐行指旧/新 runner 的触发与终判；[population identity](../../results/tf_campaign_reconciliation_20260923/population_audit.md)核生成规律和独立抽样范围。**直接证据 → 统计复核**：[旧恢复后结果](../../results/tf_cstate_prospective_20260923/recovery_20260923/analysis/RESULTS.md)与[新256帧结果](../../results/tf_cgr_prospective_mechanism_20260923/RESULTS.md)给原计数 → [条件精确统计](../../results/tf_campaign_reconciliation_20260923/statistics.json)只用于 6/1024 对 0/256。**限制**：不同新帧不能逐位配对；新8个 native syndrome trigger 不是8个信息字错误；0/256不证明真实 FER 为零。

<a id="route-scalar"></a>
### scalar closure 式 (1)–(6) 到底证明什么？

**裁决与前提**：[理论索引](../../results/tf_scalar_closure_audit_20260924/README.md)先给 `VERIFIED WITH RESTRICTIONS`，随后[正式推导](../../results/tf_scalar_closure_audit_20260924/SCALAR_CLOSURE_DERIVATION_20260924.md)列 AF 对角工作协方差、整数 delay、CPP/DAFT 和共同进入态。**方法/源码**：[逐式代码图](../../results/tf_scalar_closure_audit_20260924/SCALAR_CLOSURE_CODE_MAP_20260924.md)把 (U,R,V,\Gamma,\alpha,v_q,\bar h\) 接到冻结函数/状态时序。**直接数值证据 → 限制**：[30组合成核验](../../results/tf_scalar_closure_audit_20260924/SCALAR_CLOSURE_NUMERICAL_VERIFICATION_20260924.md)、[原始JSON](../../results/tf_scalar_closure_audit_20260924/scalar_closure_verification.json)核式 (1)–(6)，[claim matrix](../../results/tf_scalar_closure_audit_20260924/SCALAR_CLOSURE_CLAIM_EVIDENCE_MATRIX_20260924.md)给可写/禁写句。更大范围的[截图 (1)–(11)](imports/temporary/codex-clipboard-7fe170f5-7d5a-47b8-b336-bb7ff3f6dee4.png)是**未完成部分的外部请求**；(7)–(11)未作同等级核验，理论结果也不证明 CGR 改善 FER。

<a id="route-alternatives"></a>
### 旧 I1/TAIL/G0/G1/Γ 为什么没有变成同一论文主方法？

**导航/合同**：[旧 claim 审计时间线](../claim_audits_20260726_20260727/README.md) → [budgeted-support 执行合同](../../.trellis/tasks/09-05-budgeted-support-repair/execution.md)与[逐行 CSV](../../.mission/20260909_09-01-15-afdm-comprehensive-supplement/20260909_09-01-15-afdm-comprehensive-supplement.csv)。**直接证据**：[I1 强参考/成本取舍](../../.mission/20260911_19-55-51-afdm-i1-cost-adjacent-pivots/evidence/final-findings.md)、[TAIL v5 终端结果](../../.trellis/tasks/09-13-trans-next/research/tail-terminal-results-v5.md)与[接续复核](../../.trellis/tasks/09-13-trans-next/research/tail-recheck-results-20260917.md)、[G0 纠偏](../../research-assets/res-20260914-01.md)、[Γ 校准](../../.trellis/tasks/09-13-trans-next/research/gamma-crossfit-results-v1.md)分别回答不同问题。**限制**：[阶段审查](../../.trellis/tasks/09-13-trans-next/research/ce-stage-review-v1.md)说明开发、真值校准和未完成的 CONF/SCENE 不自动晋级；这些是 TF+CSTATE 之前或并行的历史分支，不能串成同一 receiver 的逐版 FER。

<a id="route-necessity"></a>

**最新审计边界**：[Stage-B裁决：UNRESOLVED／下一步D](../../results/cstate_necessity_stageB_20260928/STAGE_B_DECISION.md) → [等价门停止证据](../../results/cstate_necessity_stageB_20260928/STAGE_B_RESULTS.md) → [F1实现效率与原论文F2逻辑链](../../results/cstate_necessity_stageB_20260928/README.md)。F1在409次尝试后遇到精确评分计数差异，F2尚未进入真实接收机；不能补成完整early/triggered风险成本结论。下列Stage-A结论仍为已完成证据。

当前接续：[2026-09-28 Stage A：更强前端能否替代CSTATE？](../../results/cstate_necessity_stageA_20260928/README.md) → [裁决U及其边界](../../results/cstate_necessity_stageA_20260928/STAGE_A_DECISION.md) → [四臂/LOCAL配对风险成本](../../results/cstate_necessity_stageA_20260928/STAGE_A_RESULTS.md) → 逐帧表/独立重计数/源码与封存。4108调用完成，错40/6/12/0；更强前端未替代廉价前端+CSTATE，整体续算有效但全局重开优于LOCAL仍待证。

### Q10：CSTATE 是否只是在补救弱前端？（2026-09-25 扩展）

**最新补充**：用户随后批准便宜的初始采集重建；先读[72帧补档结果](../../results/cstate_necessity_audit_20260925/supplement/README.md) → [逐帧分组/入口匹配](../../results/cstate_necessity_audit_20260925/supplement/stage_mechanics.csv) → [重建与原存档的独立复核](../../results/cstate_necessity_audit_20260925/supplement/INDEPENDENT_RECOUNT.json)。初始OMP记录现已补齐，11/34救回帧涉及可直接追踪的delay分组丢失；这不是11/34的因果收益占比。下列A4与不可用性是补档前档案阶段，原收据按提交7f62deea保留；“F1/Stage A未运行”仅指9月25日当时状态，9月28日结果见上方接续。

**裁决 → 缺口**：[necessity 索引](../../results/cstate_necessity_audit_20260925/README.md) → [采集谱系 A4](../../results/cstate_necessity_audit_20260925/CSTATE_ACQUISITION_LINEAGE_AUDIT.md) → [可用性与逐帧边界](../../results/cstate_necessity_audit_20260925/artifact_availability.json)。**可证伪比较设计**：[F1 数学/保槽接口](../../results/cstate_necessity_audit_20260925/F1_NOMP_AFDM_SPEC.md) → [方程/源码](../../results/cstate_necessity_audit_20260925/F1_EQUATION_TO_SOURCE_MAP.md) → [真实24步OMP成本账](../../results/cstate_necessity_audit_20260925/F1_COMPLEXITY_LEDGER.md) → [Stage A 草案](../../results/cstate_necessity_audit_20260925/STAGE_A_PREREGISTRATION.md)。**限制**：初期pilot排名未存/不可访问，后期APP排名不能代替；该档案阶段尚无F1接收机比较，不能由它推出“CSTATE仍必要”；9月28日比较及限制见上方接续。此为后续新增路由，原Q1–Q9的LOGIC_WALK收据仍只证明其当时版本。

## 次级时间线（保留当时问题与状态）

| 时段/问题 | 当时答案与边界 | 证据入口 |
|---|---|---|
| 3–7 月：早期性能、论文 claim 怎样演化？ | 历史结果与解释曾多次修订；旧 headline 不再作现行主张。已晋级结果逐条查卡片，旧审计保留更正过程。 | [旧记录说明](../legacy_records_20260726/README.md) · [claim audits](../claim_audits_20260726_20260727/README.md) · [promoted 结果卡](../../research-assets/index.md) |
| 9 月 5–11 日：budgeted-support 六家族诊断如何取舍？ | v3 科学路线 HOLD；补充合同的 G1/COST/CONF/SCENE 等与 I1 强参考确认分阶段，开发诊断不等于正式主张。逐行状态只查对应 CSV。 | [执行/交接](../../.trellis/tasks/09-05-budgeted-support-repair/execution.md) · [补充 CSV](../../.mission/20260909_09-01-15-afdm-comprehensive-supplement/20260909_09-01-15-afdm-comprehensive-supplement.csv) · [I1 取舍](../../.mission/20260911_19-55-51-afdm-i1-cost-adjacent-pivots/evidence/final-findings.md) |
| 9 月 I1：轻量缺口/瓶颈是否已闭合？ | 有固定强参考确认、成本及 pilot 诊断；后置 CPU/跨场景/正式确认仍按原合同区分，不能把开发 pilot 写成新方法胜利。 | [I1 确认](../../.mission/20260911_19-55-51-afdm-i1-cost-adjacent-pivots/evidence/final-findings.md) · [瓶颈 pilot](../../.trellis/tasks/09-12-i1-bottleneck-pilot/research/results-20260912.md) · [完整批次](../../.mission/20260912_14-15-00-afdm-light-gap-closure/results.md) |
| 9 月 TAIL：尾补全能否作生产接续？ | 终端验证及多版纠错已保留；对普通 ridge 未过 GO，不能把更准 H 推成 NLL/FER 优势。 | [v5 结果](../../.trellis/tasks/09-13-trans-next/research/tail-terminal-results-v5.md) · [接续复核](../../.trellis/tasks/09-13-trans-next/research/tail-recheck-results-20260917.md) |
| 9 月 13–15 日：G0/G1、continuous/Dirichlet、CE theory/Γ 与导频融合能否开新路线？ | G0 镜像权重纠偏限定旧结论适用物理模型；G1、Γ 和导频对照各有阶段性审查/负门，开发探索不自动晋级 CONF 或论文贡献。 | [G0 披露卡](../../research-assets/res-20260914-01.md) · [外部咨询快照](../20260913_sp_integer_continuous_consultation/README.md) · [Γ 校准结果](../../.trellis/tasks/09-13-trans-next/research/gamma-crossfit-results-v1.md) · [阶段审查](../../.trellis/tasks/09-13-trans-next/research/ce-stage-review-v1.md) · [唯一探索 CSV](../../.mission/20260914_12-58-51-afdm-unified-exploration/20260914_12-58-51-afdm-unified-exploration.csv) |
| 9 月外部 Pro 与方法转向：旧 V1–V4 后采用什么？ | 旧路线材料是历史来源；后续筛选转向 native/tensor-free scalar bilinear TF。外部文档不是独立生产证据。 | [旧 V1–V4 存档](../../.trellis/tasks/09-13-trans-next/research/spafdm-gpt-20260920/README.md) · [Pro 文档角色](../20260921_22_sp_afdm_pro_documents/README.md) · [native 结果](../../results/sp_afdm_native_joint_20260921/RESULTS.md) |
| 9 月论文接收机证据：native/TF 成本与译码性能如何？ | PD1-Q Part A 数值/成本资格与 Part B 前瞻证据分开；后者是当时 TF 证据，不能自动当 TF+CSTATE 结果。 | [Part A](../../results/sp_afdm_pd1q_part_a_20260921/RESULTS.md) · [Part B](../../results/sp_afdm_pd1q_part_b_20260921/RESULTS.md) |
| 9 月 production gap：失败由多迭代、几何还是评分导致？ | A+B+C 显示几何/状态可恢复空间，有限增轮不能消除大部失败；未证明合法错误码字 basin 或排序翻转。真值干预是诊断，不是部署接收机。 | [A+B+C 结果](../../results/tf_production_gap_audit_20260922/RESULTS.md) · [原用户材料及来源 SHA](../../results/tf_production_gap_audit_20260922/inputs/manifest.json) |
| 9 月结构重开：CSTATE 能否挽救 syndrome 触发的 TF 错误？ | compact exact geometry 后重启原生 TF round；冻结 6.5 dB 前瞻旧 TF 40/1024 错、TF+CSTATE 6/1024 错，34 帧被救回。原无效/修复运行须分开读。 | [几何资格](../../results/tf_geometry_reopen_20260922/RESULTS.md) · [CSTATE 验证](../../results/tf_cstate_validation_20260922/RESULTS.md) · [前瞻恢复后报告](../../results/tf_cstate_prospective_20260923/recovery_20260923/analysis/RESULTS.md) |
| 9 月 CGR 历史 25 帧：相干 gain reaction 机制是否成立？ | 外来 investigation 先作为假设来源；四臂 100 完整调用另保留一次失败尝试。8 目标 CGR 救回4，但原物理方向门不确定，`candidate_pass=false`，不作为生产贡献。 | [来源包](../20260923_tf_cgr_investigation/MANIFEST.json) · [v2 报告](../../results/tf_cgr_mechanism_20260923_v2/RESULTS.md) |
| 9 月 CGR 离线零调用：已保存轨迹能解释什么？ | BASE-only JVP 有相位敏感的终端消息预测；BLOCK 观测/响应域混配且控制帧缺全状态，完整机制不可识别，不改历史 gate。 | [外部离线请求](../20260923_tf_cgr_offline_mechanism/MANIFEST.json) · [离线结果](../../results/tf_cgr_offline_mechanism_20260923/RESULTS.md) |
| 9 月 CGR 新前瞻：机制可重复、FER 有增益吗？ | 256 fresh 帧、三臂 768 完整wrapper；三臂均256/256正确，机制资格仅3帧且无可救 BASE 错，预设支持不足，`bounded_continue=false`；不可补帧或调 gate。 | [Decision Packet](../../results/tf_cgr_prospective_mechanism_20260923/RESULTS.md) |
| 9 月跨批次疑问：旧40/1024 与新0/256矛盾吗？ | 两数是不同 receiver 阶段；新 BASE 应与旧 TF+CSTATE 6/1024 比。修正后0/256与抽样波动相容，未发现新 BASE 关键数学漂移。 | [法证总审计](../../results/tf_campaign_reconciliation_20260923/AUDIT.md) |
| 9 月 scalar closure：CSTATE 可达几何改变了什么限制？ | 已提供的文本审计请求编号公式仅 (1)–(6)，这些公式的理论/数值核对结论为 **VERIFIED WITH RESTRICTIONS**；另有截图提出公式 (1)–(11) 的更大范围，**(7)–(11) 未核**。本结果仅作 TF+CSTATE limitation/consistency，不翻转 CGR 停止结论。 | [理论/证据总索引](../../results/tf_scalar_closure_audit_20260924/README.md) · [已审文本请求](../../results/tf_scalar_closure_audit_20260924/REQUEST_20260924.txt) · [更大范围截图](imports/temporary/codex-clipboard-7fe170f5-7d5a-47b8-b336-bb7ff3f6dee4.png) |

## 来源副本与检索边界

本目录的 `imports/` 保存本轮选定的 Downloads/附件原件的**逐字节副本**；来源路径、字节数、SHA-256 及当时的有界匹配结果见 [`MANIFEST.json`](MANIFEST.json) 和[有界盘点](INVENTORY.json)，后续发现的同字节别名以本页说明为准。文本可能含旧命令或未接受的建议；作为历史材料阅读，不覆盖上述权威结果。旧 campaign 的 invalid attempt、reader 纠错和负门槛继续保留在各自结果目录，本页不重写。

补存材料按原问题定位：[项目交接](imports/downloads/AFDM_Project_Master_Handoff_20260923.md)、[Pro 交接](imports/downloads/AFDM_GPT_Pro_Handoff_20260923.md)、[早期可用性快照](imports/downloads/availability_map.md)、[旧数学探针上下文](imports/downloads/README.md)、[早期 JCDD 推导/裁决](imports/downloads/DERIVATION_AND_VERDICT.md)、[完整旧前瞻报告来源文本](imports/downloads/prospective_final_report.md)、[7 月以外的 CLOSEST_ART 变体](imports/downloads/CLOSEST_ART.md)、[跨批次法证原问题](imports/attachments/7fdaa6c4-reconciliation-request.txt)。该 CLOSEST_ART 与9月23日 CGR 来源包中的同名文件 SHA **不同**，两版本并存，不互相覆盖。[Downloads 前瞻报告副本](imports/downloads/prospective_final_report.md)与项目已有的 [FINAL_CSTATE_REPORT.md](../../results/tf_cstate_prospective_20260923/FINAL_CSTATE_REPORT.md) 同为 SHA-256 `bf732e7591567133ff5e0035a9826af4041cb7e500bedf68b82b8fb247d1d394`，属**同文异名**；因此11件新增副本不等于11件此前缺失的唯一内容，此处保留原副本及旧manifest/verification快照不改。文献 [PBiGAMP 非均匀 Doppler PDF](<imports/downloads/PBiGAMP-Based_Joint_Channel_Estimation_and_Data_Detection_Under_Nonuniform_Doppler_Shifts (1).pdf>)仅是来源副本，未在此开展新颖性审查；Downloads 无 `(1)` 版比它少3字节且 SHA 不同，记录于manifest而未重复复制。

[Theory Closure Audit (1)–(11) 截图原件](imports/temporary/codex-clipboard-7fe170f5-7d5a-47b8-b336-bb7ff3f6dee4.png)已补存；本轮已完成的 scalar closure 数值/理论审计仍只证明式 (1)–(6)，不把截图其余 (7)–(11) 项倒写为已核。[另一会话截图](imports/temporary/codex-clipboard-bbf99ec9-1f6a-4a2c-b106-cf67a362fd50.png)按未重读内容的来源原件保存，不据此增加科学结论。此前已逐字节存档的 CODEX_TEST、CODEX_VALIDATION、离线请求和三张截图等只在manifest登记项目现有同 SHA 路径，不复制第二份。

旧 Pro 两批各17件原始档直接保留在 [9 月 20 日路线资料](../../.trellis/tasks/09-13-trans-next/research/spafdm-gpt-20260920/README.md)及 [9 月 21–22 日文档归档](../20260921_22_sp_afdm_pro_documents/README.md)；本轮将其纳入显式 Git 交付范围，不在此重复复制约 67 MB。[9 月 23 日 CGR 来源包](../20260923_tf_cgr_investigation/MANIFEST.json)是另一独立输入，不计作上述两批。冷档 `FINAL_MANIFEST.sha256` 的[原字节副本](FINAL_MANIFEST.sha256)只证明清单本身的 SHA，**未**在本次重读或逐件重算其中 9,633 条清单项所指文件。

未来定位文本证据可从项目根执行 `rg -n --hidden 'CGR|scalar closure|Gamma|CSTATE|I1|TAIL' STATE.md research-assets .trellis/tasks .mission _archive results -g '*.md' -g '*.json' -g '*.csv'`；旧材料只读，遇到历史 `pending` 或旧建议须回到当期结果/任务核状态。

本轮 [Q1–Q9 逻辑检索走查收据](LOGIC_WALK.json)仅验收入口、链接、证据层级与状态措辞，由同一项目协作流程复走；它不是新的独立科学审计、数值复算或实验结论。
