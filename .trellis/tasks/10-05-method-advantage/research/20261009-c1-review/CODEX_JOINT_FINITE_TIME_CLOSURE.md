# 联合估计–检测的有限步相关模型：Codex 独立推导与交接答复

作者：**Codex**。日期：2026-10-10。

归属边界：本文前半部分由 Codex 从已核验的实际递推独立推导。已读交接 c1-codex-handoff-joint-fp.md、J 测量汇总和探针实现，也已在前一阶段读过 Claude 的旧 c1-round1-loop-theory.md；本次初稿完成前**未读 c1-joint-fp-theory.md**。这是代码约束下的独立数学分析，不是观看 J 结果之前的预注册预测。数学核查代理只检查指定恒等式。

承接：[第一阶段独立推导](CODEX_FIRST_ROUND_INFORMATION_DERIVATION.md)；实际递推以下称原式 (12)–(20)。该文件式 (18) 的复数均值曾漏印加号，现已标记修正，原数值核验使用的是正确加法。

## Target

解释交接中的
\[
R_{\perp,T}=\frac{\|P_\perp(h_T-h^\circ)\|^2}
{\|P_\perp(h_I-h^\circ)\|^2},\qquad T=20,
\tag{J1}
\]
其中 \(h^\circ\) 是真实信道在接收机 DPSS 基上的投影，\(h_I\) 是独立随机化软符号的 refit。目标是从实际联合更新求出相关项，判断能否把它压缩为一个有效 \(\kappa\)。

J 汇总使用的工况统计量是“分子能量的帧中位数／分母能量的帧中位数”，不是逐帧 J1 的中位数。下面先精确恢复每帧能量，再按原统计规则取中位数；不把期望、逐帧比值均值或比值中位数混入原终点。

## Status

**COHERENT AFTER REFRAMING。**

得到有限步正规方程、误差比的精确分解和可直接微分的有限时响应模型。证明仅保留 MSE 的普适闭合不充分；在冻结的单个线性模态内，最少需增加“状态与同一随机源的交叉矩”。没有证明真实 AFDM 可由两个标量全局闭合，也没有得到仅从 \(K/N,\rho,\mathrm{SNR}\) 廉价计算十个 J 工况误差比的定律。

## Invariant Object

始终解释式 (J1) 的有限步误差比。反馈探针斜率、报告方差、固定点残差均是辅助量，不能代替这个目标。

J 的分子是联合接收机的 \(h_T\)，分母是另一次软 refit 的 \(h_I\)。二者**不是同一个估计器仅更换误差独立性**；推导必须保留这一差异。

## Assumptions

- 固定支持、flat prior \(I_K/K\)，原式 (12)–(20)，零译码先验，阻尼 \(\beta\in(0,1]\)。不改接收机。
- \(Y,p,n_0,P_d,K\) 沿整个 inner 循环不变；\(n_0>0\)。同一观测只生成一次。
- 算子 \(B(x)=[A_1x,\ldots,A_Kx]\)，\(\mathcal H(h)x=B(x)h\)。当前 DPSS 坐标 \(G_H=I\)。
- \(h^\circ\ne0\)，\(P_\perp=I-h^\circ h^{\circ H}/\|h^\circ\|^2\)。式 (J1) 分母为正时才定义比值。
- 代数恒等式不要求 Gaussian、正交导频、误差独立、收敛或大系统极限。
- 微分命题在固定支持且未跨越 precision floor / clipping 的分支上使用实微分；不可用假设全纯的 complex-step 差分。
- 随机矩闭合的线性化矩阵固定于一个指定参考轨迹；不把它们的帧平均代入后仍称全局精确。

## Notation

\(t\) 表示更新前的状态，\(t+1\) 表示本步输出。\(v_t,V_t\) 是报告方差，不是实际 MSE。原式中的 \(a_t,b_t,u_t,\bar x_t,\bar h_t,J_{h,t}\) 保留原义。

\[
B_t=B(x_t),\quad \bar B_t=B(\bar x_t),\quad
\Delta h_t=h_{t+1}-h_t,\quad \Delta s_t=s_t-s_{t-1}.
\]

\(h_S\) 是用当前输出软符号 \(m_T\) 作普通 refit 的结果；\(h_I\) 是独立随机化软符号 \(m_I\) 的同类 refit。二者都区别于 \(h_T\)。

## Derivation Strategy

