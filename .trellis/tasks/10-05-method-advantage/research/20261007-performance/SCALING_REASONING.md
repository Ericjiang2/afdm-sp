# Research: 固定观测预算的孔径／帧数标度与获取信息预算

- Query: N128/T2 与 N64/T4 在 NT=256、同每符号SNR及gain先验下，能否隔离一般列码与二次列码的孔径效应；优先推导当前AFDM的圆化QPSK相位信息预算、逐gain取正部的genie-Fano界，并保留通用unitary Gaussian-negentropy界作为较粗对照。
- Scope: internal，纯解析；不新增科学代码、不运行仿真/优化/seed搜索/SSH。
- Date: 2026-10-07
- Active task: `.trellis/tasks/10-05-method-advantage`
- Method: `formula-derivation`，按指定路径输出，不创建其默认根目录文件。

## Findings

### Target / Status

**COHERENT AFTER REFRAMING / EXTRA ASSUMPTION。** 固定 NT 是更直接的“有用样本如何分配到孔径与独立帧”的诊断，但不是孔径的单因素因果隔离。两种维度同时改变假设数、物理先验分辨率、随机码实现、筛选比例和有限gain网格的对称性。允许的结论是固定预算下完整已规定方法的比较，不能预言10pp、证明某种码必胜，或仅凭实验归因于渐近指数。

**更强的解析结论成立。** 当前整数格点AFDM在一个与标签无关的row-chirp去除+FFT后，只产生iid QPSK的逐坐标旋转与置换。以单坐标QPSK law的圆化Rician密度qρ为reference，可精确扣掉与标签无关的径向nonGaussian性：

`I(Θ;Y | H=h) = B d_phase(ρ²/σ²) − KL(Pmix,h || qρ^⊗B)`。

因而合法的较强风险界是**每个ρ先取Fano正部，再平均**：

`P_e ≥ 2∫_(.75)^(1.25) [1−(B d_phase(aρ²)+log2)/log M_N]_+ dρ`。

下文给出qρ的Bessel I0公式及可计算的一维／二维积分。**本轮不数值积分，强界是否为正、数值多大均尚未判定。** 本文“得到0”的结论仅针对先平均Gaussian粗预算再截断的较弱版本，不能转移到这个新界。

### Invariant Object / Assumptions / Notation

核心对象始终为完整观测law上的获取错误风险与标签信息量，而非仅最大歧义μ。

- B=NT=256为接收端保留的复样本数，噪声为独立proper complex Gaussian `CN(0,σ²)`；nominal `a=1/σ²=10^(5/10)=√10`。γ(h)=|h|²/σ²是条件实际SNR，不将隐藏ρ替换为1。
- N取64或128、T分别4或2；s=5、CP=N/4、帧间距L=5N/4；仅观察每帧N个useful samples，边界已知、单静态循环路径、guard足够。
- 每帧独立fresh iid QPSK，单位符号能量；**不是重复发送同一组未知QPSK symbols**。列码v固定已知且单位模。物理gain `H=ρexp(iφ)` 在整个B样本间共同，ρ~Uniform[.75,1.25]、φ~Uniform[0,2π)，并与标签、payload和noise独立。
- “同整数均匀prior”按完整quotient解释为 `Θ_N={(a_eff,l): a_eff∈Z_N,l∈Z_(N/4)}`，`a_eff=ν+sl mod N`，基数 `M_N=N²/4`。这是同一**归一化形式**的prior，不是两种N下完全相同的物理参数集合。
- 每个N使用固定129候选二次设计与单次随机码；不借本批性能选码。一般码存在性定理不自动认证这个单次random；129候选也不等于求得所有实c2中的最优者。
- 对数与互信息均用nats。`I_BPSK(γ)=I(B0;√γ B0+Z)`，其中B0为均匀±1，Z~N(0,1)。按此约定，单位能量QPSK的标量AWGN信息量为 `2 I_BPSK(γ)`。

### Derivation Strategy / Map

