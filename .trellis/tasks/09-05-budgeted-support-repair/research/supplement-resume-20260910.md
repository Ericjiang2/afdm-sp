# 全问题补充实验恢复检查点（2026-09-10）

> **当前下一步已被取代：** [supplement-progress-20260910-a01-s01.md](supplement-progress-20260910-a01-s01.md)。本文保留 DET 追加 runner / 16T 资格门检查点，不删除。

逐项状态只在 Mission CSV。本文只记录可回滚代码边界，不关闭科学行，不复制数字裁决。

## 权威

- CSV：`.mission/20260909_09-01-15-afdm-comprehensive-supplement/20260909_09-01-15-afdm-comprehensive-supplement.csv`
- 入口：[execution.md](../execution.md)
- 父任务：`09-05-budgeted-support-repair`（in_progress）
- 旧 v3 HOLD 与 D_test 仍封存

## 代码回滚点

- 分支：`trans/tcom-main`
- DET 追加 runner 实现提交：`bdaa6b1857ecc14ba3044e62894ead172596896e` (`feat(afdm): bind DET additional runner provenance`)
- 源码包：`.mission/.../dispatch/det-extension-source-v2.zip`
  SHA256 `c2730122537f22442483c16dbd36a934b73039d76be884ec71178421f08f72e2`
- 远端只读夹具根：`/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_comprehensive_supplement_20260909/source-det-extension-v2`

## 本轮已做、未做

已做：

- 补独立审查 P1/P2：资格准入/四缓存 proof/16T 账本绑定；删除 reservation 后拒绝再预约；additional 记录使用真实 block。
- 本地 100 tests 与远端 Python 3.10 CPU 夹具通过。
- 确认远端无 additional/stability reservation，512T 探测额度未被占用。
- COST-02 先导 798F 仅描述；正式 n 未冻结，8dB 三臂 1024 块只是报价。

未做：

- 未准入 384T 开发：冻结 verifier 在 JSON 浮点范数/残差上逐位失败；同一 allocation 的 source_manifest 不能改。
- 未启动 COST-02 正式独占计时。
- 未解封 D_test，未改论文主线，未声称 D1。

## 下一步

1. 对 P2 修复做独立审查后，才能考虑 400T 运行准入。
2. COST-02 正式采集仍缺 7/9 dB prior 与 18 臂/102 端点；不能把 8dB 先导当过门。