先从实际更新消去输出残差，推导固定点公式遗漏的有限步项。再对两个 refit 作精确有限差分，把观测到的误差比拆为可测向量与交叉项。最后推导同一输入贯穿全部 inner 更新的切线系统，说明平方分母何时成立、最少缺什么状态。

## Derivation Map

1. 实际残差与 gain 更新 → 有限步正规方程 → 动态偏离项。
2. 两个真实 refit → 设计矩阵变化的精确响应 → 误差比的完整分解。
3. 实际递推的实 Jacobian → 同源输入的有限时传播 → 单模态最小二阶闭合。
4. 去掉历史、交叉矩或回归项的反例 → 对 \(\kappa\) 的可识别性与适用边界。

## Main Derivation

### 1. 有限步的正规方程，固定点只是其特殊情形

**恒等式。** 定义正标量
\[
D_t=n_0+a_t,\quad \ell_t=D_t-b_t,\quad
\omega_t=b_t+\frac{1-\beta}{\beta}D_t.
\tag{J2}
\]
由于 \(a_t-b_t\) 是 \(V_tv_t\) 的同阻尼平均，\(\ell_t\ge n_0>0\)。把原式 (14) 的 \(s_{t-1}=s_t-\Delta s_t\) 代入，有
\[
\boxed{Y-B_th_t=\ell_ts_t+\omega_t\Delta s_t.}
\tag{J3}
\]
原式 (20) 同时给出
\[
\bar B_t^Hs_t
=(K+u_tNv_t)h_t+(K+J_{h,t})\Delta h_t
+u_tNv_t(\bar h_t-h_t).
\tag{J4}
\]
将式 (J3) 左乘 \(\bar B_t^H\)，并使用式 (J4)，得到
\[
Q_t=\bar B_t^H\bar B_t+\lambda_t I,\qquad
\lambda_t=\ell_t(K+u_tNv_t)>0,
\tag{J5}
\]
\[
\boxed{Q_th_t=\bar B_t^HY-f_t,}
\tag{J6}
\]
其中没有省略的余项：
\[
\boxed{\begin{aligned}
f_t={}&\bar B_t^H(B_t-\bar B_t)h_t\\
&+\ell_t(K+J_{h,t})\Delta h_t\\
&+\ell_tu_tNv_t(\bar h_t-h_t)\\
&+\omega_t\bar B_t^H\Delta s_t .
\end{aligned}}
\tag{J7}
\]
四项分别来自符号阻尼差、gain 更新、gain 阻尼差和残差更新。precision floor 可以继续保留在 \(J_{h,t}\)，不会破坏此恒等式。

因此真正的本步输出为
\[
\boxed{
h_{t+1}=Q_t^{-1}\bar B_t^HY+
\underbrace{\Delta h_t-Q_t^{-1}f_t}_{d_{\mathrm{dyn},t}} .
}
\tag{J8}
\]
这是一个精确平衡式；计算右侧动态项仍需实际状态，不能把它宣传成不用运行接收机的廉价预测器。

**固定点推论。** 只有所有相关状态收敛时，
\(\Delta h_t,\Delta s_t,\bar x_t-x_t,\bar h_t-h_t\to0\)，且
\(a-b=Vv,\ u=(n_0+a)^{-1}\)。式 (J6) 才退化为
\[
[B(x)^HB(x)+(n_0+Vv)(K+uNv)I]h=B(x)^HY.
\tag{J9}
\]
所以 J9 是条件正确的固定点恒等式；用它替代 T=20 缺掉的正是 J7，而不是再乘一个经验吸收系数。

**可检验界。**
\[
\|d_{\mathrm{dyn},t}\|
\le\|\Delta h_t\|+\frac{\|f_t\|}{\lambda_{\min}(Q_t)}.
\tag{J10}
\]
若 \(e_R=P_\perp(Q_t^{-1}\bar B_t^HY-h^\circ)\)，则
\[
\left|\|e_R+P_\perp d_{\mathrm{dyn},t}\|^2-\|e_R\|^2\right|
\le2\|e_R\|\|P_\perp d_{\mathrm{dyn},t}\|
+\|P_\perp d_{\mathrm{dyn},t}\|^2.
\]
相对 \(\|h_T\|\) 只有几个百分点的偏离，仍可能占信道误差很大一部分。不能从“参数变化小”直接推断“误差比变化小”。

### 2. 误差比必须区分回归变化与联合迭代

