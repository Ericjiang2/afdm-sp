# RUN-04 固定最终支撑增益桥接：归档可用性与最小接线

2026-09-06。只读检查源码和fit192归档，并用Python解析全部192条记录；没有运行接收机、生成观测、连接远端或修改代码/CSV。只读了已使用fit，未访问validation/Dtest。

## 归档足够提供最终S、原sigma与配对终端FER，但缺实际增益

源v2第64行和RUN-04要求固定新参考原最终S、观测和decoder，只以H_true最小Frobenius投影替换增益/H，原192帧配对。已冻结参考A2，对应runner `baseline`，工作点8dB（RUN-03/BASE-01）。

本地原始归档：`issues/2026-09-06_13-47-38-afdm-plan-v2/evidence/fit192-runtime-validation.tar.gz`。内含`rep30/31/32/{status.json,frames.jsonl}`及队列日志，不是validation数据；文件名中的runtime-validation意指工程验收。实际身份是split2、rep30/31/32、frame0…63。

实际解析192条baseline得到：

- 每帧恰好一条`capacity_trace.stage='final'`，含40个唯一`atom_ids`；每outer支撑与最终IDs完全相同。
- `support.final_nomination`排序后与final IDs一致；`support.expanded`可映射回同ID。取最终trace作为权威，不依赖初始raw OMP支撑。
- 全部`receiver_shell=direct40`对应nomination40/extension0；每帧`arms.baseline.sigma2_final`正且有限。
- 有`output_h_sha256`、`output_x_sha256`、`info_errors`、`decode_ok`、`raw_errors`、NMSE、输入六项hash、完整生成器关键参数、原支撑及评分日志。
- **没有最终gains张量，没有实际H_est数组，没有末次BP的mu/var/LLR数组或hash，没有逐bit译码输出。** Hhash不可逆，不能从NMSE推导实际增益向量。

原远端根由`current-fit192.json`登记为 `/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_budgeted_support_repair/v2_fit192-1788679921`。批次packet记录运行cwd `/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_budgeted_support_repair/v2_deadlinefix-1788677955/source`，完整source_hashes及输入产物hash在`fit192-1788679921-packet.json`和各status。不要用当前新机制代码重建原A2状态后默认为历史状态。

## 最小且边界清楚的终端反事实

无需重新执行OMP/F2P/10outer即可做**固定原最终S与原sigma的终端H投影反事实**：

1. 按归档原system、seed、code配置，仅重建已使用fit帧的H_true、y、pilot、info/coded/noise；逐项核对六项input_hashes。该步骤不运行receiver，也不允许换帧/重新选参考。
2. 用归档最终atom IDs解码delay/doppler，锁定顺序和40唯一ID。计算 `g*=argmin_g ||H_true-Σg_j G_j||F²` 与H_proj，保存E_repr、rank/失败、支撑与gain。
3. 只在原末次BP入口换H_est→H_proj。观测仍是原y，消导频项相应为`y-H_proj@pilot`；原`baseline.sigma2_final`保持不变。不再估sigma、不重新软反馈、不再做DA-LS/F2P。
4. 调现有真正末次BP：20iter、threshold1e-4、damp0.5、return_soft=True；同constellation。之后同demap_llr→LDPC decode(maxiter50)→extract_info，与原info比较并对照已存原baseline的info_errors/decode_ok。

这条路径科学解释为“**固定最终S、固定原噪声估计、只在终端检测器H入口改成最佳投影的oracle增益桥接**”。它不能回答每轮oracle增益/更好H反馈能改善多少，也不说明固定支撑的整闭环最大性能。源文只要求登记增益/H干预入口，主会话应在RUN-04证据冻结上述具体入口，不用泛称“完整oracle receiver”。

`budgeted_support_diagnostics.py:31–60`的project_channel_on_support已有整数Python-convention Frobenius投影及输入检查，可复用；E_repr独立参考可由REP-02验证提供。`perfect_gain_hook :68–77`则是每轮替换H的缓存callback，不适合这条终端干预。现`oracle_gains`调用该hook进入每outer H重建后的路径，会改后续检测、sigma/DA-LS反馈；即使支撑碰巧未变，也不等于原冻结终端状态，不能直接代签RUN-04。

