# 两方向可行性审查（保存结果与适用范围）

**TAIL 风险可行性通过；CWORD 在已测合法候选对上没有额外排序收益。** 合同、保存结果、主端点和联合报告的适用范围已由主会话核验，独立性 weak。TAIL 新进程核验已留下成功工具回执，原四份文件仍待逐字节回传及 Git 交付，见[接续附录](tail-completion-recovery-review-v1.md)。以下保留工程前代数检查及生产后核验。审查范围由[共同计划](next-method-feasibility-plan-v1.md)与[backend规范](../../../spec/backend/research-diagnostics.md)限定；不据此判定 FER、独立确认或 Transactions 贡献成立。

## 独立代数核验

- 理想有限 DFT 以 `r=bin−centre` 时，`FFT(exp(+j2πκn/N))[r]` 必须乘整数物理算子 `U(l,centre+r)`；若写 `m=centre−bin`，则是同一个 `alpha(-m,κ)U(l,centre−m)`。先对 N16 的 delay0/3 与 N31 的 delay4 做时域 CPP→DAFT 全 bin 展开，相对矩阵误差分别 `1.27e−15/1.86e−15/3.40e−15`；整数 U 与同一时域路径相对误差最大 `1.82e−14`。随后校验**CE分析 snapshot** `source-v4` manifest SHA `176cfd...` 及 `supplement_pilots/afdm_baselines/physical_stride` 文件条目和当前工作树逐字节一致，从其 CPP/DAFT 函数重跑 N31、delay4、ν1.3：对 bin0/1/2 的真实矩阵 Frobenius 投影复系数分别为 `0.13687364248513234+0.14399099011617839j`、`0.5255088658486744+0.6789014852120341j`、`−0.19476018234143774−0.31246381059181677j`，分别对齐 r−1/0/+1 的正号时域 Doppler FFT，最大差 `<1.3e−15`，全 bin 重建相对误差 `1.01e−15`。旧DIR生产 snapshot manifest另为 `50fb12...`；它的 `supplement_pilots/supplement_g1` 条目与CE相同，`afdm_baselines/classical_joint_unrolled` 条目不同。TAIL须同时绑定旧 ridge 产物和实际分析源码，并在工程核整数U与保存设计/H一致，不能默认两整个源码树等同。在**完整物理 CPP 算子**这个口径下没有额外 delay-dependent 系数相位；不能由理想 FFT 系数代替该算子检查。
- A3/A5 的复交叉方向正确：`M_zt=E[z g_Tᴴ]` 是 core×tail，`2Re tr(F M_zt)−tr(F M_zz Fᴴ)`。独立 N32 直接 FFT、训练5万/测试10万合成样本给经验改善 `0.06309699937975177`、矩公式 `0.06309699937975183`，误差 `5.55e−17`；故意错中心的测试改善为 `−0.275811`。这是合成代数，非 G1 性能。
- B1 随机复数 12×4 小矩阵、共同 `λ=0.1`，直接最小化残差加 ridge 惩罚得 `13.358484062987607`，二次 profile 得 `13.358484062987610`，差 `3.55e−15`。它验证 profile 代数，不验证合法码字覆盖。
- 另用 N31 的三个物理原子 `(delay,k)=(0,5),(1,0),(2,−5)` 构成相同 row-shift=5 的别名。保留完整 delay 相位时，Frobenius Gram 非对角最大 `1.22e−16`，H 的逐原子投影系数误差 `1.12e−16`，dense 完整 H 误差与 `N·||系数误差||²` 差 `7.22e−16`。这支持正交投影恒等式；运行实现仍须核实际 G1 与冻结分析源码，不能只按row shift合并。

## 冻结实现检查

[TAIL合同](tail_completion_contract_v1.md)/[runner](tail_completion_v1.py) 保持 ridge 核心 `g_solution` 原样，T 仅同选中delay的 `k∈[-5,5]` 扣S；真核心与部分真中心属于不同oracle层，部署中心只从当前z的最大幅值选出。F来自128点κ求积、名义q=.01，未读目标真κ/增益缩放。完整H用实际delay相位的物理U评分，另存S及S∪T表示残差和响应风险。DIR生产50fb与CE分析176c源码manifest分别绑定；工程0/20先做24个层内比较、saved A重建/逐列U/A@g闭合及alias检查，写持久工程admission后才进入其余30块，不重复工程。F构造、尾输出、投影和响应均逐类计数，0新receiver F/CE/BP/LDPC并不代表零线性成本。

v1首次工程启动在首个F血缘守卫拒绝，exit1/2.771秒，预读1物理A与1ridge F，0个配对比较，原失败与脚本SHA均保留。[v2合同](tail_completion_contract_v2.md)/[runner](tail_completion_v2.py) 只修块0/20选原G1**工程A**、其余30选开发recovery A，以及旧DIR生产记录的精确 `truth_access='offline scoring only'`；F、三层、四端点、384比较与工程24门未改。工程/开发G1摘要及raw收据四SHA本地对齐，v2三个小N测试新鲜PASS。随后v2的真实保存比较与工程admission也均完成，下段核其结果。

