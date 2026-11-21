# S0/S1 技术设计

唯一研究协议：[parent design](../09-05-budgeted-support-repair/design.md)。本child只实现预检与证据产物。

- 复用旧e1 evaluator；新增观察/导出接口须不改变算法路径与随机流。
- CUDA probe需CPU参考、设备确认、数值残差、峰值内存、实际库版本；严格失败，不静默用CPU。
- 回放固定历史结果_config/种子；新诊断种子留到S2，不能混合。
- profiler必须覆盖scorer闭包创建时的额外OMP、主forward、末次soft BP和LDPC；输入生成/IO单列。
- 远端只用已有环境，任务独立快照目录；不修改原远端checkout或共享驱动。
- 本地可进行单位契约和只读文献审查，不能替代deinlab性能验收。
