# A transfer protocol — calibrate once, predict elsewhere，2026-10-13

状态：**分析预登记草案；Claude freeze后执行。** 本轮仅schema/config/source阅读；未拟合、未算target指标、未仿真、未改code/git。唯一写入本文件。标签：[F] fact；[D] derivation/definition；[I] inference；[S] proposed test。

## 1. 一个问题，一个主predictor

**[S]** 在同一scalar-approximate SP joint receiver上，用一次SOURCE校准的低维state/budget model，给未见条件预测固定schedule的FER，并选满足δ的最低inner-budget配置。主对象=A的5(c)候选；不复活A′ scheduler，不用Kc(.5)代替工作点δ。

**[F]** `research-assets/res-20261013-01.md:18–38`：G4预测/排序有信号，decision增益未见；一ρ、genie support、单code/N限制仍在。`research/claude-code-review-20261013.md:16–22`要求后续Kc用upward-only isotonic crossing。M1限定：测到的是scalar-approximate DPSS receiver，不是exact vector AMP（同review §Codex KR）。

**[I] Scope先锁。** 此test允许每个目标条件的一小批**无标签round-1 probes**；随后预测Rc终点。不是仅凭(K,ρ,SNR)的零测量公式，不是逐帧genie-I_ll预测。若5(c)要求完全没有target probes，现有state models不满足该强版本；不能改名绕过。N=1024、同QPSK/LDPC、same channel family、已知genie delays；通过也只支持该scope的design criterion候选，未达TCOM提交标准。

**[S] 主模型只选一个：A-prefix7。** SOURCE-only reduced logistic，见§4。不以旧seal full/generic/rescue直接作主检：

- **[F/D] 随机流重叠。** 旧target frames0–199与原TRAIN0–599同entropy；message/noise不按ρ/SNR/L重seed，channel按frame/L。只排“相同cell”不够。原seal已见这些parent frames；8dBρ.3 L28/32还见过完全相同条件。证据：`driver_c1ib2.py:IB2_PARAMS`、各config `_config.c1.seeds`、`driver_c1ib.py:199–229`。
- **[F] Feature缺口。** `dec_iters_r`在c1esc/c1apb有，IB/IB2/FULL旧rows无；`ldpc_iters`是最终round，不能填第一轮。不得塞50、用final count、oracle ll_in或test-derived均值。
- **[F/D] Estimand不同。** 旧q只训练live states，Rc≥2，label=syndrome early-stop后的info error（`c1apb_lib.py:319–348`）。本A主检是**完整固定Rc轮的info FER**，含Rc1；不能直接把旧q当该概率。新reduced模型只重用SOURCE与load/budget机制，不冒称旧seal精确zero-shot。

## 2. 数据矩阵、隔离、零新仿真

**[S] SOURCE唯一：** OLD entropy `129abc3b…`；`out/c1esc`的6.5dBρ.3 L16/20、`out/c1apb_train8`的8dBρ.3 L28/32；只frames **200–599**，只E10/E0（恒T20/T40）。400 parent frame IDs；四cell×两schedule。原0–199、所有CAL/TEST/QUIET、其他旧档一律不参与fit、ridge选择、standardisation、阈值调优。

**[S] TARGET唯一主面板：** `out/c1ib2_rep`，OLD entropy，frames **0–199**，R4T20/R4T40；Rc=1,2,3,4，从同row截取固定终点。保留全部36cell、288配置；其中34cell属未见完整条件。模型/预测/选点先seal，才解封target truth。200个parent IDs同时是无标签probe cohort与evaluation cohort；属于预先锁定的transductive有限-grid验证，不声称另有独立deployment cohort。每个固定配置均有200帧；所有target配置的统一置信带覆盖其后按probe选出的配置，见§7。

| family | SNR dB / ρ | L grid | 角色 |
|---|---|---|---|
| H1 | 6.5 / .2 | 4,8,12,16,20,24,28 | unseen ρ，全7cell |
| H2 | 8 / .2 | 12,16,20,24,28,32,36 | unseen ρ，全7 |
| H3 | 8 / .3 | 12,16,20,24,28,32,36 | unseen load仅12,16,20,24,36；28/32为seen-condition anchors |
| H4 | 8 / .5 | 4,8,12,16,20,24,28,32 | unseen ρ，全8 |
| H5 | 9.5 / .3 | 16,20,24,28,32,36,40 | unseen SNR，全7 |