1. 从已核验的完整law二次困难pair/Bayes下界出发，代入T=B/N；保留“下界”而不换成实际风险。
2. 将一般码的annulus-net存在性上界按总维数B重写，显式留下M_N和μ_N。
3. 核查frame clock何时使T帧条件iid，以及固定48gain网格与N128的闭合性。
4. 先利用当前格点AFDM的monomial结构，圆化单坐标QPSK law；以相同径向分布的reference作KL分解，得到更小的phase-only信息预算。
5. 给decoder物理H，逐ρ应用Fano并取正部，再对ρ积分；提供可计算公式，但本轮不做积分。
6. 保留任意block-unitary调制均适用的Gaussian最大entropy界；只对其“先平均再截断”版本给出当前参数下的vacuity证明。

### 1. 固定 B 下二次障碍的正确读法

**已有命题。** 在上述圆对称共同gain、完整均匀quotient prior及C4 frame clock下，任意二次列码（包括随N优化的任意实c2）均满足

`R_quad^*(N,T) ≥ 1/4 exp{−T γbar [4K+4π²N/K²]}`, `1≤K<N`,

其中 `γbar=Eρ²/σ²=(49/48)/σ²`。这是gain已经正确边缘化后的Bayes平均风险下界；它没有1/M_N的稀释因子。依据为 `BAYES_SYMMETRY.md:77`、`:109` 的保持先验相位耦合与全部平移pair求和。

**精确代入。** T=B/N给出

`R_quad^*(N,B/N) ≥ 1/4 exp{−B γbar [4K/N+4π²/K²]}`。

取K为N^(1/3)阶，指数尺度为 `B N^(−2/3)`。因此标度项

`[2·128^(1/3)]/[4·64^(1/3)] = 2^(−2/3) ≈ .630`。

**解释而非排序定理。** 在相同B下，较大N使这个二次类错误下界在标度意义上更强；它不证明N128的真实错误率高于N64，也不证明random真实错误率保持不变。两个风险的下界不能决定两个风险的大小关系，有限N常数仍极保守。

若只看该保守表达的连续K最优值，`K_*=(2π²N)^(1/3)`，不是必须机械取floor(N^(1/3))；实际K须取允许整数。优化这个解析证明常数不涉及优化实验码，也不能使下界变成实际误差预测。

固定B且T≥1时N≤B，因此不能把本次两个可行点包装成“N→∞且B恒定”的渐近序列。这里是借已有尺度作有限预算诊断，不是观测到指数率。

### 2. 一般码上界：TN相同仍不等于难度相同

**由既有证明的直接扩展。** 令μ_N为所有非平凡允许移位的最大四阶ambiguity模。共同固定h后，T帧独立，uniform gain-pair affinity界为

`Aff(P_(θ,h0)^(T),P_(θ',h1)^(T)) ≤ exp[−c0 B(1−μ_N)]`。

不能直接把该上界平均后声称gain边缘law保留同一affinity界。按 `COMPOSITE_LATTICE_ESTIMATION.md:25` 的data-only finite-net论证，可以用总维数B构造annulus的B^(−2)-net，基数O(B⁴)。高概率能量事件上，B样本log likelihood的gain-Lipschitz常数为O(B)，真gain替代误差为O(1/B)。于是存在一个昂贵的data-only estimator满足

`sup_(θ,h) P(error) ≤ exp(−cE B) + C M_N B⁴ exp[C1/(2B)−c0 B(1−μ_N)]`。

常数只依赖固定gain/noise边界；结论仍可对h先验平均。选B-net只是令同B比较的nuisance分辨率一致；原单帧N-net中的N⁶因子不是必须照搬到每种T分配。

在B固定时：

- 主指数中的B相同，但μ_N未固定；单次随机码没有“μ一定更小”保证。
- M_128/M_64=4，union prefactor与标签entropy增加；即便其余条件相同，上界也不相同。
- 该存在性estimator使用随B精细化的annulus net；当前48点profile FULL和SCREEN128未被证明达到该上界。

所以可研究两种分配下的 `Δ_N=R_quad−R_random`，但 `Δ_128−Δ_64` 是完整实验配置的差异；保留当前网格时，不是纯粹码几何的识别量。

### 3. 控制了什么，仍混有什么

