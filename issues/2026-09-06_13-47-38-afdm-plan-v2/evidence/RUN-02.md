# RUN-02 共同壳 GPU 与旧分支验收

新 direct40 A0/A2：见 a0-a2-wire-runtime.json。两帧真实 CUDA 检测和 LDPC；A0 不准备 scorer/不修补，A2 消费已冻结400帧 prior。每轮与最终容量≤40，临时容量≤登记48。prior、输入、输出及代码快照哈希留存；两臂 exit 0。

历史旧分支：legacy-vector-replay-runtime.json 保留新插桩重放的全部 raw_bits、raw_error_mask、decoded_bits、info_error_mask。固定 source-v3 与当前 legacy 分支分别重放 rep997 两帧、baseline/covariance，共4对，所有比特数组逐项相同。输入、support、sigma、输出 H/x SHA256、原始/译码错误计数与历史 capacity-smoke40 也相同。旧 prior/source/T1 的哈希先验核对在 batch manifest；观察器返回原始计算结果，没有更改算法。

历史并未存储逐bit mask，因此这些是“冻结旧源码的新插桩参考”，不是补造历史 mask。两帧 LDPC 都成功，结论仅覆盖该工程样本；不推断 FER、geom CPU/GPU 差异已解决或新评分正确。

资源：两路并行约6.64秒，独立4核，观察到 GPU 合计1307MiB；不是独占性能计时。queue exit 全0，原180秒截止内完成。CUDA复数求解补验：complex128 相对残差3.984817089850038e-16≤1e-10；complex64 2.137434620408385e-7≤1e-4（良态5×5系统）。保留先前失败部署/截止fixture日志，不删除失败分母。

验证：direct_capacity/no_repair 7项测试通过；legacy_vector_audit 编译通过；实际 GPU/LDPC 配对与 CUDA solve 输出见上述 JSON。inline 检查通过，未修改历史接收算法。
