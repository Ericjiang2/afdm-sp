# R1 — SP-AFDM / TCOM 独立方向评审

2026-10-13。Caveman；独立于 Claude 结论，复用既有证据。**判断：保留问题，重写中心。D1+D3 当前仍是经验分析＋配置发现；未达到 Trans deliverable 5。最佳路线：有限计算下、逐帧可靠性约束的可预测负载设计。D2 暂为诊断现象；Jensen 尚不能升格 lemma。**

标签：**[F]** 文件/原文事实；**[D]** 本轮推导，条件写明；**[I]** 证据推断；**[S]** 候选假设/建议，未验证。分数评概念，实验另列。无 SSH、仿真、脚本执行、git、HTML；仅写本文件。读 Trellis-start 后按本轮只读边界手动读 workflow、STATE、指定 task；未运行含 git 的 bootstrap。未改变任务状态。

引用缩写，均为项目根相对路径：

| 缩写 | 文件 |
|---|---|
| BR | `.trellis/tasks/10-08-doppler-cluster/research/codex-direction-brief-20261013.md` |
| POS | 同目录 `c1-prelim-positioning.md` |
| DIR | 同目录 `c1-direction-review-20261010.md` |
| SC | 同目录 `c1-scalar-closure.md` |
| R1 | 同目录 `c1-round1-loop-theory.md` |
| J | 同目录 `c1-joint-fp-theory.md` |
| R2 | 同目录 `c1-round2-own-symbol-theory.md` |
| IB | 同目录 `c1-inner-budget.md` |
| OLD | `.trellis/tasks/10-05-method-advantage/research/20261009-c1-review/REVIEW.md` |
| FT | 同目录 `CODEX_JOINT_FINITE_TIME_CLOSURE.md` |
| RT | `experiments/headroom_ladder_20261008/out/c1rt/analysis/rt.md`，及 `rt.json` |
| SG | `experiments/headroom_ladder_20261008/out/c1sg/analysis/sg.md`，及 `sg.json` |
| IB2 | `experiments/headroom_ladder_20261008/out/c1ib2/analysis/ib2.md` |
| DRV | `experiments/headroom_ladder_20261008/driver_c1.py` |
| SGD | 同目录 `driver_c1sg.py` |
| SGA | 同目录 `c1sg_analyze.py` |
| C09/C10/CX | `research-assets/res-20261009-01.md` / `res-20261010-01.md` / `res-20261010-02.md` |

已打开上述源码、Markdown、RT/SG JSON；另读 STATE 顶部/历史边界、Trans PRD、lit-v3/distinction-v3/ideation-v3、c1-codex 两份复核、指定历史资产卡和 index。部分长文件采用相关章节读取。**未取远端 raw jsonl、未重算 bootstrap**；数值核验层级＝本地保存汇总＋分析代码口径，非独立原始复算。CCF 仅借 rubric/calibration、概念分解、多视角、divergence/coherence、最小判别证据；未执行完整工作流、未冒称专家共识。

## 1. Verify

### 1.1 数字核对

| 项 | 核对结果 [F] | 修正/边界 |
|---|---|---|
| 物理与接收机 | DRV:62–74：K=8L，distinct delays 0..100，1+Poisson(3)，ν=2cosθ，期望能量1、不逐帧归一化；flat τ=1/K，genie delays | K 是表示负载。不是路径数、真实随机秩或容量参数。 |
| X1 P1 | RT:28–31/67–70：1.386 [1.240,1.567]、1.174 [1.105,1.227]；1.250 [1.174,1.338]、1.082 [1.014,1.144]；4/4 PASS | BR/CX 数字正确。P1 比较两个端点；不证明所有 ρ 上严格单调。6.5 dB R2 的 g(.5)=1.220 > g(.3)=1.136，RT:19–26。 |
| X1 argmax | RT:35–38/74–77：R1 .2→.1、.3→.2；R2–R4 不变 | 仅离散网格。6.5 dB R1 T40：116.2 vs115.2，CI 大量重叠，RT:11/15；“最优值显著下移”过称。bootstrap 的 ≤ 频率允许相等，非严格下移概率。 |
| 低 pilot 替代 | RT:50–61：8 dB，ρ.15/T40 R4=237.9，ρ.3/T20=234.4，ρ.3/T40=269.3 | “每轮点估计匹配/超出”正确；R4 两 CI 重叠。不是已证非劣，也不是节约总发射能量；ρ只是能量重分配，T翻倍。 |
| X2 | SG:3–4：8000行；P4=21/40 FAIL、P5=40/40 PASS；SG:48最大 r1=1.288；SG:37唯一 r2>1=1.003 | BR 数字正确。39/40 是点估计低于1；未报告所有 r2 的置信区间。 |
| “69% bound” | SG:52、SGA:79–81：frac=(r1−1)/(bound−1)=.6855 | 69% 指**预测增量**，不是 r1/bound；该格 r1/bound≈.925。应改措辞。 |
| cliff 处 GLS 均输 | SG:20/45：6.5 dB ρ.3 K128，r1=1.013 [1.003,1.023]；8 dB 同格1.067 [1.055,1.078]；RT:19/58首轮 Kc≈74/137 | “cliff loads r1=.88–.99”不是全格定律。K/S约.35–.65仅事后交叉经验，依ρ/SNR/谱改变。 |
| 行数/日期 | CX:13新X1=16800；RT:5读31200；分析源码 `c1rt_analyze.py`:75合并REP＋RT，14400＋16800=31200；RT JSON seed20261012，SG JSON seed20261013 | 行数不冲突。运行标2026-10-10；本地分析种子日期较晚。种子不能证明运行/冻结时间；若声称分析版本跑前冻结，须对应manifest/收据，本轮未认证。 |
| IB2长轮 | IB2:96/98：180.1→213.6，1.186 [1.153,1.221] | 正确。T50/T40的CI含1＝未检出差异，非数学收敛证明；饱和检验只6.5 dB ρ.3，不能写所有工况T30–40收敛。 |
| 55%计算量 | IB2:119/129：R4T30=.99s、Kc185.4；R10T20=1.80s、Kc180.1 | 点估计正确；不是同一K、同一目标FER的完整成本非劣检验。成本平均不同L，10帧/格参考；不是对调优公开基线的非平凡省算。CX/C10已承认。 |
| “从120更新起深内层赢” | IB2“Equal inner-update budget”：3×40 vs6×20=.995 [.982,1.008]；4×40 vs8×20=1.052 [1.034,1.080] | 对T40比较，明确优势从160开始；120时T30的配置更优，不能混成同一规律。 |
| WARM | SC:98–99/134–141：只替换首轮均值为真H的DPSS投影；FULL vs WARM多数相近，L24/R2有p=.008、8/0差异 | 不是真实完整H oracle、不替换gain variance/后续refit。非显著不等于等价；仅支持该注入槽弱敏感。 |
| 首轮盲测 | R1:224–230：20新格max ΔI=.042；低SNR组ln K误差−.247，门限.25；若用I交叉为−.276 | BR总体正确。预测用每新格自己的A3效率η；不能写“仅输入SNR/ρ/K，零新receiver校准”。 |
| mean map | SC:144–155：6/6；SC“A5 outcome”：R7–R10失败，open帧译出仅29–49%，closed 0/459 | 短轮合成有价值。标量MI不具普适充分性；逐帧genie map也未充分预测真实可达轨迹。 |