34个unseen cell不改分母；H3两anchor不贡献“unseen”主预测分数，仍用于完整curve、设计候选及审计。两种T在SOURCE已见；claim是未见ρ/SNR/load及其budget组合迁移，**不是unseen T transfer**。

**[S] Secondary长budget面板，不救主失败：** 6.5dBρ.3、L24/28/32、frames0–199；T20用`out/c1f_r10`的FULL_R10，T40用`out/c1ib2_r10`的R10T40；Rc1–10，60配置。`out/c1g_r10lo` L16/20为seen-condition closure anchors；`out/c1i` FULL_R4与`out/c1ib` IB_T40只供同条件prefix/arm alias核验，不另扩主面板。WARM/FROZEN、T80、T30/50排除。SOURCE已见Rc1–10；长面板检验新load×长budget，不虚称未见Rc。

**[F] 2026-10-13 SSH schema-only spot read（每档首row＋config，非完整audit）：**

| dir | 可用量 | 缺口 / 主用途 |
|---|---|---|
| c1ib2_rep，50 shards | syn/ierr/dsha1–4，T，inner_iters，t_cum，per-round seconds | 无dec_iters_r；主面板 |
| c1ib，75 | syn/ierr/dsha1–4，T，inner_iters，full seconds | 无dec_iters_r、t_cum；alias核验 |
| c1i，100 | FULL_R4 syn/ierr/dsha1–4 | 无T显式值、dec_iters_r、t_cum；FULL=T20由driver声明 |
| c1f_r10，30；c1g_r10lo，40 | FULL_R10 syn/ierr/dsha1–10 | 同上；T20长budget/closure |
| c1ib2_r10，30 | R10T40，syn/ierr/dsha1–10，t_cum | 无dec_iters_r；T40长budget |
| c1esc / c1apb_train8，各64 | schedule、syn/ierr1–10、dec_iters_r、t_cum | SOURCE；E10/E0读取 |

七个关键numeric module hashes在上述config相同：native_twofft、receiver、dpss_rx、tapchannel、physical、messages、interventions。driver/logging hashes不同，不自动等于numeric drift，也不单凭module hashes宣布bit closure。

**[F/S] 压缩处理。** 当前spot read中SOURCE为`.jsonl.gz`，上述旧TARGET仍有`.jsonl`；用户报finished rows在gzip迁移，loader必须支持两者。gzip流式读，不落地解压，不改raw。compressed MD5与uncompressed MD5分别记；reference是uncompressed bytes。若双格式同shard共存，核uncompressed digest、只计一次；digest不同→STOP，不能随选一个。

**[I] 最小新run=0。** 指定Pe、δ设计选择、optional Kc、长budget均有既存标签与prefix；缺decoder trace通过预先declared reduction解决。无需新schema/data生成。全覆盖仍待G0，不把本次sample inspection冒称complete。若缺required rows/字段或numeric parity不成立→DATA_INCONCLUSIVE，不填补、不自动跑新simulation。统计不够也不自动加帧；另行冻结fresh-entropy confirmatory test，不能追着本轮最佳/最差cell补样。

## 3. 预测对象与可用信息

**[D] 固定schedule定义：** 每轮T∈{20,40}，执行**恰好Rc轮**；终点error `Y_i(c,T,Rc)=1[ierr_Rc>0]`。无syndrome early stop、adaptive promotion、give-up。`Pe=E Y`；不是coded BER、syndrome failure或I_ll。Rc1是nowcast；Rc≥2才是future forecast。未来可另做early-stop criterion，但不得在本test混换label。

**[D] 特征白名单：** 目标已知(SNR,ρ,L,N,T,Rc)、round-1 syndrome `s_i=syn1`。K=8L必须与declared/full design `n_cols/K`一致；genie delay set提供load，不取hidden channel质量。metadata noise用receiver units：

```text
k = K/N,     v = sigma2_raw/[2(1-rho)] = 10^(-SNR_dB/10)/[2(1-rho)]
t = 1[T=40], b = T(Rc-1)/400, u_i = ln(1+s_i).
```

