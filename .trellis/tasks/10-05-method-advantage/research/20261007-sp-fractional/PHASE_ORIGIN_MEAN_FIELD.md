# 相位参考时刻与增益–Doppler mean-field 的坐标依赖

2026-10-07，GAUGE-MF-01。解析研究；无新仿真、接收调用或参数搜索。

## Target / Status

目标是检验：同一个 SP-AFDM 物理信道，换一个完全等价的相位参考时刻后，
当前增益与 Doppler 独立的变分族是否仍等价。随后区分可证明的族差异、
局部 Gaussian 不确定性差异与尚未建立的真实接收收益。

状态：COHERENT AS STATED，待独立数学审查。这是经典重参数化思想的项目适配候选，
不主张首创，也没有证明它解释了本轮接收结果。

## Invariant object / Assumptions / Notation

不变量是原始物理条件似然及其正确推前先验后的 evidence。
令 A 为原 DAFT，L_i=C_iΠ_i A* 含真实 CPP 和循环 delay，t_n=2πn/N。
保留未知 AF 域有限字母数据 d，原时域观测为

    Y = Σ_i h_i diag(exp(i t_n ν_i)) L_i(p+d) + W.

W~CN(0,σ²I)，σ²>0；ν_i 在原有界支持，delay 固定。
工作先验取独立 circular CN(0,τ_i)，τ_i>0，并独立于 ν、d；Doppler工作先验为∏π_i(ν_i)。
这不等于真实 G0 归一化生成先验。q(d)=∏q_k(d_k)，q(h)为允许完整 covariance 的复Gaussian，
当前族仍强制 q(h)∏q_i(ν_i)。c_i 是固定实数参考相位频率系数，不是新物理参数。

## Derivation strategy / map

1. 精确改变增益坐标，保持每个 realization 的原物理观测。
2. 对比任意分布的 KL 不变性与受限 product family 的非不变性。
3. 在明确的单路径已知激励分析切片，计算 nuisance-projected Fisher。
4. 对该局部 Gaussian 模型精确求 reverse-KL mean-field 方差。
5. 回到未知 SP 数据和多径，列出可保留结构与不能推广的部分。

## Main derivation

### 1. 精确物理重参数化（identity）

设 g_i=h_i exp(i c_iν_i)，并令

    U_i^c(ν_i)=A diag(exp(i(t_n−c_i)ν_i)) C_iΠ_i A*.

则逐路径 g_i U_i^c(ν_i)=h_i U_i(ν_i)。没有改变采样、CPP、数据、噪声、
时延、Doppler 或真实增益的物理作用；只是换坐标。
变换 (h,ν)↔(g,ν) 的实 Jacobian 是 block triangular，每个复增益块是
二维旋转、行列式1，所以联合 Lebesgue Jacobian 为1。

独立 circular zero-mean Gaussian 工作先验满足 |g_i|=|h_i|，故在该坐标中仍为
∏CN(g_i;0,τ_i)∏π_i(ν_i)。若另选逐路径旋转不变且与ν独立的联合gain prior，
变换也保持该联合prior及其与ν独立；这不推出gain各路径之间的乘积分解。
**一般非零先验均值或非对角 gain prior covariance 不满足此简式**：必须推前原先验，
不能旋转后仍硬用旧先验。真实 G0 归一化先验是否逐路径旋转不变尚未证明，
本推导不作这种假定，更不重新归一化 G1 gains。

### 2. 独立性假设没有随坐标变换保持（proposition）

任意可积密度 q 经上述双射推前，KL(q||posterior) 与 ELBO 都保持不变。
这是换元公式，不代表重新拟合一个同形式 product family 也保持不变。

取单路径 q(h,ν)=CN(h;m,v)qν(ν)，v>0、m≠0，qν在一段非零长度区间具有密度。
变换后的条件分布为

    g | ν ~ CN(exp(i cν)m, v).

