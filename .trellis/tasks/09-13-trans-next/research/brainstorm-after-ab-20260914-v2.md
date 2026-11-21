# A/B之后：可辨识性、联合不确定性与完整计算

日期：2026-09-14。Scientific-brainstorming＋formula-derivation咨询工件；接续现有研究上下文，不创建/切换任务，不修改CSV执行状态。

## Target

依据最新结果筛选仍值得检验的方向，严格区分表示误差、估计器地板、联合可辨识性和判决成本。输出是有条件的研究判断，不是已成立的新方法。

## Status

**COHERENT AFTER REFRAMING / EXTRA ASSUMPTION。** 下述固定设计风险、有限集合可辨识性命题和Gaussian积分在列明条件下成立；尚无证据证明当前N256/N1024接收机会因此改善。本轮主会话自审，独立性weak；luna子代理只检索本地证据。

## Invariant Object

固定物理观测、合法信息和完整预算下的BER/FER—成本关系。信道风险、子空间距离、工作似然和矩阵乘法成本均为中间量。

## Evidence

- [A/B结论](unified-exploration-20260914/findings.md)：64开发信道、N256、pZ@20 dB，OMP_SMALL12/GCE-q5/DPSS-q5的BER为0.057892/0.089417/0.091492；后两者相对OMP的差值同时区间为[0.013135,0.049914]/[0.014174,0.053026]。九种固定基对两小支撑参照的18个主端点区间均为正，开发成本为最快参考的1.684–2.111倍。
- [A02](unified-exploration-20260914/a02-results-v2.md)：DPSS-q5表示误差约3.84e-5、LS NMSE=0.411456，小支撑为0.164395。DPSS-q5映射后的数据干扰/噪声项为0.39204/0.0081121。交叉项另存，不能直接相加或认领完整链因果归因。
- [REF-06](terminal-controls-results-v1.md)：旧32编码开发块7 dB，普通温度1/物理方差/保留码先验把4错块降至1错块。压缩了旧方法空间，但不是独立确认或Bayes饱和证据。
- [旧G1几何](g1-active-observability-v1-results.md)：640个24列设计满秩、最大归一化Gram条件数2.259815。不能解释为旧配置严重病态；它不覆盖新N256高维基，后者A02最大合法活动条件数13645。
- B02历史N256局部候选的完整真向量覆盖为0，选择器未准入。固定H欧氏稳定性不是联合后验保证。旧论文现行主张以STATE.md的审计裁决为准，不能恢复FYP备份中的学习叙事。
- 本地代码补充取证：[supplement_baselines.py](../../../../afdm_sp_joint_unrolled/supplement_baselines.py)已有固定OMP提名单一支撑的SBL型II似然（含logdet）及增益后验；[classical_joint_unrolled.py](../../../../afdm_sp_joint_unrolled/classical_joint_unrolled.py)已有固定支撑Q/C工作更新。两者不等于完整数据候选D_c对应的信道边缘似然；当前未找到后者或多支撑/多模态联合后验的接收实验。这里的“未覆盖”限该具体对象，不能说项目从未考虑后验/协方差。

## Assumptions and Notation

观测y=H(p+d)+n，p和d均已含功率缩放。初始d零均值、Cov(d)=P_d I；n独立零均值、Cov(n)=σ²I。H_q=Σ a_j B_j为固定矩阵子空间中H的Frobenius正交投影，E_q=H−H_q；G_ij=tr(B_iᴴB_j)，Φ_p=[B_1p,…,B_Kp]，LΦ_p=I。D_c=[B_j(p+d(c))]_j。A为单位DAFT。

第一段条件于固定H和观测之前固定的表示/估计矩阵；不适用于同y选支撑后直接无条件取期望。可辨识性段为精确有限模型、无噪声、有限数据集合。边缘积分段的Gaussian先验必须在本帧y出现之前指定。结构作用段要求整数延迟及合法CPP边界，允许连续多普勒相位，不优化连续多普勒参数。