### 1.2 需撤回/收窄的关键句

- **V01 [F/I] “optimally whitened start不移动cliff”未测。** SGD:4–7/116–121/147–155：G/A只旁路计算，返回原ch；CX:48–49明确X2不测FER。CX:42–44却声称完美/最优白化都不移cliff。只有WARM的特定均值注入与MSE诊断，推不出所有refiner上界。
- **V02 [D] “genie GLS最优”错误范围。** SGD:91–98为带固定flat prior的ridge-GLS；C用真H，但先验非真条件先验，第二轮v来自自身译码器。不是非线性MMSE，不是完整SP似然，不是全receiver oracle。详§2.4–2.5。
- **V03 [D] G(a)不是当前模型普适bound。** POS:19–24把独立/均匀设计近似写成上界；pilot与H谱对齐、参数依赖C、ridge条件风险都未处理。P5通过只能说40格未超过参考曲线；输的格自动容易通过。
- **V04 [D] Jensen缺必要权重。** CX:38–41/POS:54–55需E为pilot加权谱均值；SGD使用标量总功率。不能推出“除h外所有方向信息增加”或ridge偏差主导。
- **V05 [D/F] “universal MI threshold”应写固定码＋decoder＋近校准LLR族经验闭合。** SC:121–127自己记录其他prior臂门限.49–.56；IB:31–33和IB2:271–327有logloss下降而FER改善。1−logloss不自动等于MI，见§2.6。
- **V06 [F] “κ≈.7w机理”已被否定。** R1:235–258、J:141–149、R2:95–119。括号命中不把端点升成定理。J12支持相关结构重要；不支持一个标量divergence解释全部量级/ρ趋势。
- **V07 [F/I] 历史资产不可拼成C1一般主张。** STATE“历史已接受主张”；`res-20260727-01`“Supported conclusion”：白化coded BER增量分离，但FER平移仅.03–.06dB、CI含0；学习≈0及部署归因限历史链。`res-20260914-01`“影响清单”限定G0；C1为不同物理生成器/DPSS接收机。旧support scorer收益与新refit损失并不矛盾，也不相互证明。
- **V08 [F] 旧结论有时序滞后。** research-assets/index的C09入口仍写V2/V3待跑；STATE顶部“下一步V1/V2/V3是否运行”与同段已报结果冲突。DIR:99–117纠正过“预算＝配置”；BR v2不能把同一材料重新包装成已获Trans贡献。

## 2. First principles + math

### 2.1 先分物理、表示、算法边界

**[D]** 写物理归一化：a=1−ρ，n=σ²；x=p+d，‖p‖²=Nρ，Eddᴴ=aI；H(h)=Σh_jB_j，y=H(h)x+w。A(z)=[B₁z,…,B_Kz]。有限BEM加r_mis，不默认为0。

- 已知d时：y=A(x)h+w。无先验线性可辨识要求rank A(x)=K≤N；rank、条件数、mode能量比K更直接。K<N仅必要几何条件，不保证可靠。
- 未知d为**离散码字**，不是N个自由复连续参数。不能用“h有K、d有N，K+N>N”判不可识别。码约束、非Gaussian统计、pilot破歧义共同供信息。
- 增T/R不会增加N或发射训练能量；只更有效提取同一y中的信息。由T改变的Kc必是**算法/有限调度边界**，不能直接叫物理容量边界。
- K=8L随表示选择变；有限ray生成器的参数/DPSS协方差有效秩不等于8L。物理Doppler宽度与截断容限应决定阶数，不能把人为冗余等同必付物理税。[F] DRV:62–74；OLD§3/§C5。

**[D，信息恒等式]** 令消息B与h独立，pilot已知：

\[
I(B;y\mid p)=I(B;y\mid h,p)-I(B;h\mid y,p).
\tag{1}
\]

右项第二项＝观测后仍未解开的channel–data耦合。是receiver无关的信息损失；不是K的固定罚款。迭代无新观测，不能增加左侧；能提高提取的信息与decoder匹配。

QPSK码率r_c，消息熵2Nr_c。FER=P_e时，Fano必要条件：

\[
I(B;y\mid p)\ge(1-P_e)2Nr_c-h_2(P_e).
\tag{2}
\]

用Pe=.5得不到sharp Kc律；只给宽松必要条件。高SNR“每channel参数消耗一个复观测”的维数直觉可作特定非相干模型渐近起点；**本SP-LTV/有限码系统尚无通用prelog定理**。

**[D，设计信息记账]** 固定独立噪声线性模型，J=AᴴC⁻¹A，C_h为真先验。λ_j= eig(C_h¹ᐟ² J C_h¹ᐟ²)；Gaussian时：

\[
I(h;y)=\sum_j\log(1+\lambda_j),\quad
d_{\rm learned}=\sum_j\frac{\lambda_j}{1+\lambda_j},\quad
C_e=(C_h^{-1}+J)^{-1}.
\tag{3}
\]