| 项目 | N64/T4 | N128/T2 | 含义 |
|---|---:|---:|---|
| useful complex samples B | 256 | 256 | 相同，条件期望接收能量Bρ²及平均值相同。 |
| 总useful+guard采样周期T·L | 320 | 320 | 仅当CP=N/4、同采样率时相同；本模型不观察guard。 |
| 完整标签数M_N | 1024 | 4096 | 增加2 bits，先验不是同一个有限标签集合。 |
| delay支持 | 0…15 | 0…31 | 同归一化delay范围，绝对sample-delay支持扩大。 |
| 整数CFO物理间隔 | Fs/64 | Fs/128 | 同Fs时分辨率加倍；ν标签的单位并不相同。 |
| SCREEN128保留比例 | 1/8 | 1/32 | 更激进的筛选，筛选风险可改变。 |
| FULL candidate数/数据集 | 1024 | 4096 | likelihood样本数B相同，FULL候选开销约多4倍，完整实现成本另有变换/模板项。 |
| 48点gain-grid law的Weyl闭合性 | 成立 | 不对所有平移成立 | 新算法近似混杂，见下。 |

T=4相对T=2增加的是在**同一已知码和共同channel下的独立payload帧**，不是同一符号的相干重复。N128改变单帧循环几何，也改变QPSK成分在一次unitary变换中的混合维度；固定样本数并不固定完整law的形状。

固定Fs及总320采样周期是时间预算对齐，但两种帧划分的useful/guard时间位置不同。当前静态channel、白noise模型允许这样比较；不能外推为时变channel下完全相同的观测条件。

若把N128的delay范围也锁为0…15，或只保留与N64相同的物理CFO格点，可减少某些混杂，但会改变full quotient prior、标签数和困难pair平移证明的适用性。这不是本报告授权的协议改动。

**129候选与单次random。** 二次障碍覆盖所有c2，因此当然覆盖129候选的选择；但观测到random胜出不能证明优于全二次类最优者。两种N的一次random realization不同，有限样本差还可能含码实例差异；不得为修正这个不确定性事后搜seed。

### 4. Frame clock与固定gain网格

物理每帧有额外因子 `exp(2πiνtL/N)`。当L=5N/4、ν整数时，该因子为 `exp(2πi·5νt/4)∈C4`，独立均匀QPSK可精确吸收它。因此N64/T4与N128/T2均保持固定共同h后的条件iid帧law，旧二次困难pair可用一个共同gain相位耦合。

若换为非C4 clock、非整数ν、已知pilots或相关/重复payload，时间相位可能提供额外信息；旧二次Bayes下界的T倍化须重新证明。**下节通用unitary信息预算则不要求clock为C4**：只要实际block变换仍unitary、payload仍iid，任何已知时钟因子可纳入该block变换。

48gain网格的相位为rπ/32、r=0…15，结合QPSK的π/2周期等价于全圆64点。N64的Weyl cocycle旋转2πq/64闭合；N128出现2πq/128，奇数q对应半个现网格步长，不闭合。故不能将完整law的对称性无条件转移到N128的有限grid FULL/SCREEN128，也不能保证其条件风险对所有标签相同。

“不闭合”本身不证明平均误差一定增加或一定减少；真实gain先验仍圆对称，具体网格误差需数据或另行证明。保留旧48grid是一个明确的算法选择，它使本比较属于实际完整方法的标度验证，而非已证明理想连续gain估计器的检验。

### 5. 优先结论：圆化QPSK的相位信息预算

#### 5.1 适用结构及真正的ancillary

在实际观测上施加与θ无关的row-chirp去除及unitary FFT，得到X。整数effective CFO `a_eff=ν+sl`、循环delay及单位模列码给

`X_(t,j)=h exp[i c_(t,j)(θ)] S_(t,j−a_eff mod N)+Z'_(t,j)`，

其中确定相位c包含列码相位、delay相位、row-chirp常数和实际frame-clock相位；Z'仍为iid proper Gaussian。若沿用h_eff记法，必须把其依θ的相位放回c中，从而这里始终条件于**物理h**。

固定θ,h后，各坐标独立，只是同一标量QPSK law的不同旋转。每个 `R_(t,j)=|X_(t,j)|` 都具有同一个Rician径向law，整组R的law也不依θ。因此R是标签的ancillary：固定ρ或未知ρ下均有 `I(Θ;R)=0`（相应条件版本亦成立）。R仍能提供ρ的信息，因而可以帮助相位证据的解释；“ancillary”不等于应从数据中丢弃R。

