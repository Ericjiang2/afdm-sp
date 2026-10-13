# Derivation Package: 优化改善与数据置信风险分离

## Target

DATA-CORRELATION-THEORY-01。解释为何完整变分目标改善也不能保证正确概率预测，
并推导一个保留数据相关性的最小候选。目标是研究机制与可检验方法边界，不是证明
当前 AFDM 错误已经归因于 mean-field。使用经典变分/Ising/block-coordinate 理论，
不声明首创；AFDM 中的实际价值和完整成本仍待证明。

## Status

COHERENT AS STATED，独立数学审查通过；候选的完整低成本实现 NOT YET ESTABLISHED。

## Invariant Object

对固定物理 ν/delay 的工作模型，log p_work(y|ν)=F(q_h q_d,ν)
+KL(q_h q_d || p_work(h,d|y,ν))。提高 F 是减少该模型的反向 KL；
真实生成分布下的符号 log loss 是另一个量。即使工作模型正确，反向 KL 也不等同于
单符号概率的 forward log loss。改变 ν 还改变条件 posterior，不能把跨 ν 的 F 改善
直接等同于逼近同一个固定后验。

## Assumptions and Notation

沿用真实 CPP 路径算子 H_i(ν_i)，H=Σ_i h_i H_i，工作 q_h=CN(m_h,C_h)，
S_ij=E[h_i h_j*]。固定 q_h/ν 时 G=E[H*H]、r=E[H*]y−G p。
数据平均 m_d、协方差 C_d；本轮均为未编码 QPSK 工作先验。
反例另用两个实 BPSK 变量，明确不冒充当前 N1024 AFDM 原始案例。

## Derivation Strategy and Map

1. 完整变分恒等式 → 模型、联合因子化与预测风险的不同目标。
2. 正确线性模型的两变量精确反例 → 因子化可在提高目标时增加错误自信。
3. 固定 q_h 的真实 QPSK 二次能量 → disjoint pair 的精确条件更新。
4. 将 pair covariance 传回增益统计 → 明确额外计算与不可省略项。

## Main Derivation

### 1. 两种 gain 消元并非同一个变分族

记 ℓ_d(h)=log p_work(y|d,h,ν)，固定任意 q_d。
当前共用 gain 因子的最优目标是

F_shared=log∫p_h(h) exp(E_qd ℓ_d(h)) dh−KL(q_d||p_d)。

允许 q(h|d)=p_work(h|y,d,ν) 后的目标为

F_cond=E_qd log∫p_h(h) exp(ℓ_d(h)) dh−KL(q_d||p_d)。

对 q_h^*=argmax_qh F(q_h q_d)，由每个 d 的变分恒等式，精确有

F_cond−F_shared=E_qd KL(q_h^* || p_work(h|y,d,ν))≥0。

因此已验证的 Schur gain 消元仍保留共享 q_h 与 q_d 的独立性；它并没有积分掉
真实联合后验中的全部 gain–data 相关。该非负差是经典恒等式，不是已测出的
当前误码损失，更不能据此推断改用复杂变分族一定值得成本。

### 2. 正确模型下的两 bit 反例

令 s_1,s_2∈{−1,+1}、独立均匀先验，观测 y=a(s_1+s_2)+w，
w 为实 Gaussian，且在 y=0 处考虑 posterior。选噪声使其写为
p(s_1,s_2|y=0)∝exp(−J s_1 s_2)，J>0。
例如 Var(w)=a²/J；这是正确的线性观测模型，没有错误 channel 或错误 prior。
精确边缘由同时翻转两 bit 的对称性始终为 1/2。

对 product q、均值 m_1,m_2，去掉常数的 F 为

F=H_b((1+m_1)/2)+H_b((1+m_2)/2)−J m_1 m_2。

取 m_1=m、m_2=−m，F(m)−F(0)=(J−1)m²−m⁴/6+O(m⁶)。
J>1 时独立均匀解沿反对称方向不稳定，存在更高 F 的非零 m；
内部驻点满足 m=tanh(Jm)。但在精确 posterior 下，其单 bit 期望 log loss 为

−(1/2)log((1+m)/2)−(1/2)log((1−m)/2)
=log 2−(1/2)log(1−m²)>log 2。

这是严格的目标–风险分离；更高 F 可以对应更差边缘概率。确定性硬判的平均错误
仍是 1/2，不能把此例说成必然 BER 变差。y=0 的精确对称例只证明不蕴含关系；
它不证明当前 AFDM 存在完全相同列或该机制导致当前 8 条记录。

### 2a. 被 coordinate concavity 隐藏的交叉 Hessian

固定 q_h/ν，令 a=√(P_d/2)、m_d=a(u+iv)、s=[u;v]，各 bit 均值在 (−1,1)。
在 bit-product 子族上，定义 G_R=[[Re G,−Im G],[Im G,Re G]]，去除对角后为 K。
同符号 I/Q 的交叉项为零，因为 G 的对角为实数。二次能量与 entropy 给出

∇²_s F=−diag(1/(1−s_k²))−(2a²/σ²)K。

