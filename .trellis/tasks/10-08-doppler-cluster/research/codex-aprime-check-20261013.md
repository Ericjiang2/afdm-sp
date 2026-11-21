# Codex R3：A / A′，冻结前独立检查

2026-10-13。Caveman。**结论：[I] 支持一次重设计后的判别实验；不支持用 post hoc 翻转旧 verdict。论文对象优先 one object，但 A 必须有独立预测/决策内容。当前“风险 scheduler + load-cliff 名称”仍未达到 Trans。下一 run 必须胜五臂 fixed schedules＋强 adaptive proxies；否则新颖性增量可能归零。**

标记：**[F] fact**＝文件/原文；**[D] derivation**＝明确假设下推导；**[I] inference**＝证据解释；**[S] speculation/proposal**＝待检验假说或本轮冻结建议。本轮只读＋写此文件；无 SSH、仿真、分析程序运行、git。未独立重算 raw/bootstrap。数值核验＝保存汇总＋分析源码；文献核验＝下列原文相关章节，非全篇逐行审计。

## 0. Evidence 索引

以下缩写均指实际打开文件；`R/`＝本文件所在 research 目录；`E/`＝`experiments/headroom_ladder_20261008/`。

| 简称 | 文件 / 核验位置 |
|---|---|
| RC | [Claude reconsideration](claude-reconsider-AvsAprime-20261013.md)，8–35 |
| DR | [next-run draft](aprime-corrected-criteria-draft-20261013.md)，9–57 |
| ON | [T1–T3 frozen record](c1-online-headroom-T123.md)；[on.md](../../../../experiments/headroom_ladder_20261008/out/c1on/analysis/on.md)，T1–T3 |
| ES | [A′ frozen record](c1-escalation-A-prime.md)，7–56；[esc.md](../../../../experiments/headroom_ladder_20261008/out/c1esc/analysis/esc.md)，7–49 |
| PH | [esc_posthoc.md](../../../../experiments/headroom_ladder_20261008/out/c1esc/analysis_posthoc/esc_posthoc.md)，7–49 |
| FR | [frontier.md](../../../../experiments/headroom_ladder_20261008/out/c1esc/analysis_frontier/frontier.md)，1–23 |
| NV | [novelty judgment](aprime-novelty-20261013.md)，10–48 |
| L1 / L2 / PK | [candidates v1](aprime-lit-candidates-20261013.md)；[candidates v2](aprime-lit-candidates-v2-20261013.md)；[packets](aprime-lit-packets-20261013.md) |
| EA | `E/c1esc_analyze.py`：76–83 closure，85–112 cost，132–166 policy/selection，174–185 CI，199–202 各 currency 独立选策略 |
| ED | `E/driver_c1esc.py`：4–15 schedule 等价，58–98 trace，102–119 CLI，179–181 frame IDs |
| OA | `E/c1on_analyze.py`：198–204 T2 baseline 来自 T1 全300帧；244–305 T3 samples/model/verdict |
| R2 | [Codex R2](codex-direction-r2-20261013.md)，35–72；[direction brief](codex-direction-brief-20261013.md)，7–9：Trans deliverable 5 |

借 statistical-power 的 paired-power 原则、comm-lit-review 的 primary-source 核验；未跑完整技能流程。研究目标不变：deliverable 5(a) 可复用机制＋针对方法 / 5(b) 非平凡近等可靠性计算收益 / 5(c) 有预测力的理论或设计准则；经典组合＋工程验证不足。

## 1. F1–F5 / G1–G2：逐项裁决

### F1：边界选点、泛化、class efficiency

**部分同意。** [F] 旧 O 搜索大量 syndrome thresholds，F 仅 E10/E0×Rc；dev 都用 FER≤δ。独立 test 检验实际选出的 policy，问题本身合理，不是错误 gate（ES:18–25；EA:132–166）。

**[D] Selection optimism：**设 M 个 policy，`p̂_j=p_j+ε_j`。在 `p̂_j≤δ` 下再最小化 cost，会偏选负 ε；M 增大偏差增大。固定 `.02` 只挪门，不解决多重搜索。对有界 iid frame loss，简单 uniform bound：

```text
Pr(max_j |p̂_j − p_j| > ε) ≤ 2 M exp(−2 n ε²).
ε_uniform = sqrt(log(2M/α)/(2n)).
```

假设：候选先固定，或用独立 TRAIN 生成、条件于 TRAIN 固定；样本独立。若看 CAL labels 后不断新增候选，M 未封闭，式不直接适用。Hoeffding 常很松；不是建议硬用它浪费预算。**独立 TEST 检验冻结 policy；或独立 certificate/LTT。二选一，不能把 winner 的单点 SE 当 uniform guarantee。**

**[I] 旧失败不能被归因为“仅 threshold generalization”。** PH 同样选出 P*，只排除了那一次 dev-constraint 改法；没识别 failure 原因。基础 B* 的 test FER 下降、P* 的 dev winner 偏差、sampling noise、class asymmetry 均可解释（ES:42–44；PH:13）。

**[F] `.02` 后验例不是同一个 δ=.10 重试成功。** L16 的22.3%来自 **level=.125**；level=.10 的 margin 行无 admissible policy。L16 test `.093→.100`，L20 `.200→.180`；都不是精确 equal FER（FR:12–13、21）。可生成下一假说；不得证成既有 class advantage。

### F2：300 vs 2000，power

**同意样本偏小；不同意“300永不能认证 / 2000必然够”。**

**[F] 旧 frozen gate 用 point `d≤.01`，并未要求 `UCI(d)≤.01`（ES:24）。** 因此300帧并未使旧 PASS 数学不可能；现有 point `d=.0267` 确实失败。若论文需要 non-inferiority confidence，必须另加门；不能倒改旧门含义。