证据：`driver.py:227–238` rho shim；`driver_c1i.py:133–140`按round记录truth scores；`driver_c1ib.py:104–138`固定T/完整轮数；`driver_c1ib2.py:54–74`grid/arm；`c1apb_lib.py:301–311`原K/noise/remaining-budget机制。

**[S] 禁止features：** ierr/cerr、ll_in/r1_ll_*、eps_*、true gains/paths/PDP质量、e_real、未来syndrome/decoded hash、final ldpc_iters/decode_ok、full-row seconds/未来cost、frame/shard IDs、cell ID。hash只用于G0与分组，不进入预测。ρ/SNR只通过known v与实际prefix反映；SOURCEρ恒.3，不能偷偷学习未可识别的ρ coefficient。

**[I] 物理假设。** first-round syndrome代理decoder state；k表示估计维度负载；v为data-normalised noise；b为尚可投入的inner effort；kb允许effort效应依赖load。它是receiver-specific surrogate，非DoF上界/充分统计定理。ρ改变pilot/data能量，v不是全部ρ作用：例如不同ρ/SNR可有相同v但不同pilot quality，只能由prefix承接其余影响。若该state不够，迁移应失败；不按target结果追加feature。也不假定更多轮一定改善FER。

## 4. 一次SOURCE fit，三competitors

**[S] A-prefix7：**

```text
x_A = [u_i, t, Rc/10, k, ln v, b, k b]
q_A = sigmoid(beta0 + beta^T standardise_SOURCE(x_A)).
Pe_pred(c,T,Rc) = mean_i q_A(syn1_i(c,T), metadata).
```

从SOURCE四cell/E10/E0/Rc1–10构建fixed-endpoint labels，不从原`dataset()`拿early-stop labels。无live-state过滤：syn1=0也保留；完整Rc执行可能改变后续结果，不能硬置其未来error=0。总32000 records；同frame/arm/caps不是独立样本。权重每SOURCE cell1/4、parent frame1/400、T/Rc组合1/20。

标准化只SOURCE；exact-constant列先删除并记录，避免原decoder constant的近零sd问题。ridge λ∈{.001,.01,.1,1,10}；CV按frame mod5，全部cell/T/Rc同parent进同fold。CV criterion=frame-weighted Brier；Brier round到12位相同时取更大λ。各模型独立在同SOURCE/CV选λ，最后SOURCE全量fit一次、冻结系数/列/μ/σ/λ/solver。intercept不penalise；weighted logloss＋λ||β||²/2；L-BFGS-B maxiter1000、ftol1e−12、gtol1e−8、maxls100。失败显式STOP，不换优化器/λ删格。未来executor不得直接用原fit_cv给7列误标为旧GENERIC。

| competitor | 冻结定义 | 要排除的解释 |
|---|---|---|
| G-prefix3 | `x_G=[u_i,t,Rc/10]`，同label/weights/CV；无k、v、b、kb | state/iteration metadata本身已够用 |
| L-nearest | 每(T,Rc)在四SOURCE cell选nearest；`d²=((K−K_j)/32)²+((ln v−ln v_j)/(1.5 ln10/10))²`；tie按SNR,L升序。预测`(sum Y+.5)/(400+1)`，不看target labels | 四cell查表即可 |
| C-cliff | `logit Pe=theta0+thetaK ln k+thetaV ln v+thetaT ln(T/20)+thetaR ln Rc`；thetaK/thetaV≥0，thetaT/thetaR≤0；同SOURCE weights/ridge/CV | 一个简单预算/负载sigmoid即可 |

C的sign constraints是该null的假设，非A的物理结论；约束破坏non-monotone receiver时仍按原规则报告。G与A有完全相同target probes；胜L/C可能只是多了syndrome信息，**full-A added value必须胜G**。旧sealed q/rescue可留背景图，不能在A-prefix7失败后升为主模型，也不另fit rescue head。

## 5. 设计任务、cost、锁预测

**[S] δ主=.10，secondary=.20。** 同一engineering safety margin m=.02，所有方法相同；不是跨条件risk guarantee。一个design task v=(SNR,L)，候选为主面板该v确有的(ρ,T,Rc)。共23tasks：6.5dB 7个L，8dB 9个L，9.5dB 7个L。8dB L12–32有三ρ可选；L36有.2/.3；L4/8只有.5。缺grid组合不插值制造候选。

