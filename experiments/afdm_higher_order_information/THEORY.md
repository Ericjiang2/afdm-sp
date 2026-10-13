# Derivation Package：Gaussian 控制模型的四阶有效信息

## Target

证明单位功率独立 QPSK、共同已知整数 delay、正噪声的双 Gaussian 路径模型中，匹配二阶矩的单 Gaussian 近似丢失了一部分在碰撞点仍存在的平方半间距信息。目标是模型内的恒等式和局部命题，不是生产接收性能或新颖性结论。

## Status

**COHERENT AS STATED**。以下证明是解析结论；注册数值证据只核对实现，不替代证明。真实 G0 归一化先验不在此定理中。

## Invariant Object

有限输入边缘观测族 `p(r;q,eta)` 及其 q 方向在 nuisance 切空间正交补中的 Fisher 信息。固定 `eta=(mu,tau,sigma2)`；`q=delta²>=0`，delta 是两 Doppler 的**半间距**，tau 是两增益的**总功率**。

## Assumptions

- 固定有限 `N>=3`；`A=Lambda(c2) F Lambda(c1)`，F 为单位化负号 DFT，chirp 为正相位。A 酉且每个元素模长 `N^-1/2`。
- `d_k=(b_Ik+j b_Qk)/sqrt(2)`，两组符号独立且均匀取 ±1；所以 `E d=0, E|d|²=1, E d²=0, E|d|⁴=1`。没有 pilot 或 code 依赖。
- 共同 delay `ell` 已知且为 `[0,N-1]` 内整数。`U_ell` 是冻结核的循环移位和 CPP 单位相位，`v=U_ell A^H d`。
- `h1,h2` 独立 `CN(0,tau/2)`，与输入和噪声独立；`tau>0`。`w~CN(0,sigma2 I)`，`sigma2>0`。参数不以同一观测更新先验。
- `r_n=v_n exp(j mu t_n)[h1 exp(-j delta t_n)+h2 exp(j delta t_n)]+w_n`，`t_n=2pi n/N`。
- `a,b` 是不同的非零索引；因 `t_n>=0`，`t_a²!=t_b²`。

## Notation

令 `g_n=exp(j mu t_n)[h1 exp(-j delta t_n)+h2 exp(j delta t_n)]`；`C_nm=E g_n g_m* = tau exp(j mu(t_n-t_m)) cos(delta(t_n-t_m))`。`T_ab=|r_0|²(|r_a|²-|r_b|²)`。`s_q,s_eta` 是实参数的 log-density 得分；所有内积是 `E_0[XY]`。

## Derivation Strategy

先从有限 QPSK 原始四阶张量得到时间输入交叉功率矩，再消去 proper Gaussian 增益与噪声。利用有限混合正密度的正则性证明得分存在，最后对得分作 Hilbert 空间投影，而不是把一个未投影的 Fisher 元素当作有效信息。

## Derivation Map

1. 独立 QPSK 张量 + 酉等模变换 -> 输入二/四阶矩。
2. 条件 Gaussian Wick -> 精确 `E T_ab(q)`。
3. 正噪声 + 有限混合 + q 解析协方差 -> 单侧 L2 得分、矩导数交换。
4. `E T_ab(0,eta)=0` 对所有 eta -> nuisance 正交。
5. Cauchy–Schwarz -> 正的有效信息下界。
6. `SCALING.md` 在同一族中展开 KL，并明确 R 与 N 的区别。

## Main Derivation

### 1. 输入矩与 CPP 不变性〔恒等式〕

写 `B=U_ell A^H`。U 是每行、每列恰一个模长为 1 元素的矩阵，所以 B 仍酉等模。这一步只允许简化**这里的矩**，不表示任意有限字母似然与 delay/CPP 无关。

独立 proper QPSK 的原始张量为

`E[d_i d_j* d_k d_l*] = 1{i=j}1{k=l} + 1{i=l}1{k=j} - 1{i=j=k=l}`。