## 重建精度、实际增益误差与比较终点的缺口

归档channel_parameters包含l_exp/k_exp/chan_coef_exp/fro_scale等。`afdm_env.py:613–623`原先先用未归一化tap构H、再乘scale，同时归一化tap。拿已归一化tap重新求和可能因浮点顺序不同而与原H字节hash不同，且**不能再乘fro_scale第二次**。最稳妥是按原make_frame/原源码重生并核验hash；若直接从参数重建，仅数值close不能冒称原观测字节相同。原dtype、chirp及k_max也必须固定。

投影可complex128作数值参考，进入实际GPU BP的H dtype应按原H_est complex64边界；同时保存高精度E_repr和实际注入H的E_repr/差异，避免“评价的H”和“消费的H”悄悄不同。最终sigma用原记录float值可恢复其float32标量，不得替换成生成噪声真sigma²。

RUN-04还要求实际增益误差。归档没有原gains/H_est，此项目前不能仅靠已有文件完成。可选：

- 在保持原输入/源码的限定重放中额外捕获原最终gains与H_est，并验证H/x hash和逐帧错误计数与归档一致，再计算原gain与投影gain误差；费用与额外receiver调用明确另记。
- 若原服务器另有未入本归档的最终状态文件，先只读查找并核对hash。当前没有这份证据。
- 若无法取得，诚实标该子项insufficient；不能用E_repr/NMSE替代“实际增益误差”而关闭完整RUN-04。

原H_est还经过通道阻尼/图阈值，未必恰等于最终raw gains在字典上的线性重构。应分开`raw_final_gain_error`和`effective_H_error`，不能凭支撑不变就假定两者等价。

**raw BER比较陷阱：** 当前runner的归档`raw_errors`来自model的x_soft（末次BP前），而info_errors来自末次BP后LDPC。终端反事实若从新mu硬判得到pre-LDPC BER，与旧raw_errors不是同一终点。可以报告新终端pre-LDPC统计但不可计算其相对旧raw_errors的配对收益；主要配对终点是原info_errors/FER。若必须配对终端pre-LDPC BER，还需原末次mu/LLR的真实重放证据。

## 预算与验收记录

RUN-04上界192指192个原fit帧的oracle反事实接收评估，不意味着必须重复10outer。若只执行终端BP/LDPC，应该明确计为192次terminal counterfactual evaluations，记录实际次数、CPU/GPU时长、投影费用与数据准备，不能称“192次完整10outer receiver已运行”。原闭环为已归档输入证据，不重复计为新计算。

若为补原gains另外执行192次原闭环，新增计算必须单列，不能藏在“离线分析”或消耗原192oracle额度而不报告。一次原状态重放后直接分支终端原H与oracle H，可减少重复设置，但仍要如实计两种终端检测和原闭环成本；扩出已登记预算需按主会话预算规则先处置。

最小验收需逐帧保存：原archive member及hash、身份/六项输入hash、baseline arm、固定S及顺序、原sigma、投影g/H与E_repr、实际BP入口Hhash、BP/LLR/LDPC配置与输出、原/新info_errors和FER翻转、rank/失败分母、oracle范围、成本。按rep30/31/32分别配对win/harm并给区间；对已使用fit的解释不能标独立确认。

本次结论：**仅终端投影反事实的关键冻结状态已足够；实际原gain误差证据不足，且没有可直接调用的现成terminal-only CLI。** 需要主会话新增紧凑的归档消费入口或等价调用，并用真实小批验证，不能用现有oracle_gains整轮hook绕过这两个边界。

## 补充：可从旧NMSE得到有效通道超额误差，但不是原gain张量误差

主会话进一步询问span前提。实际再次核查192帧最终IDs：以N1024、k_max2、K5计算每个原子位移 `(ID-2) % 1024`，**全部192帧均没有位移碰撞**，最大ID514。先前“阈值后未必在span”的一般提醒在本配置可收紧。