这是当前整数格点AFDM的额外结构，**不适用于任意不能同时化为逐坐标旋转/置换的unitary假设族**。后者仍用第7节Gaussian预算。非C4的frame-clock仍可放入c，故本节phase预算不要求C4 clock；C4是第1节二次重复帧下界所需的另一条件。

#### 5.2 圆化reference及Bessel密度（精确）

取QPSK `S∈{(±1±i)/√2}`，定义零物理相位的标量密度

`pρ(z)=(4πσ²)^(−1) Σ_s exp[−|z−ρs|²/σ²]`。

圆化reference为

`qρ(z)=(2π)^(−1) ∫_0^(2π) pρ(e^(iα)z)dα`

`= [1/(πσ²)] exp[−(|z|²+ρ²)/σ²] I0(2ρ|z|/σ²)`，

其中 `I0(κ)=(2π)^(−1)∫_0^(2π) exp(κcos u)du`。每个QPSK分量的中心模均为ρ，旋转平均后相同，故该式没有残余四分之一因子。

pρ和qρ有相同径向density

`f_R(r|ρ)=(2r/σ²) exp[−(r²+ρ²)/σ²] I0(2ρr/σ²)`, `r≥0`。

定义无量纲 `d_phase(γ)=KL(pρ||qρ)`，其中γ=ρ²/σ²；尺度变换说明它只依γ，不依ρ、σ分别的值。

#### 5.3 条件信息的精确KL分解

在X坐标取reference `Qρ=qρ^⊗B`。它对任意逐坐标旋转/置换不变。于是每个θ、每个物理h满足

`KL(P_(θ,h)||Qρ)=B d_phase(γ)`。

令 `Pmix,h=Σ_θ π(θ)P_(θ,h)`。标准KL混合恒等式直接给

`B d_phase(γ)=I(Θ;X|H=h)+KL(Pmix,h||Qρ)`。

X来自与θ无关的可逆unitary变换，因此 `I(Θ;X|h)=I(Θ;Y|h)`。这同时给精确分解和上界 `I(Θ;Y|H=h)≤B d_phase(γ)`，无需把条件独立性错误地延伸到θ或H边缘化之后。

圆化预算确实比Gaussian预算小。令 `gρ=CN(0,ρ²+σ²)`，因为log(qρ/gρ)只依半径、pρ与qρ径向law相同，

`d_Gauss(γ)=KL(pρ||gρ)=d_phase(γ)+KL(qρ||gρ)`。

第二项就是与标签无关的径向nonGaussian性。不能再让它计入可以区分标签的预算。特别地，通用Gaussian界即使完全vacuous，也不说明phase界vacuous。

#### 5.4 可计算的一维／二维形式（未数值积分）

写z=x+iy、r=|z|，则

`pρ(z)=[exp(−(r²+ρ²)/σ²)/(πσ²)] cosh(√2ρx/σ²) cosh(√2ρy/σ²)`。

因此二维公式为

`d_phase=∫_(R²) pρ(x+iy) {logcosh(√2ρx/σ²)+logcosh(√2ρy/σ²)−log I0(2ρr/σ²)} dxdy`。

也可用两个一维积分。令u=r/σ，归一化Rice密度

`f_γ(u)=2u exp[−(u²+γ)] I0(2√γ u)`, `u≥0`。

均匀连续相位恒包络输入 `ρexp(iA), A~Uniform[0,2π)` 的标量AWGN互信息为

`I_circle(γ)=2γ−∫_0^∞ f_γ(u) log I0(2√γ u)du`。

由 `h(qρ)−h(pρ)` 或相同conditional-noise entropy相减，

`d_phase(γ)=I_circle(γ)−2I_BPSK(γ)`

`=2γ−2I_BPSK(γ)−∫_0^∞ f_γ(u) log I0(2√γ u)du`。

`I_BPSK`的一维Gaussian期望见第7节。此处的I_circle是用于表达reference entropy的辅助量，不是声称真实payload改成了连续相位输入。

另一个便于看清径向条件化的极坐标形式：令κ=2ρr/σ²，QPSK相位φ_s∈{π/4,3π/4,5π/4,7π/4}，

`C_κ(φ)=(1/4)Σ_s exp[κcos(φ−φ_s)]`，