**[D] 真正预测 precision 的量＝paired discordance。**

```text
D_i = Yπ,i − YB,i ∈ {−1,0,+1};  Y=frame failure.
p+ = Pr(D=+1), p− = Pr(D=−1), q=p++p−, d=p+−p−.
Var(D)=q−d²;  SE(d̂)≈sqrt((q−d²)/n).
```

不是只看 FER≈.1。相同 marginal FER 可几乎同错、也可错在不同帧。

| n / 假设 q，d≈0 | two-sided 95% half-width，正态近似 |
|---|---:|
| 300，q=.04 | .0226 |
| 2000，q=.04 | .0088 |
| 2000，q=.10 | .0139 |
| 4000，q=.04 | .0062 |

**[D] “永不能”反例：**若300帧没有任何 harmful discordance，`p+` 的 one-sided95% exact upper `1−.05^(1/300)≈.00994`；且 `d≤p+`，可认证+.01 non-inferiority。此为特殊样本，不是普遍有力设计。

**[D] Power 与 CI width 不同。** 检验 `H0:d≥η=.01`，真 d0 下80% power：

```text
n ≈ (z_(1−α)+z_.80)² (q−d0²)/(η−d0)².
α=.05，d0=0：n≈61,850 q → q=.04:2474；q=.10:6185.
四 cells Bonferroni α=.0125：n≈95,100 q
→ q=.04:3804；q=.08:7608；q=.10:9510.
```

假设：独立 frame、固定策略、正态近似、规划 q/d0 正确；不覆盖 cost gate 的联合 power，也不覆盖风险模型误差。**2000/.009 是某个 q 下 precision 示例，非80% power。** 不计算 observed post hoc power。

### F3：staircase / hull

**同意；漏项比 Rc granularity 更大。**

**[F] E1/E2/E3 本身是无条件 fixed round schedule**；syndrome0共同早停只让易帧提前退出。ED:4–7、ES:8–10已明写等价。它们在旧分析被归为 online，而 fixed F 排除了它们（ES:18–19）。新 baseline 必须包括所有五臂×Rc；否则“frame-adaptive gain”含 clock-only improvement。

**[D] 无 context 的随机 time-sharing baseline：**

```text
H_F(x) = min_w Σ_j w_j c_j
         s.t. Σ_j w_j p_j ≤ x, Σ_j w_j=1, w_j≥0.
```

一项 reliability 约束，最优 extreme point 至多混两个 schedules。假设 iid stationary traffic、平均 cost/FER、mixing 独立于 frame observation；不给 deadline/tail 保证。若根据 syndrome 选 arm，就是 adaptive baseline，已超出该 hull。

**[I] test hull 仅诊断。** 固定 x 下对 test 取经验 minimum，易低估 baseline cost，通常对 π 严；但 `x=p̂π(TEST)` 也随机、baseline 被 test 调优、非线性 ratio，不能概括为“自动公平且统计保守”。无有限样本 true frontier 保证。Bootstrap 若用于此诊断，须每次重建 hull 与 x，不能固定已选 segment；主门不用 test hull。

### F4：cost currency

**同意全链成本；不同意把9.6%→22.1%全解释为固定成本稀释。**

**[F] 两个数选了不同 policy：** sec 的 E2 Rc8；updates 的 E3 Rc9（esc.md:14、25；EA:197–202）。需同一个 policy 同时算两 currency，才可做该归因。独立最优化应明确标注。

**[D] 简化：**每活跃轮 `c(T)=aT+b`，则 T40→T20 的单轮 saving 为 `20a/(40a+b)`，小于 inner-step50%；并不推导整条 policy 的 saving，后者还改变外轮、decoder iterations、终止帧。

**[F/I] 旧 reference sec 不是新 escalation 真实CPU测量。** EA:90–110把 all20/all40 的平均轮增量拼接；忽略 schedule history 对 CE/LDPC耗时的影响，且 reference n=10 的不确定性未进 frame CI。新 run 不能继续用此模型当完整CPU增益证据。旧 measured noisy time .301 是 report-only，未改变 currency 层级（esc.md:17）。

### F5：范围

**同意。** [F] 两 loads、一个SNR/ρ，主 δ=.1仅L16；L20 δ=.2为 report-only。旧结果不能证明跨 load、跨SNR方法，也不代表真实support。

**[I] 四 cells 可筛5(b)，仍非跨code/general deployment。** HARQ first-BLER=.1只是动机；没有重传/feedback/resource模型，不可把 give-up 自动计作净 latency benefit（RC:17）。本轮全部give-up计 fail，latency只报receiver processing。

### G1：A 的 target

**同意 tail target；不同意宣布 Kc(.5)无价值。** [D/I] `.5`可描述 transition；不对应 δ=.1/.2 的工作边界。A 的主对象应为动作/预算条件下 `Pe(z,a,Rc)` 或尾部约束、可达动作的风险差、cost，不以均值 I 或50% cliff替代 reliability。Kc曲线可作 mechanism副图；不当 operational design criterion。

### G2：grid便宜，A与A′合一

**部分同意。** [I] 当前小 grid 离线选点价值弱；若A只重现本格最优，与强 baseline 无实质区别。可迁移预测、少量校准、提前排除不可操作区域仍可独立满足5(c)；不是 offline天然无practical价值。

**[F/I] T3不能推出“必须≥2个物理state”。** OA:255–305：特定 quadratic logistic M0，加入 ΔI/r/syndrome 的M1，预测 **next-round success**，且只看尚未 syndrome-stop 的 survivor。四 ΔLL=.0266–.0462 nats；drop-r最强（on.md:29–32）。支持“此 autonomous scalar parametric predictor 不够”；不证明任意scalar representation不够，也不证明 r 是新物理状态。