物理MSE=tr(WC_e)，W_ij=tr(B_iᴴB_j)/N。flat、W=I、等Gram时λ_j=S/K，S=Nρ/(n+a)：**每mode有效训练SNR=S/K**。不同谱/先验→相同K/S亦可有不同风险；d_learned是已学模式数，不能单独替代未学能量tr(WC_e)。当前C(h)参数相关，式(3)仅独立Gaussian surrogate，不是真SP posterior。

### 2.2 Claude scalar Kc：代数对，连接假设不足

**[D]** 若A_pᴴA_p=NρI、data interference白且独立、W=I、unit channel energy，pilot LS风险：

\[
e_{\rm LS}=\frac{K(n+a)}{N\rho}.
\]

再假定独立加性channel error＋单位有用信号，γ=a/(n+e)。I_QPSK按**每coded bit**，γ_*取AWGN码曲线，则

\[
K_{c,\rm LS}=N\rho\frac{a/\gamma_*-n}{n+a}.
\tag{4}
\]

要求a>γ_*n、ρ>0，且e足够小/上述link成立。γ_*=1.312是该码曲线等效点，不是物理常数。[F] POS:10–16；本轮未重新数值积分AWGN曲线。

**[D]** 实际flat ridge：e=k(n+a)/[ρ+k(n+a)]，k=K/N。两种detector link不能混：

1. 仍用γ=a/(n+e)：b=a/γ_*−n，0<b<1，K_c=Nρb/[(1−b)(n+a)]。
2. 若真满足LMMSE正交分解，useful energy=a(1−e)，γ=a(1−e)/(n+e)：

\[
b'=\frac{a-\gamma_*n}{a+\gamma_*},\qquad
K_c=\frac{N\rho(a-\gamma_*n)}{\gamma_*(1+n)(n+a)}.
\tag{5}
\]

式(5)相对式(4)恰差1/(1+n)；ridge改善e与useful shrinkage同时发生。引入η时γ_*→γ_*/η。**不是“补ridge必增加Kc”**。当前joint输出不保证该正交性；R1 V1已失败。两式都不能替代20/40步joint动力学。

**[D]** 式(4)连续ρ最优：

\[
\rho_* =1+n-\sqrt{(1+\gamma_*)n(1+n)}
\tag{6}
\]

再裁到可行区间。约.43/.51/.58，匹配Claude算术；不匹配实测early-round optimum≤.3。[I] 说明pilot-only+independent-error surrogate缺自生data信息与相关性；不是直接否定SP设计问题。

### 2.3 Data-aided law：何时data等于training

**[D]** m为d的校准条件均值；e_d=d−m，E[e_dmᴴ]=0；normalized v=E‖e_d‖²/(Na)。还需pilot/soft-data平均cross为0，则E‖p+m‖²/N=ρ+a(1−v)=t，residual surrogate c=n+av。

\[
e_{\rm LS}(v)=\frac{K(n+av)}{Nt},\qquad
e_{\rm ridge}(v)=\frac{k(n+av)}{t+k(n+av)}.
\tag{7}
\]

固定v、使用式(4)类型link：

\[
k_c(v)=\frac{[1-av](a/\gamma_*-n)}{n+av}.
\tag{8}
\]

这里1−av=t，a=1−ρ。固定v>0，令a_*=(√[n(1+n)(1+γ_*v)]−n)/v，ρ_*=1−a_*，裁到[0,1]；a_*随v增大而下降，故v↓→ρ_*↓；v→0趋ρ_*=0，表示完美data全部可用。

**重要条件：v不是接收机输出的任意“variance”。** 一般

\[
a=r+e+2\Re z,\quad r=E|m|^2,\ e=E|d-m|^2,\ z=E[(d-m)m^*].
\tag{9}
\]

非校准时r≠a(1−v)。m(y)与w/h都相关，A(p+m)也随机；不能直接取C=H diag(v)Hᴴ+nI并宣布真实条件residual covariance。条件E[wwᴴ|m]、cross项、非零conditional mean均可能改变。

**[F]** SC:89–97：零SP scalar closure失配1.55–3.03倍；J:174–195/R2:95–119：同true MSE，own/independent反馈误差结构不同，Gram也差。**[I]** 式(8)支持方向直觉，不预测T→v，不预测R4 optimum。T40不是新训练能量，只改变对data信息的可用程度；“导频与计算可替代”须限定可靠性、工作区、预算。

### 2.4 G(a)：精确积分、条件参考，当前非普适上界

避免a重名，令α=n/v_b，Z~Exp(1)，c=v_bZ+n。则

\[
E[c]=v_b+n,\quad E[1/c]=v_b^{-1}e^\alpha E_1(\alpha),
\]
\[
G(\alpha)=E[c]E[1/c]=(1+\alpha)e^\alpha E_1(\alpha)\ge1.
\tag{10}
\]

**[D，适用模型]** 多观测、constant-modulus regression，设计不与c对齐；等Gram且weighted Gram集中成标量。OLS每mode风险≈E[c]/(Nρ)，GLS≈1/(NρE[1/c])，比值为G。noise大时G→1；α→0时log发散。**完全separable方阵N=K、A可逆时，unregularized GLS与LS同为A⁻¹y，gain=1**；“separable LS”须定义，不能混两种极限。

若额外matched isotropic prior、J_W=SI、J_G≈SGI，则Bayes ridge风险比：

\[
\frac{e_W}{e_G}=\frac{K+SG}{K+S}.
\tag{11}
\]

固定tr J_G=KSG时，tr(KI+J_G)⁻¹≥K/(K+SG)，由convexity给等谱GLS风险下界。**只有white风险也取同一matched surrogate、trace固定时，式(11)才可叫gain上界。** 当前SP：J_G trace与pilot/H对齐；C依h；true prior非flat；round2 own m/v相关。cross-delay项只能在这些额外条件下用Jensen；不能推出当前universal bound。

Rayleigh |H_f|²亦需LTI/DFT对角模型或独立渐近谱近似；LTV H的singular values不是默认i.i.d. Exp。P5不认证这些条件。[F] POS:19–24；SGD:9–16/136–153；SGA:5–9/40–46。

