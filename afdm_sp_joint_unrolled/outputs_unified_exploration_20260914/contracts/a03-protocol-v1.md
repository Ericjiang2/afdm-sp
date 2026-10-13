# A-03 固定表示与共同接收循环

前置A-02：九配置均通过数值门；不按初始NMSE删除配置。此细则在新完整接收结果前冻结。

- `channel_representation=FixedBasisRepresentation`只接管一次组选择/初始化、9次A构造和10次H重建。共同soft_gain_update、H阻尼/阈值、20步BP、数据软反馈与噪声更新保持同一个forward循环。保留实际基和系数坐标；基编号不冒充Doppler。
- 9个BEM臂均LS初始化、mean DA-LS。经典四臂为OMP_BASE40、F2P_RESID40、OMP_SMALL12、OMP_SMALL_RIDGE12；small ridge在初始化和全部9次DA-LS均用普通零中心归一化强度0.1，无调参。
- observed-only适配入口保持y/pilot/sigma2/constellation四字段。进入旧CPU core时按complex64转换，基设计仍complex128；A-02组选择曾使用未舍入的观测，本层明确保留原core的complex64前端，不将两者宣称逐系数相同。A-03比较的全部臂共享这次前端转换。
- BEM禁止编码、oracle/诊断替换、支撑修复/交换、替代检测器、整数图捷径和新可学习头。只允许读出soft/graph状态；候选基、预算和物理带宽均公开固定。
- 先在旧信道0的四pilot/SNR端点回放OMP_BASE/F2P_RESID，共8F，与原数组逐bit/连续输出对账。随后复用A-02已保存的2个工程信道，每端点13臂，共104F；首块p0@20额外重复13F并各做一次固定最后H的单BP回放13T。总125F/13T，不新增科学信道。
- 每个F记录真实初始OMP/组OMP、gels/组refit、9CE、10BP、活动边、soft均值/方差、最后实际检测输入和初始化/设计/H算子计数。固定H回放同时检查硬判与软矩；这不是更换检测器或新的性能实验。
- 报价含公共基/字典构造、初始化、图构造/检测、CE与输出工作；配置和checkpoint设置另列，开发时保留同样插桩。以完整125F工程墙钟、每臂/端点上界和写入量估算64信道，不按工程BER挑臂。受每工程批1800秒/2GiB和开发阶段7200秒/8核时/20GiB约束。
- 若工程出现非有限输出、实际调用/信息边界或重复检查不合格，保留失败并诊断，不能以运行完成当作通过。默认路径回放、N256重复和实际计数都通过后才启动A-04。
