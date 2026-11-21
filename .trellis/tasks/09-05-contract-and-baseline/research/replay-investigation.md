# S1：geom 历史回放差异调查

2026-09-06，按 systematic-debugging 先收证据；尚未修改接收算法或放宽容差。

## 已观测

- SNR7/seed20260601 历史前8帧，classical 错误向量与 achievable 错误向量完全一致。
- geom 原始错误差异出现在索引1、4、7；译码信息位差异出现在4、7。比较器按失败返回，见 `replay-pairing-8.json`，不能称历史 bit-exact 通过。
- 新 achievable/geom 的 y、H_true、单位噪声、信息位、码字、导频哈希全部相等。
- 固定 OMP_NUM_THREADS=4、OPENBLAS_NUM_THREADS=4：未追踪旧快照 `smoke-geom`、带随机臂顺序的 `trace-8-geom`、完全重复 `trace-8-geom-repeat`，全部7个逐帧向量相等。
- 新旧远端 `classical_joint_unrolled.py`、`decision_bound.py`、`decision_gateA.py`、`decision_harvest.py` 内容哈希一致。

因此目前证据排除：本次观察器/臂顺序造成所见8帧差异。它还不能确定历史环境差异的具体算子。

## 当前假设与下一步

历史 E1 implement.md 提及 OMP_NUM_THREADS=16（smoke），当前固定为4；历史正式运行线程/库信息未完整登记。首先单变量改变线程设置，检查是否复现旧向量。若不能，记录校准lookup、候选/支撑、LS/BP数值的第一个分歧点；不把猜测写成根因。

32帧同环境扩大验证可继续；任何统计比较须使用同环境新登记基线。跨历史差异仍保留为未闭合项，不能据新基线可重复便自动完成旧 C1。

## 容量审查补充

旧 n_paths 限制簇扩展前 K_prop；随后±2邻居扩展使实际 DA-LS 支撑 K_active 更大。原规划把两者等同的描述已纠正。S3最终动作验证须覆盖剪枝和簇扩展；S5同时冻结实际容量和提名容量。这是定义/实现审查结论，不是方法收益。

## 2026-09-06 CPU 同设备验证

历史 `07-26-tmlcn-paper-submission/harvest-20260727.md:51` 明确记录 E1 当时因驱动问题全部运行于 CPU。新 CUDA 的两组线程单变量探针均不能复现旧 geom；固定历史 CPU 路径后，前8帧全部7组错误计数/种子/译码标志向量完全一致。证据：`cpu-historical-replay.json` 和 `runtime/geom-cpu-replay-8/`。

结论只到设备路径：历史 CPU 可复现，新 CUDA 可重复。离散先验分数并列导致 topk 跨设备排序差异是待验证解释，尚未定位到具体算子。不能把计数一致称为全部浮点输出 bit-exact，也不自动关闭旧 C1/E6。