整数原子G(l,k)只在循环对角线 `row=(col+5*l+k)%1024` 非零，模长恒为1。这里字典ID=5*l+k+2，不同选中ID对应不同循环对角线。因此：

1. 固定S上重构H_new在span(S)。192帧记录已证明t0后全部outer支撑不变。
2. H_hat_active从零开始，标量gamma_h阻尼的两个矩阵都在同一span，故阻尼保持span。
3. DA-LS、gain更新只改变已有S的系数；BP/噪声反馈会影响这些系数，但不额外产生H矩阵项。
4. 每个循环对角线只有一个原子，精确算术下其各元素模长相同；soft/hard幅度阈值对该原子是一致标量缩放，**本配置的阈值在精确算术下保持span**。默认tau_h_factor=.01和tau_h_sigma_factor=.1并非关闭；不能用“阈值为0”证明，而应使用无位移混叠性质。
5. C2-rel只启用cand_active_rel，关闭off_support_corr/H_corr模块、gain_correction等其他learnable heads；baseline没有diagnostic_channel_override。故H_corr恒零，不在原子支撑之外加项。若启用不同head/override、改变N/delay字典导致位移混叠，必须重审，不能外推。

当前代码对应位置：classical_joint_unrolled.py零初值约1728–1732；H_new重构与标量阻尼2081–2090；阈值2092–2107；H_corr及override2112–2128。build_receiver始终使用e1.VARIANT_HEADS['C2-rel']=('cand_active_rel',)，strict加载head权重；原fit无oracle。最终判据仍需对冻结source packet核验这些分支，不以当前文件行号代替原source hash。

浮点实现phase模长未必严格1，阈值缩放也可能在同对角线上产生微小不同，所以不要声称原complex64矩阵严格属于数学span。**更稳妥且足够的前提是矩阵坐标支撑保持在S所占循环对角线内**：零初值、重构、标量阻尼、逐元素阈值均保持这一性质，即使phase舍入也不会凭空产生对角线外非零。

令H*=投影H_true到span(S)，E=H_true−H*。由于本生成器H_true来自同一个无位移混叠截断整数字典，精确算术下E完全位于未选对角线；因此与任何坐标支撑限于S对角线的H_hat−H*正交，即便H_hat存在细微非span畸变也有：

```text
MSE_old = ||H_true − H_hat||F²
        = ||H_true − H*||F² + ||H_hat − H*||F²
effective_channel_excess = nmse_old * ||H_true||F² − E_repr_abs
```

它可称“固定S上、相对最优表示的有效通道超额误差”，包含阻尼/阈值及系数估计的总效应；**不能称原最终gains向量误差**。若严格span成立且原子范数²=N，则可对应有效系数误差N倍，但仍不是DA-LS最后输出的raw gains。

可独立数值验收且不需要H_hat数组：重建H_true与H*后，定义U为选中循环对角线像素，测 `epsilon=||(H_true−H*)[U]||F`。因为H_hat[U外]=0，任何非零交叉项只来自这epsilon。用旧MSE和投影残差可给安全上界：

```text
|MSE_old − E_repr_abs − ||H_hat−H*||F²|
  <= 2 * epsilon * (sqrt(MSE_old) + sqrt(E_repr_abs))
```

另计原归档NMSE除法/范数舍入误差。这里实际||H_true||F²应来自hash核验的重建矩阵，不仅用理论N代替。可同时求坐标支撑投影H_true[U]作独立参考，检查它与字典H*数值一致；这一步只涉及真实已用信道及固定S，没有运行接收机。

因此，**如果RUN-04所需“实际增益误差”明确接受上述有效通道超额误差而不是原raw gains误差，可用已有NMSE+独立E_repr闭合这一解释指标，无需新增192次原receiver重放**。应在证据/契约中写清命名与代数/支撑前提，不能悄悄替换概念。若任务仍要求原raw gains张量的逐系数误差，缺口依旧。数值差为微小负数时保留原值与容差判定，不静默clamp掩盖违反前提；超出误差界应HOLD并检查模型/hash/额外矩阵项。