**恒等式。** 写
\[
h_X=(B_X^HB_X+\lambda_XI)^{-1}B_X^HY,\qquad X\in\{S,I\},
\]
\(B_S=B(p+m_T), B_I=B(p+m_I), E=B_S-B_I,\ r_I=Y-B_Ih_I\)。对两条正规方程作差：
\[
\boxed{
\delta_{\mathrm{reg}}:=h_S-h_I
=(B_S^HB_S+\lambda_SI)^{-1}
\left[E^Hr_I-B_S^HEh_I-(\lambda_S-\lambda_I)h_I\right].
}
\tag{J11}
\]
这是任意幅度的有限差分。J 的 matched-MSE 分支把原报告方差传给独立 refit，故 flat 模式 \(\lambda_S=\lambda_I=K(n_0+v_T)\)。但是 \(B_S\ne B_I\)，两个 Gram 矩阵并不相同。

令
\[
\delta_{\mathrm{alg}}=h_T-h_S,\quad
z=P_\perp(h_I-h^\circ),\quad
u=P_\perp\delta_{\mathrm{reg}},\quad
w=P_\perp\delta_{\mathrm{alg}}.
\]
这里 \(w\) 仅表示投影后的算法差，以下不将它与物理热噪声混用。则
\[
\boxed{
R_{\perp,T}
=1+\frac{
2\Re(z^Hu)+2\Re(z^Hw)+\|u\|^2+\|w\|^2+2\Re(u^Hw)}
{\|z\|^2}.
}
\tag{J12}
\]
五个增量项可由同一帧的三个 gain 向量直接计算。此式同时保留相消和放大，不把相关项预先设为正。

**解释。** J 测得的 1.18–1.61 不能独自识别一个“未被 Onsager 抵消的比例”：其中包含软回归设计变化、联合迭代与普通 refit 的差异，以及它们与原误差的内积。交接中的 \(h_T\) 与 \(h_S\) 已有可观差别，这个区分不是形式问题。

此外，投影到真实信道的垂直空间并不自动去掉 ridge 偏差。令
\(Y=B_S h^\circ+r\)，则
\[
P_\perp(h_S-h^\circ)
=P_\perp Q_S^{-1}B_S^Hr-\lambda_S P_\perp Q_S^{-1}h^\circ.
\tag{J13}
\]
第二项通常非零；只有额外的等向 Gram 条件或 \(h^\circ\) 为 \(Q_S\) 特征向量时才消失。

### 3. refit 的完整微分不是一个 \(\beta d\)

**恒等式的微分。** 对
\(h_R=(B^HB+\lambda I)^{-1}B^HY\)，任意实参数方向满足
\[
\boxed{
Q\,\dot h_R
=\dot B^H(Y-Bh_R)+B^H(\dot Y-\dot B h_R)-\dot\lambda h_R.
}
\tag{J14}
\]
若软符号产生 \(\dot B=B(\dot m)\)，第一项是“设计变化与原残差的相关”，第二项包含符号被估计器吸收的方向，最后一项包含报告方差变化。只保留其中一项并用 trace 近似整个矩阵，不能得到一般的标量反馈斜率。

QPSK 的局部 denoiser 确实满足：在 pseudo-variance \(v_r\) 固定时，
\[
m_R=c\tanh(2c\,r_R/v_r),\quad
m_Q=c\tanh(2c\,r_Q/v_r),\qquad c=\sqrt{P_d/2},
\]
\[
\frac1{2N}\operatorname{tr}D_r m
=\frac{\overline v_{\rm reported}}{v_r}.
\tag{J15}
\]
它是实坐标下**单个 denoiser**的平均散度。这一局部代数恒等式本身不需要输入真的 AWGN；把其期望写成 \(qM_{\rm unc}(q)\) 才需要匹配 AWGN 的分布假设。

完整 detector 还经过 \(r(Y,h,\text{history})\) 和 \(v_r(Y,h,\text{history})\)。故实际微分是
\(D_r m\,\dot r+D_{v_r}m\,\dot v_r\)，还要经过所有前序步。J 中 \(d_{\rm hat},d_{\rm span},c_\perp/\beta_{\rm hat}\) 是三个不同响应，不能要求它们无条件相等。

### 4. 有限 T 的同源响应：历史与输入都必须保留

