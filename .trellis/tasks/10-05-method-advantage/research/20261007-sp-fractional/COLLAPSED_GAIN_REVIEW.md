# COLLAPSED-GAIN-01 独立数学审查

2026-10-07。**PASS：Gaussian消元、条件下界、相位坐标不变性、Schur目标、恢复式、
导数及整块数据更新的单调性均成立。** 作者已补充完整协方差恢复成本，并将恢复
对象精确表述为最优Gaussian gain因子q_h*；本代理定点复核完成。
无未闭合FATAL/CRITICAL问题；没有新receiver、性能或新颖性结论。

被审文件：`COLLAPSED_GAIN_OBJECTIVE.md`。
最终输入SHA256：`02c5cd41436388b77c0e48b421a806f09fe3d4dd41c9b85ce1b0e9f4146ab18f`。
该版本仅增补源码复用说明；数学审查沿用前版，新增说明已作下述窄源码核对。

- review_actual_model: `unavailable_from_current_tool_metadata`
- review_actual_reasoning: `unavailable_from_current_tool_metadata`
- validation_limited: `model parity unknown`

本代理独立做解析核对并定点读取机构文献摘要。精确model/effort不在当前可见工具
元数据中，不使用skill默认型号代替。复用此前加载的数学审查方法，不重读生命周期；
仅为文末增补核对必要源码，不运行新科学数值、求积、接收机、SSH或提交；只写本报告。

## 假设与证明义务

| 义务 | 已核对的关键条件 |
|---|---|
| 条件ELBO与解析消元 | ν是确定参数；q_d与q_h独立；proper CN先验C0≻0；σ²>0 |
| 数据支持 | 有限字母；q_d不在p(d)=0处放质量；0log0约定不允许正质量乘log0 |
| 相位不变 | 固定实c_i；g=Dh、B^c=B D*；diagonal零均值工作先验正确保留 |
| Schur化简 | 固定q_d及ν_−i；U_i酉；prior diagonal；A为正定主子块 |
| 导数 | 对实ν_i求导；A、b_−、d_i固定，只有u、b_i变化 |
| 复杂度 | source缓存已建立且未失效；每坐标重建/分解A另计；完整C恢复另计 |
| 数据块单调性 | 块开始gain因子最优；3步固定同一gain因子；增加的是同一F |

证明链为：ELBO→Gaussian最优因子→消元目标→Schur分解/导数，数据块单调性
只使用最大化定义和既有固定gain的目标增益。没有借用后续收益来证明前面的恒等式。
有限字母期望是有限求和，ν导数涉及有限指数和；Λ≻0保证逆矩阵、logdet与最优
Gaussian参数光滑。因此本范围内没有未说明的积分/微分交换或奇异求逆。

## 1. 完整Gaussian积分与下界常数

展开期望残差可得

    E_qd ||y−B_d h||² = ||y||²−2Re(h*f)+h*Rh.

proper复Gaussian prior的密度常数为−P logπ−logdet C0。连同似然，h相关项为
−h*Λh+2Re(h*b)，其完成平方形式为

    −(h−m)*Λ(h−m)+b*Λ^{-1}b,  m=Λ^{-1}b.

在C^P对应的2P维实Lebesgue测度上，积分为
π^P detΛ^{-1} exp(b*Λ^{-1}b)。π^P正好抵消prior中的π^{-P}，所以原文

    H(q_d)+E log p(d)−N log(πσ²)−||y||²/σ²
    −logdet C0−logdetΛ+b*Λ^{-1}b

无遗漏的P、π或½因子。最优q_h*=CN(m,Λ^{-1})也是在所有合适密度q_h中的
最优解：目标等于该log积分减去KL(q_h||CN(m,C))，非负KL给出唯一最优分布。
这不是把gain covariance对角化的结果。

两项解析退化核对也成立：

- R=f=0时Λ=C0^{-1}，两个logdet抵消，q_h*=prior；没有残留gain维度常数。
- q_d退化在一个允许符号向量d0时，令Σ=σ²I+B C0B*。矩阵行列式引理给出
  detΣ=(σ²)^N detC0 detΛ，Woodbury给出
  y*Σ^{-1}y=||y||²/σ²−b*Λ^{-1}b。因此结果等于
  log p(y|d0,ν)+log p(d0)，与标准复Gaussian边缘化一致。

对一般未知随机数据，上述消元最大化的是product q_d q_h的ELBO。
所以F_coll≤log p(y|ν)，不等于先精确求和所有QPSK数据、再求真实条件似然。
同理，恢复的CN(m,C)是最优完整Gaussian gain因子q_h*；真实p(h|y,ν)在未知
离散数据下通常是Gaussian混合，不能把这两个对象等同。
本文ν是point参数，不包含ν的微分熵；不能以连续Dirac的“有限熵ELBO”解释此目标。
若加入非uniform ν prior，坐标目标还必须加相应log prior；本文只额外讨论固定uniform。

## 2. 相位坐标逐点不变性