## Derivation Strategy and Map

同一观测 → 固定设计风险 → 区分估计器地板和联合辨识 → 候选相关边缘积分 → 结构作用与完整软输出成本。数学成立、机制解释、候选收益分别标注。

## Main Derivation

### 1. 更准的表示为何可以给出更差的估计

**[恒等式]**
\[
y=\Phi_p a+E_qp+Hd+n,\qquad
\hat a-a=LE_qp+L(Hd+n).
\]
正交性tr(B_jᴴE_q)=0逐样本消去信道空间交叉项，再对d,n取期望：
\[
\boxed{\mathbb E\|\hat H-H\|_F^2
=\|E_q\|_F^2+\|LE_qp\|_G^2+
\operatorname{tr}\{GL(P_dHH^H+\sigma^2I)L^H\}.}
\tag{1}
\]
||z||_G²=zᴴGz。三项分别是未表示部分、遗漏响应泄入已有系数的偏差、数据干扰及噪声放大；无需Gaussian数据假设。

非正交分解需保留额外交叉项；ridge需计收缩偏差；同y选择支撑/形成反馈时需处理条件依赖，不能直接套(1)。A02是实际路径分账，不是这些统计条件已满足的证明。

**[解释/候选]** A的失败与“更低逼近偏差被更大的干扰拟合代价抵消”相容。经典偏差—方差公式本身不是新贡献。值得追的是能否提前预测扩维转折，并用合法规则跨工作点胜过小支撑和普通ridge；不是继续换基或事后解释曲线。

### 2. SP估计地板不是联合信息极限

**[条件性结论]** 精确模型E_q=0下，固定左逆估计的增益误差协方差为
\[
C_{\hat a-a}=L(P_dHH^H+\sigma^2I)L^H.
\tag{2}
\]
当σ²→0且LHHᴴLᴴ非零时留下地板。它只约束该估计器。

**[严格反例]** 两个QPSK数据符号、单符号能量P_d、未知非零复增益g，无噪声，p=[a,0]ᵀ且a>√(2P_d)。纯导频估计g_hat=y_1/a有
\[
\mathbb E|\hat g-g|^2=|g|^2P_d/a^2>0.
\tag{3}
\]
但联合(g,d)唯一：若另一(g',d')生成同一y，第二分量给λ=g'/g=d_2/d'_2∈{1,−1,i,−i}；第一分量要求a(1−λ)=λd'_1−d_1。λ≠1时左边模至少a√2，右边至多2√P_d，矛盾。因此λ=1，d=d'且g=g'。

这个例子证明“导频LS有地板”与“联合无噪声唯一”能够同时成立；不是N256性能证明，也不是当前项目的功率调整建议。

**[有限模型命题]** 若各D_c列满秩K且不同c的K维列空间互不相同，则连续分布的g在无噪声下几乎处处可辨识c,g。两个不同K维子空间交集维数<K；该交集的g原像为零测集；有限个错误候选的并仍为零测。实际AFDM还需验证相位/移位歧义、未知支撑和失配；K<N或单个设计满秩都不足以单独保证前提。此为基本条件性推导，不认领AFDM新定理。

### 3. 优先判别：候选相关信道不确定性是否有检测价值

**[模型内精确积分]** 固定表示，g∼CN(m_0,Γ)、Γ≻0，在当前y之前指定并与数据候选c独立；n∼CN(0,σ²I)。则
\[
y|c\sim\mathcal{CN}(D_cm_0,R_c),\qquad R_c=\sigma^2I+D_c\Gamma D_c^H,
\]
\[
\ell(c)=(y-D_cm_0)^HR_c^{-1}(y-D_cm_0)+\log\det R_c-\log\pi(c).
\tag{4}
\]
π(c)为数据先验。该方向在根目录旧推导式(13)–(14)已有概念，本轮是根据A/B负结果重新排序，不称首次提出。