把复变量拆成实部/虚部，将原式 (12)–(20) 的充分状态记为 \(S_t\)：
gain、数据均值、报告方差、残差及其精度、阻尼均值和两个阻尼方差。设 \(y_{\mathbb R}=(\Re Y,\Im Y)\)。
\[
S_{t+1}=F_t(S_t,y_{\mathbb R}),\qquad
\dot S_{t+1}=A_t\dot S_t+B_t^{(Y)}\dot y_{\mathbb R},
\tag{J16}
\]
其中 \(A_t=D_SF_t,\ B_t^{(Y)}=D_yF_t\)，沿实际参考轨迹计算。上标用于区别观测响应与原设计矩阵 \(B(x)\)。

若 \(P_{T:j}=A_{T-1}\cdots A_j,\ P_{j:j}=I\)，则
\[
\boxed{
\dot S_T=P_{T:0}\dot S_0+
\sum_{j=0}^{T-1}P_{T:j+1}B_j^{(Y)}\dot y_{\mathbb R}.
}
\tag{J17}
\]
冷启动时 \(\dot h_0=W_p\dot Y\)，不能把 \(\dot S_0\) 随意设零。每步用的是**同一个** \(\dot y_{\mathbb R}\)，不能改为 T 个独立扰动。J17 是有限时响应，完全不需要假设 fixed point。

随文脚本通过原式逐项微分构造 Jacobian–vector product，不显式存储巨型 Jacobian。关键微分包括
\[
\dot X_t=2\Re(x_t^H\dot x_t)/N,\quad
\dot q_t=2\Re(h_t^H\dot h_t),\quad
\dot v_{t+1}=-2\Re(m_{t+1}^H\dot m_{t+1})/N,
\]
\[
\dot h_{t+1}
=\frac{\dot J_{h,t}h_t+J_{h,t}\dot h_t
+B(\dot{\bar x}_t)^Hs_t+\bar B_t^H\dot s_t
-N[(\dot u_tv_t+u_t\dot v_t)\bar h_t+u_tv_t\dot{\bar h}_t]
-h_{t+1}\dot J_{h,t}}{K+J_{h,t}}.
\tag{J18}
\]
其余乘积、倒数、tanh 与阻尼按链式法则传播；在 max 的固定分支上使用相应导数。

若把状态分成 \(S=(h,r)\)，消去辅助状态 r，一般会产生所有过去 \(\dot h_j\) 的记忆核。只有在固定点、辅助状态可稳定消去等额外条件下，才有 Schur 补响应
\[
C_{\rm eff}=A_{hh}+A_{hr}(I-A_{rr})^{-1}A_{rh},\quad
D_{\rm eff}=B_h+A_{hr}(I-A_{rr})^{-1}B_r,
\]
\[
\dot h=(I-C_{\rm eff})^{-1}D_{\rm eff}\dot y_{\mathbb R}.
\tag{J19}
\]
实际 20 步的 J17 与“固定 gain detector 跑 20 步，再普通 refit”的探针并非同一算子。探针中的定向 Rayleigh 商也不是自动成为联合递推的特征值。

### 5. 平方分母的条件，以及最少缺失的交叉矩

**条件命题。** 对冻结的单个线性模态
\[
e_{t+1}=a_t e_t+b_t\xi,\qquad
U_t=E|e_t|^2,\quad C_t=E[e_t\xi^*],\quad Q_\xi=E|\xi|^2,
\]
其中 \(\xi\) 是整个循环共享的同一个随机源、\(a_t,b_t\) 为确定系数，有精确二阶递推
\[
\boxed{\begin{aligned}
C_{t+1}&=a_tC_t+b_tQ_\xi,\\
U_{t+1}&=|a_t|^2U_t+|b_t|^2Q_\xi
+2\Re(a_tb_t^*C_t).
\end{aligned}}
\tag{J20}
\]
**最小性限于允许一般初始联合二阶矩的这类模型。** 取 \(e_t=\xi\) 或 \(e_t=-\xi\)，二者 \(U_t\) 相同，但 \(C_t\) 相反；当实 \(a_tb_t\ne0\) 时 \(U_{t+1}\) 不同。所以单个 MSE 状态不能闭合。实系数单模态用 \((U_t,\Re C_t)\) 两个实数；一般复系数用一个实 MSE 和一个复交叉矩闭合。若额外已知 \(e_t=g_t\xi\)，可直接跟踪带符号/相位的响应 \(g_t\) 而降维；不能声称任何初始化下都绝对需要两个状态。

