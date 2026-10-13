# A：固定带限表示与导频可观测性推导

## Target

核验固定 q 时间基是否以合法、可估的系数表示完整 CPP/DAFT 信道。推导对象为表示误差和导频线性映射；BER 与完整成本需要后续实验。

## Status

COHERENT AS STATED。以下恒等式不包含接收性能保证。

## Invariant Object

完整 sampled channel H 及其作用 Hx。少量系数不是低秩 H，也不保证稀疏检测图。

## Assumptions

- A=L2 F L1 为单位 DAFT，F 使用负指数；L1/L2 使用正 chirp。
- 时延为 0..24 的整数，CPP32 足够；无宽带伸缩。
- UqᴴUq=I，固定且只由 N、公开频带和 q 确定。令 B=sqrt(N)Uq。
- 真信道只用于外部分解；合法系数与时延选择只使用已知 pilot 和接收 y。

## Notation

Cl 的第 n 行在列 (n-l) mod N 上非零。n-l<0 时该值为 exp[j2πc1(N²+2N(n-l))]，否则为1。
Tlj=A diag(B[:,j]) Cl Aᴴ；a_lj 为自由复系数。P 为选中时延组集合，Phi(x) 的列为 Tlj x。

## Derivation Strategy

从 CPP 传播构造时间算子，经单位变换得到 H；再分别分析 Frobenius 投影与 pilot 观测。二者使用不同内积，不能互相替代。

## Derivation Map

1. CPP 延迟的显式相位 → Tlj。
2. 不同时延的时间矩阵支撑不交，组内 Uq 正交 → 算子 Frobenius 正交。
3. 固定投影误差的迹恒等式 → 平坦频谱下 DPSS 平均最优。
4. 作用在一个 pilot 上 → Phi 的秩与噪声放大；Frobenius 正交不保证 Phi 正交。

## Main Derivation

**恒等式 1（算子）**：Hq=Σ_(l∈P,j) a_lj Tlj，因而 Hq x=Phi(x)a。实现先构造时间包络 B a_l，再做双侧 FFT；独立验证按每个 DAFT 单位脉冲经过真实 CPP 延迟、时间乘法和 DAFT 完成，不复用同一矩阵公式。

**恒等式 2（完整矩阵投影）**：对不同整数时延，Cl 的非零位置逐行不同；同一时延的前缀相位模长为1。因此 <Tlj,Tmk>_F=N δ_lm δ_jk。系数 oracle 为 a*_lj=<Tlj,H>_F/N，且 ||H-Hq||²_F 可分为固定全域表示、选组遗漏和系数误差。这里的正交性需要完整 N×N 算子；阈值化/阻尼后的实际 H 不自动属于该子空间。

**恒等式 3（单时延平均表示）**：对 v[n]=exp(j2πνn/Fb)，R=E[vvᴴ]，有 E||v-UqUqᴴv||²/N=1-tr(Uqᴴ R Uq)/N。平坦 ν∈[-νmax,νmax] 时，R_mn=sinc(2νmax(m-n)/Fb)。写 R=VΛVᴴ，tr(Uqᴴ R Uq)=Σ λ_i w_i，其中0≤w_i≤1、Σw_i=q，因此前 q 特征向量最大化该迹。该命题只约束平坦设计分布；随机角度 ν=16cosθ 的评价协方差不同。

**恒等式 4（导频映射）**：Phi(p)=[Tlj p]。其 Gram 为 pᴴTljᴴTmk p，通常不等于 <Tlj,Tmk>_F。合法可估性以实际选中矩阵的秩/奇异值为准；全字典最大相干性不能单独判定活动估计失败。

**命题（当前 pZ 的 Fourier 碰撞）**：当2Nc1=5，B_j[n]=exp(j2πkn/N)，pZ=sqrt(Nrho)e0 时，Tlk pZ 只在 (5l+k) mod N 处非零。q=5 使用 k=-2..2，25 个时延产生125个不同位置；q=7 使用 k=-3..3，总175列却只有127个不同位置，故全字典秩至多127。稀疏选组可能恢复满列秩，须直接检查，不允许据全字典结论删除所有 q7 活动构造。

GCE 的频点固定等距覆盖公开频带，经 QR 只改变坐标、不改变子空间。DPSS 的特征向量符号由最大幅度元素确定。所有基用相同 sqrt(N) 缩放，使物理系数与普通整数 Fourier 算子保持一致的归一化。

## Remarks and Interpretation

单时延 DPSS 误差优势只是表示线索。合法多时延选择、SP 数据干扰、带噪系数估计、图阈值化和 BP 方差消费均可能改变排序。A-01 的旧观测仅检验实际选择几何，不用于独立确认。

## Boundaries and Non-Claims

无连续频率估计；oracle 时延不进入接收端；离散频率网格最大误差不等于连续区间严格界；正交投影最优不等于 LS/MSE/BER 最优；无 BP 或 LDPC 性能保证。

## Open Risks

q7 的 pilot 碰撞、GCE/DPSS 组间近相关、错误时延选择和稠密 BP 开销。每个风险按实际构造记录，不能以修改 q/频带或隐藏丢列通过原门。