于是 `E vv^H=I`，且

`E[|v_n|²|v_m|²] = 1 + |(BB^H)_nm|² - sum_k |B_nk|²|B_mk|²`。

当 `n!=m`，该量为 `1-1/N`；当 `n=m` 为 `2-1/N`。等模性不可省略：B=I 也是酉矩阵，但非对角交叉功率为 1。输入独立性也不可省略：QPSK repetition code 不满足该张量。

由输入与增益独立，`E rr^H=C odot I+sigma2 I=(tau+sigma2)I`，而 `E r=0`。因此精确匹配均值/协方差的单 proper Gaussian 族对 q、mu 恒定。

### 2. 观测四阶矩〔恒等式〕

给定 v，r 是 proper Gaussian，协方差

`K_v(n,m)=v_n v_m* C_nm+sigma2 1{n=m}`。

对不同 n,m，Wick 恒等式给出

`E[|r_n|²|r_m|² | v] = K_v(n,n)K_v(m,m)+|K_v(n,m)|²`。

消去 v 后，均匀 QPSK 条件下

`E[|r_n|²|r_m|²] = tau²(1-1/N)[1+cos²(delta(t_n-t_m))]+2 tau sigma2+sigma2²`。

两个非对角项相减，常数、噪声及 tau 的一次项均抵消：

`E T_ab = (1-1/N)tau²[cos²(delta t_a)-cos²(delta t_b)]`。

利用 `cos²(sqrt(q)t)=1-q t²+q² t⁴/3+O(q³)`，得到

`E T_ab = kappa_ab q+O(q²)`，`kappa_ab=(1-1/N)tau²(t_b²-t_a²)!=0`。

### 3. q=0 的单侧 L2 得分〔局部命题及证明〕

枚举有限支持 d，概率 `pi_d=4^-N>0`，其分量协方差为

`K_d(q,eta)=sigma2 I+tau diag(v exp(j mu t)) Cq diag(v exp(j mu t))^H`，

其中 `Cq(n,m)=sum_{k>=0} (-q)^k(t_n-t_m)^(2k)/(2k)!`。

这是 q 的实解析函数，q>=0 时等于 `cos(sqrt(q)(t_n-t_m))`。在 q=0，所有 K_d 至少有 sigma2 的特征值下界。由于 d 有限，存在包含 `(0,eta0)` 的共同开邻域，使所有解析延拓 K_d 仍严格正定、最大最小特征值统一有界，且任意固定阶导数统一有界。**负 q 延拓只是局部证明工具，不是物理双径分布。**

分量密度为 `phi_d=exp(-r^H K_d^-1 r)/(pi^N det K_d)`，分量得分为

`s_j(d,r)=r^H K_d^-1 K_{d,j} K_d^-1 r-tr(K_d^-1 K_{d,j})`。

边缘得分 `s_j(r)=sum_d P(d|r) s_j(d,r)`，所以在上述邻域有统一界 `|s_j(r)|<=C(1+||r||²)`；log-density 的二阶、三阶导数也被有限阶多项式支配。

更强地，密度比在 `L2(p_0)` 中可微：对每个 d，`p_0>=pi_d phi_{d,0}`。邻域再缩小，使 `2 K_d(theta)^-1-K_d(0)^-1` 一致正定。于是

`int |partial^j phi_d(theta)|²/p_0 dr <= pi_d^-1 int |partial^j phi_d(theta)|²/phi_d(0) dr < infinity`

并有统一 Gaussian-多项式可积上界，j=0,1,2 均成立。有限求和和 Taylor 积分余项给出

`||p_q/p_0-1-q s_q||_{L2(p_0)}=O(q²)`。

因此物理半轴 `q downarrow 0` 上得分存在、平方可积，`E_0 s_j=0`；该族也可在此证明邻域中按通常平方根密度意义作二次均方可微处理。以上论证使用正噪声；不能直接移植到 sigma2=0 的奇异支持。