当 \(a,b\) 恒定、\(|a|<1\) 时，
\[
e_T=a^Te_0+b\frac{1-a^T}{1-a}\xi,\qquad
U_\infty=\frac{|b|^2Q_\xi}{|1-a|^2}.
\tag{J21}
\]
只有再假定 \(a=c\) 为实、\(|b|^2Q_\xi=e_{\rm ind}\)、初值项已消失，才能写
\(e_\infty/e_{\rm ind}=(1-c)^{-2}\)。同一观测重复使用只支持“同源”这一条，**不证明分子仍等于独立 refit 的误差**。

更直接地，固定任意 \(0<c<1\) 和 \(Q_\xi=e_{\rm ind}>0\)，取 \(b=(1-c)\sqrt R\)，就得到任意指定的正误差比 R，而反馈斜率始终为 c。这证明的是：**仅凭斜率与独立误差，目标比值不可识别**；不是证明某个固定实验族永远不能建立经验标量近似。

对 J16 的冻结线性模型，令 \(\xi=\dot y_{\mathbb R}\)，矩阵版为
\[
C_{t+1}=A_tC_t+B_t^{(Y)}Q_\xi,
\]
\[
U_{t+1}=A_tU_tA_t^T+B_t^{(Y)}Q_\xi B_t^{(Y)T}
+A_tC_tB_t^{(Y)T}+B_t^{(Y)}C_t^TA_t^T.
\tag{J22}
\]
这是局部扰动二阶矩的充分闭合；若采用协方差而非原始二阶矩，还须单独传播均值。矩阵与基础随机帧相关时，不能把帧平均矩阵直接代入 J22。

**另一个反例。** 即使固定点线性稳定、驱动为各向同性，平均斜率也不能决定增益。令
\[
C=\begin{bmatrix}c&M\\0&c\end{bmatrix},\quad |c|<1.
\]
trace/2 和所有特征值恒为 c，但单位各向同性驱动的平均稳态增益为
\[
\frac12\|(I-C)^{-1}\|_F^2
=\frac1{(1-c)^2}+\frac{M^2}{2(1-c)^4}.
\tag{J23}
\]
这里取 c、M 实数。非正规耦合可任意改变误差，而平均探针斜率不变。不存在由这一斜率自动导出的普适上下界。

### 6. “只吸收热噪声”也需要相关矩，而非指定平方因子

**Gaussian 条件恒等式。** 固定真实信道和码字，使用实坐标：
\(Y_{\mathbb R}=\mu+\nu,\ \nu\sim N(0,\Sigma_\nu)\)，其中 proper complex 热噪声对应 \(\Sigma_\nu=n_0I/2\)。令 \(g(Y_{\mathbb R})\) 是估计数据的真实信道输出，\(s\) 是真实数据的输出，残差 \(r=s-g(Y_{\mathbb R})+\nu\)。在 Stein 恒等式的可微和可积条件下，
\[
\boxed{
E[rr^T]=E[(s-g)(s-g)^T]+\Sigma_\nu
-E[Dg]\Sigma_\nu-\Sigma_\nu E[Dg]^T.
}
\tag{J24}
\]
证明：展开平方，使用 \(E[g\nu^T]=E[Dg]\Sigma_\nu\)。

式 (J24) 保留了真实符号误差与噪声的相关。符号误差能量里已含其对噪声的响应；不能再任意把这一整体乘 \((1-d)^2\)。从 trace 散度还原到 refit 误差，仍需 J14 的方向权重和相关性。

J 的独立随机化控制还有一个明确条件：AWGN 新噪声独立，但其 q 被逐帧调到原 \(m_T(Y)\) 的真实 MSE，refit 的报告方差也来自原 Y。因此它是**匹配标量后的随机化对照**，不是对原观测完全外生的误差源。

在未截断、根简单的分支，若匹配条件为 \(f(q,\zeta)=v_{\rm true}(Y)\)，则
\[
D_Ym_I=\frac{\partial_qm_I}{\partial_q f}\,D_Yv_{\rm true}.
\tag{J25}
\]
这条通过 q 的数据依赖秩至多 1；通过 refit 正则化参数还有另一条依赖。它不使控制无效，但排除了不加条件地令全部相关项为零。

## Remarks and Interpretation