G 为 PSD 并不保证 K 为 PSD。对两 bit 正耦合的例子，uniform 点的 Hessian
为 [[−1,−J],[−J,−1]]，当 J>1 时一个特征值为 J−1>0。
每个坐标的二阶导数为负，只说明固定其余坐标时严格凹；不能推出联合凹。
在各 symbol probability 的单纯形切空间中，跨 i≠j 的二阶变化同样包含
−2 Re(δm_i*G_ij δm_j)/σ²，通常不是零。

这给出阅读相关通信 VB 证明时必须检查的具体条件。已读取并视觉核对
[Yuan 等 1911.12538v1](https://arxiv.org/pdf/1911.12538v1) 第 3 页 §III-B 式 (21)
之后的 Hessian 论证；该段由混合导数为零推出全局凹及全局最优收敛。
上述一般耦合二次模型保留非零交叉项，因此不能将该论证直接当作本项目的全局保证。
上述反例尚未严格匹配该文 OTFS 特例的全部限制，因此不是该特例的专属反例。
当前核查严格限于该 arXiv v1 段落，未核实期刊终版或更正；不否定其已报告实验。
也没有声称首次发现这一标准 mean-field 非凸现象。

### 3. 最小相关数据块更新

令数据按不相交 blocks 因子化，block B 含两个 QPSK 符号；固定其余 blocks 与 q_h/ν。
精确坐标目标的最优 q_B 是对 16 个候选 a_B：

q_B(a_B) ∝ p_B(a_B) exp([2 Re(a_B* r_B^c)−a_B*G_BB a_B]/σ²)，
r_B^c=r_B−G_{B,−B}m_{d,−B}。

理由：E[d*Gd] 的跨 block 部分仅依赖均值，B 内保留完整二次能量，
熵为 block entropy。独立 QPSK 更新是 |B|=1 的特例；若 G_BB 非对角，
两符号相关项一般不能分成两个 softmax。
这是固定其他状态下的经典 block mean-field 坐标最优解，不是全局最优或真实 posterior。
所有 blocks 同步更新时，单块坐标证明不能保证整个 F 单调；必须另推阻尼/MM或顺序更新。

当前产品 QPSK 更新从均匀因子开始；其目标对 I/Q bits 是可分的线性项，
几何阻尼也保持该 bit 分解。故当前实现不借四元表示自动引入跨符号相关性。

### 4. pair covariance 不能丢回 diagonal variance 接口

gain 统计必须使用

R_ij=E_d[(H_i(p+d))*H_j(p+d)]
=(H_i(p+m_d))*H_j(p+m_d)+tr(H_i*H_j C_d)。

当 pair (u,v) 有 c_uv=E[(d_u−m_u)(d_v−m_v)*] 时，C_d 的 (u,v)
与 (v,u) 元素为 c_uv 与 c_uv*。相应 trace 增量为
c_uv (H_i*H_j)_{v,u}+c_uv* (H_i*H_j)_{u,v}。
固定 gain 的 expected residual 也必须保留 tr(G C_d)。
只把 pair marginal variance 传入当前对角 SourceMoments 会删除这些项，
从而不再是上述 block 目标；这不是可接受的实现捷径。

## Remarks and Interpretation

保存轨迹显示优化与预测风险分离，能支持检查变分族；但也可能受工作先验、
ν 的 empirical-Bayes 更新、获取误差或模型因素影响。反例只证明因子化本身足以
产生此现象，不证明它是本项目观测的原因。structured q(h|d) 与 pair q_d 是不同修正，
需要分别消融，不能把两者混合后将收益归给一个模块。

## Boundaries and Non-Claims

经典 block inference/structured VB 在通信中有先例；若后续 AFDM 实现有用，
主张仅为适配、可解释消融和实测收益。未运行新仿真、未定义部署停止策略、
未替换已接受原始主张或改变科学门。

## Sources and Overlap

- [Plummer, Pati, Bhattacharya, 2020](https://arxiv.org/abs/2007.06715)：
  两节点 Ising 的 CAVI 非凸区间、串行与并行动态已有系统分析。
  本轮读取摘要；不将本笔记两 bit 反例或分叉主张为新理论。
- [Hoffman and Blei, 2015](https://proceedings.mlr.press/v38/hoffman15.html)：
  structured VI 允许全局/局部 latent 依赖已有明确先例；本轮读取论文元数据与摘要。
- [Yuan 等，1911.12538v1](https://arxiv.org/pdf/1911.12538v1)：
  本轮读取 PDF §III 的 mean-field 与 Hessian 段落并核对第 3 页截图。
  本地原件位于 `.mission/20261007-sp-fractional-trans/literature/1911.12538v1.pdf`，
  SHA-256 `821d82e0736dd727cd22aa0c68db391e6f737bfb99fb2e6379a8a40997569346`。
  定点检索没有找到足以核验的更正信息；这不证明不存在更正或前人批评。

## Open Risks

当前已实现的非均匀 variance FFT 只覆盖 diagonal C_d。补充推导
`PAIR_COVARIANCE_FFT.md` 已将稀疏 cross 项按实际 CPP/DAFT 频差分组，给出精确
FFT 公式与操作量；尚无数值验证或完整运行时间。挑选 pairs 必须只用观测/模型
与固定预算，不能看 true errors。最小下一步先验证这些矩，再明确有限配对规则
和完整更新成本，之后才判断接收实验的价值。当前尚无经实测通过的低成本候选。
