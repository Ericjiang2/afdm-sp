# Research: 从算子、奇异几何与离散代数重新选择推断对象

- Query: 超越上一轮单一全局仿射、忽略余项候选，找出 4 个不同的数学研究对象及最便宜的可证伪检验。
- Scope: internal source / mathematical derivation / original literature, no new experiments.
- Date: 2026-10-03
- Skills: scientific-brainstorming（本轮读取）、scientific-critical-thinking（同代理前轮已读并复用）。
- 输出目录由主会话明确指定为本轮研究 artifact 根，不新建生命周期或 CSV 状态系统。

## Findings

### 结论与优先级

最值得先做的是 **碰撞路径的可辨识组合坐标**，其次是 **路径表示变化下的先验一致性**。这两项都有可定位的当前代码接口，几乎可以先用纯代数与极小实例判断是否真有问题。更远但能真正跨过上一轮限制的是 **直接推断双线性乘积的提升变量** 和 **把离散相位模式作为商空间变量做解析边缘化**。四者改变的分别是物理参数坐标、先验所附着的对象、随机状态的阶数、以及模式的组织方式；不是四种新增循环。

本报告未运行接收机或性能实验；初版“测试”均为建议，随后经授权完成文末生产LDPC相位自同构代数检验。静态事实不等于 FER 原因；标准 Prony、lifting、Gaussian prior pushforward、群作用本身都不宣称原创。上一轮 FINDINGS 的结论继续成立：没有新主接收机性能证据，也没有穷尽整个方向。

### 1. 碰撞路径不应该只能在“强行合并”和“病态分开”之间选择

**已确认源码事实。** `experiments/sp_afdm_native_joint_20260921/src/twofft.py:87–88` 先 `np.unique(ls)`，每个相同整数 delay 仅保留 strongest Doppler center。因此 native 的局部物理模型排除了“同整数 delay、不同连续 Doppler”的多路径组合。F1 已通过 `experiments/cstate_necessity_stageA_20260928/keep_slots.py:23–28` 去掉这个压缩，故“保留相同 delay 多路径”已经是项目内已有能力，不是新 idea；也不能说完整 cascade 永远无法恢复它。

**新的数学对象：路径碰撞附近的低阶矩 / confluent 坐标。** 固定 delay l 和 Doppler 中心 ν0，令真实相邻路径为 νj=ν0+δj。代码物理算子满足

U(l,ν0+δ)=sum_(k=0)^r δ^k/k! · ∂ν^k U(l,ν0)+R_(r+1)(δ),
∂ν^k U(l,ν0)=A diag((j2πn/N)^k) Dν0 C_l P_l Aᴴ.

于是
sum_j h_j U(l,νj) ≈ sum_(k=0)^r M_k/k! · ∂ν^k U(l,ν0),
M_k=sum_j h_j δ_j^k.

两个近碰撞路径的 M0=h1+h2、M1=h1δ1+h2δ2 通常比单独 (h1,h2,δ1,δ2) 更直接可辨识。保留 M1 能表达两个路径相消导致 M0≈0 但导数响应不为零的情形；单个有效增益/实 Doppler center 无法一般等效地表达这种复幅度组合。中心不要用 M1/M0 直接算：该比值在相消时发散，而且一般为复数，不能冒充实 Doppler。

这里的 Taylor 是 **连续几何参数 δ 的算子近似**，不是上一轮对随机 h,d 的一阶仿射化；H仍作用在完整(p+d)上，二者的区别必须明确。固定 x 下可给保守余项界：设 |δj|≤ε，则
||sum_j h_j R_(r+1)(δj)x|| ≤ ||x|| sum_j |h_j| exp(2πε)(2πε)^(r+1)/(r+1)!.
该界来自单位ary A/CPP/shift与指数级数，足够保守；不假称它证明未知数据后验正确。

**为什么可能自然。** 物理散射模型在路径碰撞处是一个奇异参数化：交换路径不改变H，完全重合只识别总增益，接近重合时差模态弱可辨。算法应在“可预测的算子组合”上工作，而不是对实际上不可稳健识别的单路径标签反复优化。通过正交化 response/derivative 列，可以维持同一有效维度预算，直接替换原槽参数化；只有真的需要新可辨识导数方向才增加物理有效阶数。