1. **应解释的对象已从一个 \(\kappa\) 改为有限步误差分解。** J7、J11、J12 是精确等式；J20/J22 是有明确参考轨迹的局部随机模型。二者不混用。
2. **20 步预算有独立的数学入口。** 它进入 J7 的尚未消失项和 J17 的有限乘积，不能用另一个标量映射的收缩率证明实际 kernel 已收敛。
3. **\(\rho\) 不只改变软数据能量占比。** 它同时改变 pilot ridge 初始化、每步 Gram、阻尼轨迹、报告方差及输入响应。现有推导不保证误差比关于 \(\rho\) 单调；J 的下降趋势需要上述项的有符号贡献解释。
4. **“同源相干”不等于“只有放大”。** J12 的交叉项可负，J21 的分子也可同时下降。仅通过误差比倒推的 \(\kappa_{\rm eff}\) 是重参数化，不能独立证明机制。
5. **投影约定须对齐。** J 的误差投影使用 \(h^\circ\)，而正交探针使用 \(h_T\)。两者的投影差范数为相应复一维子空间夹角的正弦；比较时应保留这一区别，不能默认同一模态。

## Boundaries and Non-Claims

- 没有把 J 的十个工况拟合成新 \(\kappa(\rho)\)，也没有称旧平方分母是有保证的上界。
- 没有声称两个标量足以描述真实 AFDM 全部状态；只证明冻结线性单模态的最小二阶状态需要交叉矩。
- 没有从局部导数推出无扰动帧的完整 MSE 或 FER。实际误差还有基线偏差、非线性与有限幅度效应。
- 当前 J 标量行不足以恢复 J12 全部向量内积；只有各项范数或各列中位数，无法反推出内积，也不能把中位数当作可加的期望。
- 参数无拟合不等于推导已经成为廉价工程预测器。原精确递推与本篇响应模型给出了可检验的数学基准；进一步压缩仍需证明或独立验证。

## Open Risks

剩下的具体问题是能否把 J17/J22 的方向与时间依赖压缩到少数可独立计算的模态，同时控制目标误差。J12 允许先查清真实超额主要来自哪个分量，避免再为未识别的混合量拟合一个“物理系数”。

## 最小数值核验与可执行预测

随文保存 [check_joint_finite_time.py](check_joint_finite_time.py)：仅作小矩阵、单线程的数学核验，结果写入 [joint_finite_time_checks.json](joint_finite_time_checks.json)；不改任何接收机或既有结果。

预先固定的检查：

- 用实际 DPSS/DAFT/CPP 算子验证 J3、J6–J8，逐步检查，包含非固定点暂态。
- 用中心差分核验 J16–J18 的完整同 Y 输入响应，T=10/20/40/80；比较 h 和 raw LLR。
- 验证 J11/J12 的有限差分、单模态交叉矩反例和 J23 的非正规响应。
- 所有失败均保留并显式退出；合成数组只代表代数验证，不代表 J 的新性能测量。

**可独立测试的预测**：给定一条参考轨迹，先由 J17 冻结扰动响应，再运行 \(Y\pm\epsilon dY\)。误差应在光滑分支上按中心差分的 \(O(\epsilon^2)\) 缩减。这是对有限时相关模型的局部预测，不是对 FER 的拟合。

对于 J 的实际误差比，最少只需追加三个 gain 向量及逐步 J7 的四项；无需再次跑 LDPC 或新建 FER 网格，即可逐帧核对 J12 并定位超额来源。是否足以压缩为标量，应由这一步的方向/交叉项结果决定。

**实际核验已通过，首次执行退出码 0，无失败、无阈值调整。** N=32，K=8/16/24，实际 DPSS/DAFT/CPP 算子；确定性数据和噪声数组；T=10/20/40/80。表中的向量误差使用二范数。

| 核验对象 | 结果 |
| --- | --- |
| J3；J6/J7；J8，逐 inner 步 | 最大残差分别 \(2.08\times10^{-15}\)、\(1.65\times10^{-14}\)、\(8.65\times10^{-16}\) |
| J11 两次 ridge 差；J12 误差比分解 | 误差均小于 \(6.8\times10^{-16}\)，包含相同和不同正则化参数 |
| 同 Y 的完整 h / raw LLR 响应 | 24 组 JVP；72 个中心差分误差减半比为 3.995248–4.010458，符合二阶 |
| 最细步长 \(\epsilon=5\times10^{-5}\) | 最大相对 JVP 误差 \(2.963142\times10^{-6}\)，位于 K=8、T=80 |
| 与已有 codex_recursion 的一次实现对照 | K=16、T=20，含算子的最大差 \(6.30\times10^{-15}\) |
| 单模态相关性反例、非正规响应反例 | 均通过 |