D_c=D_p+D_d(c)给出
\[
R_c=\sigma^2I+D_p\Gamma D_p^H+D_d\Gamma D_d^H+
D_p\Gamma D_d^H+D_d\Gamma D_p^H.
\tag{5}
\]
最后两项来自同一未知信道同时作用于pilot和data。全局固定白化或标量LLR缩放一般不能表达这种候选依赖；不代表(4)已优于强经典接收。

若S未知，还需Σ_S π(S)p(y|c,S)，不能免费给真支撑。用本帧y先筛选候选/支撑再局部归一化是截断近似，必须检查覆盖/遗漏概率；不能沿用B的局部四点假装全空间比较。把同y拟合的后验当独立先验再使用似然也不满足(4)。

**[计算恒等式]** Q_c=Γ⁻¹+D_cᴴD_c/σ²：
\[
R_c^{-1}=\sigma^{-2}I-\sigma^{-4}D_cQ_c^{-1}D_c^H,\qquad
\log\det R_c=N\log\sigma^2+\log\det\Gamma+\log\det Q_c.
\tag{6}
\]
部分求解转为K维；Gram构造一般仍需O(NK²)、分解O(K³)，再乘候选数，远非免费。利用AFDM离散相位/移位共享计算才是实现问题。当前归一化路径增益未必服从此Gaussian先验。

**最小判别建议：** 在独立小型、精确匹配模型中建立完整候选参考，比较点估计、标准双线性消息传递与保留不确定性度量；先验证错误/LLR差距。只在真支撑、特选错误块或极大计算量下有效则不晋级。差距存在，再开发有限预算N256近似，面对小支撑、普通SBL/PBiGaBP等参照。本轮未执行这些接收实验。

### 4. 备选：同质量软输出的结构化计算

**[算子恒等式]** CPP相位吸收到h_l[n]后：
\[
H_t=\sum_{\ell\in\mathcal L}\operatorname{diag}(h_\ell)\Pi_\ell,\qquad H_{\rm eff}=AH_tA^H.
\tag{7}
\]
h_l已构造时，H_eff及伴随每次作用O(NlogN+N|L|)，不用显式展开所有DAFT泄漏边。h_l构造、存储仍须计费；真路径不可在线使用；该恒等式不新。

Gaussian软输入模块需Jz=b，其中J=V⁻¹+σ⁻² H_hatᴴH_hat。V正定时可迭代求均值，残差r=b−Jz_t满足
\[
\|z_*-z_t\|_2\le\|r\|_2/\lambda_{\min}(J)
\le\lambda_{\max}(V)\|r\|_2.
\tag{8}
\]
这是线性均值数值界，不是BER/FER界；不控制soft-output所需diag(J⁻¹)。V为零的确定符号要先消去/重参数化，不能直接求逆。时域离散BP也不能忽略变换后先验耦合。

可研究的剩余问题是可靠方差/外信息、近似偏差和全SP接收成本同时受控。仅FFT/CG/缓存/普通STOP不构成新颖贡献，也不能由单次乘法复杂度宣布完整接收机近线性。

## Remarks and Interpretation

优先顺序：**先判别联合不确定性还有多少可兑现差距；有差距才做预算内近似；结构软输出作为备选。** (1)可作为机制/预测理论。现有论文整理最有证据基础的是已接受的机制与系统结果及适用/失败边界；新Transactions方法贡献仍未证实。旧G0、旧N1024编码、新N256水声独立报告，不拼接效应量。

## Literature and Novelty Boundaries

检索截至2026-09-14，为定向检索而非穷尽查新。以下只支持所列事实，不代表所有公式经逐式审查或算法已复现。

