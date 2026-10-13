# 观测无关码设计：几何资格通过，性能待验证

固定旧随机码为唯一初值，经200个冻结Adam相位更新，在201个状态中按实际最大歧义峰选择第199点。mu从0.3253236536113068下降到0.18375555862063078，约43.5161%；selected Q=.00106464277847，单位模最大误差2.22e-16。通过预设至少10%峰值下降门；不表示全局最优或错误率改善。

数学上，N64受限联合Weyl轨道具有J1=15+16Q、1005项非特殊旁瓣能量15(1+Q)，因此mu>=1/sqrt67。二次CAZAC可以使J1达到最小却留下15个完全歧义峰；直接套用cubic64也有完全歧义。推导已被非作者独立复核。这些结论说明应评价危险峰，而非仅评价平均旁瓣能量；经典字符正交、CAZAC及Adam不称首创。

16项固定工程测试、独立source admission通过。源码9f889650，远端9906b88c2759dc84bb3d1a4e73fe697b6a7ffb86。D/A完整，累计1.382412423秒，RSS40689664 bytes；201个目标评估、202608几何值、0新观察/0获取/0设计随机抽样。A用直接字符及导数和独立复算201状态、12864导数、200更新，最大mu差2.22e-15、gradient6.59e-16、energy1.60e-14、Adam phase差0。

原始远端根 `/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_code_design_20261007/`。92/92回传stage文件SHA核对通过，完整路径/MD5/SHA在同名本地REMOTE_INVENTORY.json。新code.npz SHA88e1b59be3dca8d7ff997b8e01528eaa41d6a7ef8b1a5da6d8d1bee803cdaee8，trace SHA c69ecb6e75101ee889044c31b3b45f24dc4589c968c0b8fde9566aa6d61af2e7。

旧三批性能FAIL不变。OPTIMIZED_PROTOCOL.md单独冻结新三臂1024组验证，同码SCREEN128/FULL与旧随机/调优二次对照均保留。只有新的真实数据能判断几何改善是否变成性能收益；若与旧随机同批差异不足，不能把跨批变化归功于优化。