**最便宜可证伪检验。** 不跑 FER：已知x、同delay双路径、小δ及反相增益；比较 (a) native单中心模型，(b) F1双槽模型，(c)相同或更少实自由度的 r=1 jet 模型。报告 noiseless model residual、Jacobian最小非零奇异值、算子预测误差及每个模型实际参数数目。不能只比单路径 gain NMSE，因为弱可辨标签误差未必影响Hx。若真实旧状态几乎无近碰撞，或相同预算 F1 稳定而jet无益，则降低该方向；若 jet 仅在虚构超小δ有效，不升为主创新。

**最近邻与差异。** Batenkov–Yomdin 的 confluent Prony 已使用节点导数和 confluent Vandermonde，原文见下；Tang等的 off-grid atomic norm已经处理连续频率，但其经典保证需要间隔条件。项目的新机会只能是：CPP/连续Doppler与叠加导频下的可辨识jet状态、配套合法软推断及同资源效果。使用Prony/原子范数的名字本身没有贡献。

### 2. 先验应附着在物理算子上，还是附着在“当前列表里有几个槽”？

**已确认事实。** `twofft.py:46` 使用 h~CN(0,I/P)，P由`physical.Channel.p:102`定义为当前槽数。上轮 PRIOR-02 比较的是 CE precision 1 与 P、再由同一个 joint prior 运行；它没有验证**改变等价物理表示是否改变先验**，所以这是不同的因果问题。

**精确反例对象。** 原表示 H=aU+bV，a,b独立CN(0,1/2)。将U仅作冗余拆分，写H=(a1+a2)U+bV。若自动切成 P=3 iid CN(0,1/3)，则U聚合增益方差变2/3，V变1/3，原来却各1/2。物理算子集合没变，但先验分布变了。注意全体只有一个U时从P=1拆为P=2 iid1/2，聚合方差仍1，不能用该特殊例声称一般不变或一般失效。

**真正不变量。** 若两套参数满足 α=Tβ 且 H=Dα=D Tβ，等价的Gaussian prior须满足
mα=T mβ， Cα=T Cβ Tᴴ.
例如上述冗余拆分可取 Var(a1)=Var(a2)=1/4、Var(b)=1/2。更一般可在物理散射测度的分区上分配先验功率质量：把一块分成两块时，总质量相加不变。真正不同的两个物理散射体可以有不同先验；**表示冗余**与**物理模型改变**必须分开，不能强迫所有选槽具有一个统一先验。

**一个很自然但不应直接部署的构造。** 令 D_p=vec(U_p)/sqrt(N)，D=[D_p]，R=DᴴD、r=rank(R)。定义 C_h=R†/r，则
Cov(Dh)=D R† Dᴴ/r=Π_range(D)/r， E||Dh||²=1.
这给算子子空间的各向同性Gaussian prior，完全相同span的冗余列表示具有相同算子先验；等价于规范化的Gaussian g-prior思路。它不是任意物理多径的真实prior。近碰撞时R小特征值的逆让坐标gain变大；rank变动还会使r归一化不连续。它有意在弱可辨导数方向投入与强方向同样的算子能量，可能与真实散射功率规律相反。不能把R† whitening称为已解决方案。

最稳妥的第一步是**测试prior pushforward是否守恒**，再决定使用物理功率质量、jet正交坐标prior或其他明确的模型。改变prior是可解释统计建模，不是自动提升创新性。

**生成器提醒。** `.../afdm_env.py:505–531,625–645`先生成路径gain再按旧有限虚拟算子的 Frobenius norm 统一缩放；`.../supplement_g1.py:76–90,114–123`保留这组gain而换真实CPP连续物理算子，不再次按真实H归一化。因此真实生成gain分布并非自动等于独立CN(0,I/P)，也不能断言真实H每帧恰有||H||F²/N=1。Gaussian working prior可以仍是合理近似；上述事实只要求避免把它冒充生成真分布。

**最便宜检验。** 固定相同U,V,y,pilot和输入先验，做冗余拆分/合并的模型等价性试验：先直接验证prior-predictive covariance B C_h Bᴴ和精确小模型 LLR 在正确pushforward下相同；再测当前1/P机制的变化。若两种表示是有意不同物理模型，不能把结果叫bug。若变化大且与实际路径槽机制相关，才进入改prior及同预算验证。该检验不需要增加检测轮数或新候选。

