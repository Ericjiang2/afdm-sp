# 固定软数据下解析消去完整增益因子

2026-10-07，COLLAPSED-GAIN-01。formula-derivation；数学和源码对应，0新仿真。

## Target / status / invariant object

目标：在保留full gain covariance的前提下，得到不依赖相位参考时刻的Doppler
坐标目标，避免为一个candidate冻结不合适的gain phase；核对完整运算成本与旧MM数据步的兼容性。
状态：COHERENT AS STATED，待独立审查。Gaussian积分、Schur complement和variable
projection均是经典方法，不是首创；实际收益尚未验证。

不变量是固定参数ν下对log p(y|ν)的同一变分下界。这里ν是待优化的确定参数，
**不把Dirac ν的微分熵当成有限，也不声称构造了完整连续ν posterior的ELBO。**

## Assumptions / notation

原模型y=Σ_i h_i U_i(ν_i)(p+d)+w，U_i含真实DAFT/CPP/整数delay，均为unitary。
σ²>0，工作prior h~CN(0,C0)，C0=diag(τ_i)≻0，与有限字母数据prior p(d)独立。
固定q_d=∏q_k，数据仍未知；任何概率为0的项按0log0=0计算，要求q_d不在p(d)=0处赋质量。
生成器、真实G0-normalized gains及G1物理样本不改变。

给定d、ν，B_d是N×P矩阵，第i列为U_i(ν_i)(p+d)。定义

    R(ν)=E_qd B_d* B_d,     f(ν)=E_qd B_d* y,
    Λ(ν)=C0^−1+R(ν)/σ²,    b(ν)=f(ν)/σ²,
    C(ν)=Λ^−1,             m(ν)=Λ^−1b.

R是Hermitian PSD，Λ≻0。R包含非均匀AF data variance产生的交叉项，不能用
E B* E B替代。当前moments.py::gain_statistics和gain_update已计算同种R/f/full C。

## Derivation map

Jensen/ELBO → 完整Gaussian积分 → 相位坐标不变性 → 单坐标Schur目标 →
导数与成本 → 整个数据块的单调性 → 与现有方法及未验证收益的边界。

## 1. 条件下界与消元（identity / proposition）

对任意q_h，条件ELBO为

    F(q_d,q_h;ν)=E log p(y,d,h|ν)+H(q_d)+H(q_h) ≤ log p(y|ν).

固定q_d时，与h有关的指数为−h*Λh+2Re(h*b)。完成平方，最优q_h恰为
CN(m,C)，无需把full covariance改成diagonal。积分∫exp(−h*Λh+2Re h*b)dh
=π^P det(Λ)^−1 exp(b*Λ^−1b)，因此

    F_coll(q_d;ν)
      = H(q_d)+E_qd log p(d) − N log(πσ²) − ||y||²/σ²
        − logdet(C0) − logdet(Λ) + b*Λ^−1b.

这是对q_h的精确解析最大化，仍只是log p(y|ν)的下界，因为q_d与h的独立限制仍在。
并不等于“先对真实QPSK数据精确边缘化后得到的似然”。ν若配固定uniform prior，
可额外加其常数log density作MAP式优化；没有ν entropy或ν方差声明。

## 2. 相位参考坐标不变（identity）

令D(ν)=diag(exp(ic_iν_i))，g=Dh，B_d^c=B_dD*。
则R_c=DRD*、f_c=Df。由于diagonal C0与D可交换，Λ_c=DΛD*、b_c=Db，
从而logdetΛ_c=logdetΛ，b_c*Λ_c^−1b_c=b*Λ^−1b。
F_coll对任意固定c_i逐点相同。这是整个目标相同，不只是正确global optimum相同。
非对角/非圆对称prior必须正确推前，不能仍沿用固定C0。

若在每个candidate上重新计算m,C，原h坐标或居中g坐标应给出同一个F_coll值。
有限精度、不同一维求解器/停止规则可能影响数值轨迹，不能仅凭恒等式宣布实现等价。

## 3. 单坐标的精确Schur化简（identity）

固定q_d及ν_{−i}，把i坐标排列到最后，写

    Λ = [[A,u],[u*,d_i]],       b=[b_−; b_i],
    v=A^−1u,                  z=A^−1b_−,
    s=d_i−u*v,                t=b_i−u*z.

这里A与b_−不随ν_i变。所有U_i均unitary，所以
R_ii=E_qd||p+d||²，d_i=τ_i^−1+R_ii/σ²也不随ν_i变；只有u与b_i变化。
block inverse和det恒等式给出

    b*Λ^−1b = b_−*A^−1b_− + |t|²/s,
    logdetΛ = logdetA + log s.

因此该坐标只需优化

    J_i(ν_i)=|t(ν_i)|²/s(ν_i) − log s(ν_i).

必须保留−log s；仅用残差能量或|t|²/s会改变原始下界。
Λ=C0^−1+PSD还给出**s≥τ_i^−1>0**：Schur补等于固定最后分量为1时
min_x [x;1]*Λ[x;1]，该二次型至少为τ_i^−1。
浮点实现若严重违反此界必须报错，不得靠clip/jitter伪造成功。

若P=1，采用空A的自然约定，s=d_1常数，J_1等价于|b_1(ν)|²。
相位参考变化仅旋转b_1，故目标立即不变。原冻结非零gain的条件更新依赖
Re(h*b_1)，二者的候选轨迹不同；这不是声称原算法收敛后一定找到不同物理解。