T 是次数 4 的实多项式，有限 Gaussian 混合拥有全部多项式矩，故 `E_0 T²<infinity`。上面的多项式与 Gaussian 支配也允许交换 `partial_j E T = E[T s_j]`。

### 4. 有效信息，而非原始信息〔局部命题及证明〕

在 q=0，`E T_ab(0,eta)=0` 对邻域内所有 `(mu,tau,sigma2)` 成立，所以

`E_0[T_ab s_mu]=E_0[T_ab s_tau]=E_0[T_ab s_sigma2]=0`，

同时 `E_0[T_ab s_q]=kappa_ab`。

记 nuisance 切空间为三个得分的线性张成空间 H；即使它降秩，H 仍是有限维闭空间。令 `s_eff=s_q-Proj_H(s_q)`。用 `I_etaeta` 的 Moore–Penrose 广义逆进行投影合法：其零方向是 L2 零得分，所以与 s_q 的交叉内积亦为零。

`I_eff=E s_eff²=I_qq-I_qeta I_etaeta^+ I_etaq`，且

`kappa_ab²=(E T_ab s_eff)² <= Var_0(T_ab) I_eff`。

正噪声使 p_0 对所有 `r in C^N` 严格正，而 T_ab 是非恒定实多项式；例如固定 `r_0=1` 后改变 r_a、r_b 会改变 T。其在两个开集内取不同值，两个开集均有正概率，故 `Var_0(T_ab)>0`。因此

**`I_eff_qq(0+) >= kappa_ab² / Var_0(T_ab) > 0`。**

完整族原始 `I_qq` 一般大于有效信息，数值结果分别保存。单 Gaussian 近似的 q 得分为零，因此它的原始和有效 q 信息均为零；两者比较使用相同输入、Gaussian 增益和观测空间。

### 5. T 的精确方差与多 lag〔恒等式〕

给定 d，任意 k<=4 及允许重复的索引 `i_1,...,i_k` 有

`E product_j |r_i_j|² = permanent(K_d[i_u,i_v]_(u,v))`。

故 `E T_ab²` 是索引 `[0,0,a,a]`、`[0,0,b,b]`、`[0,0,a,b]` 三个永久式按 `1,1,-2` 的有限输入平均。这是精确 eighth-order 消元，不是采样方差。不同 T 的协方差同理。

若 `F=(T_a1b1,...,T_aJbJ)`、协方差为 Sigma、导数为 k，则 `I_eff>=k^T Sigma^+ k`。必须保留完整 Sigma。例：`T_13=T_12+T_23` 恒成立，三个 lag 的 Sigma 只有秩 2，它们不是三个独立重复。

## Remarks and Interpretation

- 碰撞时 q 信息存在而 delta 的一阶得分为 `2delta s_q=0`，这只是坐标和边界结构；没有消除标签对称或全局周期混叠。
- T 对 mu 完全不敏感，只能用于 q 的局部信息证明或辅助统计，不能据此声称能同时估计中心。
- 参数族和有限字母输入必须一致。把已知数据、cavity 或归一化增益偷偷换入会改变命题。
- 注册网格在 `results/afdm_higher_order_information/THEORY_CONFIG.json`。`theory_study.py --mode moments|information|inputs --stage <new_name>` 负责不可覆盖尝试；正式数值结果尚须由实际 attempt 终态判定。

## Boundaries and Non-Claims

不证明真实生产归一化先验的正信息、不证明有限 N 下全局唯一可辨识、不证明估计器达到 Fisher 下界、不把 N 个采样点当作 N 个独立信道，也不宣称数学工具本身新颖。sigma2=0、tau=0、N<3、a=b、未知非共同 delay、相关或非均匀输入均不适用该简式。

## Open Risks

数值 Fisher/KL 积分只有注册 Monte Carlo 精度，需保留批次标准误；相邻小 q 的加密不能代替独立观测数量。实际先验的核、裁剪支持和归一化导数由 PRIOR 文档另行裁决，不能依据本控制定理推断。