### 2.5 Jensen修正＋更强风险记账

**[D，固定h，round1]** SVD H=U diag(s_i)Vᴴ；u=h/‖h‖。A_pu=Hp/‖h‖。v_bI data covariance下，沿u的mean-model precision：

\[
j_G=\frac1{\|h\|^2}\sum_iw_i\frac{s_i^2}{v_bs_i^2+n},\quad w_i=|(V^Hp)_i|^2.
\tag{12}
\]

φ(z)=z/(v_bz+n)凹。W_p=Σw_i，E_p=Σw_i s_i²/W_p。Jensen只给

\[
j_G\le\frac{W_p}{\|h\|^2}\frac{E_p}{v_bE_p+n}.
\tag{13}
\]

white precision若分母用v_bE+n，则需**E=E_p**才能等于右侧。receiver使用E=1或Wt使用tr HHᴴ/N；一般不是pilot加权E_p。

反例：H=diag(1,3)、p=(1,0)ᵀ、v_b=n=1、E=5。省公共‖h‖⁻²，j_G=1/2，j_W=1/6；**GLS沿h信息反而更高**。随机isotropic pilot独立于H时，对pilot平均可令E_p→trace均值；ZC确定pilot＋structured H不自动满足。

即使式(13)适用，也只比较一个Rayleigh商；不能推出正交方向全部增加、不能推出MSE/FER次序。ΔJ一般非PSD；未知orthogonal参数还引入Schur损失：

\[
u^H(KI+J)^{-1}u=
\left[K+j_\parallel-j_\times^H(KI+J_\perp)^{-1}j_\times\right]^{-1}.
\tag{14}
\]

方向耦合与特征向量同样重要；仅j_parallel不足。

**[D，精确conditional ridge风险；比Jensen强]** 固定h、pilot A，E[e|h]=0、Cov(e|h)=C(h)，暂忽略BEM misfit。Q=AᴴC⁻¹A+KI，J=AᴴC⁻¹A，ĥ_G=Q⁻¹AᴴC⁻¹y：

\[
R_G(h)=\|KQ^{-1}h\|^2+\operatorname{tr}(Q^{-1}JQ^{-1}).
\tag{15}
\]

有物理metric W时分别改为biasᴴWbias与tr(WQ⁻¹JQ⁻¹)。white Q_W=AᴴA/c̄+KI，L_W=Q_W⁻¹Aᴴ/c̄：

\[
R_W(h)=\|KQ_W^{-1}h\|^2+\operatorname{tr}(L_WC(h)L_W^H).
\tag{16}
\]

因此**GLS胜负＝偏差变化＋真实噪声路径方差变化**；高load有ridge偏差可能，方向/符号需算，不凭口号。無ridge且满列秩、正确C：Gauss–Markov使GLS在线性无偏族不劣。matched prior＋C独立h时：Bayes LMMSE亦不劣任何固定线性white估计。X2输说明这些“最优”前提不能套；未证明信息不足或white全局更优。

第二轮A/m与w相关，式(15)需conditional mean和cross项，不能直接复用round1。检验Jensen假说最小对象：保存每帧bias、noise、misfit及cross；判断ΔR由哪项承载。ρ/K趋势只作结果，不先规定归因。[S，未运行]

**[D，SP covariance本身携带信息]** 若把data近似proper Gaussian，y|h~CN(A_ph,C(h))。实参数θ的log-likelihood score：

\[
\partial_i\ell=2\Re[\mu_i^HC^{-1}r]
+r^HC^{-1}C_iC^{-1}r-\operatorname{tr}(C^{-1}C_i),
\tag{17}
\]

Gaussian Fisher：F_ij=2Re(μ_iᴴC⁻¹μ_j)+tr(C⁻¹C_iC⁻¹C_j)。X2冻结真C再做ridge，仅使用mean score；**没有使用covariance score**。即使pilot mean信息沿h降低，总channel信息仍可能来自HHᴴ。第二项是经典Gaussian likelihood工具；不是本项目已证新算法，QPSK真实边缘似然也非Gaussian。

另一个“statistic gap”边界：C已知且与h独立Gaussian线性族，充分统计为AᴴC⁻¹y；LS压缩Aᴴy在K<N且coloured C时可能损失。若LS变换可逆，或网络仍拿raw y，则无这种数据处理损失。参数依赖C时连固定GLS statistic也未必充分。**不能从LS标签断言Transformer输入信息不足。**

### 2.6 Cliff应由什么预测，最优(ρ,R,T)应求什么

**[D]** b∈{−1,+1} uniform，LLR=L，q_L(b)=logistic(bL)：

\[
I_{\rm ll}=1-E\log_2(1+e^{-bL})
=I(b;L)-E D_{\rm KL}(P(b|L)\|q_L).
\tag{18}
\]

所以“MI=.577”含calibration penalty。可报告I_GMI=max_{s≥0}I_ll(sL)，但scale在独立校准集冻结；不是逐格用truth调到最好再伪称deployment。相同平均I也可有不同错误相关、trapping set、逐帧尾部；固定码长threshold是经验decoder接口，不是iff定理。

**[D，finite-time局部模型]** 状态误差e_{t+1}=A_te_t+B_tξ，同一观测扰动ξ反复用：

\[
e_T=P_{T,0}e_0+\sum_{t=0}^{T-1}P_{T,t+1}B_t\xi.
\tag{19}
\]

平方包含同源cross；trace divergence或一个MSE不能恢复这些项。常系数scalar时e_T=c^Te₀+b(1−c^T)/(1−c)ξ；只有实c、驱动能量=e_ind、T足够大等额外条件才得(1−c)⁻²。FT J20–J24已给non-normal反例/相关矩；本轮沿用，不当新发现。

**[I] 最小有意义的预测坐标，不是K单数：**

1. 几何/能量：C_h、A_p/soft Gram谱、BEM residual、realised channel energy；K/N只是索引。
2. 算法：有限T响应＋至少一个有符号own-error/noise或belief-history量；不能以divergence替换全部相关结构。
3. 码接口：LLR calibration与逐帧输出分布；真实decoder状态可达性。

**[S] 建议center的可证伪对象**：给定接收机族，预测逐帧/分层条件分布及成功概率，而非仅mean Φ。

