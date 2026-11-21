# S0/S1 模型契约与基线验证

## Goal
执行parent的S0/S1：冻结单位/容量/基线边界，验证deinlab CUDA和旧链路可复现性，建立完整计时口径。

## Authorization
用户在审阅parent执行计划后于2026-09-05明确“go on”。沿用既定范围与1 GPUh/1单机小时阶段上限。主会话负责实现/验收；2026-09-06用户追加授权独立研究子代理与远端任务并行。

## Requirements
- R1：输入/输出单位、随机流、真实路径数依赖、checkpoint与实际scorer路径可追溯。
- R2：检验相邻方法边界，不能把原始多天线方法与单天线适配混称。
- R3：真实CUDA运算与完整接收链路检查，不能以nvidia-smi替代。
- R4：同帧回放、外生样本hash和包括额外OMP/末次BP/LDPC的计时。
- R5：失败显式记录，保留原数据和用户工作；无法SSH时完成独立本地契约工作，GPU验证保持未通过。

## Acceptance Criteria
- [ ] S0：contract、baseline-map、provenance完整。
- [x] S1：CUDA数值检查和2—4帧真实链路通过。见research/runtime与preflight证据。
- [ ] S1：8→32帧基线回放、输入配对及旧输出差异解释完成。
- [ ] S1：B_mean/B_p95、内存和完整计时记录。
- [ ] 代码检查与原始证据验证，无假成功。

## Scope
仅契约/预检/回放工具，不修改接收算法，不进入S3/S4，不替旧E6/C1结案。