```text
C(a)=T*Rc   (nominal inner updates; exact fixed-schedule count)
a_pred = argmin C(a), subject to Pe_pred(a) <= delta-m.
tie: smaller Rc, then smaller T, then smaller rho.
no predicted feasible candidate -> NO_FEASIBLE (design abstention, not per-frame erasure).
```

**[I]** 此currency不是total receiver seconds：CE、LDPC、pilot front开销未等价成inner updates。报告Rc为第二effort量；历史t_cum仅可用档的descriptive secondary，不能用不同load/host历史seconds挑主winner或声称省时。T*Rc相同但Rc不同，按tie rule少CE轮优先；仍不冒称相同wall time。SOURCE/target probes的采集成本另列：每目标cell 200×(20+40)=12000 inner updates，加两种prefix的CE/LDPC/pilot开销；archive复用不等于真实部署zero overhead，应用须amortise。

**[S] 顺序，不能跨阶段偷看：**

1. G0 metadata/schema/digest与SOURCE partition审计；freeze本文、target名单、规则。
2. 只SOURCE fit A/G/L/C；freeze四predictors。target extractor只向预测API返回metadata与syn1；future/truth字段屏蔽。
3. 生成全部Pe_pred表、23×4个a_pred、δ-boundary panel、optional predicted Kc；带MD5/参数的prediction seal。**在任何target label汇总前**冻结。
4. 解封target ierr_Rc评估、生成observed-best与CIs。不重新normalise、fit、recalibrate、筛cell、改δ/m/rule。preflight发现out-of-range特征只标记，不clip/删格救指标。

**[S] 泄漏contract：** target truth与round2+全部scramble/删除→预测表及a_pred逐字节相同；target rows排序改变→相同；重复archive aliases→不增加样本数。源码/model/input MD5、uncompressed row MD5、_argv/_config、feature allowlist与phase时间存未来结果。

## 6. 指标：概率、工作点、设计

**[S] 主预测分数：** 34 unseen cell，T20/40，Rc2–4，共204配置；先每frame平均，再每cell/config平均，再五family equal weight（H3只5个novel load）。Rc1 nowcast、两anchor、Rc5–10全部另报，不混入主分数。

- Brier：`mean (q_i−Y_i)^2`；三个gain=`Brier_comp−Brier_A`。
- Reliability：bins `[0,.05,.10,.20,.40,.60,.80,1]`；每bin predicted mean/observed FER、record数与unique-parent数；weighted ECE及每family mean calibration bias。空bin=NA；稀疏bin保留，不能丢掉坏校准bin。相同frame的多配置不增加独立n。
- 所有288配置的Pe_pred、Pe_obs、signed/absolute error完整列出。细点不准隐去饱和区/不operable cell。
- 工作点panel：每unseen cell、每method在T20/40×Rc2–4中选`|Pe_pred−δ|`最小点（tie按§5），取四method点的union；**仅按封存预测选，不按target truth挑near-δ格**。所有method评同一个panel。`E_delta=五family宏平均绝对Pe error`；另报panel中abs error≤.05的比例。

**[D] Observed-best有限表reference：** 每task `F_obs={a:Pe_obs(a)≤δ}`；非空时a_obs按§5最小cost/tie rule。它是finite-sample empirical optimum，**不是已知population optimum**。方法不接触a_obs来改自己的a_pred。

```text
safe empirical pick:       regret = C(a_pred)/C(a_obs) - 1
unsafe pick / false abstention with F_obs nonempty: bounded loss J=1
safe empirical pick:       J=min(1, regret)
F_obs empty:               J=0 for NO_FEASIBLE; J=1 for recommending operation
```

完整报unsaturated cost regret（unsafe时undefined，不给低cost奖励）、推荐FER、δ violation、false-feasible/false-abstention、J。J宏平均按三SNR equal weight、SNR内L equal weight；23tasks分母固定。新增设计价值量=`J_comp−J_A`；不是从模型Brier偷推design gain。

**[S] Optional Kc，secondary-only：** 主五family×T2×Rc1–4=40 curves；K=8L。在K grid上分别对预测Pe与observed Pe做weighted PAVA非递减fit（weights=帧数）；只找从低于.5向≥.5的**首次upward** crossing，线性连接相邻K点插值。首点≥.5→left-censored Kc≤Kmin；末点<.5→right-censored Kc>Kmax；不外推、不用downward crossing。uncensored pair报`|ln(Kc_pred/Kc_obs)|`，≤.15比例；逐curve列censor状态，不以只剩好curve的比例宣成功。PAVA只用于Kc；主Pe/error/design用raw frozen预测，不能用target isotonic fit改model。