`g_κ(φ)=C_κ(φ)/(2π I0(κ))`，`d_angle(κ)=∫_0^(2π) g_κ(φ)log[2πg_κ(φ)]dφ`。

于是 `d_phase(γ)=∫_0^∞ f_R(r|ρ) d_angle(2ρr/σ²)dr`。这些形式均精确且d_phase≥0；γ=0时为0。本轮不执行数值积分，不凭小γ渐近式替代当前SNR区间。

### 6. 先逐gain取Fano正部，再积分

**Genie不会削弱下界的有效性。** 给decoder物理H=h后标签prior仍均匀，因为H与Θ独立。任何不使用H的估计器也属于允许使用H的估计器，因此对每个h的条件Fano下界可用于原问题。采用第5节预算得

`P_e(H=h) ≥ [1−(B d_phase(γ(h))+log2)/log M_N]_+`。

d_phase与物理φ无关，故最终较强界是

`P_e ≥ 2∫_(.75)^(1.25) [1−(B d_phase(aρ²)+log2)/log M_N]_+ dρ`。

这也可作为只揭示ρ的genie界：未知共同φ的条件互信息不大于再揭示φ后的信息。不得把共同H按帧重新抽样或独立边缘化。

取正部是凸操作，故

`E[ [1−(B d(H)+log2)/logM]_+ ] ≥ [1−(B E[d(H)]+log2)/logM]_+`。

因此即使高gain令先平均的界为0，也不能否定低gain区域贡献。正确评价本式必须逐ρ确定积分项，而不是先做E d。

本次M64=1024、M128=4096、B=256，积分项为正的准确条件分别为

- N64：`d_phase(aρ²)<log512/256≈.02437 nats/sample`；
- N128：`d_phase(aρ²)<log2048/256≈.02978 nats/sample`。

尚未判定哪些ρ满足该条件。历史按ρ分层错误的集中现象与“先条件化”的必要性一致，但不能把那些错误频率当作d_phase或本理论下界的值，也不构成本式数值认证。

该普适phase预算对当前所有单位模列码相同；码的区别仍在第5.3节的混合残余KL，而非标量d_phase。固定B及gain先验时，N只通过M进入这个Fano放松；M128较大使其逐ρ下界不弱于M64，但**下界的排序仍不是实际错误率的排序**，也不提供quad-vs-random差值。

**还可更强地条件化ancillary半径（精确、未计算）。** 既然Θ在给定H及整组R后仍均匀，各角度conditional law是g_κ的旋转，信息上界为 `Σ_(b=1)^B d_angle(2ρR_b/σ²)`。逐(H,R)取Fano正部后再平均，又不弱于上述仅按ρ条件化的界。这里R_b在给定ρ下为iid Rice。该表达展示了径向样本可作为解释相位可靠性的侧信息；本轮不将它扩成新的计算任务。

### 7. 较粗但更通用：任意unitary modulation的Gaussian预算

**命题条件。** 固定一个已知列码，把全部B个useful复样本堆叠。给定标签θ及共同**物理**gain h，写

`Y = h U_θ S + Z`，`S_j iid QPSK`，`Z~CN(0,σ²I_B)`，`U_θ^H U_θ=I_B`。

`U_θ`包含各帧unitary调制、循环delay、整数CFO和实际frame-clock相位；也允许其他已知unitary结构。U可依θ，不依未知payload或noise。block内不同frame的矩阵可不同。H与Θ独立。

**步骤1，恒等式。** 固定θ,h，unitary逆变换给hS+同分布白noise，复unitary变换的实Jacobian模为1。因此

`h_diff(Y | Θ=θ,H=h) = B [log(πeσ²)+2 I_BPSK(γ(h))]`。

QPSK两实坐标经相位旋转与噪声标准化各为 `√γ B0+Z_real`，这里没有额外的2或1/2 SNR因子。一种明确的标量表达为

`I_BPSK(γ)=log 2−E_(Z~N(0,1)) log[1+exp(−2γ−2√γ Z)]`。

**步骤2，entropy上界。** 每个θ都有均值0、协方差 `(ρ²+σ²)I_B`；混合θ后仍相同。Gaussian最大entropy给