\[
\widehat P_e(K;\rho,R,\{T_r\},r_c,N)
=E_f\left[\widehat{P}(\text{fail}\mid\mathcal Z_{f,R})\right],
\tag{20}
\]

Z由可用谱、calibration、真实belief轨迹摘要构成；不把genie h/true bits放deployment输入。若暂仍用sharp码阈值，应用Pr(I_{f,R}<I_*)，不是1{E I_{f,R}<I_*}。mean map已在A5失效；可达状态校准比更多Gaussian injection格更关键。

优化必须带应用货币：

\[
\min_{\rho,R,\{T_r\}} C_{\rm full}\quad
\text{s.t. }\widehat P_e\le\delta,
\tag{21}
\]

或预算B下max goodput≈2r_c N(1−P_e)/(N+N_CPP)。ρ不直接乘1−ρ作频谱效率：SP仍在全部data位置发符号，但改data SNR；学习/CSI history成本另算。发送能量、码率、CPP、support acquisition、LDPC早停/内层全部计入。**FER=.5的Kc是诊断货币；实用配置须指定δ，例如.1/.01及deadline。** 无cliff之外观测，不能宣称高可靠优势。

## 3. Innovation map

**[I] L1>L2>L3是用户排序，不是TCOM形式门槛。** 等级×practicality同时判断。新问题须改变观测/约束/评价对象；旧问题重命名“load cliff”最多L1-lite。成熟L3机制＋实用大收益可胜空泛L1。

### 3.1 公开近邻，覆盖诚实

本轮定向web检索SP/EXIT/scheduling及Transformer receiver；读决定性原文相关部分。**整体partial，非穷尽查新。** 无声称“没人做”。

