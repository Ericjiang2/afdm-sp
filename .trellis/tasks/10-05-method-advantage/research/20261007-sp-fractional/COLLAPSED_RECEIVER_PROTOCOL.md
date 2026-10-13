# Collapsed 局部接收比较协议（待独立协议审查）

2026-10-07，COLLAPSED-RECEIVER-01。先完成 COLLAPSED-MATH-01 原始审计，
再实现与准入本协议。沿用 Gaussian/Schur/经典连续频率优化，不声明首创。
任务是验证实际收益；本开发切片只有原 4 blocks，不是独立确认。

## 问题与四臂

已有连续边缘化未改善旧开发切片的误码且成本较高；解析消去增益后的
point-Doppler 条件下界已经有数学依据与保存案例的数值核验。
本轮把有限局部搜索与增益重求解分开比较，不把减少搜索/轮数的效果归给消元。

1. `f1_scalar`：原完整 F1 + scalar 接收基线，行为不变。
2. `vb_point`：原 20 sweeps、257 点全域网格及原细化，行为不变。
3. `vb_local_point`：5 固定 sweeps，顺序保持原 `gain_before_doppler` →
   在该完整 gain 因子固定下顺序执行局部 Doppler 搜索 → 原 `gain_after_doppler` →
   3 个原 data steps。冻结仅限 Doppler sweep，不省略前后两次 gain 更新。
4. `vb_collapsed_point`：同样 5 固定 sweeps及局部搜索；每个候选解析重求 gain，
   按 `J=|t|²/s−log s` 评分，接受后恢复完整 m/C。

两条局部臂均保留每 sweep 3 个原 KL-MM data steps、全部独立 objective/
Eq. (8)/回溯核验、完整 gain covariance、原符号 prior 与观察量白名单。
不增加 decoder，不修改工作噪声、G0→G1 gain 归一化、真实 CPP 或旧三臂默认配置。
5 sweeps 是本次预先固定的计算预算，不是已证收敛或根据 truth 自适应早停。

## 有限局部搜索与算术边界

每个坐标以当下 Doppler 为中心，窗口为
`[max(-3,previous-.75), min(3,previous+.75)]`；.75 取自既有物理局部细化范围。
显式评分 previous 与两端点；一次 scipy bounded scalar minimization，
`xatol=1e-4, maxiter=32`。保存其全部实际调用、候选及状态。
不能把此有界数值搜索称为全局最优；返回不成功或非有限值明确失败，不重试/加密。
比较顺序 previous、下端点、上端点、优化器返回候选，只有严格增大目标才替换，
等分保留 previous；数值搜索返回的候选必须在既定窗口内。

局部 point 与 collapsed 共用搜索控制，前者使用原 Fourier 条件势，后者使用 Schur 势。
每坐标最多 35 次搜索评分（3 显式 + 最多 32 内部）；优化器终点须能对应到已记录评分。
可在选定点重新调用一次完整 collapsed evaluate，以保持实现简单并检查 full covariance；
这第 36 次可能评分/求解必须另计，不能伪称免费 cache reuse。
完整诊断 evaluate 默认行为不变；score-only 路径复用同一 s/t/J 核心，
跳过完整 covariance/precision residual，仅保留原有限性与 s 下界检查。
完整胜者评估仍检查 residual、Hermitian 和 s 下界。

collapsed 接受后以新 factors/m/C 重建 canonical op/source，再进入下一坐标；
禁止给新 op 强塞旧 SourceMoments，禁止在旧 kernels 上只换 ν。
重建 phase、FFT、完整 R/f、Schur 块 factor/identity RHS、全部 rejected work 均计费。
不必额外执行旧 gain_before_doppler：collapsed 自身已解析最大化。
最后坐标的完整 m/C 供本 sweep 的原数据步骤使用。

## 工程核验（ENG；具体源件清单在源码冻结后逐 SHA 登记）

只复用本次已封口 COLLAPSED-MATH-01 的 attempt.json、registration.json 与6个 case.npz，
加原 MATH-01 的10文件，共18个输入，逐 SHA 绑定；不读取新truth或生成物理样本：

- 原 6 cases、9 坐标、45 个固定候选：执行 score-only 核心，对比旧已保存的
  s/t/J/full score；每坐标在 0 offset 再执行完整默认 evaluate，共 9 次，
  对比旧保存 m/C/precision。所有准备/求解/重复计算另计。不重复物理 basis 仿真。
- 执行 3 个本次数学协议已列原 gain/增量系数/data-step fixtures，各一次。
- 2 个明确的小型确定性搜索合同：常数势保持原点；区间端点最优势保留该端点。
  它们只证明搜索控制与计费，不冒称接收性能；不 mock 求解或冒充真实 receiver。
- 对原默认配置与 original saved-population seal/评分入口做静态/合同检查。
  有效完整 receiver 运行留在 DEV；ENG 的 receiver/decoder/new observations 均为 0。

值/矩沿用 N8/16 1e-10、N1024 1e-9，precision 1e-10。
ENG stage CPU/wall 上限各 120 秒，完整进程 150 秒 + 10 秒退出宽限，
4 GiB、128 MiB、单 CPU、CUDA 隐藏。实际确切准备次数随源码冻结，不藏进45候选。

## 配对开发比较（DEV）

只有 ENG 全部通过并完成其原始核对才进入 DEV。
复用原 `RECEIVER-DEV-01` population：N1024、rho=.5、SNR6/8dB、原 4 blocks、
8 observations、真实 G1/CPP；observed/truth 原件逐 SHA 绑定，不生成新样本。
4 臂各自执行完整 F1，不跨臂缓存或免费复用支持；共 32 完整计费调用。
顺序按 block 模 4 轮转，同 block 的两个 SNR 使用同顺序。
先封口全部接收原件，再读取 truth 评分。LLR<0 判 1；分母每 observation 2048 bits。
每臂记录原始 LLR/hard/log_q、全部迭代/失败/操作计数、端到端 wall/CPU、保存成本；
记录进程启动与峰值 RSS，source/population preparation 另计。
全封口后的独立审计还将原 scalar/point 两臂的 LLR/hard 与上一冻结同输入原件逐值比较，
报告任何差异，不静默替换旧基线或重跑来掩盖差异。

沿原筛选门槛判断 collapsed：32/32 完整；错误数≤原 `vb_point` 的90%，
不差于 scalar；完整中位 wall≤scalar 的1.25倍。point 零错误则该相对门无结论。
额外报告 collapsed 对匹配 `vb_local_point` 的逐 block/SNR 错误数、硬判净改变与
完整成本差；仅当 collapsed 总错误数严格小于 `vb_local_point`，才记录对匹配控制的
开发改善；两臂拥有相同轮数和搜索调用上限，但实际计算量/耗时仍各自记录，
不把“同预算上限”说成“相同实际成本”。
失败或未过门原样保留，不能临时改轮数/窗口/容差/样本或放宽旧门槛。
这些仍是复用开发数据的筛选，不作独立置信、泛化、coded 或 Trans 验收。

DEV stage CPU/wall 各 240 秒，完整进程 270 秒 + 10 秒退出宽限，
4 GiB、128 MiB、单 CPU、CUDA 隐藏。每阶段 source commit、snapshot、imports、
输入、配置和 launcher 独立准入，只执行一次。全部写入/cache/tmp 在 /data/guoyikun。
任何失败保留，不自动重试；原 adaptive 负结果不重跑、不删除。