**[D]** Bayes最优时 `LL(X)−LL(X,H)=I(Y;H|X)`；有限 fitted logistic 的差还含 model misspecification/estimation。r可表示剩余预算、非平稳更新、survivor composition。数千 rounds来自每fold150 frames，不能当数千独立样本。

**[F] T2 held-out还需降级：**baseline T/Rc来自全300帧T1，再切150/150选give-up（OA:198–204）。11.1%不是全pipeline纯held-out估计。A-first旧门保留；该数仅development佐证。

## 2. Post hoc：该保留、该撤

| 命题 | 独立判断 |
|---|---|
| 旧 L16 S=.261、d=.027、frozen NOT viable | **[F] 保留。** ES:35–37、esc.md:13。主门判的是选中policy，不是所有未来A′。 |
| 15–30% equal-FER class advantage looks real | **[I] 降为假说。** FR：不完全等FER、在线搜索多、test内优化、尚无五臂hull。 |
| `.585→.496`，point FER同.100，约15.2% | **[F] 算术正确**：`1−.496/.585≈.152`。 |
| 上述15.2%=escalation独立贡献、胜prior art | **[I] 不成立。** Rc7→Rc10，give-up r1/>264→r2/>284，arm E0→E3同时改变；不是matched-component ablation。baseline也没调优E1–E3＋give-up。需这两个固定policy的paired joint CI；同point FER不等true FER。 |
| threshold泛化已定位为旧失败原因 | **[I] 未定位。** PH只排除一个改门反事实。 |
| oracle .35证明online实际余量 | **[I] 仅family optimistic headroom。** 看true errors、最便宜成功路径、可弃最贵易帧；无deployable-state限制。不同arms增加后oracle对象也变。非物理上限，非可达收益。 |
| decoder state＋elapsed rounds就是load-cliff机制 | **[I] 过称。** generic decoding dynamics也给r信号；须风险差/动作收益与load-budget交互的额外预测证据。 |

## 3. Novelty：原文复核＋漏掉近邻

**[F] Coverage＝partial，targeted searched。** 本轮重点：CE-in-loop effort、per-input switching、decoder-risk stopping。Lee/Yang及Chen两篇full text未取得；不能把abstract当实现审计。未声称“first / 没人做”。以下网页只用于原文事实；关系判断另标[I]。