`h_diff(Y | H=h) ≤ B log[πe(ρ²+σ²)]`。

减去步骤1得固定h版本

`I(Θ;Y | H=h) ≤ B J(γ(h))`,

`J(γ) := log(1+γ)−2 I_BPSK(γ) ≥ 0`。

**步骤3，更强的精确分解。** 令 `Q_h=CN(0,(ρ²+σ²)I_B)`、`P_(θ,h)`为条件观测law，`Pbar_h=Σ_θ π(θ)P_(θ,h)`。所有标签都有

`D(P_(θ,h) || Q_h)=B J(γ(h))`。

KL混合链式恒等式给

`B J(γ(h)) = I(Θ;Y | H=h) + D(Pbar_h || Q_h)`。

这对任意固定标签prior成立，不仅均匀prior。左边是由输入QPSK非Gaussian性、SNR和样本数决定的预算；右边留在整体混合law中的negentropy由码几何及标签混合决定。**同B、同SNR只固定预算，不固定用于区分标签的互信息。** 两者之差恰是非负的混合残余KL，不是一个可凭样本计数忽略的量。

校验特例：若把未知iid payload改为proper Gaussian，标量信息为log(1+γ)，J=0；所有unitary标签产生相同Gaussian观测law，I(Θ;Y|h)=0。已知pilots或重复/相关payload不满足本命题的iid未知QPSK条件，不能继续使用上式的标量entropy相加。

**步骤4，共同随机gain。** H与Θ独立意味着

`I(Θ;Y) ≤ I(Θ;Y,H)=I(Θ;Y|H) ≤ B E_H J(γ(H))`。

ρ在本协议是半径均匀，故 `E_H J = 2∫_(.75)^(1.25) J(aρ²)dρ`；没有额外ρ Jacobian。不能将未知共同h按每帧独立重新积分，也不能未经凸性证明就把该积分替换为J(Eγ)。

对physical h条件最直接。若改用 `h_eff=h exp(−πis l²/N)`，它形式上依θ；只有证明圆对称物理gain先验使h_eff与θ独立，才可照搬最后的独立性步骤。条件固定物理h的unitary推导不需要这个重参数化。

### 8. 仅“Gaussian预算先平均再截断”版本的vacuity检查

均匀M_N标签、任意估计器的平均错误P_e满足经典Fano放松式

`P_e ≥ [1−(I(Θ;Y)+log2)/log M_N]_+`

`≥ [1−(B E_H J(γ(H))+log2)/log M_N]_+`。

可另取信息上界与logM_N的最小值；这不挽救下述负值。N128相比N64有 `log M_128−log M_64=log4` 的标签需求，而相同B及gain先验给相同的普适预算。但这个必要条件不含具体码的μ，也不提供实际误差顺序。

**当前SNR5、B256下，本节这个先平均Gaussian预算的Fano界为0，可以纯解析判断，无需积分BPSK或采样。该论证不适用于第6节逐ρ正部界，也不适用于更小的phase预算。** 因为 `2I_BPSK(γ)≤log4`，

`E J(aρ²) ≥ E log(1+aρ²)−log4`。

令f(ρ)=log(1+aρ²)，则

`f''(ρ)=2a(1−aρ²)/(1+aρ²)² ≥ −a/4`。

以ρ=1作Taylor下界并用Eρ=1、Varρ=1/48，得到

`E f(ρ) ≥ log(1+a)−a/384`。

因此

`B E J ≥ 256[log((1+√10)/4)−√10/384] ≈ 8.07 nats`。

而较大的M128=4096也只有 `log M128−log2=log2048≈7.625 nats`。所以代入上述**上界预算**的Fano表达已经非正，两种N均只能得到0。这里用预算的下界只是证明“该预算足够大使Fano放松失效”，**不是证明真实互信息大于8.07**。

这个较粗预算仍是严谨的概念解释，但当前参数下不能定量解释约26%的错误率。第5—6节已经去除了径向nonGaussian性并避免过早平均，故其非平凡性必须单独评价；本轮尚未积分，不宣称该强界为0或为正。

### Remarks / Boundaries / Open Risks

