# CORE-01 direct40容量契约

新增resolve_receiver_capacity统一解析：direct40必须整数cap40→nomination40/extension0；legacy cap40仍→8/2。forward新增receiver_extension，不改cfg.k_leak或物理生成器。注册容量检查初始/每outer/最终唯一atom ID，并记录F2P临时union独立预算。非法域、重复列、越界/超容量显式失败。

先运行新增契约，因resolve_receiver_capacity缺失而失败；实现后本地CPU 21项容量/软反馈/诊断回归通过，py_compile通过。原始命令与结果见CORE-01-checks.json及CORE-01-tests.txt。独立小复数求解涵盖complex128≤1e-10与complex64≤1e-4。没有声称GPU、prior、runner或LDPC接线验收；这些分别由后续WIRE/RUN行负责。

现有未提交classical中的fixed-cap、诊断hook、soft-feedback基础属于本CSV直接依赖；已按diff复核且纳入相关回归，保留其现状随容量提交。启动前hash在GOV-01-source-snapshot.json，未撤销其他修改。本次新容量功能的最小测试为test_direct_capacity；额外旧回归证据对应当前工作树，不冒称仓库其他未提交依赖已交付。

初审：模拟k_leak与receiver extension分离，默认None保持旧数值路径，无第二个扩展实现。回归：初始、临时、外轮、最终容量及非法配置测试通过；新增规范已同步。真实GPU历史错误向量回放仍由RUN-02验收。