**文献边界。** covariance pushforward、g-prior和Gaussian随机测度都是标准对象。本轮没有完成AFDM representation-invariant prior的全面原文近邻检索，不可称首创。它与第1项的关系是先选稳定物理坐标，再转运同一prior，而不是把prior调成让新坐标胜出。

### 3. 不再把 E[h]E[d] 当作自然中心：直接以乘积提升变量作为状态

**对上一轮结果的正确反应。** 最佳全局仿射只作用于(h,d)的一阶坐标；bilinear乘积可以在这些坐标的线性span之外。把乘积作为坐标，改变了近似族，故不受那个affine residual-neglect no-go直接否定。但“提升后是线性的”不等于统计推断已变容易。

定义 x=p+d，Z=h xᵀ∈C^(P×N)，注意是**转置**不是共轭转置。令
𝒜(Z)=sum_p U_p Z_(p,:)ᵀ， y=𝒜(Z)+w，rank(Z)=1.
精确 posterior predictive mean为
E[y_noiseless|y]=𝒜(E[Z|y]),
E[Z|y]=m_h(p+m_d)ᵀ+E[(h-m_h)(d-m_d)ᵀ|y].
最后一项是**非共轭 cross moment / pseudo-cross**。用Cov(h,d)=E[δh δdᴴ]替换它会改变预测对象。每个样本Z秩1，而其后验均值一般可以达到min(P,N)阶；强行将E[Z]压回秩1会再次丢失模式与耦合信息。

一种候选是保留小P的乘积矩阵及可识别行子空间，直接传播𝒜(Z)的自然参数，同时用rank-one/finite-constellation约束恢复h,d的边缘，而不是先乘两个均值。为保留pilot，可用扩展W=h[1,dᵀ]：第一列就是h，输出为sum_p[W_p0 U_p p+U_p(W_p,1:)ᵀ]；这样不会把已知pilot与未知数据的约束混为任意rank1矩阵。

**有限星座提供比核范数更强的代数条件。** 实数化后每个data坐标满足 d_i²=pd/2。若采用矩松弛，moment matrix
M=E[[1;z][1;z]ᵀ]≽0
且对应data对角元素固定pd/2；完整平方残差似然关于(h,d)是四次多项式，因此仅有二阶M不足以精确表示posterior，至少需要相关四阶/局部化信息或一个明确近似。不能把通用rank1核范数最小化直接称为QPSK Bayes解。

**最便宜可证伪检验。** 利用已封存oracle，不运行接收机：构造精确E[Z]，检查(1)𝒜(E[Z])等于精确信号均值；(2)压到rank1、rank2…时预测误差与LLR可用信息是否保留；(3)缺失pseudo-cross时的直接预测偏差；(4)相同预测均值仍可能具有不同LLR，避免把预测MSE冒充检测质量。这里的SVD只定位最小信息状态，不是终端补偿。若保留的Z仅改善预测而不提供闭合合法symbol messages，该路线仍未形成算法。

**最近邻与未解决点。** Ahmed–Recht–Romberg已把blind deconvolution提升为rank1线性测量，并给随机子空间/频域spread条件下的核范数恢复；这不是本项目可直接搬用的证明。其论文写w x*，因为采用相应的复内积约定；本项目需明确把第二变量共轭化才能映射，不能无意把h dᵀ改成h dᴴ。项目旧exact mixture/branch cavity也已保留联合prediction，因此新的贡献必须在**无需枚举码本的lifted闭合及AFDM算子计算**，不是再证明全矩公式。当前没有该可扩展闭合的完成证据。

### 4. 模式不是误差：在合法离散相位轨道上解析边缘化

**第一性原理。** 无pilot时(h,d)→(e^-jθh,e^jθd)，θ∈{0,π/2,π,3π/2}，保留QPSK集合与H(h)d。完整posterior可能多个对称模式，E[h]=E[d]=0却乘积有信息。这解释为什么全局单Gaussian中心不是唯一自然选择。生产有pilot，群对称被**已知pilot**破坏；这不意味着所有模式都消失，而是它们有可计算相对权重。

