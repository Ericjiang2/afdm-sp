# 完整 CE 状态、风险分解与文献边界

日期：2026-09-15。任务：THEORY-01；主会话推导及自审，独立性 **weak**。
本文绑定 `ce-state-theory-checks-v1.json` 中的源码哈希，不覆盖历史推导包。
证据为源码核对、有限代数检查和指定原文段落；本行 **0 新 G1 接收链、0 FER**。

## 1. 当前实现的充分状态

固定输入为观测 $y$、已缩放导频 $p$、物理噪声功率、码、星座、字典参数及完整超参数日程。
对于本轮 FULL 配方，在外层轮次边界可用以下带记忆状态描述确定性转移：

\[
 z_t=(S_t,g_{t-1},\widehat H_{\mathrm{active},t-1},\widehat H_{t-1},
       x_{\mathrm{soft},t-1},\mu_t,V_t,\sigma^2_{\mathrm{eff},t},
       L_{\mathrm{code},t},L_{\mathrm{channel},t},m_t,t,r_{t-1},s_t).
\]

这里 $m_t$ 记录 moments 的来源及译码 checkpoint；$s_t$ 记录停止状态。
启用固定先验时还须保留初始化中心、支撑及 precision；启用历史选择器时还需符号/残差历史。
这些是充分记录，不主张最小状态：在具体轮次边界，一些字段可从其他字段重建。
不把未启用的学习模块、候选修正或随机控制偷偷并入本轮配方；切换这些模块须重新检查状态充分性。

源码对应：`classical_joint_unrolled.py` 初始化约1865–1885；CE约2104–2229；
H重建、阻尼与逐元素软阈值约2293–2338；检测及反馈约2348–2442；
噪声EMA和残差停止约2448–2485；`supplement_feedback.py:104–194`。
`CodeFeedback.capture` 保存检测 channel LLR 和离散后验矩；checkpoint译码用本次 check extrinsic **替换** prior，
并按 channel+delivered prior 重建因子化矩，不跨轮累加APP。
BP内部消息在每次检测调用时重新初始化；上述 prior、矩和 H 记忆跨轮保留。
仅 $(S,g,\mu,V)$ 不能区分相同四元组、不同 prior/噪声/阻尼记忆/checkpoint 的下一轮输出。

本轮首次DA-LS是 $t=1$：`ce(1)` 读取 $t=0$ 未译码检测的矩；
随后 $t=1$ 检测，最后才调用 checkpoint=1 的LDPC。
O3只能在 `ce(1)` 返回后、`x_total` 构造前替换局部均值；$t=2$ 恢复正常反馈。
源代码变量 `x_hard_scaled` 在 soft FULL 分支实际是均值，不能被变量名误导。

## 2. 固定状态的仿射 CE

给定整数原子 $U_i\in\mathbb C^{N\times N}$、支撑 $S$、设计输入 $x=p+\mu$，令

\[
 A_x=[U_i x]_{i\in S},\quad
 f(g)=(y-A_xg)^HW(y-A_xg)+\lambda\|g-g_{\rm previous}\|^2+g^HQg.
\]

假设 $W=W^H\succeq0,Q=Q^H\succeq0$，且

\[
 M=A_x^HWA_x+\lambda I+Q\succ0,\quad
 B=M^{-1}A_x^HW,\quad c=M^{-1}\lambda g_{\rm previous}.
\]

配方对应的精确解是

\[
 \widehat g=By+c.\tag{T1}
\]

普通路径 $W=I$。源码GLS路径先Cholesky解 $C$，再乘物理/当前有效噪声参数：

\[
 W=\sigma^2 C^{-1},\quad C=\widehat H V\widehat H^H+\sigma^2I.
\]

源码禁止同时提供 Q 与 C；本式统一两条**分别启用**的路径，不授权组合新臂。
Q是零中心惩罚，不在RHS加入 $Qg_{\rm previous}$。`proximal` 臂则增加 \(\lambda\)，中心仍为 previous。
Dirichlet/ridge先验的惩罚缩放依赖实际 $A_x$ 能量；换成真数据设计后必须按原公式重算。

推导：展开 $f$，与 $g^*$ 有关的一阶条件为

\[
 (A_x^HWA_x+\lambda I+Q)g=A_x^HWy+\lambda g_{\rm previous}.
\]

**必须冻结** $S,A_x,W,Q,\lambda,g_{\rm previous}$，才得到关于 $y$ 的仿射映射。
只冻结S不够：标量例 $A(y)=y,Q=0,\lambda=1,g_{\rm previous}=0$ 给出
\(\widehat g(y)=y^2/(y^2+1)\)，在 $y=0,1,2$ 分别为 $0,.5,.8$，并非仿射。
同一观测决定反馈、选支撑、权重和正则后，整轮接收机是更一般的非线性映射。

## 3. 实际误差：四向量、六个交叉项