B_d^c=B_dD*给出R_c=DRD*、f_c=Df。diagonal C0与D交换，故

    Λ_c=DΛD*,  b_c=Db,  C_c=DCD*,  m_c=Dm.

D酉，detΛ_c=detΛ>0，b_c*C_c b_c=b*Cb；其它下界项均不变。
因此每一个确定ν的目标值都相同，不只最优值相同。每candidate正确消元gain可避免
冻结一个未随candidate相应旋转的gain因子，但不免除数值实现的等价性核验。

非对角或非零均值prior须随D推前，不能继续硬用旧固定prior参数；否则在比较不同
统计模型。本文没有将此恒等式推广到未知真实G0归一化law或新的物理增益归一化。

## 3. Schur目标、正下界与恢复公式

将i置于最后，u是Λ的右上列。A≻0且不依赖ν_i；酉性给出
R_ii=E||p+d||²，与ν_i无关。故d_i、b_−也固定。
联立Λm=b得到

    m_−=A^{-1}b_−−A^{-1}u m_i=z−v m_i,
    (d_i−u*A^{-1}u)m_i=b_i−u*A^{-1}b_−=t.

因此m_i=t/s，s=d_i−u*v，t=b_i−u*z；t中的共轭方向正确。
block inverse给出C_ii=1/s、C_−,i=−v/s、C_−,−=A^{-1}+vv*/s，
相反块由Hermitian对称性恢复。所有gain间相关性仍保留。

代入二次型与det分解可得

    b*Λ^{-1}b=b_−*A^{-1}b_−+|t|²/s,
    logdetΛ=logdetA+log s.

故ν_i可变部分恰为J_i=|t|²/s−log s，不能丢掉−log s。
只对h做MAP/profile最大化通常没有这个logdet项，不能将二者视为同一目标。

对任意x∈C^{P−1}，

    [x;1]*Λ[x;1]
      = Σ_(j≠i) τ_j^{-1}|x_j|² + τ_i^{-1}
        + E||B_d[x;1]||²/σ² ≥ τ_i^{-1}.

对x取最小，最小点x=−A^{-1}u，得到s≥τ_i^{-1}>0。
R即使因重复路径而秩亏，正定prior仍保障此界；若撤掉proper prior或放任其精度
退化为0，则不能继续无条件使用此正下界或有限Gaussian积分。

P=1时空A约定正确：s=d_1>0固定，J只与|b_1|²成正比加常数；相位旋转
不会改变其值。冻结非零gain的Re(h*b_1)条件目标与之不同，但这不证明实际迭代
最后必然到达不同的物理解。

## 4. 导数、rank与复杂度

因A^{-1}Hermitian，

    s'=−u'^*A^{-1}u−u*A^{-1}u'=−2Re(u'^*A^{-1}u),
    t'=b_i'−u'^*z,
    J'=2Re(conj(t)t')/s−(|t|²/s²+1/s)s'.

整体微分利用dC=−C(dΛ)C与d logdetΛ=tr(C dΛ)，得到

    dF_coll=2Re((db)*m)−tr((C+mm*)dΛ).

右侧在Hermitian方向dΛ上为实数；没有遗漏C对ν的导数或重复计算其影响。
最优gain因子唯一且光滑，所以envelope解释成立：当前最优gain处，冻结gain与
collapsed目标一阶导数相同；candidate离开当前点后的曲率/目标可不同。

变化仅在R的第i行/列且对角差为0，令a_j=ΔR_ji、a_i=0，则
ΔR=e_i a*+a e_i*，rank≤2。这里e_i是标准基向量，与source能量无关；
该结构不要求用不稳定的反复rank更新来实现。

候选求和的共轭可独立核对如下。令原DAFT为𝒜、ỹ=𝒜*y、s_i=E[L_i(p+d)]，
K_ij[n]=E[(L_i x)_n conjugate((L_j x)_n)]。在原相位坐标中，j≠i时

    u_j=(1/σ²)Σ_n exp(i t_n(ν_i−ν_j)) K_ij[n],
    b_i=(1/σ²)Σ_n exp(−i t_nν_i) conjugate(s_i[n]) ỹ_n.

分别乘i t_n和−i t_n给出相应ν_i导数。这些有限求和为O(PN)，不能把
K_ij替换成均值外积而丢掉非均匀软数据variance的贡献。

对原DAFT/CPP/整数循环delay结构，公共逆DAFT和variance Fourier量可复用，
再构建各路径对source统计；O(N log N+P²N)预处理与O(P²N)存储范围合理。
这不是任意unitary U_i都自动具有的复杂度，而是当前明确的结构化AFDM算子假设。
q_d变化后该缓存须失效；初始R/f构建也须计费。

- 每个坐标的A分解O(P³)，z求解等一次性工作另计；不能在ν_−i变化后继续把A当常量。
- 每candidate构建u/b_i及导数O(PN)，通过Cholesky解A v=u为O(P²)
  （通常包含两次三角求解），因此评分O(PN+P²)成立。
- **完整C恢复不免费。** 从Cholesky构建A^{-1}需identity多右端求解O(P³)，
  可每坐标一次缓存，此后vv*/s为O(P²)；也可只在选定点/数据块前构造完整C并单列费用。
  作者已加入这一成本，未把完整C构建混入“单次O(P²)求解”。
