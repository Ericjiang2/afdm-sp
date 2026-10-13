# 技术稿：固定侧带截断与盲功率可辨识性不相容的一个 AFDM 实例

本稿组织已独立审阅的定理与证明，供论文模型分析小节及附录使用。它不修改现行论文，也不声称一般的对称性原理、CMA 或谱因子分解是新方法。数值接口和完整限制见 [研究报告](RESEARCH_REPORT.md)。

## 模型与核心命题

固定相干响应 \(H\in\mathbb C^N\)，观察

\[
Y^{(t)}=\operatorname{diag}(H)US^{(t)}+n^{(t)},\quad t=1,\ldots,T,
\]

其中 U 为已知 DAFT 逆变换，源为独立均匀 QPSK，噪声各快照相互独立、与全部源独立，且 \(n^{(t)}\sim\mathcal{CN}(0,\sigma^2I)\)。所有概率均条件于同一固定 H；不在本命题中边缘化 gain prior。

**命题 1（完整模型的功率不可辨识性与截断模型的相反性质）。**

(a) 对共同零 delay 的完整双径响应，采用与完整响应匹配的 Gram 归一化。只要共同 Doppler 平移 a 后仍为合法参数，存在单位对角 \(D_a\) 使 \(H_{\mu+a}=D_aH_\mu\)。任意有限 T 的原始坐标功率数组 \(\{|Y_i^{(t)}|^2\}_{i,t}\) 联合分布均不变，即使已知信号尺度和噪声方差。任何该数组的可测统计都不能识别此轨道上的共同中心。

(b) 在冻结 G0 中，设 N≥9，两条不同 Doppler 位于同一合法正分支 \(I\subset(.22,.42)\)，共同零 delay、无 clipping，且**每条路径**完整保留 m=−2,…,2 五行。若下文定义的有效复 gain 满足 \(\operatorname{Im}(\gamma_1\bar\gamma_2)\ne0\)，总体功率的三个去相位 Fourier 虚部唯一确定无序 Doppler 对，不需要未知 gain、信号尺度或噪声方差。因此这个截断模型的中心可辨识性不能外推到 (a) 的完整模型。

### (a) 的证明：把物理对称性推到整个观测分布

正时序完整列为 \(F_\nu(n)=e^{2\pi i\nu n/N}\)，所以

\[
F(\nu_1+a,\nu_2+a)=D_aF(\nu_1,\nu_2),\qquad
D_a=\operatorname{diag}(e^{2\pi ian/N}).
\]

匹配 Gram \(R=F^HF/N\) 在共同平移下不变。固定非零 raw gain g、\(g^HRg>0\)、相同尺度 τ，以

\[
H=\frac{\sqrt\tau Fg}{\sqrt{g^HRg}}
\]

归一化，得到 \(H_{\mu+a}=D_aH_\mu\)。在同一概率空间采用相同 S，并令 \(n'^{(t)}=D_an^{(t)}\)；圆白 Gaussian 噪声的分布及与 S 的独立性保持不变。于是逐样本 \(Y'^{(t)}=D_aY^{(t)}\)，故整块功率数组完全相等。耦合给出联合分布相等，进而给出所有其可测函数的分布相等。证明也适用于相同 proper Gaussian 对角噪声协方差；不要求 H 的所有坐标非零，也不要求 US 的坐标独立。证毕。

**源码符号边界。** 冻结 Dirichlet 系数是

\[
\alpha_N(m+\nu)=N^{-1}\sum_{r=0}^{N-1}e^{2\pi i(m+\nu)r/N}.
\]

用源码正号整数 Fourier 基补全全部 N 个残基时，双和正交性给

\[
\sum_{m\bmod N}\alpha_N(m+\nu)e^{2\pi imn/N}
=e^{2\pi i\nu r_n/N},\qquad r_n=(-n)\bmod N.
\]

因此对应反转时间索引；把 D 的 n 改为 \(r_n\)，同一证明仍成立。不能将该补全直接标成正时序 G1。

