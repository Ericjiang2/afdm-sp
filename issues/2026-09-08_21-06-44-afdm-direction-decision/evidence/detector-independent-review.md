# 参考检测与八格接线：独立源码审查

审查模型：gpt-6-astra，low；独立子代理 `/root/csv_review`，未参与实现。仅读 direction_detector.py、direction_factorial.py、测试及 preregister；没有运行仿真，没有读取 D_design FER 或 D_test。

结论：本轮静态检查未发现阻塞。real2N 使用 sigma_complex/2；BPSK cavity LLR=2a*eta，正号对应bit0，allI/allQ；直接送真实LDPC，未二次Gaussian demap。非正site同时保留旧lambda/gamma且计数，非有限和Cholesky失败传播。零H的lambda4、拒绝0符合公式。

八格H_cancel/H_data独立选择，共用冻结sigma；pilot/data已缩放，不重复乘sqrt。每格重新取消并创建BP/EP状态，Hcov绑定Hdata哈希。保留3能量+3cross；正常输出单列；真值臂CSI_oracle，所有格只作诊断。before_call与异常传播支持失败计费。

证据边界：mock仅测路由，CPU小尺寸调用真实BP/EP/LDPC。审查时未核验v2实际运行，也未验证大N EP成本或性能；这些必须另有运行证据。

方法依据：[Schmid等，2024，§II-B](https://arxiv.org/html/2404.15968v2#S2.SS2) 的经典Gaussian-site EP描述。使用精确dense Cholesky求解，不声称采用其iCG新方法；固定10轮、阻尼0.5、float64与数值保护属本实验预登记选择。参考为近似推断，不是最优性下界。
