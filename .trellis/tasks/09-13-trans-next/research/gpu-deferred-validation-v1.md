# GPU-01：后置验证及论文引用边界

本项验收是完成延期登记，不是运行GPU验证。用户要求CPU优先；本轮没有运行nvidia-smi、CUDA测试或驱动修复，不声称知道硬件此刻是否恢复。最后记录的驱动故障只作为历史事实。

| 后置工作 | 恢复与验收条件 | 目前对论文的限制 |
|---|---|---|
| 旧CUDA完整基线等价/C1回放 | 硬件健康检查后，在原源码、checkpoint、码配置和配对输入上跑完整接收链，保存连续状态与最终错误向量；单算子成功不代替完整回放 | 旧CUDA与新CPU-gels属于不同数值路径；不得混合样本、计算跨路径效应量，或声称逐位等价 |
| 新强参考及后续候选的CUDA移植 | 先冻结CPU最终候选；CUDA接口、复数求解、重复性和完整链分别核验；设备差异及失败保留 | 当前结果只支持相应CPU实现；不声称跨设备复现 |
| CUDA部署成本 | 已通过CUDA完整链后，在固定独占负载下测全部CE/BP/LDPC/控制器成本，区分冷启动与稳态 | CPU仪表化时间及CUDA单算子时间均不证明GPU完整加速 |
| 旧GPU G1结果与当前新CPU G1对照 | 不重新解释既有GPU单臂数据；若需设备比较，另行冻结同输入、同实现的设备配对验证 | 旧192块GPU G1与当前CPU工程不得拼接为配对收益；当前工程也未完成最终候选G1 |

恢复顺序：只读设备/环境检查 → 有界复数算子资格 → 固定样本重复/完整链工程 → 必要的设备验证与独立成本。驱动安装、重启、sudo等仍需管理员处理；本任务不执行这类动作。恢复不意味着自动重跑旧实验或撤销旧失败。

新研究可在明确的CPU范围内完成独立确认、成本、传播和跨场景/码验证；GPU故障本身不证明这些门已通过。若最终稿保留跨设备或GPU性能主张，则对应GPU证据恢复为该主张的必要条件。若仅报告CPU结果，应明确实现与适用范围，不能用GPU延期掩盖尚缺的新方法贡献或确认结果。

当前CPU路径实证：REF-06的完整开发summary与raw审计通过；G1工程environment记录device=cpu、threads=1、source5c0fac1e。见terminal-controls-results-v1.md、g1-strong-engineering-v1-results.md及其Mission exact-harvest收据。

## 历史证据定位

- [STATE.md](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/STATE.md)：SHA256 `0b73867a266aaacaa6d1a86b760e9ec0b86f2e7ec3f7632b55833f571358885b`。
- [preflight-readonly.json](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.mission/20260912_14-15-00-afdm-light-gap-closure/evidence/preflight-readonly.json)：SHA256 `5df752fdbcf3c68b20422a65c1cdb3bc863c91be35e8cb2a5769dbb9b23ab47a`。
- [gpu-driver-diagnosis.json](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.mission/20260912_14-15-00-afdm-light-gap-closure/evidence/gpu-driver-diagnosis.json)：SHA256 `bd64dd32fd0743fe0ed2bc295afd3d4c8788ce5d63e744c43fd125e9014d52a5`。
- [mission-budget-evidence-20260906.md](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/.trellis/tasks/09-05-budgeted-support-repair/research/mission-budget-evidence-20260906.md)：SHA256 `951eb9fa0c523c0295a4867c395e8eb634df486fb97143dc8a356c57844e8e49`。

2026-09-12 preflight记录NVML返回18，驱动/库不匹配；diagnosis记录内核580.173.02与用户态580.178。2026-09-06预算证据记录CUDA复数求解小测试成功，但STATE仍明确旧CUDA完整基线等价未证明。旧light-gap CSV的L13保存旧门失败与另立CPU-gels工程通过，未将二者合并成CUDA通过。所有这些都是历史收据，本轮没有重新测试GPU。

文档核验：四个证据文件实际存在并取哈希；当前CPU环境与完整开发收据读取核对；延期工作、恢复条件及稿件限制逐项列明。GPU-01可按“登记完成”关闭，所有GPU计算验收仍未执行，主会话审查独立性weak。