固定一个orbit代表(h,d)，定义v=H(h)p、s_d=H(h)d、r=y-s_d。相位变换后的预测为
s_θ=s_d+e^-jθ v，
log L_θ=const+(2/sigma2) Re[e^-jθ rᴴv].
因此一个代表的4个相位权重只需一个复inner product及4项logsumexp；不必重复4次完整物理检测。可考虑直接推断商变量“data-product state + orbit representative”，同时保留这些有限相位权重。条件h/d边缘与不变的data-product预测分别计算，避免一次mode选错就向CE注入高度自信但相反的软符号。

**生产约束决定是否真的合法。** QPSK字母表在90度旋转下封闭，但LDPC合法码字集不必封闭。I/Q交换与符号翻转诱导binary仿射变换 b' = Pθ b+cθ (mod2)。若原码由生成矩阵G生成，合法自同构可检验
H_check Pθ G=0， H_check cθ=0 (mod2).
若不满足，该θ并非同一code prior下的对称轨道，不能对非法码字赋相等权重或说已消除相位 ambiguity；应由码约束破坏该模式，或直接关闭exact-orbit方案。bit prior非对称时同样须保留π(dθ)/π(d)。这里只给精确fixed-representative似然比例；对未知h,d的posterior积分仍需模式内近似，不能把4点公式夸大成完整joint decoder。

**与一般chirp/DAFT equivariance的边界。** 接收空间任意unitary旋转可同时旋转y和算子并保持白噪声，但数据空间任意chirp/unitary一般不保留QPSK可分prior。只有适当的单项矩阵（坐标置换、各坐标4阶相位）且通过code automorphism检验，才是这个有限prior的精确对称。不能用Heisenberg/Weyl群的整个代数作用自动获得“同分布数据”，也不能以unitary变换引用VAMP随机右旋不变保证。

**最便宜检验。** 首先对冻结LDPC G/H和I/Q映射做4个代数自同构检验；无需新样本、无FER。若不合法，记录精确群路线上界而不硬凑。若合法，再在现有oracle验证phase权重公式和quotient reconstruction是否完整恢复边缘；比较mode内信息与mode权重，查明单峰错位是否真解释小模型LLR误差。现有短码oracle的对称性不能替代生产LDPC检验。后续若需要更多general modes或数据驱动bank，就已改变此有限解析机制，不能以新增候选数量冒充同一贡献。

**新颖性边界。** 群平均、商空间与相位ambiguity解析均是标准思想；本轮未取得直接AFDM+该LDPC quotient receiver的最近邻全文，首创性未知。它不同于旧有限任意码字bank，因为首先利用一个明确有限群的共享不变计算，而非随错误增加候选；但若最后只能实现4次原接收机重启，它就退化为算力堆叠，应该放弃主创新表述。

## 本轮实际阅读的原文与相关来源