令 $H_S=\Pi_SH=\sum_{i\in S}g_{S,i}U_i$ 是完整真实H在所选算子张成空间上的Frobenius正交投影，
\(R=H-H_S\)，真实观测为 \(y=H(p+d)+w\)。满秩时解向量化投影；秩亏时须明确秩阈值及最小范数解，
不能直接截取存在歧义的“真系数”。当前不同合法整数原子在Frobenius意义下正交，但不把这一事实外推到任意参数化。

由 \(H(p+d)=A_xg_S+Rx+H(d-\mu)\) 与T1得

\[
 \widehat g-g_S=\underbrace{(BA_x-I)g_S+c}_{e_{\rm map}}
 +\underbrace{BRx}_{e_{\rm tail}}
 +\underbrace{BH(d-\mu)}_{e_{\rm feedback}}
 +\underbrace{Bw}_{e_{\rm noise}}.\tag{T2}
\]

这是逐样本恒等式，不要求独立、零均值、白噪声或正确先验。必须保存四个复向量、四个平方范数、
六个 \(2\Re(e_i^He_j)\)，并核验

\[
 \|\widehat g-g_S\|^2=\sum_i\|e_i\|^2+\sum_{i<j}2\Re(e_i^He_j).\tag{T3}
\]

交叉项可正可负；各平方项占比不能作为独立风险占比。真数据干预令 \(\mu=d\)，反馈项为零，
但 $A_x,B,c,Q$ 也会改变，尾项和噪声投影同时改变。
因此O2是配对干预，不用50%/20%标签裁决“反馈主导/遗漏主导”。
错误时延系数能量只是系数误差的子分账，不能再与T3相加。

系数误差与实现的完整H误差分开。若 \(D_S= [\operatorname{vec}(U_i)]\) 且 \(D_S^HD_S=NI\)，
纯重建满足 \(\|U_S\widehat g-H\|_F^2=N\|\widehat g-g_S\|^2+\|R\|_F^2\)。
实际 \(\widehat H\) 还含阻尼、逐元素软掩码及可能启用的修正，须记
\(\Delta_H=\widehat H-U_S\widehat g\)，直接保存 \(U_S(\widehat g-g_S)-R+\Delta_H\) 的范数和交叉项。
不能一律写 \(\widehat H=U_S\widehat g\)。

## 4. 期望风险与同观测选择

固定上述设计及previous后，记 \(L=BA_x-I\)、
\(\eta=Rx+H(d-\mu)+w\)，令 \(m_g,m_\eta\) 为条件均值，
\(R_g,C_\eta,C_{g\eta}\) 为**中心化**条件协方差。则

\[
\begin{split}
\mathbb E\|\widehat g-g_S\|^2={}&\|Lm_g+c+Bm_\eta\|^2\\
&+\operatorname{tr}(LR_gL^H+BC_\eta B^H)
 +2\Re\operatorname{tr}(LC_{g\eta}B^H).\tag{T4}
\end{split}
\]

证明只需将 \(g,\eta\) 分成均值和中心化项并展开；本行的有限分布检查专门包含非零均值和相关扰动。
若设计本身随机，T4先条件化，再对设计积分；不能把随机的B从无条件期望中提出。
同y选S或形成反馈后，条件噪声通常不再保持原先的独立白零均值分布。
省略均值、交叉协方差的Wiener风险需要另加相应假设；匹配特征方向的最优Wiener标量风险
不为任意 ridge/diag/Dirichlet 强度提供普遍排序。

合法可观测预测只能用预先给定的先验/噪声模型及可观测状态；用本批真实 $g,R,d,w$ 算的T2/T4值是oracle诊断。
不得用同批真值拟合先验，再把其排序称为独立预测。

## 5. Schur几何与选择代理

固定带同一常数项的二次目标 \(C_0+g^HJg-2\Re(g^Hb)\)，
对增加一列后的 \(J_+=\begin{bmatrix}J_S&q\\q^H&h\end{bmatrix}\succ0\)，定义

\[
 s=h-q^HJ_S^{-1}q>0,\qquad
 f^*_S-f^*_+=\frac{|b_a-q^HJ_S^{-1}b_S|^2}{s}.\tag{T5}
\]

通过对旧坐标配方消元得到T5，非启发式近似。它只保证固定二次代理目标下降。
固定容量替换还要计删除的影响；若previous在增删维度中非零，须保留
\(\lambda\|g_{\rm previous}\|^2\) 对应常数，不可比较两个不同常数的最优值。

对无正则LS，\(G=A_S^HA_S,r=A_S^Ha,h=a^Ha\)，相同定义的Schur余量s给出白噪声方差增量

\[
 \sigma^2\{\operatorname{tr}(G_+^{-1})-\operatorname{tr}(G^{-1})\}
 =\sigma^2\frac{1+\|G^{-1}r\|^2}{s}.\tag{T6}
\]