**现有 G1 控制的归一化边界。** 代码中的正时序 `g1` 复用了 G0 Gram。固定同一 g，写 \(r_0=g^HR_{G0}(\mu,\delta)g\)、\(r_a=g^HR_{G0}(\mu+a,\delta)g\)。固定 τ 未必给功率不变；当 τ 未知，选择 \(\tau'=\tau r_a/r_0\) 恢复精确调制关系。要求两能量正、mask 在邻域恒定、参数为内点且 τ′仍合法；足够小平移满足这些条件。这是 fixed-gain 参数类的混淆，不声称一个 τ′可统一匹配边缘 prior 的所有 gain 分量。

### (b) 的证明：消去共同 gain 因子后只剩一个单调方程

令

\[
h=\pi/N,\quad c=\cos h,\quad e=\cos2h,\quad
d=2c^2/e>2,\quad k=e^2/(dc^2).
\]

设 G0 合成系数 q 已包含信号尺度及 Gram 归一化，\(H_n=\sum_{m=-2}^2q_me^{2\pi imn/N}\)。Dirichlet 比值给出

\[
\beta_m=e^{imh}q_m=\gamma_1f_m(y_1)+\gamma_2f_m(y_2),\quad
y_j=\tan h\cot(h\nu_j)>1,
\]

\[
f_m(y)=\frac1{c_m(1+t_my)},\quad
(t_m)_{m=-2}^2=(-d,-1,0,1,d),\quad(c_m)=(e,c,1,c,e).
\]

有效 gain 包括各列的 Dirichlet 相位，故其非共线条件不能替换为 raw gain 的非同相条件。具体为
\(\gamma_j=\sqrt\tau\,\alpha_N(\nu_j)g_j/[a_N(\nu_j)\sqrt{g^HR_{G0}g}]\)，其中 \(a_N\) 是五点窗口的正范数。

总体功率 \(p_n=|H_n|^2+\sigma^2\)，定义

\[
I_\ell=\operatorname{Im}\left\{e^{i\ell h}\frac1N
\sum_{n=0}^{N-1}p_ne^{-2\pi i\ell n/N}\right\},\quad \ell=2,3,4.
\]

N≥9 分离 −4,…,4 全部功率谐波；噪声只占 DC，不进入这三个量。写

\[
P=y_1y_2>1,\quad S=y_1+y_2,\quad U_0=1+P,\quad V_0=1+d^2P,
\]
\[
A=U_0^2-S^2>0,\quad B=V_0^2-d^2S^2>0,\quad
\Gamma=(y_2-y_1)\operatorname{Im}(\gamma_1\bar\gamma_2)\ne0.
\]

展开 \(\operatorname{Im}\sum_m\beta_{m+\ell}\bar\beta_m\)，各自功率项为实数，而交叉项满足

\[
f_a(y_1)f_b(y_2)-f_a(y_2)f_b(y_1)
=\frac{(t_a-t_b)(y_2-y_1)}{c_ac_bD_{t_a}D_{t_b}},\quad
D_t=(1+ty_1)(1+ty_2).
\]

有限和因此化为

\[
\frac{I_4}{\Gamma}=\frac{2d}{e^2B},\quad
\frac{I_3}{\Gamma}=\frac{2(d+1)(U_0V_0-dS^2)}{ceAB},\quad
\frac{I_2}{\Gamma}=\frac{2dV_0}{eB}+\frac{2}{c^2A}.
\]

所有分母正，故 I₄非零。令

\[
x=\frac{cd}{(d+1)e}\frac{I_3}{I_4}
=d+\frac{(d-1)(P+1)(dP-1)}A>d,\qquad v=I_2/I_4.
\]

消去 S 得

\[
v=F(P;x)=e(1+d^2P)+kd^2+
k(d+1)\frac{dP+1}{P+1}(x-d),
\]
\[
F_P=ed^2+k(d+1)\frac{d-1}{(P+1)^2}(x-d)>ed^2>0.
\]

真实模型保证存在 P>1，严格单调保证唯一；然后

\[
A=\frac{(d-1)(P+1)(dP-1)}{x-d},\quad
S=+\sqrt{(P+1)^2-A},\quad y_{1,2}=\frac{S\pm\sqrt{S^2-4P}}2,
\quad \nu_j=h^{-1}\arctan(\tan h/y_j).
\]

正支、相异根和真实 mask 是明确的模型条件，不能靠裁剪样本根强行满足。相同总体功率必给相同 x、v，因而给相同无序节点。证毕。

给定节点后的增益/噪声设计为
\([|b_1|^2,|b_2|^2,2\operatorname{Re}(b_1\bar b_2),-2\operatorname{Im}(b_1\bar b_2),\mathbf1]\)。
其全分支秩 5 证明见 [POWER §8](../../.trellis/tasks/10-05-method-advantage/research/20261006-usable/POWER_IDENTIFIABILITY.md)：非零 Fourier 系数分离三个偶列、一个奇列及 DC。该辅助定理不提供统一最小奇异值；本轮浮点重建的失败诊断单独保留。原始 gain 公共径向尺度已被归一化消去，不是可恢复对象。

## 推论：相位敏感四阶对比能观察共同平移方向

设 U=RFᴴC，其中 R、C 为单位模 chirp 对角阵，F 为酉 DFT。另假设每个 H_i≠0。取所有候选**共同固定**的正幅度向量 \(\tilde a\)，可以直接取全 1。定义

\[
J(\theta)=E\|U^H\operatorname{diag}(e^{-i\theta}/\tilde a)Y\|_4^4,
\quad q_i=|H_i|/\tilde a_i>0,\quad\phi_i=\arg H_i-\theta_i,
\]
\[
\widehat d_k=N^{-1}\sum_i d_ie^{-2\pi\mathrm i ki/N},\qquad B(d)=\sum_k|\widehat d_k|^4.
\]

以下四阶闭合求和的索引 \(i,j,k,l\in\mathbb Z_N\)，所有闭合条件均按模 N 理解。则

\[
J(\theta)-J_\star=L_q(\phi)=N[B(q)-B(qe^{i\phi})]
=\frac1{N^2}\sum_{i-j+k-l\equiv0\; (\mathrm{mod}\,N)}q_iq_jq_kq_l
[1-\cos(\phi_i-\phi_j+\phi_k-\phi_l)].
\]

**证明。** QPSK 的平衡四阶累积量为 −1，且 Uᴴdiag(d)U 的每行二次模和均为 \(\beta=N^{-1}\sum q_i^2\)，四次模和均为 B(d)。变换噪声的共同边缘方差为 \(\eta=\sigma^2N^{-1}\sum\tilde a_i^{-2}\)，与候选相位无关。所以
\(J=N[2\beta^2-B(d)+4\beta\eta+2\eta^2]\)。展开 Fourier 四次方并求和给上式；其每项非负。零损失要求 \(e^{i\phi_i}\) 为公共相位乘循环 character；取闭合四元组 (i,0,k,i+k) 即得乘法关系，反向代入亦成立。

令到这些等价相位的平方距离为

\[
D^2=\min_{\varphi,r}\sum_i|e^{i\phi_i}-e^{i\varphi}e^{2\pi iri/N}|^2.
\]

单位 q 时，写 \(m=\max_k|\widehat{e^{i\phi}}_k|\)，有 \(D^2=2N(1-m)\)、\(L_1=N(1-\sum_k|\widehat{e^{i\phi}}_k|^4)\)。Parseval 给各平方模和为 1，再用 \(m^4\le\sum|\widehat{e^{i\phi}}|^4\le m^2\)，得到 \(D^2/2\le L_1\le2D^2\)。逐项比较正权给

\[
\boxed{\frac{q_{\min}^4}{2}D^2\le L_q\le2q_{\max}^4D^2.}
\]

完整物理响应共同平移的残余相位为 \(e^{\pm2\pi ian/N}\)。当 a 非整数时，它不是循环 character：第 0 项固定公共相位，第 1 与第 N−1 项的乘积为 \(e^{\pm2\pi ia}\ne1\)。反转索引情形同理。因此对应 J 的总体 gap 严格为正。证毕。

这只沿共同平移轨道打破连续歧义，不证明所有物理参数的全局唯一性。character 是该对比的逐样本不变性，不能未经检查 DAFT 列相位就说完整 QPSK 分布也不变。这里先做非对角混合再取模，**不属于命题 1(a) 排除的原始坐标 power-only 统计**。总体最优与距离界不等于梯度法全局收敛或有噪有限样本优势。

## 为什么近似模型会有“额外信息”

对未作逐列归一化的固定 Fourier 投影 P，定义 \(E=[P,D_a]H\)。则

\[
|PD_aH|^2-|PH|^2=2\operatorname{Re}(\overline{D_aPH}\odot E)+|E|^2,
\]
\[
\|E\|_2\le\|(I-P)H\|_2+\|(I-P)D_aH\|_2.
\]

这给出交换子诊断：截断与物理调制不交换时，可以产生中心相关幅度；P=I 时严格消失。非零交换子不保证非零功率差，支撑增大也不保证信息单调增加。实际 G0 还有逐列窗口归一化与公共 Gram 归一化，必须按其代码处理，不能用这条原始投影恒等式取代完整 G0 公式。

## 适合论文保留的结论句

> In the fixed-channel, common-zero-delay model, a common Doppler shift preserves the joint law of all raw coordinatewise power measurements. The frozen five-component Dirichlet approximation breaks this modulation symmetry and admits a monotone second-order inverse on its positive, non-collinear branch. Thus, identifiability certified in the truncated model need not represent identifiability of the full channel. Phase-sensitive fourth-order contrasts can distinguish noninteger common shifts at the population level, without establishing a finite-sample receiver advantage.

本文数学命题在所列条件内有完整证明；三个谐波逆、完整/截断模型差异和四阶恒等式另有冻结 SSH 检查。新颖性定位是这个具体模型反差与解析证书，非一般原理首创。有限样本的强参考比较、共线未知节点层、全部物理参数恢复与生产收益仍未解决。