| 来源 / 本轮阅读级别 | 核验、区别 |
|---|---|
| **Ylioinas 2010 thesis**，[author repository PDF](https://oulurepo.oulu.fi/bitstream/handle/10024/34735/isbn978-951-42-6220-3.pdf)，Ch6 §§6.5–6.6，印刷pp114–121；相关full-text章节 | **[F]** detector/CE/decoder EXIT scheduling、按channel realization的examples、窄EXIT opening收益均已讨论；long-block和动态实现有局限。**[I]** mechanism“临近收敛边界更需调度”非新。2013TCOM具体实现仍未读；不能断言仅一个global schedule。 |
| **Lee & Yang 2010 TCOM**，[author-group publication list](https://www.csdl-lab.postech.ac.kr/international-journals)；PK:69–73 / L2:75；metadata/abstract partial | **[F]** 题名与publication存在；inner equalizer是否再执行的abstract描述与NV一致。**[I]** 不能据此称“syndrome stall就是Lee rule”；CE-in-loop、具体signal/threshold未核。冻结baseline写proxy，不冒称原算法复现。 |
| **Amador et al. 2010**，[EURECOM PDF](https://www.eurecom.fr/en/publication/3166/download/cm-publi-3166.pdf)，III-A/B，Alg1/2；full相关章节 | **[F]** syndrome成功退出＋SCMS erased-message increments非收敛退出；static thresholds、false alarm/missed detection调参。NV概述基本正确；不是简单syndrome阈值一个机制。当前五臂未存SCMS erased messages；只能用明确proxy。 |
| **Strodthoff et al. JSAC 2019**，[author preprint](https://arxiv.org/html/1807.10495v2)，II-A/C、III；full相关章节 | **[F]** decoder-progress→failure predictor，FNR/FPR operating point，target effective HARQ BLER；新重传/资源模型承担部分可靠性代价。**[I]** “calibrated early HARQ”若指threshold tuning可；若指distribution-free finite-sample guarantee则错。不是本单次receiver FER证书。 |
| **Kanazawa et al.**，[preprint v3](https://arxiv.org/html/2501.15935v3)，IV-C、V-C、VI；full相关章节 | **[F]** static coded/uncoded轮预算，adaptive residual/LLR stopping留future work；PK/NV此项读对。**[I]** future-work一句不是新颖性授权；当前分数范围窄不能证明填满它。 |
| **Akyildiz & Mahdavifar 2026 preprint**，[全文](https://arxiv.org/html/2603.20385v1)，III-A/B Eq11–12；full相关章节 | **[F]** cost＋λ×FER stopping、预测继续搜索能否挽救、progress/history features；无hard FER约束，decoder-only。**[I]** “action-benefit predictor＋cost-risk控制”也非概念首创。与A′的区别须是joint-receiver可达动作及有用机制；不能仅把MLP换logistic。 |
| **Wu et al.**，[preprint](https://arxiv.org/html/1509.09059v2)，V-A；full相关段 | **[F]** turbo CE第一轮5 inner，后续1；L2:C1-08读对。预算随outer-round变化早已有；不是新method。 |
| **Hu, Shi, Cai, Yu**，[adaptive-depth SBL preprint](https://arxiv.org/html/2201.08477v3)，V-B；full相关章节 | **[F]** per-input residual-based halting，CE迭代深度自适应；无coded FER。**[I]** 邻接证据：per-sample CE effort不是空白，只是其目标不同。 |
| **新增最重要：Alves, Guimarães, Pinto 2015**，[IET publisher full text](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/iet-com.2015.0151)，§4，Eq26–30、Table2 | **[F]** turbo receiver用channel estimate/soft-symbol信息检验，控制false-alarm的threshold，FLPSCV→便宜BCJR切换。依赖Gaussian/uncorrelated/估计误差近似；不是distribution-free最终FER guarantee。**[I]** 已把physical CE-quality state→online computational-mode switching连起来；比“普通decoder early exit”更近。方向是降档，A′升档；这点不足独立撑TCOM。 |
| **Liu, Guan, González，Turbo BEM OTFS，TCOM72(1):601–617，2024**：L2:C5-05仅snippet；[NTU官方技术页](https://www.ntu.edu.sg/innovates/tech-portal/tech-offers/detail/system-and-method-for-orthogonal-time-frequency-space-communication) / [NTU publication list](https://www.ntu.edu.sg/ancl/achievements)已独立读；论文full text未取得 | **[F]** SP＋BEM order/pilot power优化＋CE/detection/decoding soft-feedback loop。**[I]** NV的same-class map应纳入；scheduler有无仍未核，不能称其固定预算，也不能声称Kanazawa是唯一最近工作。 |
| **新lead：Huang & Ritcey 2005 TWC，SIED**，DOI10.1109/TWC.2005.853977 | **[F]** Ylioinas thesis §2.7及ref184明确指向decoder iterations before CE scheduling。该论文primary full text/landing此次未取得；secondary abstract说online soft-convergence才反馈CE。**[I]** 优先补读lead；此处不把secondary描述升格已核机制/新颖性否决。 |

**[I] NV总体诚实：M1/M2高度已知，M3已知，M4/M5组合尚有窄增量。需修正四处：**

1. NV:21–22把per-block CE scheduling一并概括，阅读层级不齐；区分Lee的per-block abstract、Ylioinas的EXIT schedule/channel adaptation。
2. NV:25–29剩余区别是 **待实现对象**；旧ES没有risk-triggered choice between e，只有clock schedule＋give-up。DR:14–15虽拟合q_esc，trigger只用q_cont；还没真正利用action differential。
3. NV:30–35，15%=纯escalation、new guarantee、TCOM-worthy“only with mechanism and/or guarantee”都偏强。没有保证成品；普通binomial certificate＋经典scheduler不自动有method novelty。
4. closest-work补Alves；补核Liu；Huang/Ritcey作为open lead。Lee/Chen原算法未读透前，禁止“优于这些论文算法”的声明。

**[I] Remaining distinction够不够？当前不够。** 更可信目标：在短coded SP joint loop，低预算失败高风险与“额外inner budget能挽救”不是同一量；可观测state预测该差异，驱动受FER预算约束的单次升档，胜强generic controller。机制＋transfer/action-value evidence＋完整cost若成立，可做中等L3、强practicality的TCOM候选；还不是新问题L1或新model L2。只加新waveform名字、logistic和常规置信区间：低L3。

## 4. A / A′ / one object：排序、数学对象

**[I] 论文价值排序：one object（条件成立）> A（真能预测/指导）> A′单独。执行排序改：先一次严格A′判别；同时取A所需action-state证据。**

- **改变R2的run priority。** 五臂现在已有可做causal replay的动作数据，判别增量比再扩配置grid直接；近邻文献也使A′独立新颖性更弱。
- **不改变R2的实质中心要求。** A若只为scheduler附一张cliff图，one object是叙事拼接。A′ killed 不自动kill A的5(c)；A已不能退回“50% Kc＋本格最佳配置”。
- **one object可一句写：**可达反馈状态怎样预测额外inner effort的净挽救价值，并在已知support SP joint receiver里实现可靠性预算内的计算分配。one object不必宣称普适state law。

**[D] 在共同低预算前缀 z_r：**

```text
Y20,Rc = all20、syndrome-stop、cap Rc 的最终failure。
Ye,Rc  = 前e轮20、后40、syndrome-stop、cap Rc 的最终failure。
q20(z)=E[Y20,Rc | Zr=z], qe(z)=E[Ye,Rc | Zr=z], e=r。
Δe(z)=q20(z)−qe(z)
     =Pr(Y20=1,Ye=0 | z)−Pr(Y20=0,Ye=1 | z).
```

假设：r≤3、两paths到r的数值前缀一致，数据/receiver seeds共用；z不含future。五臂同frame提供两potential outcomes，训练label可用truth；部署z/q不得用truth。

**[D] 高q20不等高Δ。** `.9→.9`救不了；`.5→.1`值得救；`.9→.95`还伤害。仅 `q20>τe`最多是failed-frame classifier，非action-value方法。对future固定tails的conditional mean cost m_a，Lagrange surrogate选 `argmin_a[m_a(z)+λq_a(z)]`；升档条件为 `λΔe(z)>m_e(z)−m20(z)`。

**[D]** 理想context价值：`E[min_a E[J_a|Z]]≤min_a E[J_a]`，`J=C+λY`。持平若Z不改变最佳动作。此为经典decision identity，不是新定理；observation/policy开销可吃掉收益。顺序最优还需continuation-policy Q、belief/state转移；几个fixed-tail logistic heads≠Bellman solution。

**[I] 本轮A最小判据：**q20/qe分开预测正确还不够；需Δ排序/挽救净率有效，跨cell至少初步保持。next-round success的T3并未检验此对象。

## 5. 五个open questions：直接答案

| DR:53–57 | 冻结答案 [S] |
|---|---|
| Q1 test hull还是cal选？ | **主：cal选并freeze endpoints/weights。** test hull report-only；包括五臂×Rc及adaptive proxies。禁止在TEST按π realised FER重新取最佳baseline。 |
| Q2 600 per-cell vs pooled？ | **pooled predictor主，cell-specific operating threshold可。** 相同code/N/ρ；输入可部署known-cell metadata。per-cell fit仅secondary上限，不替换主失败。pooled trained四cells≠条件外transfer；另做预定leave-one-cell-out。 |
| Q3 `.02` vs`1.64 SE`？ | **两者均非搜索后保证。** 用target-dependent、预先固定buffer：`m_c=1.645√(ℓ_c(1−ℓ_c)/600)`，约.0201/.0269；所有classes同规则。它只是selection buffer。主TEST的confidence门负责认证；若要calibration guarantee，另用独立certificate或finite-family LTT，不伪装此公式。 |
| Q4 15%合理？ | **作为工程go/no-go point bar可；不是TCOM数学标准。** 对强adaptive参照的steady-state完整receiver时间，点省≥15%、CI排除0；不能说“95%保证省≥15%”。近邻controller也有大收益；仍须state/action机制增量。 |
| Q5 PASS无信息的条件？ | **未来/truth特征；E1–E3漏baseline；弱stall冒称prior复现；CAL/TEST复用；same-data多重调参；test-hull追点；只算inner updates；旧10-frame时间拼接；忽略policy/calibration/支持获取；genie→deployment偷换；只胜fixed而不胜generic risk controller。** 详§6–7。 |

## 6. Next run (b)：可冻结协议 [S]

下列是独立建议，**未执行、未代替Claude正式freeze**。仅需每frame五臂E10/E0/E1/E2/E3；不增加新的receiver action path。分析replay、prediction timing不算新增channel/receiver arm。

### 6.1 Cells / frame隔离 / power

| cell | SNR dB | ρ | L / K=8L | hard target ℓ |
|---|---:|---:|---:|---:|
| C1 | 6.5 | .3 | 16 /128 | .10 |
| C2 | 6.5 | .3 | 20 /160 | .20 |
| C3 | 8 | .3 | 28 /224 | .10 |
| C4 | 8 | .3 | 32 /256 | .20 |

N/code/support/prior/receiver内核按ES固定；known/genie delays范围。**不自动把ℓ提升到.2/.3。** cal无baseline达到target→该cell标nonoperable/不能PASS，仍保留预定分母4。可说明target失配；不能删cell再报3/3。

**TRAIN：**旧namespace `129abc...` frames0–599，6.5存量可复用；8补同五臂。所有既看过资料仅作TRAIN/design。q fit用TRAIN，不用CAL/TEST labels。已有cal0–599被post hoc反复看过；本轮不能再叫独立calibration certificate。

**CAL / TEST新namespace：**建议entropy明确固定为SHA-256 digest of ASCII `AFDM_C1_APRIME_B_20261013_R3`，lowercase64hex传ED `--entropy-hex`；正式freeze记录digest，确认旧config未用该digest。这里只定义，不运行hash/仿真。CAL frames0–599；TEST从600起，长n_c见下。**ID需包含(namespace,frame)**；仅偏移frame无freshness保证。旧J/V2已看600–679（`c1-codex-handoff-joint-fp.md`:26、34；`c1-joint-fp-theory.md`:83）；ED:14表明同seed复用obs。old300–599现也只能TRAIN。

**CAL用途：**冻结每class参数、P*、baselineB*、mixture weights、decision/model超参、margin、code/trace/cost定义；随后封存。不可看TEST后换per-cell模型、阈值、target、cost currency或baseline。

**TEST样本量规则，CAL完成后、开TEST前一次决定：**

```text
q̂cal = mean 1{Y(P*) ≠ Y(B*)}，用已选policy及预定mixture实际hash allocation。
q_plan = min(1, max(.04, q̂cal + 1.96 sqrt(q̂cal(1−q̂cal)/600) + 1/600)).
n_req = 100 ceil(95,100 q_plan /100).
n_c = min(10,000, max(4,000, n_req)).
```

95,100来自§1四cell corrected、d0=0、η=.01、80% NI power近似。**q_plan只是planning inflation，winner所选CAL不是其valid confidence bound。** 4000足够与否取决于q、真d；若`n_req>10000`，记录power cap，不能称80%设计。成本不足的方案需在TEST前缩为screening并明确降级；不在看结果后加帧。TEST一次读完；无optional stopping。n_c≤10000，frame范围600..(599+n_c)。四cell关联用shared frame bootstrap，不把20条arm/cell rows当独立。

**[D] 绝对FER门也有power：**其近似n取决于 `pπ(1−pπ)/(ℓ−pπ)²`，不由q决定。m有用但不是true p保证；pπ真在ℓ边界，任何有限n都难以高power认证`pπ≤ℓ`。把贴门CI判inconclusive，不能叫FAIL机制。

### 6.2 因果replay / action-risk定义

**G0先验收trace，再freeze模型：**

1. 每frame五臂obs/hash相同；所有r≤e，Ee与E10的`dsha/syn/cerr/ierr/dec_iters_r`数值前缀一致。现closure仅E10/E0对旧anchors，没查新switch前缀（EA:76–83）。加入所有escalation prefix检查。任何不一致→停止科学比较，先修trace；不重标label救结果。
2. 可观测state `z_r=[log1p(syn_r), dec_iters_r, r, Δlog1p(syn_r)]`；r1的Δ固定0。ED:97已存`dec_iters_r`，无须额外decoder runs。扩展metadata仅`K/N, known σ², Rc, e/current mode`及预定交互；不含ierr/cerr/truth I_ll、eps_ce、true h、未来轮统计。r0无decoder features；**P*统一start20**。E0是baseline；不“偷看r1再倒选E0”。
3. 终止score沿用ES:17：syndrome0立即stop；Rc到达输出当前hard bits，actual `ierr>0`为fail；give-up一律erasure/fail；syn0错码仍算fail。不得剔除give-up帧。若希望cap无syndrome也一律NACK，另报更严格operational FER，对全部classes同改；不混主口径。
4. 只允许一个20→40永久switch；end of r∈{1,2,3}，下一轮开始40。r>3仍未switch者只能20到cap。give-up只在r≤4且r<Rc；无40→20、重启、e4以上、随符号预算。

**q queries：**统一pooled模型`q(z_r,e,Rc)`，训练五臂所有live `r<Rc` rows，label=`Y_Ee,Rc`。共同低前缀：q20＝e10 query；立即升档qe＝e=r query，Ee与E10在该r数值前缀相同。已升档后或B3 fixed arm：用当前Ee实际state查询其e。E0也有训练rows；不能只训练E1–E3再给E0外推充baseline。Rc作为输入，不能用R10 final label去选Rc4。r≥Rc无decision query。

**固定tail说明必须进论文：**q label中的future＝该臂syndrome-stop直到Rc，**无后续adaptive give-up/新switch**。P*可重复观测后重新决策；其closed-loop FER由完整replay直接测。q queries不是P* continuation Q，也不是逐时刻conditional guarantee。

**pooled logistic fit：**按TRAIN frame分组，四cells等权，单frame多arm/r/Rc记录总权重归一；unweighted-class cross-entropy，不用balanced-class LR后直接当probability。标准化仅TRAIN；ridge λ从预定`{.001,.01,.1,1,10}`以TRAIN五fold按frame Brier选择，tie更强ridge；固定无高阶全trajectory特征。若某训练fold全部target相同，显式使用Jeffreys-smoothed事件率并报事件数，不静默失败fallback。CAL不重fit q；per-cell fit secondary。

模型列固定：generic列=`z, Rc/10, e/10, mode`，mode＝已执行当前轮的T是否40；full A再加`K/N, log σ², B_rem/400, (K/N)·B_rem/400`。`B_rem=20·max(0,min(e,Rc)−r)+40·max(0,Rc−max(e,r))`，即假定fixed tail到Rc的剩余inner steps；不是逐帧真实future-stop工作量。q20是`20(Rc−r)`；立即升档或post是`40(Rc−r)`。LOCO/ablation均同结构；B3/B4允许这些相同metadata，免把侧信息优势算method增量。

**P family＝DR最小实质修订：**

```text
先syndrome-stop / cap-stop。
若low mode、r≤3、q20>τe、Δe=q20−qe>κ：安排下一轮升40。
本次所选fixed-tail risk qsel：升档用qe；不升用q20；已升用post-head。
若r≤4、r<Rc、qsel>τg：give-up；否则执行已选continuation。
```

所有阈值、`Rc`只CAL选：`Rc=1..10`；`τe∈{0,.1,.2,...,.9,1}`；`κ∈{0,.02,.05,.10}`；`τg∈{.5,.6,.7,.8,.9,.95,.99,1}`。阈值1为off；strict `>`；动作优先次序按上列，give-up时不执行未付费的下一轮escalation。无需开新臂。

**选择：**对P候选的CAL `(FER,cost)`，可同baseline一样用frame-independent time-sharing hull；选FER≤ℓ−m的最低cost点，至多混两policy。tie低FER→少decision queries→固定字典序。需freeze endpoints/weight，不能在TEST按当前FER移动权重。mixture用独立于message/noise/channel的hash/PRNG stream，每frame一个U；TEST实际选其中一policy，保留Bernoulli FER。不要把fractional weighted labels塞进binomial CI。

### 6.3 强baselines：同target、同calibration机会

| class | 冻结候选 [S] | 角色/阅读边界 |
|---|---|---|
| B0 clock | 五臂×Rc1..10＋共同syndrome-stop；重复prefix可去重 | 必须含E1–E3。CAL lower hull；代表本action family的condition-level schedule。不是Ylioinas完整EXIT算法复现。 |
| B1 syndrome give-up | 任一B0 schedule；rg1..min(4,Rc−1)，`syn/Mchecks>θ`；θ=0:.025:1，含off | Shin/T2-style proxy。所有五臂上调优；不只在旧E0赢家上加give-up。 |
| B2 progress/stall | 任一B0；当前syndrome fraction>θs，最近w次`Δsyn/Mchecks≥−θd`则give-up；w∈{1,2,3}，θs=0:.1:.9，θd∈{0,.01,.025,.05}；r≤4，history不足不触发 | convergence/stall proxy。不是Lee exact算法或Amador SCMS。全syndrome/history可由五臂算。 |
| B3 predicted failure | pooled terminal-failure logistic，generic z含r/Δsyn/decoder iterations；固定任一B0，按τg于r≤4give-up | Strodthoff-like progress failure predictor迁移；同TRAIN/CAL和model容量。无HARQ收益假设。是必须加入的强learned proxy。 |
| B4 generic adaptive promotion | 与P相同pooled q模型、Rc、τe/τg网格；只按q20>τe升级；不以qe/Δ决定是否升档，升档后的give-up仍用该tail risk | DR原policy的强control。区分“generic失败预测＋升档”与action-conditioned挽救价值。不能只胜不升档rules就报新机制。 |

**B***＝B0–B4所有CAL candidates的union lower hull，target同ℓ−m，freeze一个点（最多两policy）。P也允许time-sharing，geometry对称。cal costs加各自feature/prediction开销；所有baseline的early stop、cap、fail口径相同。最低cost baseline是否来自B4，本身要报。

另封存每个class自己的cal optimum作secondary contrasts，不能TEST再选赢家充主。B3/B4必须实际拟合/实现，不可用未调阈值的toy版本。

**限制：[I] 五臂不支持完整prior-art重现。** Amador的SCMS erased-message kernel、Alves的FLPSCV→BCJR、Ylioinas任意block activation序列都不在本action set。此run可杀/支持**五臂family内**的实用增量；成功不能写beats those original receivers。若TCOM方法最后站住，再决定更完整prior-art或second receiver验证；本轮不扩run。

### 6.4 Cost currency / overhead

**主currency：quiet、实际路径的完整known-support receiver elapsed seconds**，用新五臂自身` t_cum[r−1]`＋feature/q/decision overhead；包含pilot front、CE、joint inference、LDPC。**不以all20/all40轮均值拼成主cost。** ED:94–97已有所需字段；先核ready时间起点含pilot且无double count。simulator生成channel/message不计receiver。

- timing采集：单线程、固定hardware/software，warm-up只影响cache不看TEST labels；five arm执行顺序按frame循环平衡/预定seed打乱，hardware负载诊断预定。保留timing blocks；不因为某cell不省时再选“quiet subset”。仅环境故障可按与方法无关的规则整block重采并留档。
- causally选e后，数值path＝Ee；终止轮s取该Ee的`t_cum[s−1]`。真实π不执行另四臂；replay不能把五臂总time计成单frame部署cost。执行未升档时取E10前缀。公共prefix的数值等价须G0通过，timing差异由平衡顺序/分块处理。
- feature/q推理计时用同host既有z记录，独立replay timing repetitions；不得用future/truth。主cost计每frame真实query次数；simple baseline也计自己的overhead。预测器setup/load注明steady-state scope。
- secondary：inner updates、outer rounds、LDPC iterations、tail/p95 cost、组件seconds。若只能旧10-frame proxy，结论降为“reference-cost screening”，**不能过完整CPU 5(b)门**。
- support acquisition此run用genie；不包含真实support search。主张仅known-support processing；其部署完整cost另需证据。

**calibration accounting：**报五臂data collection＋fit/search总成本，baseline对应成本，同共享数据不要重复虚记。steady-state saving不等短session净收益：

```text
Cπ,eff(M)=E[Cπ]+Ccal,π/M;  CB,eff(M)=E[CB]+Ccal,B/M.
Mbreak=max(0,Ccal,π−Ccal,B)/(E[CB]−E[Cπ])，分母>0才有break-even。
```

报M=10³/10⁴/10⁵及Mbreak；不把CAL后永久可用假定成已证现实。闭式time-sharing平均成本不保证latency deadlines。

### 6.5 Confidence / PASS / KILL

**Primary比较对象固定：P* vs B***。`pπ,pB,d=pπ−pB,R=E[Cπ]/E[CB]`。不追TEST realised FER hull；称**+.01 margin的近等可靠性**，不称exact equal FER。

四cell family nominal α=.05，cell α=.0125。每cell下面是intersection门；不因多个必要门再机械相乘α。四cells任意选3，仍用四cell multiplicity控制，不能先挑三个再做95%CI。CP部分可给iid下finite-sample coverage；paired score及cost bootstrap为近似。**整个PASS不是distribution-free finite-sample scheduler定理。**

1. **Absolute reliability：**one-sided98.75% Clopper–Pearson upper `U(pπ)≤ℓ`；B*也须 `U(pB)≤ℓ`才称目标可操作的comparison。若B*不满足，cell为baseline/calibration inconclusive，不TEST重选。DR的point `p̂π≤ℓ+.01`不足。CP假设iid Bernoulli frame，mixture按实际U选择，错误/give-up全计。
2. **Non-inferiority：**`U(d)≤.01`；冻结为paired Tango score inversion，one-sided98.75% upper。参考[原论文](https://www.site.uottawa.ca/~nat/Courses/csi5388/Tango.paired.pdf)，§3 Eq24–25、§4 Eq32–33；本轮已读这些部分。sign映射用failure：`x+=#(Yπ=1,YB=0), x−=#(Yπ=0,YB=1)`。给定d0，先在`q∈[|d0|,1]`最大化trinomial loglikelihood `x+log((q+d0)/2)+x−log((q−d0)/2)+(n−x+−x−)log(1−q)`；再反演 `Z=(d̂−d0)/√((q̃−d0²)/n)` 的one-sidedscore test。边界按论文处理；实现用预设count tables验sign/zero cells，不用TEST调实现。score为近似；discordant总数<20的预定保守分支用exact `U_CP(p+)−L_CP(p−)`，各component α=.00625。不可用bootstrap的zero-discordance“精确0”替代。分支整体仍按近似coverage报告。
3. **Compute：**`R̂≤.85`且one-sided98.75% paired/frame-block bootstrap `U(R)<1`；B=20000，percentile端点，RNG seed在manifest固定。重抽整frame全部paired outcomes，跨cell相同frame ID同步；n_c不同时按“哪些cells拥有此ID”的availability集合分层，层内保留原frame数。timing shared block也重抽。不把reference constants/同frame轮当独立。点15%＋confidence positive；若要“保证≥15%”，门必须改`U(R)≤.85`，本建议不做该更强claim。
4. **Coverage：**至少3/4 cells同时通过1–3，且含两SNR。四cells非operable/trace缺失不得删除分母。pooled主policy失败不能由per-cell secondary补PASS。

**[S] G0–G5 frozen用途：**

| gate | 最小证据 | pass / kill / inconclusive |
|---|---|---|
| G0 trace与因果 | 五臂共obs；switch前prefix closure；可观测features；sample IDs/cost字段 | mismatch/future/truth泄漏→证据无效，暂停比较。不是科学kill。 |
| G1 operability＋calibration | 四固定target；CAL选择sealed；TEST CP及pairedNI | 强证据超target/NI→该policy kill；贴门CI→inconclusive。不得提δ救。 |
| G2 实用5(b) | P* vs CAL强参照B*，fullcost、overhead、fixed multiplicity | ≥3/4 PASS＝development可继续；不足且CI尚可能≥15%→inconclusive；upper possible saving仍<15%且可靠性成立→选中policy kill。family kill另需多候选同时证据。 |
| G3 novelty increment | 封存B0–B4各赢家；特别B3/B4；P的escalation-only、give-up-only及clock-switch＋give-up ablations | 只胜B0/E0、不胜strong risk/progress controllers→kill“新controller”headline。并非自动killA。 |
| G4 A的action/state价值 | Δ预测及实际net rescue/harm；budget/load交互；预定LOCO预测 | generic z同样解释、action ranking失败、收益只clock→one-object机制未支持；有tight无增量证据则kill该机制。CI宽→inconclusive。 |
| G5 scope / Trans | 两SNR只作b筛；实际support/secondcode/第二receiver或少校准transfer留后续 | 本run通过仍不宣称TCOM已达标；genie限定不能自动写deployment。 |

**G3/G4的可运行细化：**同五臂，无新增sim。

- 各次common-prefix可选state，按TRAIN预先固定的Δ quintile边界，TEST报`Y20−Ye`均值、harm/rescue两个频率；不把高q20的failures比例冒称Δ。round e、Rc、cell分层；同frame重复state用cluster CI。最终P的实际policy决定净reliability/cost。
- LOCO：每次q fit只用其余三cell TRAIN，held cell CAL/TEST不重fit q；主P操作阈值仍按既定CAL协议，另报**未经held-cell概率重标定**的Brier/calibration。主pooled四cell fit与LOCO列分开；后者预测迁移不是完整policy zero-shot迁移。
- generic G与full A模型列按§6.2固定；TRAIN拟合与ridge规则同，LOCO比较frame-averaged Brier。cap R不同、剩余预算不同要区分，不能r单独当physics。B3/B4主baseline保留full metadata；G模型仅作受控state ablation。
- pragmatic G4 positive gate：LOCO四cell中≥3，full A的Brier gain≥.005（固定工程效应线）且frame-cluster one-sided95% CI排除0；实际Δ高quintile净rescue大于低quintile，pooled差CI>0。此为**developing A-support**，不证明充分state/普适law；若未达但interval很宽，留inconclusive。
- G3 novelty-specific positive：预定两SNR合并、四cells等权，对B3、B4各自CAL冻结赢家，P平均cost ratio≤.95、one-sided97.5% paired/frame-block bootstrap lower saving>0；相同分层bootstrap的97.5% upper d≤.01。两contrast α=.025 each，nominal整体.05；不同n_c按cell均值再等权，不能按rows加权。此为secondary，不补primary失败。5%是新增Δ predictor的最小工程增量，非TCOM行业标准。

**明确KILL one object（不是只没PASS）：**

1. [I/S] 可靠性达标后，强adaptive参照已覆盖全部收益；在≥3cells中，P对B*的saving upper CI<15%，并且对B3/B4的increment upper CI<5%。这给“实用增量不足”的正面证据，结束本次选中one-object方案；不再挪threshold重跑。若未对其余候选同时认证，不能升级为整个family不可能。
2. [I/S] A的LOCO Brier gain upper CI<.005、Δ排序净挽救差upper≤0，且generic controller已同等cost/FER。机制/预测双失败，kill“load-cliff state导致新scheduler”中心；可保留负结果。单个cell extrapolation失败只限定范围。
3. [I/S] 所有可省≥15%的CAL封存候选在TEST均有可靠性损害的明确证据，而安全候选被tight upper排除15%收益；说明受限action family无所需trade-off。需预先封存这组候选并对多候选CI同时控制；若只检验P*，只能kill选中policy，不能宣称family impossibility。
4. [I/S] “优势”只在少计LDPC/CE/feature开销或用truth/未来信息时出现；修正后相应CI明确排除门线。kill原实用主张；数据泄漏本身先标invalid，不伪装receiver机理结论。

**保留出口：**A′未过b，但A的LOCO/action预测有力→A-only 5(c)可继续，需真正few-calibration transfer/design regret证据；generic controller够用但A有机制→方法改为generic并诚实降novelty，不能继续宣称action-risk新法。A与b都tight失败→one object kill，回B（soft-feedback correlation修正）或限定diagnostic rescue；Trans保持open，venue由用户决定。

## 7. 冻结前必须写进manifest的差异

**[S] 必改DR：**五臂全进baseline；补B3/B4；qe进入promotion；固定tail/Rc labels与closed-loop风险分开；新namespace；target不可自动上调；CAL封存hull；q-dependent power；新五臂实测quiet fullcost；test CI门＋四cell multiplicity；全give-up计fail；scope known-support。

**[I] 公平对Claude：**gate critique抓住selection、granularity、currency、operating-tail、范围；把A/A′收为同一决策对象有用。独立分歧：post hoc还未证class收益；E-clock baseline遗漏最关键；2000帧不是通用认证；最近CE-quality switching工作更近；普通risk calibration不自动补足TCOM新颖性。**建议一次严格判别，保留真实failure出口；不再靠“online”三个字提高创新等级。**