增加列即使降低残差也增加该方差项；遗漏偏差和相关干扰需要T2/T4核算。
T5/T6均不是FER晋级门，也不等于Tipping–Faul的边际似然准则。

定义等能量K列的白噪声LS几何因子 \(\gamma=(E/K)\operatorname{tr}(G^{-1})\)。
\(G=EI\) 时严格 \(\gamma=1\)；若 \(\|G/E-I\|_2\le\epsilon<1\)，才可用谱界控制其放大。
小最大相干本身不够：24列、对角1、非对角 \(-(1-.001)/23\) 的合法正定Gram，
最大相干.043435、最小特征值.001、\(\gamma=42.5851\)。
旧W2的640状态 \(\gamma\le1.026229\) 是已有样本事实，不给W3/W4或新反馈5%的普遍保证。

## 6. 数据不确定性Q的等价条件

令 \(v=d-\mu\)、采用的二阶矩 \(V=\mathbb E[vv^H]\)。当均值确为所用分布的期望时，它是协方差；否则须保留均值偏差。期望设计正规矩阵中的不确定性项为

\[
 Q_{ab}=\mathbb E[(U_av)^H(U_bv)]
       =\operatorname{tr}(U_a^HU_bV).\tag{T7}
\]

这里Q不含导频；若V只是因子化后验的plug-in估计，T7是**该近似分布**的期望，而非真实码后验的保证。
CE侧Q与检测侧 \(C=HVH^H+\sigma^2I\) 不同，不能直接把Q当 \(\operatorname{tr}(BCB^H)\) 风险。

整数AFDM原子为带单位模相位的循环置换，物理位移
\(\delta_a=(2Nc_1)l_a+k_a\pmod N\)。当 \(V=\operatorname{diag}(v_n)\) 时：

- 若不同原子的循环位移各异，\(U_a^HU_b\) 无对角非零项，故 \(Q=(\sum_n v_n)I\)。
- 若位移碰撞，非对角Q为 \(\sum_n v_n\overline{u_a(n)}u_b(n)\)，一般不为零。
- 若 \(V=\bar vI\) 且原子Frobenius正交，即使位移碰撞也为零。
- 一般非对角V不满足以上按位移的坍缩。不能仅由单比特LLR恢复这种V。

合法反例：N1024、\(2Nc_1=5\)，原子(3,3)/(4,-2)同位移18；
\(v_n=.25[1+\cos(2\pi n/N)]\) 可由已缩放QPSK边缘实现，
Q对角256，交叉项模128。任意更换p均不改变这一固定V结果。
边缘不可识别反例：两个符号都在 \(\{\pm.5\pm.5j\}\) 上均匀，所有单比特LLR都为0；
独立符号时 \(V_{12}=0\)，两个符号完全相同时 \(V_{12}=.5\)，边缘LLR无法区分。
实际Q、Schur和直方图随既定oracle/导频状态采集，不为证明额外开接收链。

## 7. 平均Gram与可检验范围

固定S、零均值数据、\(\mathbb E[dd^H]=P_dI\)、原子Frobenius正交且p确定时，

\[
 \mathbb E_d[A_{p+d}^HA_{p+d}]=A_p^HA_p+NP_dI.\tag{T8}
\]

逐项展开即可：两项含d的交叉均值为零，数据二次项是 \(P_d\operatorname{tr}(U_a^HU_b)\)。
本行N4全256种QPSK枚举核验T8。T8不推出 \(\mathbb E[G^{-1}]=(\mathbb E G)^{-1}\)，
也不适用于任意同y选S或真实软反馈 \(\mu_t\) 的所有轮次。
导频、支撑、遗漏响应、干扰和反馈同时变化时，须报告多状态条件及T2的全部项。
没有由此得到译码阈值、两个固定点或双稳态定理；经验传递若不由标量闭合就保留多维状态。

## 8. 验证与交付边界

执行：`.mission/20260914_12-58-51-afdm-unified-exploration/.venv/bin/python .trellis/tasks/09-13-trans-next/research/ce-state-theory-checks-v1.py`。
结果PASS：两次真实公共 `soft_gain_update` 单测（Q/GLS分开）、T2/T3六项交叉、
相关且非零均值的T4、T5/T6、合法Q碰撞/LLR反例、全枚举T8与小相干反例。
最大CE相对误差小于 \(8\times10^{-16}\)；Q碰撞交叉模为128；结果含源码SHA256及调用计数。
初次本地检查因包导入路径失败，尚未调用CE；已修复脚本路径，生产代码未改。
后续DICT-01会修复W与物理位移混用，当前代数检查不冒充W3/W4生产路径验收。

文献模型、原文式号、读取层级和缺口见 `ce-state-literature-map-v1.md`。
普通Wiener、Schur、Q恒等式及完整记忆记账是分析工具；本行不将其认领为新算法贡献。