若 c≠0，条件均值在正质量集合上并非常数，因此 g 与 ν 不独立。
这个原族中的分布不属于 q(g)qν；逆变换给出反方向反例。故两个受限族一般不同，
并不存在自动的包含关系。这个结论只证明“可能不同”，并不证明任意数据下两族最优解不同。

在原 h 坐标解释新族 q(g)∏q_i(ν_i)，当q(g)=CN(m_g,C_g)时，有

    h | ν ~ CN(D_c(ν)* m_g, D_c(ν)* C_g D_c(ν)),
    D_c(ν)=diag(exp(i c_iν_i)).

所以相位居中的 product approximation 相当于原坐标中一种有明确结构的
gain–Doppler 相关族。原 q(h) 即使有完整 gain covariance，也没有包含这种条件旋转。
特例 m=0、isotropic/逐路径圆对称 gain 分布可以保持独立；不能把非不变性说成无条件成立。

### 3. 单路径已知激励的局部信息（proposition，分析切片）

现在仅考虑 Y_n=r exp(iθ_c) exp(i(t_n−c)ν)s_n+W_n，r>0，s固定已知。
这里 θ_c=arg(g)，不是额外给接收机提供真实数据。
令 w_n=|s_n|²，E=Σw_n>0，a=Σw_nt_n/E，v_t=Σw_n(t_n−a)²/E>0。
对 real 参数 (θ_c,ν)，proper complex Gaussian 的 Fisher 为

    J_c = k [[1, a−c], [a−c, v_t+(a−c)²]],
    k = 2r²E/σ².

推导：两列导数分别为 iμ_n 和 i(t_n−c)μ_n，Fisher内积为
2 Re(∂μ*∂μ)/σ²。r 导数与这两列在实 Fisher 内积下正交，所以把幅度也作为
unknown nuisance 不改变下式。消去 unknown phase 的 Schur complement 为

    J_eff,ν = k v_t,

与 c 完全无关。c=a 只让局部 phase–frequency 两列正交，没有创造额外信息。
v_t=0（激励仅作用于同一时刻）时信息为零，不能套用逆矩阵。

### 4. 对局部 Gaussian 的精确 mean-field 结果（proposition within surrogate）

考虑 real Gaussian 目标 p_G(z)=N(m,J_c^−1)。最小化 KL(qθ qν || p_G) 的
坐标最优解为 Gaussian，均值为 m，方差分别为 1/(J_c)11 和 1/(J_c)22。
证明：固定另一个因子时，E log p_G 对当前变量是曲率为对应 diagonal precision
的严格凹二次式；均值固定点解 J_c(m_q−m)=0，J_c≻0，所以唯一为 m。

真实 Gaussian 边缘与 mean-field 边缘分别是

    Var_G(ν)=1/(k v_t),
    Var_MF,c(ν)=1/[k(v_t+(a−c)²)],
    Var_MF,c / Var_G = v_t/[v_t+(a−c)²].

因此同一个局部统计实验，在未推前 variational family 时，其 mean-field 方差
可以随任意参考 c 而显著变化；c=a 在这个二维 Gaussian 切片精确消除了损失。
等权 N≥2、c=0 时

    Var_MF,0 / Var_G = (N+1)/(2(2N−1)) → 1/4.

这个比例来自有限求和恒等式，不是本轮 receiver 的测量值。
对固定的该 Gaussian 目标，c离a越远可让比例趋近0；不能把这一 surrogate 结论
当成对任意有限SNR的非线性、多峰或有界真实 posterior 的统一结论。
当前 CN(h)×qν 在高信息量、非零gain、局部单模态下可与此局部块近似联系；
其严格渐近条件尚未在 SP 多径生成器上建立。

### 5. AFDM+SP 的可计算结构与边界（identity / interpretation）

