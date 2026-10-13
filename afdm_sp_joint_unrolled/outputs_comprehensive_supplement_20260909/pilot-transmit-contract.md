# P-01 导频及发射合同

## 冻结选择与资源

p0 保留原 ZC 序列。p1 从原序列和 7 个预定随机相位常模序列中，只按公开字典的最大归一化列相干性最小化选择一次。p2 用独立固定种子产生，不进入候选池。种子、排序和判据在 N=1024 评估之前写入 `pilot-selection-protocol-v1.json`。

结果选中 index 3（phase-2）。p0 相干性 0.3757321，p1 为 0.0802623。该数值只说明选定字典的几何性质，不能证明接收收益。实际 pilot 数组冻结在 `frozen-pilots-v1.npz`，后续不得重新选样或按 FER 更新。

三个导频共享 N=1024、rho=0.5、长度 102 的 CPP、码率与数据量。每一配对块共享 H、已按数据功率缩放的 x、单位复噪声 w 和 sigma2。`paired_observations` 分别构造 y_p=H(sqrt(rho)p+x)+sqrt(sigma2)w；只向接收端返回 y、当前 pilot 和 sigma2，真 H 留在生成侧。字典由当前 pilot 重建；取消使用同一个当前 pilot，不能复用 p0 字典或取消缓存。

不对各帧 p+x 重新归一化。记录导频能量、数据能量、2Re<p,x>、payload 能量、prefix 能量、峰值和 PAPR。不同 p 的交叉项及有限帧总能量可以不同；等资源是相同预期功率、码率、帧长及前缀开销，不伪称每帧实际能量完全相等。

## DAFT、CPP 与传播

A=Lambda_c2 F Lambda_c1，Lambda 使用正号相位。IDAFT 实现为 conjugate(Lambda_c1) IFFT(conjugate(Lambda_c2)z) sqrt(N)。负时间样本补为 s[n+N] exp(j2pi c1(N²+2Nn))。

`propagate_cpp` 使用整数采样延迟、连续归一化 Doppler 与复增益，直接对 prefix 后样本传播，不做路径或全局能量重标定。整数路径同原 `gen_h_daft` 及 sensing dictionary 的关系已执行验证；非整数 Doppler 用解析 chirped tone 独立校验。FFT 变换与显式矩阵、小系统逆变换及 N=1024 逆变换均通过。

冻结 G0 仍使用原截断虚拟原子生成器。旧审计已证实其分数 Doppler 展开与上述物理传播存在差异；本工作不修改 G0，也不把它称为已验证的物理发射链。G1 使用明确的 CPP 物理关系，单独报告结果。用户对 G1/等资源导频仿真已有授权，见 gate-01.json；不涉及实际发射或硬件操作。

## 共同功率门

预先声明的仿真门：PAPR ≤12 dB，归一化峰值功率 ≤16。prefix 与 payload 共同检查峰值，分母使用 payload 平均功率。三个臂完全同门；任何不通过的块必须保留记录并标为不满足本仿真部署约束，禁止裁剪后假称原模型不变，禁止丢块选优。

单个固定合成 QPSK 向量的 p0/p1/p2 PAPR 为 8.239/9.924/8.950 dB，均过门；这不是全部数据或硬件功放的验收。P-02、CONF-P 必须逐块检查功率门与 prefix 能耗，并一起报告 FER、成本。实际硬件峰值限制未测，不能宣称硬件可部署。

## 验证范围

6 项数值测试通过，包括实际整数 `gen_h_daft`/字典对照、解析分数 Doppler、配对取消、Parseval 与交叉能量、确定性 pilot 及非法延迟。重复复杂数组运算曾在相同 CPU 上出现 ulp 级 dictionary hash 差异；几何分数按 1e-14 数值容差核对，冻结 pilot 数组仍逐位相同，实际字典哈希逐次记录，未修改科学门限。

本行验收为合同和实现，不代替 P-02/CONF-P 的配对科学试验、完整 G1 对照或最终独立审查。