## 7. 不确定性、multiplicity、oracle optimism

**[S] Parent重采样。** B=20000，seed20261017；从frame IDs0–199重采样200次，整frame跨L/ρ/SNR/T/Rc同步。primary cost是确定budget，不按timing shard当独立样本。SOURCE params固定：CI是conditional-on-this-calibration，不重新fit SOURCE。

每draw重算Pe_pred与Pe_obs、同一frozen selector的a_pred、boundary panel、observed-best与J；这是bootstrap整个已登记statistic，不是用TEST labels挑新model/rule。A/G选择只依赖重采样prefix；L/C不看labels。重算oracle会反映不稳定，**不会自动消除min-over-config的selection optimism**。

**[S] 主family error预算=.05：**

- .04给六个预定增益量：Brier vsG/L/C、J vsG/L/C。每量同时报lower/upper，故每tail Bonferroni alpha=.04/(2×6)；positive gate用lower，increment kill用upper。label为approximate paired-cluster simultaneous bounds，非普通双侧95%CI。未来若实现p-values，须用null-centred统计，不能把uncentred bootstrap正值比例冒充exact p。
- .01给288个固定配置的population FER uniform bands：Clopper–Pearson两侧，各tail alpha=.01/(2×288)。seen anchors也纳入，因selector能选择它们。依赖配置间相关不破坏union bound；假设frame parents iid。它覆盖随后按无标签probe选出的配置，不要求selected配置再装作预先固定。
- calibration/error/profile plots的95%cluster CI为descriptive；engineering cutoffs是预定point criteria，不宣equivalence certificate。δ=.20、Kc、Rc5–10、所有分组afterthought不能翻转主PASS/kill；若要正式新增hypothesis，另开freeze。

**[D] Population oracle band（每task）。** 用上述FER `[L_a,U_a]`定义possible feasible `F_pos={a:L_a≤δ}`、definitely feasible `F_def={a:U_a≤δ}`。

```text
C_pos=min C(F_pos), C_def=min C(F_def), if defined.
If F_def nonempty:             C_pos <= true optimal cost C* <= C_def.
If chosen U_a <= delta:        max(0,C_a/C_def-1) <= true regret <= C_a/C_pos-1.
If every L_a > delta:          certified non-operable on this finite grid.
F_def empty but F_pos nonempty: optimal cost/operability unresolved; NOT impossible.
```

若chosen没有U_a≤δ，不能叫risk-feasible；若regret upper宽，不能叫near-optimal population design。empirical best的optimistic cost/FER与bootstrap bias都明列；不能用point oracle差直接写真最优保证。

**[D/I] n与power限制，非本轮算出的结果。** n=200在p=.1处binomial SE≈.0212、普通95%half-width≈.0416；p=.5处half-width≈.0693。Pe±.05的普通precision粗需n≈139（p=.1）或385（p=.5）；uniform288 bands更宽。因此不要求每个cell各自显著，也不把Kc小CI当默认。paired gain阈值h的粗power要求`n≈[(z_(1−alpha)+z_.8) sd(g_i)/h]^2`；sd未知，本轮不臆报power%。不确定→INCONCLUSIVE，不自动扩n或降门。SOURCE/target有共同frame seed结构，独立n不是204×200，也不是32000。

## 8. Pass / kill，冻结后不得改

**[S] 下表判的是本A-prefix7，非所有未来A。** 主任务为一次archival transfer screening；历史data与部分aggregate结果已被早期review见过，不能写成data-collection-before-hypothesis的prospective trial。