- 本次可准确提出的科学问题是：固定B和明确算法近似下，码类别的实际风险差随“孔径／独立帧”分配如何变化。可以说它减少了样本量混杂，不能说它已经完全隔离了结构。
- 旧二次下界仍适用N128，但有限48grid的general-code实现不等于存在性定理的estimator。二者必须分别说明。
- 四个历史performance FAIL保持；最新optimized μ改善与本批random/optimized错误对照不支持继续凭μ预设获取收益。这里不搜更多seed、不调p、不改旧门。
- 任何后续实验需要自己的冻结协议/source admission；本报告不授权科学运行、新码设计或服务器工作。
- 无10pp预测、无BER/多径/连续CFO/guard-inclusive/时变channel外推。若改变Fs、CP规则、参数prior或payload重复方式，应重新检查表中控制项和相应定理。
- phase预算依赖可由标签无关变换化为逐坐标旋转/置换的结构；一般unitary族只能自动使用Gaussian预算。圆化reference仍使用真实固定ρ的genie条件，不把隐藏ρ泄露给实际估计器。

### Files Found / Code Patterns

- `research/20261007-performance/BAYES_SYMMETRY.md:31`：共同gain的正确T帧边缘law；`:77`：二次Bayes KL耦合；`:109`：无1/M稀释的平均风险下界；`:139`：有限phase-grid闭合边界。
- `research/20261006-continuous/QUADRATIC_BARRIER.md:23`：二次困难pair的显式KL上界与N^(1/3)阶。
- `research/20261006-continuous/COMPOSITE_LATTICE_ESTIMATION.md:8`：uniform gain-pair affinity；`:25`：gain-net data-only估计器与union上界。
- `experiments/afdm_acquisition_performance_20261007/core.py:21`：实际generator的frame clock `t*(N+N/4)+j`、共同physical gain和每臂unitary调制；`:36`：固定48gain网格；`:40`：完整T×N混合似然。
- `experiments/afdm_acquisition_screen128_20261007/core.py:17`：复用的完整调用入口、观测/已知码/已知noise接口及SCREEN128固定候选数。

路径以当前task为根时，前两类 `research/` 均位于 `.trellis/tasks/10-05-method-advantage/`。

### External References / Related Specs

未进行外部检索或新颖性主张。Gaussian最大entropy、KL混合链式分解、Fano和Bretagnolle–Huber均为经典工具；本报告给出本模型所需的条件与推导。沿用主会话提供的任务/服务器边界；仅读取当前问题涉及的理论与代码，不重新加载Trellis生命周期。

## Caveats / Not Found

- 没有科学运行或新性能结果，不能将本报告当N128协议或源码准入。
- 未证明固定random在N128具有更低实际风险，未证明129候选二次baseline达到全类最优，也未证明现48gain-grid达到存在性上界。
- 通用Gaussian上界及当前AFDM更强的圆化phase上界均已解析证明。只有“先平均Gaussian粗预算再截断”的Fano版本已证为0；逐ρ正部的phase-Fano尚未数值积分，不能转移该0结论。

## 附录 A：共同未知相位与低 SNR 常数的独立核验

### A.1 未知共同物理相位的精确分解

固定ρ，令Φ为整个B样本共同的物理gain相位，独立于Θ且圆周均匀；`Pmix_(Θ,Φ;ρ)`为同时混合两个变量后的实际X law，`Qρ=qρ^⊗B`。对每个θ、φ已有 `KL(P_(θ,φ,ρ)||Qρ)=B d_phase(γ)`。先用KL混合恒等式、再用互信息链式法则，精确得到

`I(Θ;X|ρ) = B d_phase(γ) − I(Φ;X|Θ,ρ) − KL(Pmix_(Θ,Φ;ρ)||Qρ)`。

**所提分解成立。** reference Qρ相当于各坐标独立圆化，只是计算参考；实际channel只有一个共同Φ，不能把实际相位积分替换为独立逐坐标积分。

给定θ，逆转已知unitary／旋转／置换后，观测等价于B个 `ρexp(iΦ)S_b+Z_b`。所以

`J_B(γ):=I(Φ;X|Θ,ρ)`

仅依B、γ及iid QPSK假设，在相同B和ρ时不依列码、N/T划分或已知θ对应的frame-clock相位。因此码对上式实际标签信息量的影响，全部留在最后的**标签与共同相位混合残余KL**；不能把码的效果解释为改变了标量d_phase或J_B。J_B不是B个独立相位的信息量，也不能未经证明写成B·J_1。