所有名义及扰动轨迹均未触发 precision floor、方差零分支或 tanh 数值饱和。核验使用四个预先固定的步长 \(4,2,1,0.5\) 乘 \(10^{-4}\)。这里的 \(m_I\) 是合法软符号的代数测试数组，**不是 J 的 matched-MSE 独立对照**；这些结果不验证 J 十个工况的性能预测。

为避免导入实验驱动时触发无关工作，脚本从本地源码抽取指定 AST 定义，记录完整文件与所用定义的 SHA256；核验不启动 LDPC、真实 C1 帧或服务器作业。JSON 中的理论稿 SHA 对应执行时版本，之后只在本文补充结果说明。脚本及配置未改变。

复现命令（从项目根目录执行）：

    PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 MKL_NUM_THREADS=1 \
    .mission/20261001_23-33-35-afdm-innovation-space/scratch/venv/bin/python -B \
    .trellis/tasks/10-05-method-advantage/research/20261009-c1-review/check_joint_finite_time.py

## 与 Claude 新推导的对照：在独立初稿之后进行

首次读取 c1-joint-fp-theory.md 前，本篇独立初稿 SHA256 为
3babf3c3255034608a7e93e20e877e4404d27ab6386a081a093c8243f5d6ff0c。
以下对照没有倒写成独立发现的先验条件。

### A. 固定点正规方程正确，但不足以替换整个接收机

Claude §1 的 \(\lambda_J=(n_0+Vv)(K+uNv)\) 与本篇独立 J9 一致，应该保留为**条件固定点恒等式**。标题中“round-1 output is a ridge”须限定为固定点；T=20 的正确版本是 J6–J8。

此外，“joint 的固定点也是 fixed-gain detector＋ridge 的固定点”还有独立的问题。实际探针调用 twofft.scalar_joint 的 fixed 模式，源码把 \(V\) 置零；联合模式保留 \(V>0\)。令候选 \(x=p+m,\ r=Y-\mathcal H(h)x,\ q=\|h\|^2,\ X=\|x\|^2/N\)，在 precision floor 未触发的固定点方程中，两者的数据自然参数分别为
\[
\boxed{\begin{aligned}
z_J&=u_Jqm+\frac{\mathcal H(h)^Hr}{n_0+Vv}-u_JVx,
&u_J&=\frac1{n_0+vq+V(X+v)},\\
z_F&=u_Fqm+\frac{\mathcal H(h)^Hr}{n_0},
&u_F&=\frac1{n_0+vq}.
\end{aligned}}
\tag{J26}
\]
二者一般不同。即使都真正收敛，也不能只更换 ridge 正则化就使这两个循环等价。需要保留数据端的不确定性项和相同状态，才能比较真正的 joint 响应。此结论由源码的 V=0 分支与原自然参数式直接推出，不依赖 J 的拟合优劣。

### B. “改变信道＝加一个等效观测扰动”也缺项

改变 h 会同时改变前向项、伴随项和功率归一化。以自然参数中的伴随项为例，
\[
\delta[\mathcal H(h)^Hs]
=\mathcal H(\delta h)^Hs+\mathcal H(h)^H\delta s.
\]
把信道变化只写成 \(\delta Y=-\mathcal H(\delta h)x\)，最多覆盖残差路径，遗漏第一项及 q、精度、方差的变化。因此 Claude §2(a) 的 \(c=\beta d_{\rm span}\) 不是一般恒等式。J 的 Q2 失败，也不能单独判定“额外增益一定来自 refit”；detector 对信道和观测的两种响应原本就不同。

### C. Bussgang 分解成立的对象与吸收公式的额外假设

对**匹配标量 AWGN posterior mean**，\(z=x+n_r\)、噪声方差 \(\sigma_r^2\)，数据误差 \(e_0=x-E[x\mid z]\) 确有
\[
E[e_0n_r^*]=-v,\quad d=v/\sigma_r^2,\quad
e_0=-dn_r+\varepsilon,\quad
E[\varepsilon n_r^*]=0,\quad E|\varepsilon|^2=v(1-d).
\tag{J27}
\]
Claude 的这一步可以保留，前提是 v 为该匹配 posterior mean 的真实 MSE。不能把实际算法的报告方差、最终真实 MSE、true-H 下的误差三者任取其一代入。