1. Dmitry Batenkov, Yosef Yomdin, *On the accuracy of solving confluent Prony systems*, [arXiv:1106.1137v3 原文](https://arxiv.org/html/1106.1137v3)。本轮实际读原文定义、confluent系统与Jacobian：sum_i sum_j a_ij(k)_j ξ_i^(k-j)=m_k，及节点/系数导数。该文讨论局部稳定性，不证明本项目低SNR未知data可直接Prony解耦。
2. Ali Ahmed, Benjamin Recht, Justin Romberg, *Blind Deconvolution using Convex Programming*, [arXiv:1211.5608v3 原文](https://arxiv.org/html/1211.5608v3)。本轮实际读lifting、核范数方案及随机子空间假设；原文已明确rank1线性测量。不能把确定性AFDM+离散LDPC套入其恢复条件。
3. Gongguo Tang, Badri Narayan Bhaskar, Parikshit Shah, Benjamin Recht, *Compressed Sensing off the Grid*, [arXiv:1207.6053v3 原文](https://arxiv.org/html/1207.6053v3)。本轮实际读连续频率模型、atomic norm/Toeplitz SDP和间隔要求；它不解决任意近碰撞与未知data混合。
4. P-BiG-AMP、AFDM PBiGaBP、EP/EC、VAMP的原文核对复用 `.trellis/tasks/10-02-inference-causal-defects/research/literature-neighbors.md`；本轮不伪称重新读取全部全文。
5. 本轮实际读取 `experiments/afdm_inference_causal_20261002/FINDINGS.md` 和前述current source；旧candidate-admission由同代理撰写并保留上下文，未重复旧closure审查。

网络仅查询公开题名/公开数学方法，未向外部发送项目代码、数据或未发表论证。arXiv API和上述原文HTML成功取得；没有下载PDF或写外部缓存。

## 建议的有限研究顺序

1. 先做表示等价的prior pushforward与生产码相位自同构两个零接收调用检验；它们能快速排除假创新。
2. 再做已知x近碰撞的同自由度jet对照，确认改变的是可辨识坐标而非更多paths。
3. 对封存oracle做lifted prediction与rank谱诊断，检查上一轮已丢弃的pseudo-cross是否存在低维可保留对象。
4. 只有找到非退化效果和可合法闭合的消息，才报价同预算主推断验证；不能把这些数学检验作为性能结果。

## Caveats / Not Found

- 四个idea均无接收性能验证；文末仅完成方向4的编码代数准入检验。未修改代码/CSV/状态或执行remote工作。
- 没有证实native同delay压缩是生产失败主因，也没有从6个失败帧的分支混杂中作因果推断。
- Gaussian算子prior可能物理不合理，jet有效范围可能很窄，lifted推断可能仍指数/高阶昂贵，码相位自同构可能只有恒等元；这些是最便宜测试要先回答的具体问题。
- 精确rank/群恒等式不是首创性证据。当前优先级来自数学匹配和已有接口，不是文献全面查无结果。


## 经授权补充：生产 LDPC 相位自同构的实际代数检验

主会话授权最多30 CPU秒的单线程缓存矩阵运算。直接读取既有H/G，未调用建码函数、receiver、生成器或实验runner。通过uint8逐校验行XOR计算H Pθ G和Hcθ，另外穷举4个QPSK字母验证bit变换与复旋转一致。实际结果如下：

```json
{
  "cache_path": "experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz",
  "cache_sha256": "cbb1557dbbd9ac27bdaf27099ccca2d831943bd1a27d14e46faedf4e9fb9c052",
  "H_shape": [
    1026,
    2048
  ],
  "G_shape": [
    2048,
    1024
  ],
  "H_sha256": "54086fac997cfd06c10d748708826b9471f424fa206b6b6aed7102da360389e8",
  "G_sha256": "bfd4247263adedc9a095b87603c2a7a4c2f2e8cb83f7e78bad721c5b06eaa6af",
  "records": [
    {
      "rotation": "0",
      "hpg_nonzero": 0,
      "hpg_nonzero_rows": 0,
      "hc_nonzero": 0,
      "code_preserving": true
    },
    {
      "rotation": "pi/2",
      "hpg_nonzero": 362702,
      "hpg_nonzero_rows": 1026,
      "hc_nonzero": 354,
      "code_preserving": false
    },
    {
      "rotation": "pi",
      "hpg_nonzero": 0,
      "hpg_nonzero_rows": 0,
      "hc_nonzero": 0,
      "code_preserving": true
    },
    {
      "rotation": "3pi/2",
      "hpg_nonzero": 362702,
      "hpg_nonzero_rows": 1026,
      "hc_nonzero": 354,
      "code_preserving": false
    }
  ],
  "alphabet_mapping_checked": true,
  "arithmetic": "uint8 XOR reductions, no matrix BLAS, no code regeneration, no receiver",
  "cpu_seconds": 0.03556300000000001,
  "before": {
    "threadpoolctl": "3.7.0",
    "pools": [],
    "numpy_blas_name": "accelerate",
    "accelerate_current_thread_mode": 1
  },
  "after": {
    "threadpoolctl": "3.7.0",
    "pools": [],
    "numpy_blas_name": "accelerate",
    "accelerate_current_thread_mode": 1
  }
}
```

**结果改变方向4的可行范围：生产码保留180度全符号翻转，但不保留90/270度旋转。** 所以精确code-preserving群至少含{0,π}，此4元素QPSK相位族中的合法子群恰为C2；不能再使用无条件4相位等权quotient。pi/2与3pi/2的offset本身也违反部分parity，且交换I/Q后的生成空间不闭合。

180度作用b→b⊕1对应非零全1码字；在均匀信息比特先验下code prior不变，但译码器非均匀入站bit prior未必不变，须保留prior比。已知pilot使两个模式的似然权重不同：固定代表时log(L_0/L_pi)=4 Re(rᴴv)/sigma2。这个检查只证明编码集合与群作用的代数合法性，不证明实际后验有显著双模式或边缘化改善性能。下一步若做研究，应把方向4缩为两个共享data-product的符号模式，先用现有oracle/合法码先验检验其实际质量；不是增加两个完整重启。

## C2 条件模式的精确矩与非二次势：不做新的实验

固定一个商空间代表 q=(h0,d0)，令 s∈{−1,+1}、h=s h0、d=s d0。这里d0是含数据功率缩放的合法码字。上一节验证了生产码在全符号翻转下封闭；若码先验均匀、gain先验在h→−h下不变（圆对称Gaussian充分但并非必要），且q的两代表先验权重相等，则P(s=+1|q)=P(s=−1|q)=1/2。该条件不能套到任意非均匀decoder入站先验。

记v=H(h0)p、u=H(h0)d0、r=y−u。因为H对h线性，

H(s h0)(p+s d0)=s v+u，
||r−s v||²=||r||²+||v||²−2s Re(rᴴv)。

对proper噪声w~CN(0,σ²I)，定义a=2 Re(rᴴv)/σ²，则精确条件模式后验为

P(s|q,y)=exp(sa)/(2 cosh a)， κ=E[s|q,y]=tanh a。

由s²=1立即有

E[h|q,y]=κh0， E[d|q,y]=κd0，
E[h dᵀ|q,y]=h0 d0ᵀ，
E[h|q,y]E[d|q,y]ᵀ=κ²h0 d0ᵀ，
E[(h−E[h])(d−E[d])ᵀ|q,y]=(1−κ²)h0 d0ᵀ。

因此，丢失的**非共轭cross moment是一个精确rank≤1的模式相关项**。除退化零向量外，|κ|<1时rank为1；当模式被充分识别、|κ|→1时它消失。此项来自有限符号模式的相关性，不是独立Gaussian扰动的方差乘积。相应的共轭cross covariance是(1−κ²)h0 d0ᴴ，但物理双线性预测使用前面的转置版本。

精确条件信号均值为u+κv，而把gain/data均值相乘会给κ²u+κv，少掉(1−κ²)u。特别地κ=0时，两个参数边缘均值为零，但不变的data-product信号u仍保留；这不等于“什么都没估计出来”。仅来自s的条件信号协方差为(1−κ²)vvᴴ，也是rank≤1；不能把它混同为全部未知q所产生的信号协方差。

对s解析求和，得到商空间条件似然

p(y|q)=(πσ²)^(-N) exp[−(||r||²+||v||²)/σ²] cosh(a)。

因此忽略与q无关常数的负对数势为

Φ(q;y)=(||r||²+||v||²)/σ²−log cosh(a)。

这是一个**精确的非二次logcosh势**。其一阶相位响应是tanh(a)，二阶响应为sech²(a)=1−κ²；平均模式响应与上述cross moment由同一个归一化常数产生，不需要人为添加一个“补偿项”。数值实现应使用稳定logcosh，但本次没有实现或执行该算法。

若固定q的先验模式对数比为L_s=log[P(s=+1|q)/P(s=−1|q)]，则κ=tanh(a+L_s/2)，且上述cosh因子改为cosh(a+L_s/2)/cosh(L_s/2)。L_s必须来自当前因子分解里合法的入站信息；不能把同y已得到的模式后验再当独立模式先验。完整decoder prior可通过两个合法码字的prior比形成L_s，但这不自动建立整个循环的精确cavity性质。

**范围。** 这些式子仅在固定orbit q下精确；h0、d0及几何仍需推断/积分，不能冒充完整闭式receiver或整个posterior只有两个模式。对未知q混合后，多个orbit的rank1项可能积累成更高秩。生产有pilot时a由观测识别符号模式；有限|a|意味着该固定orbit仍有真实不确定性，而不是继续迭代就必然消失。更多局部迭代可能改善对q或其权重的近似，却不会为固定q与同一个y创造新信息；v=0时在等先验下本模式不可识别，κ恒为零。

群混合、相位ambiguity和logcosh边缘化不是新发明。主会话正在核对更直接的公开近邻（包括使用旋转不变Gaussian mixture处理phase ambiguity的arXiv:2001.03930）；本附录不把rank1模式公式或一阶几何导数单独称为论文创新。它们的作用是给出一个能跨过“均值相乘/单全局仿射”限制、同时可明确检验的最小数学对象。