| ID / 原文 | 已有内容、与本项目差别 | 覆盖 |
|---|---|---|
| W1 [Liang–Rave–Fettweis ICC2006](https://www.vodafone-chair.org/pbls/legacy/t-j-liang/Iterative_Joint_Channel_Estimation_and_Decoding_Using_Superimposed_Pilots_in_OFDM-WLAN.pdf)，III/IV；[IEEE年份](https://ieeexplore.ieee.org/document/4024670/) | SP CE+decoding、LS/MMSE误差、density evolution、ρ/包长优化已存在。新差别须是structured rich-LTV、有限计算与真实反馈尾部的迁移预测；不是首创training law/EXIT/power tradeoff。 | searched；相关原文 |
| W2 [Zheng et al. SP-AFDM](https://arxiv.org/html/2404.10232)，III/Appendix C | AFDM SP LMMSE、covariance、迭代消除已有。K-load、编码有限步联合过程可增量；公式反解本身弱。 | searched |
| W3 [Benzine et al.](https://arxiv.org/html/2504.13762v2)，IV/V | clustered/off-grid DPSS、已知support CE、阶数误差/代价已有。当前SP自生反馈不同；DPSS应用不算新模型。 | searched相关段；证明未全审 |
| W4 [Kanazawa et al. SP-OTFS](https://arxiv.org/html/2501.15935v3)，IV-C/D | 已区分uncoded/coded阶段、切换迭代数、精度–复杂度权衡。使D3“第一次内外预算协同”不可主张。并非直接否定C1特定有限预算规律。 | searched相关段 |
| W5 [Huang–Guo–Zhang–Zakharov，MP SP-OTFS](https://arxiv.org/html/2309.08177)，III-C/IV | SP doubly-selective GCE-BEM joint message passing、pilot频域能量集中、SINR选择ρ、runtime分析已有。新pilot/loop设计须机制级比较；仅减ρ不新。 | searched相关段；作者由原文header核对 |
| W6 [Cui–Tellambura SP-OFDM](https://onlinelibrary.wiley.com/doi/10.1002/ett.1461) | publisher abstract：Taylor/Gaussian近似ML、MMSE、复杂度、CRB。式(17)路线有直接经典谱系。具体covariance-score实现/假设未读全文。 | partial，abstract |
| W7 [PD-CEViT，ComSoc目录](https://www.comsoc.org/system/files/2025-08/publications_contents_digest_2025_jun.pdf)，p9 | TCOM73(6):4363–4377，2025；题名明确pilot pattern design＋CE。非所有Transformer工作只LS refinement。DOI10.1109/TCOMM.2024.3502687未成功打开原文；不判其内部实现。 | partial，官方metadata |
| W8 [Comm-Transformer，ComSoc目录](https://www.comsoc.org/system/files/2024-05/Publications_Contents_Digest_2024_Apr.pdf)，p12 | TCOM72(4):2014–2026，2024；DOI10.1109/TCOMM.2023.3343787。仅确认venue/题名，不把二手abstract当原文架构审计。 | partial，官方metadata |
| W9 [Reducing Pilots with PFM](https://arxiv.org/html/2512.15562v1)，III/IV；[IEEE记录](https://ieeexplore.ieee.org/abstract/document/11543378) | TCOM2026记录可查；原文用historical CSI predictive prior＋pilot ViT融合，评OOD、BER、ablation/latency。它增加侧信息；WARM单槽测试不能排除。 | searched相关method/evaluation；不是复现实验 |
| W10 [Cross-Attention Transformer joint decoder](https://arxiv.org/html/2602.04728v1)，III-D/IV | **预印本**，raw多AP网格→LLR→LDPC，以bit metric训练；直接反例“Transformer只做LS后处理”。不是TCOM已发表证明，也不属于同SP-SISO公平数字对比。 | searched |

### 3.2 每候选定位

| 候选 | 创新等级 | practicality / TCOM含义 |
|---|---|---|
| Claude D1当前：Kc＋measured Φ | 旧SP可行性问题的新负载切片；L1-lite/L3 analysis | 有诊断用途。若每场景重测map，设计价值有限；不是物理容量界。 |
| Claude D2当前：white→ridge-GLS | L3经典估计迁移；X2负诊断 | 轻load有效MSE改进，highload不稳；新方法中心失败，Jensen lemma未立。 |
| Claude D3当前：ρ/R/T grid | L3配置 | practical tuning；对under-converged自家默认的优势不构成deliverable5。 |
| A：可达状态＋逐帧尾部的有限预算负载设计 | L1-lite问题细化＋L3新预测准则 | 不要求新architecture；成功迁移预测＋近最优配置可满足5(c)。 |
| B：自生软反馈的相关性控制/外信息化 | L3针对性method | 推断目标不变；若修复被测EIV项，且等成本胜tuned references，可满足5(a)/(b)。 |
| C：coded-risk决定DPSS阶数/逐步扩展 | L3表示选择method | 阶数不能只按NMSE。需区别W3及已有order adaptation；高实用、重叠风险中高。 |
| D：参数依赖covariance信息与task-matched shrinkage | L3模型内likelihood/estimator | 不是new Gaussian score。可解释D2负例；算法收益未证、推断成本高。 |
| E：固定energy/延时的SP vs embedded-pilot可行区 | L1-lite部署问题＋L3设计 | 直接决定SP是否值得用；最贴prakticality，普通SP/EP对比不足，需预测Pareto/切换边界。 |
| F：init/refit/soft-feedback信息余量图谱 | L1-lite诊断/benchmark | 可防无效模块堆砌；单独negative result通常撑不起本Trans目标。 |
| Transformer迁移本身 | 用户口径L2 | 新model可接受；通信增量仍需明确。不能以“没从零发明Transformer”贬低论文贡献。 |

**[I] Benchmark真正要求：**明确通信瓶颈；模块/信息来源为何有效；公平E2E可靠性、overhead、完整成本、条件迁移。不是必须Transformer、必须第一性原理全闭式、必须从未有人碰SP。我们的比较标准应是“相近创新＋更清楚机制/更实用收益”，不是击败虚构的弱LS网络。

若只做设计理论：无需强行训练Transformer反证；对W1/W4/W5的调优经典参照更决定性。若宣称“替代/匹配Transformer”：必须明确具体网络、同信息/同channel/support、同码、训练侧信息/成本；现有0 headroom论证不够。W9历史CSI是额外信息，不可不记账。

## 4. CCF reviewer

### 4.1 同一概念尺；六维20/25/20/20/10/5

对象：V2＝BR的D1+D3，D2作lemma；A＝§3.2的预测准则修订；B＝结构不同的soft-feedback方法。**未把缺实验扣进概念分；逻辑过称与已知重叠可扣。** Novelty provisional，整体partial。分数不是录用概率。

| 维度 | 权重 | V2 | A | B | 依据 / 改判条件 |
|---|---:|---:|---:|---:|---|
| 问题重要/具体 |20|4|4.5|4|V2负载有意义；A加可部署可靠性/预算；B直指EIV。C1-C10：须明确应用δ/物理族，非抽象maxK。 |
| 近邻新颖性 |25|2.5|3.5|3 provisional|W1/W4/W5覆盖分析/预算/power骨架；A增量＝真实可达tail＋跨配置预测；B工具有bilinear/EP谱系，算法差别尚粗。C1-C07/R1-C04。 |
| 概念洞察 |20|3.5|4|4|V2 smooth-info×code已知、负D2误解释；A把mean/可达性/有限budget分开；B指出same-MSE非同信息。R1-C01/C02。 |
| 机制逻辑 |20|3|4|3.5|V2缺T→真实transfer连接，D2 lemma无前提；A目标与观测兼容；B不能简单把现有Onsager再加一次。R1-C03/C05/C06。 |
| 简洁/必要性 |10|3|4|3.5|V2多故事并列；A只保留预测接口＋约束求解；B须单一correction，禁止拼decorrelation＋新prior＋新pilot多模块。 |
| TCOM贡献适配 |5|4|4.5|4|A理论/设计，Bmethod/cost，通信受众明确。是否实现另属证据评估。 |
| 加权 /5 |100|**3.225 ≈ 3.23**|**4.00**|**3.60**|0.20P+0.25N+0.20I+0.20M+0.10E+0.05F；100% assessed，novelty暂定。 |

V2：**pivot-with-rescue-route**。A：**revise**，发展潜力较高；不是accept-to-submit。B：**pivot-with-rescue-route**，潜力中高；进一步novelty decision仍needs-literature-search，先收紧correction。置信：V2中高；A中；B中低。新分数评BR v2，不与DIR3.65或OLD3.00做机械升降比较。

### 4.2 Concern IDs；最小修正

| ID | 状态/严重度 | 具体问题→修正；改判条件 |
|---|---|---|
| C1-C03 | partly / medium | K≠物理DoF；DRV已清楚表示。标题/公式范围保持receiver load；加入谱与representation error即可。 |
| C1-C04 | open / medium | N scaling改变物理ν、码长、CPP；固定f_s/f_D及选阶容限，各码单独校准。无此条件不主张Kc∝N。 |
| C1-C05 | narrowed / medium | 真实多吸引域未证；SC末尾scope correction已承认。仅finite-round start dependence；新稳定性证据才能升级。 |
| C1-C07 | open / high | iteration allocation有W4直接近邻；D3当前配置。A必须predict-before-sweep；B须tuned references等可靠成本。 |
| C1-C08 | open / high | genie Gaussian map不代表真实decoder可达族；A按actual trajectories校准，验证条件分布跨history一致。 |
| C1-C09 | accepted limit | κ=w保留预测拟合，撤机理；新公式不得用sameMSE/trace divergence假装完整结构。 |
| C1-C10 | open / scope | fixed code/N/modulation/genie delay；概念可保留，但TCOM论文范围与部署主张必须一致。 |
| R1-C01 | new / high | “MI universal”混I_ll、true MI、finite-code FER。用式(18)、独立scale calibration、per-frame终点。 |
| R1-C02 | new / high | mean-map成功/短轮与physical boundary混；用式(20)，允许校准误差/状态维不足被否定。 |
| R1-C03 | new / high | D2 optimal/bound/Jensen缺前提；式(10)–(16)修正，真实covariance/prior风险核对后才lemma。 |
| R1-C04 | new / high | “Transformer＝LS refiner”是错误比较对象；W7/W9/W10。按具体功能/信息输入比较。 |
| R1-C05 | new / medium | “减少ρ”无明确收益货币；固定power＋code＋deadline，求FER约束cost/goodput。 |
| R1-C06 | new / high, B | 自生反馈相关很强，但加correction也可删掉有用data信息；必须给可观测目标与有限T一致性，不偷用truth。 |

单代理四视角：problem＝值得研究receiver feasibility；novelty＝减去EXIT/ρ/scheduling已有部分；logic＝现V2结论过宽；audience＝可迁移criterion或等成本targeted method即可。无独立panel共识。

### 4.3 实验证据评估，独立于概念评分

**强：**[F] X1配对early coupling、IB复现、短轮frozen composition；J12/R2保留失败且exact attribution一致。**弱：**X2旁路MSE不能决定E2E；cheap时间参考非完整equal-reliability；Kc=.5非应用指标；mean/per-frame Gaussian map都未充分预测real history。

**[I] 当前能入稿的观察**：finite schedule改变load cliff；early pilot–inner budget互补；same-MSE own errors导致不同refit风险；scalar calibration与mean map有失败边界。**还不能当headline**：通用Kc律、最优(ρ,R,T)、GLS伤害信息定理、所有refiner无余量、Trans计算优势。

## 5. CCF optimizer — divergent

### 5.1 六候选，不只同一路线换名字

| ID / op / parent | 问题轴＋机制一句 | 证据类型 / 最近工作＋区别 | 风险 / coherence |
|---|---|---|---|
| **A refine / D1+D3** | **有限预算feasibility**：用真实可达belief＋逐帧谱/尾部预测Pe，约束选择ρ/R/T | 冻结跨条件prediction＋config regret；W1/W4：已有transfer/scheduling，增量必须是可达tail和迁移，不是新叫法 | TCOM中风险。单一输出Pe＋配置，一致；若逐格再测Φ则退化lookup。 |
| **B invert / J12+失败T2** | **软反馈可信度**：不把APP误差当独立training；显式控制对同y噪声/信道误差的重复响应，给一致外信息refit | signed cross-risk ablation＋同MSE对照＋等成本FER；closest W5及BiG-AMP/EP谱系（本轮未补读原文，novelty partial/unsearched具体correction） | TCOM中高风险。保持observations/representation；只改一个feedback rule。直接搬dense Onsager与现kernel重复，须否决。 |
| **C combine / A+DPSS阶数** | **表示精度与译码启动冲突**：按mode学习代价与BEM residual选择/扩展阶数，让decoder belief跨可达瓶颈 | modal risk预测＋full saturated DPSS vs NMSE选阶对照；W3及lit-v3 A8已有order adaptation，区别＝coded reliability/启动代价，而非NMSE | TCOM中高风险。缩阶同时加失配，必须两项算全；H warm start遗忘不否定decoder-belief continuation。 |
| **D transfer / D2+Gaussian marginal likelihood** | **信息方向而非white/colour标签**：使用参数依赖C的完整score或task-weighted shrinkage，避免盲信fixed prior GLS | 式(15)–(17)conditional risk/proof＋完整receiver干预；W6直接ML谱系，区别＝SP-LTV有限码风险/低成本近似，未认证 | TCOM高风险。经典score不是新贡献；若只能diag ridge tuning或cost过大，降为lemma/诊断。 |
| **E invert / D3+SP spectral-efficiency口号** | **何时值得SP**：固定frame energy、CPP、deadline，预测SP vs embedded pilot Pareto与切换条件 | 相同physical channel、equal payload/reliability/完整成本；W1已有SP/preamble对比、W5已有pilot设计，区别＝rich-LTV计算瓶颈与迁移边界 | TCOM中风险。transmit策略不同；控制总rate/overhead，不能同SNR不同payload。 |
| **F instrument / WARM+X2+旧learning-null** | **模块信息余量**：分init-only、persistent refit、decoder beliefs、support acquisition；oracle只诊断各槽可得增量 | 配对slot intervention＋representation/统计信息审计；W10直接LLR receiver为反例，差别＝SP rich-channel load诊断协议 | 单独TCOM高风险。无新method/criterion，保留为A/B证据层或letter/conference rescue。 |

axes已变：feasibility / statistical consistency / representation / likelihood geometry / deployment protocol / diagnostic；机制、证据、venue风险亦变。候选均为[S]，不当结果。

### 5.2 Coherence filter与选择

- **A保留，主选。** 一条故事：self-interference使available information随mode/feedback/有限budget变化→码的真实轨迹决定Pe→预测配置。优先少状态；不是要求把全部jacobian压成普适闭式。
- **B保留，结构不同fallback。** A是预测现receiver；B改变软反馈。收益不能靠更深T/新prior混杂。把correlation correction写成一个可实现方程后再查近邻；否则仅研究动机。
- **C条件保留。** 只有低阶削减估计税大于representation残差、且coded metric选阶胜NMSE选阶才成立；Slepian prior现有负结果必须留。
- **D降优先级。** 有数学价值；W6 overlap强。先解释X2的bias/variance，未有targeted gap前不新建昂贵likelihood receiver。
- **E可与A择一扩大，不能再加第三中心。** 若A能预测SP/EP切换，practicality更高；先完成C1族内部预测才扩。
- **F保留支撑/救援。** 当前足以纠正headroom叙事，不足以单独满足deliverable5。

**最佳route＝A；fallback＝B；rescue＝限定SP joint receiver诊断/设计研究＋已有scoped system收益。** 若A/B均未过实质贡献门，明确Trans目标仍开放；不把配置表/旧部署壳＋几条经典公式自动拼成regular paper。可缩为letter/conference，但需用户决定venue，非本轮降目标。

## 6. Recommendation

**[I] 赞同Claude：** learning/architecture不该强撑中心；K是有用receiver负载；D2正收益已失败，降级合理；κ纯scalar机理应停止；配置alone不够。**不同意：**D1+D3无需进一步改变便能成为中心；“initial slot≈0”可推所有Transformer无余量；Jensen已解释高loadGLS损失；I*=.577/Kc具有普适物理意义。

**[S] 建议中心句：**

> 已知delay的SP-AFDM联合接收中，表示谱与自生软反馈决定有限计算下可达的译码信息分布。建立受限、可迁移的预测准则，选择pilot power与joint/decoder预算，在固定可靠性与完整成本下接近调优前沿。

TCOM fit：**有条件可做**。符合deliverable5(c)，或A引出的B满足5(a)/(b)。不必完整Shannon界，不必真正L1；需一个可复用、非平凡且能提前指导选择的对象。当前只有现象/diagnostic证据，尚无这项deliverable。

### 6.1 最小决定性证据＋冻结式kill rules

全部是**建议协议，尚未冻结/运行/获新仿真授权**。现有X1/X2作为development，不能再叫独立confirmation。先纸面修正D2，后只测能区分贡献的东西。

| gate | 最小证据；先封存什么 | 建议pass / kill |
|---|---|---|
| **G0 可达性/状态闭合** | 用已有/少量未来真实decoder轨迹，固定窄工况；相同I_ll但不同history/calibration/spectral strata比较下一轮。genie injection只对照；一个新增状态最多 | 若scalar map next-I误差>.03且history偏差显著，kill scalar sufficient-state claim；仅允许预定一次2-state修订。若仍依赖full trajectory/每frame genie，A不能叫轻量可部署criterion。 |
| **G1 迁移预测，主门** | 固定一次校准范围、特征、系数、code接口及未见SNR/ρ/T组合；小网格覆盖cliff，两种T；预报Pe曲线、Kc、best配置。加入一项改变N或码率的transfer；固定物理f_s/f_D和选阶容限 | ≥80%未见格满足\|ln Kpred/Kobs\|≤.15；另Pe预测绝对误差≤.05、预测区间coverage登记。若必须每格A3/Φ重校准或cliff回拟合，kill“calibrate once/generalise”；可以保留scoped分析。 |
| **G2 决策价值** | 应用δ先选，例如FER≤.1；固定预算、ρ/R/T grid，比较预测选点与独立穷举tuned frontier；经典简单规则同预算：T饱和后选R、syndrome/residual early stop | 可靠性constraint必须满足；达到目标的完整平均成本≤grid最优1.10倍，或固定成本goodput regret≤5%。若只胜R10T20而不胜简单tuned规则，kill实质design-method claim。 |
| **G3 B仅fallback启动** | 固定N/K/support/prior/pilot；一个correction对照原joint、更多T/普通damping及公开近邻适配。封存完整cost、同MSE随机化诊断与负例 | δ下配对FER非劣（预定margin，例如绝对+.01）且cost节约≥15%、paired CI排除0；或等cost具预定可靠性增量。correlation中介应随干预改变。仅MSE降/extraT解释全部收益→kill B方法中心。 |
| **G4 D2机理资格** | 按式(15)/(16)拆白/GLS的bias、variance、misfit/cross，测E_p−E_trace，η/calibration分开。oracle仅diagnostic | 若Δbias不承载预定多数positive Δrisk，kill“ridge bias主导”；若E_p条件不满足，撤Jensen→receiver结论。P5通过不算理论验证。 |
| **G5 deployment范围** | 最终主张才加真实support acquisition＋完整分数传播、一个第二code/工况；CPU全链成本计入，旧G0不拼效应量 | 如果贡献只genie成立，scope降至known-support design；不得写deployed practical advantage。失败不抹去G1的限定理论价值。 |

G1/G2是A最小主证据；G3只在A失败且B有具体correction时做，非全部平行铺开。阈值是工程判别建议，不是TCOM官方标准。Bootstrap用frame block、paired外生块；多格primary数目先写；censored crossing只界，不算exact/固定CI；真值、选参、CONF命名空间分开。

**Drop/demote：**

- Drop：通用scalar Kc theorem、先验“所有learned无headroom”、GLS optimum、未证Jensen regime lemma、T≈40全域收敛、物理K/N容量缩减、真实双稳态。
- Demote：κ bracket/有效常数、pilot LS/ridge公式、G参考曲线、预算scan、历史learning-null；作为假设/基础/诊断，各守范围。
- Keep：短轮冻结prediction、失败的mean/per-frame map、J12有符号结构、physical load定义、X1early substitution。失败可变成机制边界，不能单靠负结果自称中心创新。

## 7. Challenges for Claude

1. **主贡献一句话＋数学对象？** A跨条件prediction、Btargeted method、还是现象描述？具体满足deliverable5哪一项；其“非平凡”差别是什么？
2. **G的上界前提逐项列？** 设计独立谱、J trace固定、true prior、risk定义、LTV→Rayleigh singular-spectrum；哪项当前实际成立？
3. **Jensen的E到底何值？** pilot加权E_p、trace功率、ensemble1？式(13)与当前Wt分母差多大？如何排除§2.5反例？
4. **“GLS最优”究竟哪一族？** 为什么真C＋flat prior可视Bayes optimum？是否遗漏参数依赖covariance score？
5. **X2未改receiver，何来cliff headroom上界？** WARM替换仅均值、gain variance重置；可否只保留该槽弱敏感，撤Transformer普遍结论？
6. **预测用什么输入？** 新格η需真H-A3，Φ需genie injection，I需true bits；哪些可部署、哪些校准oracle？总校准成本与“calibrate once”如何对齐？
7. **相同I但history不同是否同next distribution？** A5 open帧失败及T增大logloss下降如何解释；额外state只能加一个时选什么、有何可检验必要性？
8. **ρ/R/T目标货币？** Kc=.5、δ=.1/.01、deadline、goodput、pilot能耗分别会选不同配置；哪个是真应用约束？
9. **同K不同谱/表示是否同cliff？** K=8L是flat receiver复杂度；为何不先检验C_h/Gram effective information与BEM residual，而继续说physicalDoF？
10. **现成本优势能否胜调优参照？** R4T30对R10T20仅配置修复；与W4阶段切换、普通early stop、饱和T规则比较，剩什么？
11. **Transformer benchmark是哪篇、哪功能？** PD-CEViT、history-PFM、raw→LLR receiver不能统称LS refiner；是否仅作创新尺度比较，撤直接性能替代claim？
12. **提前给失败后动作？** A预测失败→只允许一次state修订还是转B；B未胜→限定稿/保持Trans开放？不得把每次failure后再校准叫generalisation。