**TAIL v2 现已得到已存开发风险证据。** 工程0/20的24个层内比较先写SHA绑定的admission，随后其余30物理块一次完成；summary COMPLETE、384行及同进程重读audit PASS。本审查从行表重算同一32物理簇、20,000次共同配对bootstrap、冻结seed202609150701和四比较Bonferroni `[.00625,.99375]`，实际核心/实际中心臂的补全减同核心F=0均值及同时95%区间为：t1完整H `−0.019470 [−0.025565,−0.013901]`、无噪真响应 `−0.017018 [−0.023285,−0.011312]`；t9完整H `−0.026076 [−0.031428,−0.021315]`、响应 `−0.024975 [−0.030584,−0.020075]`。四区间在这批已暴露开发信道中均低于0；128个合法输入状态中完整H改善124、响应改善120，仍有4个t1完整H恶化状态。

表示上，原S的真实投影残差平均`0.058653`，有限S∪T残差平均`0.015787`；这是可覆盖能量，并非实际估计收益或全N尾可消除。实际输出每状态平均增加`157.16`个**非零**尾原子，完整检测图、后续CE及FER均未运行，不能据此称同成本接收收益。两实际核心臂的ridge `g_solution` SHA及同核心F=0 baseline逐状态一致；真核心臂的baseline另算，未混入合法对照。部分真中心oracle仅在864个唯一真路径delay出现中替换了14个实际中心，不能把它称为强错中心应力检验；选中delay中大量没有真路径，有限窗外/未选delay残差依然存在。v2 producer含同进程自审supervisor exit0 `60.215`秒，v1失败`2.771`秒另计；39次F矩阵解、128次保存A分析重建、9823次逐原子投影和69520次非零原子响应动作均单列，0新receiver F/CE/BP/LDPC。其raw audit是同进程重读，科学独立性弱。

[CWORD合同](codeword-profile-method-v1.md)/[runner](codeword_profile_runner_v1.py) 核全部64旧F/A配对，只在原ridge15失败点评分；工程2点≤6唯一候选refit，开发余13点≤39，总≤45。三者 `true_c/decoded_raw/reencoded_info_hat` 各保身份，原decoded无效只作非合法诊断。逐点共用实际旧t9 S、y/p和由保存A决定的λ，核Q；真值只生成oracle truec。固定H使用实际终端H，同时存相对t9 H与纯S/g重建H两差距。CE分析源与DIR生产源双manifest绑定，并以冻结CE分析U重建旧t9保存A作2e−6相对数值门；profile直接目标、闭式分数、法方程及唯一bit SHA→唯一profile record/refit数均在审计闭合。新profile是零中心惩罚，不等同旧previous/proximal CE，也不是含logdet的边缘似然。

**CWORD 真实保存结果现已审计完成。** 工程2点+开发13点的summary均COMPLETE、raw audit均PASS，6+39=45实际唯一候选信道refit，审计0新增refit、0新receiver CE/F/BP/LDPC；四份supervisor exit0合计39.907秒。15行分数/margin与固定正值“真胜”方向独立复算一致，旧t9保存A与分析算子最大相对偏差`5.59e−8`、Q门最大`1.69e−7`。原`decoded_raw` **15/15无效**：真码字固定H/profile各胜10点，1救回+1新增错误，这只是不合法向量诊断。合法`reencoded_info_hat` 15/15由固定H和profile都排在真码字之后，0救回/0新增错误。本轮没有发现合法候选的profile排序增量，不支持据此投入有限列表或称部署收益；真码字始终是oracle参照，列表覆盖未测。旧G1环境JSON未在本地逐文件复哈希，生产及raw审计绑定它；其余本地结果/退出与CE/DIR manifest哈希对齐。

早期 A/B 两组目标测试共7项PASS（1.50秒）；接续时9项TAIL/CWORD目标测试亦已通过，见[测试回执](resume-evidence-v1/afdm-feasibility-recovery-pytest-v2.json)。测试验证代数、phase、alias、候选身份与失败守卫。[TAIL报告](tail-completion-results-v2.md)、[联合结论](next-method-feasibility-results-v1.md)及[审查 JSON](next-method-feasibility-review-v1.json)现已完成范围核验；原四份核验文件的逐字节回传及最终Git交付仍待完成。新进程复算增加39次预测矩阵求解、384次数学比较，累计117次求解、1152次比较、94.428秒，唯一生产比较仍为384。

两方向只在已暴露开发 G1 上做有限诊断；实际输入的H/响应改善支持下一份冻结接收实验，不能算 FER、独立 CONF 或方法新颖性。接续的[实际终端合同](tail-terminal-contract-v1.md)已冻结，但尚无目标运行结果。CWORD合法重编码诊断没有给出profile排序增量；不能把TAIL有限风险改善与CWORD真码字诊断合成联合接收收益。
