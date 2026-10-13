# DET-01 验收

固定 real-EP10-damp0.5-f64，10次迭代、0.5阻尼、直接cavity LLR；算法/尺度/停止与异常规则见 detector-reference-preregister.json。仅诊断，不是部署候选；无改善不能证明 BP 最优。

9项CPU契约测试通过，退出0，命令与耗时见 mechanism-entry-tests-v5.log。小尺寸精确枚举、旋转一致性和近似误差见 dense-ep-audit.json；对角精确似然/离散矩、无观测、24位真实LDPC、非法输入均有测试。独立静态复核见 detector-independent-review.md。

真实N1024、engineering块17、8dB，使用冻结B_star，1完整+8终端调用成功。8.6375 GPU/host秒，8.4756 CPU秒，峰值260433408字节；计入共享资源账本。EP每格约0.30–0.35秒，仅工程成本探测，不能代替COST-02。完整命令、源码/配置哈希、原始记录、实测残差与正常输出比较见 factorial-wiring-tests.json 和 mechanism-smoke-v5/contract.json、complete.json。