| gate | 固定条件 | 失败如何解释 |
|---|---|---|
| A0 integrity | SOURCE/target parent不重叠；五种family全覆盖；correct arms/endpoints；known receiver/checkpoint/code hash；alias prefix一致；truth-scramble不改预测 | DATA/IMPLEMENTATION_INCONCLUSIVE；不算科学kill；修record/parser须retain seal与审计，不改数学criterion |
| A1 calibration / delta | ECE_A≤.05；每family abs calibration bias≤.05；E_delta≤.05且≥80%boundary-panel points abs error≤.05 | 点门未过→NO_PASS；若相应cluster lower已排除阈值→transfer falsified |
| A2 added probability value | Brier gain vsG point≥.005；vsL/C point>0；三个Bonferroni lower>0 | 无full-A added value不能靠赢弱lookup讲机制；宽CI=INCONCLUSIVE |
| A3 empirical design | J_A宏平均≤.10；≥80%tasks J_A≤.10；三J gains point≥.05且Bonferroni lower>0 | calibration好但不能改善设计，5(c)中心未完成；不以Kc救场 |
| A4 population check | 逐task给FER/optimal-cost uniform bounds；声明feasible须U≤δ，声明regret≤.10须其upper≤.10；declared NO_FEASIBLE须所有L>δ才能certify | unresolved保持unresolved；不凭经验optimum认证FER/近最优 |

**ARCHIVAL_TRANSFER_SCREEN_PASS**仅A0–A3全过；A4限定其能说多强。不能把该screen pass当population-optimal/FER certificate或TCOM已达标。若要称本有限-grid criterion已认证可靠且近最优，另需至少80%全部23tasks通过A4：操作推荐的U≤δ且regret upper≤.10，或拒绝的全部L>δ；不得仅在容易/被选择的feasible子集算80%。未过A4不虚构kill，明确population design证据不足。

**[S] 科学kill rules：**

K-A1的negative decision family另预定七统计量：E_delta、五family abs bias、false-feasible比例；其lower均用单侧alpha=.05/7的同步parent bootstrap。它是单独的负方向decision family，不与positive-PASS的nominal .05混称一个联合证书。K-A2/K-A3的increment upper用上面六量simultaneous bounds。所有bootstrap界仍近似；若δ附近可行性/最优点跳变导致非regular，报告point sensitivity与uniform bands，不把bootstrap单独当population设计certification。

1. **K-A1，迁移失效：** A1的E_delta lower>.05，或至少两family abs calibration-bias lower>.05，或false-feasible task比例lower>.20。kill该一次校准criterion；禁止target intercept/feature修订后把同test改报PASS。
2. **K-A2，load/budget增量归零：** vsG的Brier gain upper<.005，且J gain upper<.05。kill“full-A额外predictive/design value”中心；G可用不算A成功。
3. **K-A3，只有概率诊断：** A2过，但vsG的J gain upper<.05，且原始a_pred与G在≥90%tasks相同（含NO_FEASIBLE）。kill本variant作为有额外设计价值的5(c)中心；保留概率/机制诊断，不复活controller。非否定所有A理论。
4. **K-A4，错误跨对象：** 只能预测50% Kc、不能预测δ tail/选配置；或必须目标future states/truth/per-cell fit才能达到A1/A3。kill本test宣称的“calibrate once, predict elsewhere”。

主不通过但CI仍包含有用effect→INCONCLUSIVE/NO_PASS，不强kill，也不按结果换模型/τ/ρ/δ。只有secondary通过不能救主失败。新增kernel B/M1、第二code/N/support mismatch是新receiver/scope，须新protocol；本A和B并行，不共享target-label调参。

## 9. Freeze交接与证据索引

Claude freeze前只需确认本文是**带round-1无标签probes的fixed-endpoint criterion**；如果要冷启动纯metadata公式，须显式改目标，不将此test偷换。未来模型seal必须注明与旧(b) seal的差别：SOURCE200–599、fixed endpoint label、7/3列、全prefix样本、ridge/CV、δ/m、candidate pool、seed、CI/multiplicity；旧seal `466a92d0fa371e7871c97c475ff0a906`不改。

证据：`research-assets/res-20261013-01.md`；本task `research/claude-code-review-20261013.md`、`research/codex-direction-r1-20261013.md` G1、`research/codex-aprime-check-20261013.md` §6及A-only出口、`research/collab-plan-b-20261013.md` Next workstreams；`experiments/headroom_ladder_20261008/{driver_c1i.py,driver_c1ib.py,driver_c1ib2.py,driver_c1esc.py,c1apb_lib.py}`；各`out/*/config_shard000.json`。Remote schema inventory根=`/data/guoyikun/00inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/`；本轮仅read，不产生remote文件。未验全row digest/coverage/paired parity；这些是未来A0，不冒充已过。