固定 q(d)，e_i,n=E_q |(L_i(p+d))_n|²=|L_i(p+E d)|_n²+(L_i diag(v_d)L_i*)nn。
这能由当前 source statistics 计算。在E_i=Σe_i,n>0时，以 e_i 为权重的 c_i=Σt_ne_i,n/E_i
可让**单路径 expected complete-data Fisher 的自身 phase–Doppler 交叉项**为零。
E_i=0时该路径没有自身激励信息，中心不定义，不能除以零。
它不是未知数据边缘似然的有效 Fisher；多径的跨路径列与 data–channel 相关性仍在。
改变 q(d) 后更新 c_i 还会改变受限族；不能在既有 ELBO 单调性证明中悄悄换坐标并
丢掉旧相关性。初次方法研究应先冻结 c_i，而非动态重居中。

在新族下定义 ψ_i[n]=E exp(i(t_n−c_i)ν_i)，m=E g，S=Cov(g)+mm*。
则平均通道和 E H*H 仍采用原有路径矩结构，只需用 ψ 替换 φ、用 g 的二阶矩替换 h 的：

    E H = Σ_i m_i A diag(ψ_i) C_iΠ_i A*,
    E H*H = Σ_i S_ii I + Σ_(i≠j) S_ji (E U_i^c)* E U_j^c.

同路径能量仍精确保留。Doppler坐标指数依旧是有限指数和，但频率为 t_n−c_i，
必须修改该坐标的相位评估与导数，不能只在输出gain上乘一个常数。
一般 qν 下也不能把 ψ_i 写成 exp(−ic_i Eν_i)φ_i；期望内的相关旋转不可外提。

固定公共 c=(t_0+t_(N−1))/2 时，max_n|t_n−c|是原值的一半。
因此既有特征函数 Taylor 余项中的频率上界可以收紧；但新的 density 和 posterior
也变了，不能凭此推断实际节点数、完整运行时间或 BER 必然改善。

## Prior art and claim scope

2026-10-07定点检索已发现两个直接的经典来源：

- Linda S. L. Tan, *Use of Model Reparametrization to Improve Variational Bayes*,
  JRSS B 83(1), 30–57 (2021), DOI 10.1111/rssb.12399。
  [出版社全文](https://academic.oup.com/jrsssb/article/83/1/30/7050743)第1节明确讨论
  posterior dependency、受限族与重参数化，不能把这个一般思路声明为新方法。
- *Carrier phase and frequency estimation for pilot-symbol assisted transmission:
  bounds and algorithms*, IEEE记录1542484（2005），
  [IEEE记录](https://ieeexplore.ieee.org/abstract/document/1542484)。检索摘要明确给出
  burst中心参考相位与phase/frequency解耦；正文open失败，因此仅引用可核查摘要范围。
  独立的[Adelaide大学研究记录](https://digital.library.adelaide.edu.au/items/af7f125c-e176-4e67-996d-5d52a2c4403b)
  *Carrier-phase and frequency-estimation bounds for transmissions with embedded reference symbols*
  同样报告居中解耦，不把两篇误并为同一论文。

另检索 VALSE centered steering、AFDM variational phase centered、OFDM variational
reparameterization，未取得足够直接的特定AFDM现有实现证据；这不是新颖性证明。
当前允许的描述是：用已知重参数化原理检验本项目mean-field近似的坐标依赖，
并探索带真实CPP与未知SP数据的低成本结构相关族。

## Remarks / boundaries / open risks

- 已完成的 adaptive 接收比较只说明当前固定算法/同一4blocks中积分精确化未带来
  aggregate误码增益；没有证明坐标依赖是其原因。
- 时间参考改变不是实际波形设计，也不提高物理 Fisher；其潜在收益来自近似族和优化路径。
- 不保证centering使所有多径相关性消失，不保证连续后验校准，不保证更低BER。
- 当前 point 算法若找到同一个精确全局profile解，其物理解应不变；实际有限坐标更新
  路径可能改变，需把族变化与优化路径变化分开验证。
- 最小可证伪下一步先核原/新坐标的逐realization物理等价与prior、同一个联合q的
  KL不变性，再核Gaussian比例及现有矩算子的推广。新receiver仍需单独协议与字节准入。
- 不修改生产先验、实际G0-normalized gains、旧失败、STATE或论文主张。