若实际等效输入噪声为 \(n_r=G\nu+\zeta\)，物理残差则是
\[
\mathcal H e_0+\nu
=(I-d\mathcal HG)\nu-d\mathcal H\zeta+\mathcal H\varepsilon.
\tag{J28}
\]
只有再规定 \(\mathcal HG\) 的作用、\(\zeta\) 的来源及交叉协方差，才能计算残差能量。把它直接换成
\((1-d)^2n_0+(1-d)qv\)，使用了不在原推导中证明的标量化与正交条件。对白化输入做 Bussgang 分解本身，并不能证明物理热噪声在每个 refit 方向都缩小同一倍数。

因此 \(A_B(d)/(1-\beta d)^2\) 应标为**带额外假设的候选近似**；J24 是更一般的相关矩恒等式。J 中 Q6 的 7/10 命中说明该近似在若干工况接近数量级，不能把 Q1、Q2、Q3、Q5、Q7 的失败全部解释为一个已确认的机制。

### D. 合并后的正确模型及结论边界

| 原推导环节 | 审查结论 | 合并后采用 |
| --- | --- | --- |
| joint 固定点 ridge 公式 | 条件正确 | J9；有限 T 使用 J6–J8 |
| fixed-gain 探针代替 joint | 一般不等价 | J26；联合响应用 J16–J18 |
| \(c=\beta d_{\rm span}\) | 缺少伴随、精度和完整 refit 导数 | J14 与完整链式法则 |
| matched AWGN 的误差–噪声分解 | 条件正确 | J27，不替换真实算法的误差分布 |
| \(A_B/(1-c)^2\) 给实际超额 | 未成立为普适定律 | J12 的有符号分解与 J20/J22 的同源交叉矩 |
| 由单个 c 得到 \(\kappa_{\rm eff}\) | 不可识别 | 同时保留驱动强度、方向和有限时历史 |

可直接执行的完整数学模型仍是：物理生成分布 → 原精确 T 步递推 → \(h_T,L_T\) → 逐帧误差/信息指标；本篇进一步给出每步遗漏项、精确对照差与局部响应。**正确的合并结果不再是一个未经证明的标量平方分母。**

本轮未重跑 J 的 400 帧，也未复核其全部原始行；数值事实仅按交接与本地 J 汇总使用。对这些事实所作的必要数学修正已经给出，后续性能外推和论文主张不在此处自动升级。

## 其余 C1 结论的最小必要审查

仅阅读 c1-scalar-closure.md 的 D2、A4、**最新 A5 outcome** 和关联本地汇总；不重跑实验、不复审全部流水线。三点会改变原汇报的适用范围：

1. **短轮数成功不能扩写为全部轮数。** A5 已将旧的 R7–R10 “不确定”更新为：冻结 mean-map 在 R1–R6 通过，R7–R10 点估计按原门槛失败，偏差 \(\ln(\mathrm{pred}/\mathrm{obs})=.152\)–.163；R10 的门槛落在置信区间内，不据此声称强统计拒绝。实测 \(K_{c,R10}=180.1\,[176.2,184.8]\)，旧 mean-map 预测约 210。R10 仍是有限轮数，不能直接称 \(T\to\infty\) 的真实断崖。
2. **同帧初态依赖有证据，两个渐近稳定吸引子尚未证明。** A5 的 genie Gaussian 初态能在两轮内救回原 R10 失败帧的 70.1% / 62.5%（L28/32），这是有价值的配对干预。它支持“同一观测的有限轮结果依赖初态”；低态真正稳定、真实反馈能到达高态、平滑映射满足 fold 的切向及非退化条件，仍是不同命题。尤其单帧地图 A5-2 的 open 类成功率预测失败（49.5% / 28.6%，要求至少 80%），故一个信息标量尚未被验证为完整状态。
3. **\(I^*=.577\) 保留为指定码和接口的独立校准基准。** 当前量是 \(1-\mathrm{logloss}\)，是前篇式 (2) 的“真实信息减校准损失”；不能无条件称 Shannon MI 或任意 LLR 分布通用的码常数。现有 flat 分支多个工况的阈值一致性值得保留；它不补足 joint detector 的动力学或标量闭合证明。

这些是对现存证据的范围修正，不否定已经通过的短轮数预测，也不替用户作研究方向或论文主张的正式变更。