QPSK law只依Φ modulo π/2；因而这里J_B也等于该商相位的信息量，未知的四个扇区不另贡献信息。边界核验：B=1时，Φ积分后每个θ都给qρ，所以J_1=d_phase、混合残余KL=0、I(Θ;X|ρ)=0，符合单个未知公共相位可吸收一切标量旋转的事实。

由于J_B与残余KL均非负，第6节使用B d_phase的genie-Fano仍有效，但可能松；若另有可证明的J_B下界，可将预算进一步收紧为B d_phase−J_B。这里没有计算J_B，也没有把d_phase的低SNR阶数当成未知共同相位下真实标签信息的阶数。

### A.2 独立核验 d_phase(γ)=γ⁴/24+O(γ⁵)

取第5.4节的κ与角密度。标准Bessel Fourier展开及QPSK四重对称性给

`2πg_κ(φ)=1+2Σ_(m≥1) [I_(4m)(κ)/I0(κ)] cos[4m(φ−π/4)]`。

令右边减1为ηκ。小κ时 `I4(κ)/I0(κ)=κ⁴/384+O(κ⁶)`，其余首个谐波I8为O(κ⁸)。因均匀角度下Eηκ=0，且ηκ一致趋于0，

`d_angle(κ)=E_unif[(1+ηκ)log(1+ηκ)]`

`=(1/2)E_unif ηκ²+O(E_unif|ηκ|³)`

`=[I4(κ)/I0(κ)]²+O(κ¹²)=κ⁸/147456+O(κ¹⁰)`。

系数来自cos²的均值1/2及谐波前面的2，不能漏掉其中任意一个。代入κ=2√γ u，得到 `d_angle(2√γ u)=γ⁴u⁸/576+O(γ⁵u¹⁰)`，此式目前仅在κ小的范围一致有效。

**积分交换的控制。** 不在整个u半轴无条件逐项展开。取 `Rγ=γ^(−1/8)`，分为u≤Rγ与尾部：

- 内部有κ≤2γ^(3/8)→0，上述余项一致；Rice的十阶矩在0≤γ≤1时一致有界，故余项积分为O(γ⁵)。八阶矩精确为 `E_γ U⁸=24+96γ+72γ²+16γ³+γ⁴`。
- 尾部利用 `0≤d_angle(κ)≤κ`（角密度相对uniform的比值至多e^κ/I0(κ)≤e^κ）和 `f_γ(u)≤2u exp[−(u−√γ)²]≤C u exp(−u²/2)`。于是尾部至多为√γ乘Gaussian尾部多项式，在Rγ处为 `o(γ^m)` 对每个固定m均成立；截去的八阶矩尾部也一样。

因此

`d_phase(γ)=γ⁴(E_γ U⁸)/576+O(γ⁵)=γ⁴/24+O(γ⁵)`。

这独立确认了所提1/24常数，并补足了非一致角展开下的积分交换理由。

### A.3 与Gaussian预算 γ⁴/6 的一致性

实BPSK表示给 `I_BPSK(γ)=γ−E logcosh(γ+√γ Z)`，Z~N(0,1)。用

`logcosh x=x²/2−x⁴/12+x⁶/45−17x⁸/2520+O(x¹⁰)`

及Gaussian矩直接得到

`I_BPSK(γ)=γ/2−γ²/4+γ³/6−5γ⁴/24+O(γ⁵)`。

这里可以交换期望：logcosh的十阶实导数有界，Taylor余项被C|x|¹⁰控制，而 `E|γ+√γ Z|¹⁰=O(γ⁵)`。故

`d_Gauss(γ)=log(1+γ)−2I_BPSK(γ)=γ⁴/6+O(γ⁵)`。

结合精确分解 `d_Gauss=d_phase+KL(qρ||gρ)`，径向部分为

`KL(qρ||gρ)=γ⁴/8+O(γ⁵)`，

且 `1/24+1/8=1/6`，三个系数一致。在低SNR极限，phase预算的首项是Gaussian预算的四分之一；**这不是当前γ≈1.78…4.94区间的近似认证**。本附录没有执行任何数值积分、仿真或新科学代码。