- 按逐坐标重新分解的直接实现，一个P坐标sweep的分解总阶数是O(P⁴)，另加
  所有候选的Σ_i M_i·O(PN+P²)与source/data/F1/检查/保存。若P固定小，可作为常数
  处理，但不能据单candidate阶数声称整机更快。

## 5. 数据块单调性的精确含义

假设块开始时q_h*确为当前q_d的解析最优因子；随后ν与该q_h*固定，三个数据步
提高同一F。则最大化定义逐项给出

    F_coll(q_d';ν) ≥ F(q_d',q_h*;ν)
                    ≥ F(q_d,q_h*;ν)=F_coll(q_d;ν).

逻辑与不等号方向正确。块结束重优化gain实现左端最优值；不须对角化covariance。
每个中间数据点的collapsed值至少可用固定q_h*值下界，但这个下界本身不能保证
两个相邻中间点的collapsed最优值按顺序不降。作者已明确只对完整数据块作声明。

纯逻辑反例可说明不能加强该结论：设F(q,h)=V(q)−(h−a(q))²，在三个数据状态
令(a,V)分别为(0,0)、(2,5)、(1,3)。固定h=0时F依次为0、1、2，上升；
但max_h F依次为0、5、3，中间collapsed值会下降。这里只是解析反例，未执行数值试验。

该命题要求实际旧MM步骤提高包含当前数据prior的同一F。它不自动授权把适用于
原uniform QPSK prior的更新公式套到任意新的p(d)。原independent objective、
equation (8)、回溯与显式失败仍须保留。ν_i在固定q_d下接受不降J_i的候选，也
不降同一F_coll；非uniform ν prior则还需包括其变化项。
这些结论不保证全局收敛到最优解、BER收益或连续Doppler posterior校准。

## 文献与结论边界

本轮独立定点核对Aalborg作者机构记录，确认Lu、Navarro Manchón、Wang，
IEEE Access 7:16665–16674（2019），DOI 10.1109/ACCESS.2019.2896125。
摘要明确为massive MIMO-OFDM的DP结构稀疏模型和collapsed VBI，足以支持
“collapsed VB在OFDM信道估计已有使用”。本轮未读其全文，不能据此把具体消去
变量、Gaussian gain目标或复杂度机制判为与本笔记相同。
[Aalborg机构记录与摘要](https://vbn.aau.dk/en/publications/collapsed-vbi-dp-based-structured-sparse-channel-estimation-algor/)。

本候选允许称为固定软数据下完整Gaussian gain因子的解析消元与精确Schur坐标目标。
Gaussian积分、Schur补、variable projection、envelope导数是经典工具；它们的成立
不构成新颖性、全局优化或性能背书。当前目标仍优化point ν，不能同时宣称保留了
完整连续Doppler后验。旧adaptive开发筛选失败和原物理样本均不被本推导改写。

没有发现需要改变核心公式的错误。修订闭合后数学PASS；未来实现仍需自己的
协议、成本记录与receiver证据。本轮Lint/TypeCheck/运行测试不适用，无新科学数值。

## 源码复用说明增补窄核

仅针对作者新加的implementation connection段，结论PASS；未重审前文数学，
没有运行被读模块或新增计算。

- `receiver.py::gain_update`已使用precision=`P I+Gram/σ²`，一次Cholesky，
  将identity和matched/σ²拼成多右端，再经两次三角求解同时取得完整C和m。
  full covariance及CN(0,I/P)工作prior已存在，不是新候选贡献。
- `moments.py::prepare_source/_cross_source/gain_statistics`保留owner身份检查，
  使用mean response、variance FFT及完整跨路径项构建R/f。不能复制一份只带mean
  response的Gram，并宣称与canonical统计等价。
- `afdm_structured_inference_20261003/collapsed.py::CollapsedModel.evaluate(y,x)`
  的确已有确定x下Gaussian gain消元、logdet及完整gain矩。其Gram来自确定regressors，
  没有软数据variance参数；直接用x=p+E[d]代入会漏E[B_d*B_d]中的variance贡献。
- `physical.py::fit`和`keep_slots.py::time_refine_keep_slots`的candidate内都已重新
  解gain；工作矩阵为`B*B+Gamma+noise I`，评分为`||y||²−b*h`，没有logdet。
  该ridge项对应CN(0,I)，与当前P条路径的CN(0,I/P)精度不同，不能把已有refit
  自动等同本笔记下界。它们也已经包含非均匀软variance投影，不能把这项冒称新增。
- `physical.fit`以`np.unique(delays)`压缩同delay路径，并选该delay中的一个中心；
  keep-slots接口保留传入的有序物理槽位。因此前者不能直接替换当前保槽路径。

新段对现有能力与缺失部分的划分准确：应复用gain solver、canonical source统计
及现有receiver/harness，只增加尚缺的collapsed坐标目标和相应接线。此处的复用
依据是源码读取，不是运行验证或实现已经完成的声明。
