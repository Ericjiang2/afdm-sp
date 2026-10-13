# FFT 整体四阶相位对比：人口识别、局部曲率与有限候选选择

## 1. Target / Status

本文解决：在实际 DAFT 混合的固定相干信道下，能否不用逐坐标四阶张量、也不用真实幅度，构造具有定量相位识别保证的整体四阶对比。

**解析结论。** 可以。在每个共同固定的正幅度权重下，样本 quartic 与 CMA 对比具有相同相位梯度；其人口超额是带正权的循环四阶相位闭合损失。零集恰为全局相位乘循环 character，并有全局商距误差界及显式局部强凸区域。直接取幅度权重全 1 即可，不需要知道信道幅度或噪声方差。若二阶统计和物理约束只留下有限个不同相位候选，则优先对候选做 FFT 评分，不必先优化 N 维相位。

**证据状态。** 本文的核心公式已获独立解析核查，尚未运行梯度检查或验证有限样本收益。CMA、ICA 非 Gaussian 对比及谱因子零点翻转均为经典机制；本文不声称方法首创。新增 [POWER_IDENTIFIABILITY.md](POWER_IDENTIFIABILITY.md) 已证明：在冻结 G0、N≥9、完整五 atom、正 Doppler 且有效 gain 非共线时，二阶虚部 I₂/I₃/I₄ 已唯一恢复节点，不需要噪声或尺度真值。因此四阶不是该分支泛型节点识别的必要条件；退化层及有限样本收益仍待判断。完成本文不代表长期“可用推断或论文成果”目标完成，也不能将冻结截断 G0 的识别结论直接外推到未截断物理信道。

任务权威为同目录 [ROUND.md](ROUND.md) 指向的 PLAN/CSV；本文不保存第二份任务状态。旧证据只读：

- [BLIND_INVARIANTS.md](../20261006-deep/BLIND_INVARIANTS.md)：固定 H、DAFT 约定、完整四阶闭合与 character 歧义。
- [ALGEBRA_CANDIDATES.md](../20261006-important/algebra/ALGEBRA_CANDIDATES.md)：物理三 atom 反演与完整 H 的限制。
- 源码 experiments/afdm_efficient_information/prior_likelihood.py 的 daft、system_for：继承实际变换和随 N 变化的 cap；不能用固定三 atom 替代所有 N。

## 2. Invariant object / Assumptions

下标属于 \(\mathbb Z_N\)，所有期望条件于同一个固定 H：

\[
Y^{(t)}=\operatorname{diag}(H)US^{(t)}+n^{(t)},\qquad
n^{(t)}\sim\mathcal{CN}(0,\sigma^2I),\qquad U=RF^HC.
\tag{1}
\]

\(F_{ki}=N^{-1/2}e^{-2\pi\mathrm i ki/N}\)；R、C 为已知单位模 chirp 对角阵，与源码 \(U=A^H\) 一致。各 \(S_i^{(t)}\) 为独立均匀旋转 QPSK，满足
\(E S_i=E S_i^2=0,\ E|S_i|^2=E|S_i|^4=1\)，平衡四阶 cumulant 为 −1。不同 t 独立，噪声独立于符号。H 包括实际信道增益尺度，不再对 H 或 gain 边缘化。

选一个**对所有相位候选共同固定**的正向量 \(\tilde a\)，定义

