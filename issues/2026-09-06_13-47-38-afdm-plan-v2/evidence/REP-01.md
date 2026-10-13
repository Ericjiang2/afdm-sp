# REP-01 — 支撑与实际图账本

已实现并通过真实 D_cal997/frame0、direct40、A0/A2 集成验证。P_phys、原始 K_emit、复系数先合并后阈值 K_true，以及 raw/pool/selected/union/protected/pruned/final 的真实集合、数量和临时容量分列。完整 truth 不按接收机 Doppler 域截断，域外原子保留且接收机 ID=null。阶段差集是重叠历史关联；已活跃真值不算未入候选池，A0 直接标 repair_disabled。

物理槽匹配在数据前固定 delay/Doppler 各0.5、一对一最大匹配后最小距离；完全碰撞真值排除并单列，争抢和多解候选单列。接收机没有物理槽估计器，因此物理召回=null，不以K/P代替。默认无估计器也记录已知真值碰撞。

实际BP图复用检测器转complex128后的mask和row/column索引，记录阈值>=、E、完整度向量、H hash、舍弃平方F范数及分母。零H比值undefined；零图测试只覆盖图观察契约，不声称其终端soft/LDPC处理已验收。

7项REP测试及18项联合针对性测试通过。真实样本 P_phys=8、K_emit=K_true=13；两臂final K=40，但末次图E分别18432/15360，证明E不能由K代替。每臂10outer+1final完整。证据：repwire-runtime-validation.json、analyze_repwire.py、repwiresets-1788686980-runtime.tar.gz。失败尝试与费用见WIRE-02.md。CLAIM-063全局综合要求保持pending。