| 文献和来源 | 本轮读取层级 | 对本研究的边界 |
|---|---|---|
| [Zheng等 AFDM-SP，2024作者稿v1](https://arxiv.org/html/2404.10232v1) | 模型/接收框架，结合本项目已有推导 | 导频设计、SP和迭代CE/检测已有 |
| [He与Tugnait，TSP 2008作者上传原文](https://www.researchgate.net/publication/220322641_On_Doubly_Selective_Channel_Estimation_Using_Superimposed_Training_and_Discrete_Prolate_Spheroidal_Sequences)，DOI 10.1109/TSP.2008.919639 | 摘要/引言原文；出版社DOI本次抓取失败 | SP+DPSS+数据干扰处理和迭代DML早已有 |
| [Liu等 BEM-AFDM，2025 v2全文](https://arxiv.org/html/2504.18901v2) | §II–III | GCE及模型/估计误差分析已有；嵌入保护导频条件不同 |
| [Huang等 SP-OTFS，2024 v2](https://arxiv.org/html/2309.08177v2) | 方法框架及既有笔记 | SP+BEM+联合消息传递已有 |
| [Li、Lee与Bresler，双线性可辨识性](https://arxiv.org/abs/1501.06120) | 摘要 | 约束及变换歧义是通用框架；本篇反例/有限命题自行推导，不冒称其AFDM定理 |
| [Ranasinghe等 AFDM联合估计，v3](https://arxiv.org/html/2405.16945v3) | 方法框架与已有信息假设笔记 | PBiGaBP直接近邻；联合Bayesian不是新颖性；算子先验需公平对齐 |
| [Luo等 2026-07数据辅助SBL](https://arxiv.org/html/2607.18881v1) | 摘要/引言，结合既有§III笔记 | AFDM-SP、离栅、MMV、数据辅助/GAMP已有；不建议用换SBL填创新 |
| [Chen等 PCG-MPI-AVrEP，2025机构摘要](https://scholars.lib.ntu.edu.tw/entities/publication/4c73a60c-f716-4b65-b120-e0cca9d8c97c)，DOI 10.1109/LWC.2025.3627115 | 摘要，未取得全文 | AFDM的PCG均值、近似方差已有；具体算法新颖性尚须全文比对 |
| [Mao等 chirp/低复杂度MMSE，2026-07](https://arxiv.org/html/2607.20227v1)；[Li、Yu DI-S-MMSE](https://arxiv.org/abs/2207.00866) | 方法范围/摘要及既有笔记 | 结构接收和完整软输出必须面对这些参照；perfect CSI不能代签SP估计链 |

## Boundaries and Non-Claims

- 无新接收机、训练、仿真、独立CONF或正式COST；不恢复停止的A/B配方或后置跨块C，不开展连续参数/宽带模型。
- (1)不是同y自适应风险估计；(2)不是信息论下界；(3)仅反例，不代表N256。
- (4)仅在指定Gaussian先验内精确；真实模型适配、近似算法和收益未证。
- (8)只控制线性均值，不保证译码/方差/全局收敛或完整近线性复杂度。
- 当前零合格新候选和七个后置门保持原状态；不认领首次。

## Open Risks

标准SBL/PBiGaBP/EP可能覆盖所有收益；小系统差距可能无法扩展；有限候选可能再次漏掉正确向量；先验失配/真实支撑遗漏可能主导；方差、候选和初始化成本可能抵消所有乘法优势。

## Verification and Provenance

[代数脚本](brainstorm-algebra-20260914-v2.py)用NumPy 2.1.3运行成功，[结果JSON](brainstorm-algebra-20260914-v2-results.json)记录：768个有限分布联合状态精确加权核验(1)，相对误差3.33e-16；32个复矩阵例核验(5)/(6)，最大相对误差3.09e-16/8.45e-15；反例16个完整数据向量两两不共线，最小夹角正弦平方0.017994，纯导频LS地板0.137996（该例数值）。

AFDM接收机调用=0、新信道实验=0。公式依据是正文推导，有限数值例不替代证明，也不是BER证据或独立科学审查。