\[
\begin{aligned}
H'_i&=\tilde a_i e^{\mathrm i\theta_i},&
b&=\operatorname{diag}(1/H')Y,&z&=U^Hb,\\
d_i&=H_i/H'_i=q_i e^{\mathrm i\phi_i},&
q_i&=|H_i|/\tilde a_i,&
\phi_i&=\arg H_i-\theta_i.
\end{aligned}
\tag{2}
\]

本节起先假设 \(H_i\ne0\)，故 \(q_i>0\)。固定 \(\tilde a\) 不必等于真实幅度；最简单的选择是 \(\tilde a_i=1\)。定义

\[
\widehat d_k=\frac1N\sum_i d_i e^{-2\pi\mathrm i ki/N},\quad
B(d)=\sum_k|\widehat d_k|^4,\quad
\beta=\frac1N\sum_iq_i^2.
\tag{3}
\]

归一化为 \(1/N\)，不是酉 Fourier 的 \(1/\sqrt N\)。对应信号混合阵

\[
V=U^H\operatorname{diag}(d)U=C^HF\operatorname{diag}(d)F^HC,
\quad |V_{st}|=|\widehat d_{s-t}|.
\tag{4}
\]

因此各行的二范数平方都等于 \(\beta\)，各行四次模和都等于 \(B(d)\)。这一步使用 DAFT 的已知 Fourier/chirp 结构，不能替换为任意酉混合阵。

## 3. Main derivation：人口四阶与 Gaussian 项

独立 proper QPSK 的四阶恒等式给

\[
E\left|\sum_s v_sS_s\right|^4
=2\left(\sum_s|v_s|^2\right)^2-\sum_s|v_s|^4.
\tag{5}
\]

变换后的噪声为

\[
\eta=U^H\operatorname{diag}(1/H')n,\quad
C_\eta=\sigma^2U^H\operatorname{diag}(\tilde a^{-2})U,\quad
(C_\eta)_{jj}=\nu=\frac{\sigma^2}{N}\sum_i\tilde a_i^{-2}.
\tag{6}
\]

整个 \(C_\eta\) 与候选相位无关；各坐标噪声可以相关，本推导只需其共同边缘方差。由独立 proper Gaussian 的四阶展开，

\[
J(\theta):=E\sum_j|z_j|^4
=N\left[2\beta^2-B(qe^{\mathrm i\phi})+4\beta\nu+2\nu^2\right].
\tag{7}
\]

这不是把噪声忽略或估计后扣除：固定 \(\tilde a\) 时其余相位无关项自动不影响人口排序。有限样本中噪声仍影响评分方差和梯度。

令
\[
\mathcal C=\{(i,j,k,l)\in\mathbb Z_N^4:i-j+k-l=0\},\qquad
\Delta_{ijkl}\phi=\phi_i-\phi_j+\phi_k-\phi_l.
\]
Fourier 正交性给

\[
B(qe^{\mathrm i\phi})
=\frac1{N^3}\sum_{\mathcal C}q_iq_jq_kq_l
e^{\mathrm i\Delta_{ijkl}\phi}.
\tag{8}
\]

右端为实数；将各项与共轭项配对后，所有项在 \(\phi=0\) 同时达到最大实部。故最小人口目标 \(J_\star\) 存在，且

\[
\boxed{\quad
L_q(\phi):=J(\theta)-J_\star
=N[B(q)-B(qe^{\mathrm i\phi})]
=\frac1{N^2}\sum_{\mathcal C}q_iq_jq_kq_l
[1-\cos(\Delta_{ijkl}\phi)].
\quad}
\tag{9}
\]

每项非负。若 \(L_q=0\)，取闭合四元组 \((i,0,k,i+k)\)，令
\(u_i=e^{\mathrm i\phi_i}/e^{\mathrm i\phi_0}\)，得到 \(u_{i+k}=u_iu_k\)，
因而 \(u_i=u_1^i\) 且 \(u_1^N=1\)。反向代入也成立：

\[
L_q=0
\quad\Longleftrightarrow\quad
e^{\mathrm i\phi_i}=e^{\mathrm i\varphi}\chi_r(i),\qquad
\chi_r(i)=e^{2\pi\mathrm i ri/N},\quad r\in\mathbb Z_N.
\tag{10}
\]

这个零集对所有严格正 q 相同。**未知幅度改变权重和条件数，但不造成人口相位偏差。**

## 4. 全局误差界：character 商距

先令 \(q_i=1\)。记 \(p_k=|\widehat {e^{\mathrm i\phi}}_k|^2\)，则
\(\sum_kp_k=1\)，且

\[
L_1=N\left(1-\sum_kp_k^2\right).
\tag{11}
\]

定义未归一化平方商距

\[
D^2(\phi)=\min_{\varphi,r}
\sum_i|e^{\mathrm i\phi_i}-e^{\mathrm i\varphi}\chi_r(i)|^2
=2N(1-m),\quad m=\max_k|\widehat {e^{\mathrm i\phi}}_k|.
\tag{12}
\]

由 \(m^4\le\sum_kp_k^2\le m^2\)，得到

\[
\frac{1+m}{2}D^2\le L_1
\le\frac{1+m+m^2+m^3}{2}D^2,\qquad
\frac12D^2\le L_1\le2D^2.
\tag{13}
\]

一般 q 由 (9) 逐项比较：

\[
q_{\min}^4L_1\le L_q\le q_{\max}^4L_1
\quad\Longrightarrow\quad
\boxed{\frac{q_{\min}^4}{2}D^2\le L_q\le2q_{\max}^4D^2.}
\tag{14}
\]

若目标和距离都除以 N，常数不变。该界说的是“人口目标值接近最优 ⇒ 相位接近某个 character 等价类”，**不蕴含所有驻点正确或梯度法全局收敛**。

全局相位与 character 不仅使人口目标相同，也使每个样本的 quartic/CMA 相同：乘 character 经 \(U^H\) 共轭后是单位模对角阵乘循环置换，故不改变输出四范数。增加样本不能由这个对比消除它们。这仅是 quartic/CMA 的精确不变性；DAFT 列 chirp 引入的旋转未必属于 QPSK 的 C₄ 对称群，因此不能据此宣称完整 QPSK 观测分布也不变。

## 5. 局部曲率与一个严格限定的有限样本结论

在任一 character 极小点附近去掉该 character，并选局部相位 lift
\(\epsilon\in\mathbb R^N,\ \sum_i\epsilon_i=0\)。令
\(P=I-\mathbf1\mathbf1^T/N\)，
\(v_{ijkl}=e_i-e_j+e_k-e_l\)。则

\[
\nabla^2L_q(\epsilon)
=\frac1{N^2}\sum_{\mathcal C}q_iq_jq_kq_l
\cos(v_{ijkl}^T\epsilon)\,v_{ijkl}v_{ijkl}^T,\qquad
\frac1{N^2}\sum_{\mathcal C}v_{ijkl}v_{ijkl}^T=4P.
\tag{15}
\]

第二个恒等式可将四个平方项与六个交叉项分别求和验证。特别地

\[
4q_{\min}^4P\preceq\nabla^2L_q(0)\preceq4q_{\max}^4P,\qquad
\nabla^2L_1(0)=4P.
\tag{16}
\]

若 \(\|\epsilon\|_\infty\le r<\pi/8\)，每个闭合角绝对值不超过 \(4r\)，所以

\[
4q_{\min}^4\cos(4r)P
\preceq\nabla^2L_q(\epsilon)\preceq4q_{\max}^4P.
\tag{17}
\]

这是去掉全局相位后的显式局部强凸区域，不覆盖所有初值。单位幅度时，

\[
L_1(\epsilon)=2\|\epsilon\|_2^2+R(\epsilon),\qquad
|R(\epsilon)|\le\frac83\|\epsilon\|_\infty^2\|\epsilon\|_2^2.
\tag{18}
\]

证明使用 \(|1-\cos x-x^2/2|\le x^4/24\)、\(|v^T\epsilon|\le4\|\epsilon\|_\infty\) 及 (15)。没有三阶项，因为 \(L_q(\epsilon)=L_q(-\epsilon)\)。

**有限样本局部引理，仅限 noiseless + 精确幅度。** 令 \(\sigma=0,\tilde a=|H|\)，在真相位处 \(z=S\)。对每个样本，
\[
\sum_j(|z_j|^2-1)^2\ge0
\]
且真相位恰取零，所以真相位也是该有限样本目标的全局极小点；这不能排除其他有限样本零点。

令 \(K_\epsilon=U^H\operatorname{diag}(\epsilon)U\)，用残余相位 \(d=e^{\mathrm i\epsilon}\) 作局部坐标，定义实线性映射
\[
B_t\epsilon=-2\operatorname{Im}
\{\overline{S^{(t)}}\odot K_\epsilon S^{(t)}\}.
\]
该样本 CMA 在真解的 Hessian 为 \(2B_t^TB_t\)。由 (16)，
\[
E[B_t^TB_t]=2P,\qquad
\|B_t\|\le2\|US^{(t)}\|_\infty\le2\sqrt N,\qquad
0\preceq B_t^TB_t\preceq4NI.
\tag{19}
\]
在 \(N-1\) 维全局相位补空间上应用矩阵 Chernoff：对 \(0<\eta<1\)，
\[
\Pr\left[
\lambda_{\min}\left(\left.\frac1T\sum_tB_t^TB_t
\right|_{\mathbf1^\perp}\right)<2(1-\eta)\right]
\le(N-1)e^{-\eta^2T/(4N)}.
\tag{20}
\]
因此 \(T\ge4N\eta^{-2}\log((N-1)/\rho)\) 足以使经验 Hessian 在真解处以至少 \(1-\rho\) 概率下界为 \(4(1-\eta)\)。连续性再给某个局部邻域，但 (20) 本身未给其半径。这是保守的局部充分条件，不是全局恢复样本复杂度，也不适用于 raw 非等幅或带噪时的样本零点。

## 6. FFT 实现与 CMA 的精确关系

定义单样本目标 \(F(\theta;Y)=\sum_j|z_j|^4\)。固定 \(\tilde a\) 时，对每个实际观测都有

\[
\|z\|_2^2=\|b\|_2^2=\sum_i|Y_i|^2/\tilde a_i^2,
\tag{21}
\]

与候选相位无关。因此任意固定实数 \(R_0\) 的 CMA
\[
\sum_j(|z_j|^2-R_0)^2=F-2R_0\|z\|_2^2+NR_0^2
\tag{22}
\]
和 quartic 具有完全相同的相位排序、梯度及 Hessian。特别地无需利用真实增益或噪声来选择 CMA 模值常数。

令 \(w=|z|^2\odot z\)。由于 \(db=-\mathrm i b\odot d\theta\)，
\[
dF=4\operatorname{Re}(w^HU^Hdb)
\quad\Longrightarrow\quad
\boxed{\nabla_\theta F
=4\operatorname{Im}\{\overline{Uw}\odot b\}.}
\tag{23}
\]
符号为正。CMA 可用 \(w=(|z|^2-R_0)z\)；额外项为
\(-R_0\overline b\odot b\)，虚部为零。T 帧平均目标的梯度也按 T 平均。

一次评分只需 \(z=U^Hb=C^HF R^Hb\)，一次梯度再做 \(Uw=RF^HCw\)。因此每帧评分/梯度均为 \(O(N\log N)\)，T 帧为 \(O(TN\log N)\)，可按 batch 保存 \(O(BN)\) 工作内存；不构造 \(N^4\) 张量。全局相位不变性要求 \(\sum_i(\nabla_\theta F)_i=0\)，可作为未来实现检查。若优化相位，可固定 \(\theta_0\) 或采用均值零局部坐标；初始化与重启成本必须计入，本文没有全局收敛保证。

## 7. 幅度未知、估计误差与失效边界

**优先选择：\(\tilde a=\mathbf1\)。** 此时 \(q=|H|\)、\(\nu=\sigma^2\)，原始白噪声经相位和酉变换后仍为白噪声，无小幅度除法。相位人口识别不依赖任何噪声方差或幅度估计。代价是局部条件数界随 \((q_{\max}/q_{\min})^4\) 变化；动态范围大时可能比准确归一化的情况差。尚无证据说明两者谁具有更好的有限样本误差。

**可选幅度归一化。** 若固定估计满足
\[
\left|\tilde a_i/|H_i|-1\right|\le e<1,
\]
则 \(q_{\min}\ge(1+e)^{-1},q_{\max}\le(1-e)^{-1}\)，从而
\[
\frac{D^2}{2(1+e)^4}\le L_q
\le\frac{2D^2}{(1-e)^4}.
\tag{24}
\]
这是幅度误差影响条件数、但不产生人口相位偏差的界。归一化后噪声方差 \(\nu=\sigma^2N^{-1}\sum_i\tilde a_i^{-2}\) 可能明显增大。

若 \(\tilde a\) 从同一批评分数据自适应估计，不能直接将上述“固定权重人口公式”条件化后声称样本仍独立同分布。独立训练/评分拆分可避免该依赖；\(\tilde a=1\) 则无需估计这一步。

H 含零坐标时，(9) 仍是合法恒等式，但正权零集证明及正的稳定性下界失效；闭合图可能不连通，有额外相位歧义。\(q_{\min}\to0\) 也不允许统一稳定性结论。

该相位对比本身不估计完整信道幅度、噪声方差或物理路径。已知 \(\sigma^2\) 时可由 \(E|Y_i|^2-\sigma^2\) 恢复幅度平方；有限样本负值必须显式报告或经预先登记的估计规则处理，不能静默截断。未知噪声时必须另行解决功率/噪声分离，不能在评分器中偷用真实噪声。

## 8. 最小可执行候选：二阶生成候选，整体四阶选择

若二阶谱因子分解及实际物理约束已把 H 缩减为有限集合
\(\mathcal H=\{H^{(1)},\ldots,H^{(K)}\}\)，优先进行：

1. 用可部署的二阶估计和实际物理约束生成完整候选；不使用真实 H、Doppler、gain 或标签初始化。
2. 对所有非零候选，仅抽取相位 \(\theta^{(k)}=\arg H^{(k)}\)，共同取 \(\tilde a=1\)，计算
   \[
   \widehat J_k=\frac1T\sum_t
   \left\|U^H\operatorname{diag}(e^{-\mathrm i\theta^{(k)}})Y^{(t)}
   \right\|_4^4.
   \tag{25}
   \]
3. 按最小评分选候选；全局相位等价候选合并，character 等价候选必须交给物理约束处理。候选生成失败、空集、病态根、候选含零点、未决并列均保留为显式结果。

在精确人口候选包含真相位的情况下，(9) 保证真相位达到最小值；所有非 character 等价候选严格劣于它。若已知 Fourier mask 为 S，真合成支撑为 Q，则可保留的移位为
\(\{r:Q+r\subseteq S\}\)（r 的正负取决于候选乘 character 的命名）。只有排除全部非零移位，才可把四阶选择结论说成“至多剩全局相位”。不能仅凭“已知 mask”四字断言消歧；若 Q=S，还需要 S 没有非零循环平移对称性。

**N5 歧义对的直接推论。** 对任一实际可行的 \(H,H^\dagger\)，若逐坐标幅度相同且严格正，而 \(H/H^\dagger\) 不等于全局相位乘 character，则它们有相同协方差，却满足
\[
J(\arg H^\dagger)-J(\arg H)
=L_{|H|}(\arg H-\arg H^\dagger)
\ge\frac{\min_i|H_i|^4}{2}D^2>0
\]
（共同取 \(\tilde a=1\)）。该严格正人口 gap 对所有有限 \(\sigma^2\) 不变；gap 不被 Gaussian 项偏移不代表评分方差不随噪声增大。实际 N5 构造的非零、非 character 和物理可行性由相应二阶研究证明，本文不以假定代替该验证。

精确同功率谱因子有相同逐坐标幅度，故也可以共同使用那个正幅度向量归一化。**不应为不同近似候选分别使用不同幅度分母，再直接比较 quartic**：此时 \(\beta,\nu\) 和人口基准随候选变化，(9) 不保证正确排序。取共同的全 1 权重自动规避这个问题。

### 8.1 “至多 4 / 16 个因子”的适用前提

长度 L 的连续 Fourier 支撑，对应次数 \(L-1\) 的普通谱因子多项式。已知无混叠完整自相关，且不存在单位圆根、重复根等退化时，互为倒数共轭的根对给出至多 \(2^{L-1}\) 个因子，模去全局相位；物理约束还可继续删去候选。

- 三 atom、\(N\ge5=2L-1\)：至多 4；N4 不能直接套用无混叠根枚举。
- 五 atom、\(N\ge9=2L-1\)：至多 16；N6–8 的循环自相关存在混叠，不能直接套 16。
- 若未知噪声使自相关零阶未确定，必须先证明或估计其可辨识性；否则上述有限集合前提未成立。
- 这是谱因子数量上界，不是实际物理分支内多解存在的证明，也不保证从有限样本得到的功率估计恰有可行物理因子。

当前实际正 Doppler 分支，N4/N5 为三公共 atom，而 N≥6 通常保留五公共 atom。N5 的物理二阶歧义保留；但新增五 atom 命题已证明 N≥9、完整五行保留、正 Doppler、有效 gain 非共线时，可由 I₂/I₃/I₄ 直接单调反演节点，无需完整 DC 或 16 因子枚举。后续满秩证明还支持在已恢复不同正节点下恢复缩放归一化 gain 外积及噪声；具体条件见 POWER_IDENTIFIABILITY。数值病态、有效 gain 共线层、N6–8 混叠及有限样本收益仍须分别处理，不能再把泛型五 atom 的二阶可辨识性写成待判假设。

### 8.2 有限候选的有限样本保证及其边界

假设候选和共同 \(\tilde a\) 预先固定，或由独立训练集产生；评分集有 T 个独立观测。在候选集合中存在唯一人口最优等价类 0，令
\[
W_k=F(\theta^{(k)};Y)-F(\theta^{(0)};Y),\quad
\Delta_k=EW_k>0,\quad v_k=\operatorname{Var}(W_k)<\infty .
\]
QPSK 有界且 Gaussian 噪声的八阶矩有限，所以 \(v_k<\infty\)。单侧 Chebyshev/Cantelli 加并集界给
\[
\Pr(\widehat k\ne0)
\le\sum_{k\ne0}\frac{v_k}{v_k+T\Delta_k^2}
\le\sum_{k\ne0}\frac{v_k}{T\Delta_k^2}.
\tag{26}
\]
若候选含真相位，则
\(\Delta_k=L_q(\phi^{(k)})\ge q_{\min}^4D_k^2/2\)。
该界是正确性/一致性的充分结论；没有证明比逐坐标 cumulant 更省样本，\(v_k,\Delta_k\) 都可能依赖 N、动态范围和候选间距。

若有限样本候选集不含真相位，(26) 仅保证选中集合内人口最优者，不能保证其物理参数正确。一个明确的近似条件是：某候选到真相位商距至多 \(\delta\)，其他候选至少 d，则
\[
\Delta_k\ge \frac12q_{\min}^4d^2-2q_{\max}^4\delta^2
\tag{27}
\]
（右端为正时），由 (14) 相减得到。该式把候选生成误差与评分误差区分开；深衰落或几乎重合候选会削弱分离。

条件于独立训练集可使用相同推导。若同一数据同时产生和选择候选，上述有限集合概率界不能直接使用；必须另证一致控制，或预先固定拆分。评分额外成本为 \(O(KTN\log N)\)；总成本还包括功率估计、根枚举、物理可行性求解、任何训练拆分损失和失败处理。

## 9. Interpretation / Open risks

对比利用 iid QPSK 的负四阶 cumulant；如果源改为单位方差 proper Gaussian，(5) 中最后一项消失，(7) 完全不含相位。故这里没有“所有源分布都有效”的盲推断结论。

已知经典关系：这是约束在已知 DAFT 结构及相位校正上的 quartic/CMA 对比，有限候选选择也是用高阶统计消除二阶谱因子歧义的经典思路。可以争取的模型特定结论，是任意正幅度权重下的精确 character 零集、定量商距界、免幅度 oracle 的评分，以及它们与实际 N 依赖 mask/物理分支的兼容性；是否具有文献差异仍需查新和独立判断。

下一步优先验证已获解析支持的五 atom 二阶单调反演及其病态边界；N5 四阶对比用于核对实际等功率候选的消歧。若以后研究五 atom 的四阶收益，须针对方差、稳健性或额外退化层设置实际收益门，并以真实物理全功率拟合作强二阶参考。公平验证要求同原始 Y、相同 nuisance 知识、无真实初始化、预先冻结主指标与失败口径、完整端到端成本；oracle 与真实实现结果分开。

本文未运行任何科学数值、仿真或 SSH；实现及执行状态由任务 CSV 管理。文献差异认证、梯度实现核验和实际收益证据仍待完成。