获得候选后最优完整Gaussian gain因子q_h*可恢复为

    m_i=t/s,       m_−=z−v(t/s),
    C_ii=1/s,      C_−,i=−v/s,
    C_−,−=A^−1+vv*/s.

不丢弃gain之间的相关性。A用Cholesky求解即可，无须显式大矩阵求逆或不稳定的连续rank更新。
若实际恢复完整C，计算上式中的A^−1需要对identity的多右端求解，成本O(P³)，
可每坐标缓存一次；再构造vv*/s为O(P²)。也可只在选定点/数据块前构造full C，
但这项O(P³)仍须单独计费，不能把一次vector solve当成免费取得full covariance。

## 4. 导数、rank与真实成本（identity / complexity）

对实数ν_i求导，A、b_−、d_i固定：

    s' = −2Re(u'* A^−1u),
    t' = b_i'−u'*z,
    J_i' = 2Re(conj(t)t')/s − (|t|²/s²+1/s)s'.

等价的整体导数为

    ∂F_coll = 2Re((∂b)*m) − tr((C+mm*)∂Λ).

这也给出envelope theorem检查：在gain因子已经最优的当前点，冻结gain的
一阶导数与collapsed目标相同。区别在离开当前点后允许gain跟随candidate调整的
曲率/目标，不是凭空添加一阶信息。

改变ν_i只改R第i行/列，且diagonal不变，故ΔR=e_i a*+a e_i*（a_i=0），rank≤2。
这是精确结构；实际可选稳定的Schur计算而无需实现rank-update技巧。

固定q_d后，复用当前精确CPP source统计：s_i=L_i(p+E d)、
K_ij[n]=E[(L_ix)_n conjugate((L_jx)_n)]。这些预处理成本仍为
O(N log N+P²N)，存储O(P²N)，并按data改变失效。
每个候选ν_i只需构造一列与其余P−1列的交叉和、一个matched项，O(PN)；
A的factorization每个坐标一次O(P³)，每candidate一次triangular求解O(P²)，
所以candidate成本O(PN+P²)。导数增加同阶加权Fourier求和。
完整sweep仍有P个坐标，candidate个数、失败、data block、F1、保存都另计。
该尺度没有证明比现有point/scalar完整运行快。

## 5. 和原data-step证明的连接（proposition）

假设某数据块开始时q_h*=argmax_qh F(q_d,q_h;ν)，ν固定。
旧KL-MM数据更新在这个**固定q_h***下，经过全部3步使
F(q_d',q_h*;ν)≥F(q_d,q_h*;ν)。之后重新优化gain，则

    F_coll(q_d';ν) ≥ F(q_d',q_h*;ν)
                    ≥ F(q_d,q_h*;ν) = F_coll(q_d;ν).

故整个data block的collapsed下界不下降；无须将full covariance对角化。
这里不是说不重优化gain时，每个中间data step都相对其前一步的collapsed最优值单调。
若要逐step作该声明，就须各step重新优化gain或另证条件。
ν_i步在同一q_d下接受不降低J_i的candidate，也不降低F_coll。
两个块交替仅证明单调性，不保证全局最优、BER改善或校准posterior。
实际实现还需保留原independent objective/equation (8)核查与显式失败。

## Prior art / implementation connection / non-claims

2026-10-07检索已找到Lu、Navarro Manchón、Wang (2019)，
*Collapsed VBI-DP Based Structured Sparse Channel Estimation Algorithm for Massive MIMO-OFDM*，
IEEE Access 7:16665–16674，DOI10.1109/ACCESS.2019.2896125。
[Aalborg作者机构记录](https://vbn.aau.dk/en/publications/collapsed-vbi-dp-based-structured-sparse-channel-estimation-algor/)
证明collapsed VB在OFDM信道估计已有使用；其DP结构prior与本笔记消去Gaussian gain的
具体步骤不能仅凭标题等同，需读全文才判断方法重合。
Gaussian积分、Schur补、profile/variable projection和envelope导数本身均经典。

当前源码已有gain_statistics、joint Cholesky、精确source cross moments与F1连续搜索。
应复用这些能力。新增候选是固定软QPSK数据下的完整gain消元及精确单坐标目标，
不能把现有F1 refit、已有data variance cross term或已有full covariance冒称新增。

窄源码复用核对（只读，无数值）：`receiver.py:89`已用同一次Cholesky与多右端求解
取得C,m；`moments.py:116–175`已有owner绑定的source及完整R,f。
`experiments/afdm_structured_inference_20261003/collapsed.py::CollapsedModel`
已有确定x下的Gaussian消元与logdet，但直接传p+E[d]会漏软数据方差项。
`frozen/src/physical.py::fit`和当前实际调用的`keep_slots.py::time_refine_keep_slots`已有逐candidate refit，
但采用ridge profile、不含logdet，且prior尺度为CN(0,I)，不能等同当前CN(0,I/P)下界。
前者还合并相同delay，不能替代保槽接口。实现应只添加缺失的collapsed坐标目标，
共用gain solver与canonical统计，不复制整条receiver/harness。

与相位居中候选相比，这条路线直接消除目标的相位参考依赖，保留full gain covariance，
也不需要P维连续Doppler积分；代价是ν仍为point参数，放弃完整连续后验声明。
是否因此比旧point更可靠、更快，需固定预算的实现与receiver证据。
零误码增益的旧adaptive结果不被这一推导改写；所有未来run仍需独立协议与准入。
