# AFDM v2 任务CSV使用说明

- 源方案：[.trellis/tasks/09-05-budgeted-support-repair/research/next-execution-plan-20260906-v2.md](../../.trellis/tasks/09-05-budgeted-support-repair/research/next-execution-plan-20260906-v2.md)；SHA256 `4b18115841b3cb946bbe6bff3b4d7da223f4f1ba7fbe4d31118000679029f139`。
- 执行清单：[2026-09-06_13-47-38-afdm-plan-v2.csv](2026-09-06_13-47-38-afdm-plan-v2.csv)，59行（含最终REVIEW-01），固定19列、UTF-8 BOM、全部字段双引号。
- 承诺账本：[2026-09-06_13-47-38-afdm-plan-v2.claims.json](2026-09-06_13-47-38-afdm-plan-v2.claims.json)，69/69条承诺有任务映射，**生成时运行证据全部pending；当前证据以CSV/ledger为准**。
- 生成阶段仅交付CSV；随后用户已明确授权执行。逐项进度以CSV为准，原G1/G2/G3、Dtest门及额外S1预算接受门保留。
- Trellis父任务仍是生命周期权威；本CSV是今后逐项状态唯一权威，execution.md只存静态链接。

## 依赖、并行与状态

`depends_on`是必须先取得结果或明确条件处置的任务；`depends_any`表示任一支路准备好即可评估候选，**不自动等于该支路GO**。`activation`必须单独核验。phase仅用于组织，不是全局屏障。这些notes标签是供执行者遵守的调度协议，不声称Mission工具自动解析它们。

共同壳/prior→新壳真实实验。数学MATH-01和反馈入口FB-01可先在本地独立推进；旧V(T1)不等新prior。覆盖RUN-06/07先出结果，慢RUN-08仅阻塞完整有限池排序。MECH-01和FB-05各自可使SEL-01进入候选评估，无V全局GO门，无全池枚举全局门。一次验证冻结后，其他路线可继续开发但不得利用该validation；后续候选必须新登记独立验证流和预算。

实现与检查由主会话inline承担，共享receiver代码串行修改。只读研究可用最多3个GPT-6（gpt-6-astra）代理：索引low、模块分析medium、公式/统计耦合high，最高high。不可原地改强度时为下一独立子任务新建代理，不假称已切换。GPU开发2槽起、实测后3—4槽，总显存≤22GiB；CPU先2×4线程互斥核；正式计时独占。

条件未触发时，记录触发证据、not_applicable及execution_performed:false，并完成该行的条件审阅；这仅关闭任务处置，不表示未执行实验通过。预算耗尽、矩阵不全可以形成INCONCLUSIVE，但不得把缺失实验标成科学成功。仍需用户接受的TIME-01在相关分支激活且未接受时保持未开始并写blocked，依赖它的正式工作不能伪关闭；若正式分支从未激活，则只记录该门未动用。

科研终态放在证据中：SUPPORTED_WITHIN_SCOPE / NEGATIVE_WITHIN_SCOPE / INCONCLUSIVE / ENGINEERING_BLOCKED。它们不是CSV状态枚举。REVIEW-01最终核对全部源承诺；inline禁止派implement/check代理，不强行调用不可用的superpowers reviewer技能。若仅主会话受限审阅，记录weak和limited_review，追加REVIEW-02，不把受限事件视为愿景已全部满足。

## 成本与闸门

接收评估上界：384基线 +192增益 +48共同pool +48注入 +2280剩余枚举 +72位置 +432机制 +192旧V +192新反馈 +384候选fit +1152validation = **5376**。相同state/hash/action才可去重。

另计prior400帧、所有smoke、每局部位置帧最多33次目标拟合、离线矩、条件SNR校准/基线复现、正式计时和Dtest/9护栏；不能用5376掩盖这些费用。每批按实测费用加至少20%余量，首包≤2 GPUh且≤2单机忙碌小时，并在S2原4h或S3/S4原8h余额内分别划拨。新增S1最多1h与未来记账口径仍待明确接受；S5—S7合计24h不变。每次发车重新查余额，不跨阶段借用。

正式数据依赖开发GO、合格强参考、G2、实际分析器覆盖/功效、费用和预登记全部成立。G1/G2/G3阈值不降；无可行预算报告MDE/不足。当前不会产生正式样本或科学通过状态。

## 证据与验证

每行notes的`planned_evidence:evidence/<ID>.md`是未来证据目标，**文件目前不代表存在**。必须记录命令、代码/配置/input hash、实际结果、区间、失败分母、费用及日志路径。需要真实接收证据的行不可仅凭单元测试关闭为通过。

本次结构检查保存在`2026-09-06_13-47-38-afdm-plan-v2.validation.json`；它只验证CSV/来源/依赖/承诺映射与预登记工作量，不能证明算法、服务器、SSH、GPU或实验结果已通过。未来完成后才生成`2026-09-06_13-47-38-afdm-plan-v2.handoff.md`，本次不伪造执行交接。
