# FB-01：实际反馈入口与旧V(T1)补格来源

2026-09-06；只读源码及已有本地结果研究。未执行接收机、未连接远端、未改CSV/源码；本文件不是运行验收报告。路径以下相对项目根，行号对应下方内容hash，其他代理后续编辑可能移动行号。

## 1. 实际调用链

`budgeted_support_eval.build_receiver:55–67` 固定软决策、BP、10个外环、每次20个BP内部迭代、自适应sigma开启、外环早停关闭。`run_frame:87–102` 先以OMP获得H0，传入 `make_genie_lambda(H0,...)`。该名字虽含genie，本调用没有用H_true构造scorer。

`decision_gateA.py:150–169` 捕获H0，预计算 `(1-rho)H0H0^H`；调用时加传入标量sigma²，对白化统计装配prior分数。H0/先验功率项不会因后续DA-LS反馈重算。`classical_joint_unrolled.py:1629–1636` 的t=0分支运行初始化OMP/F2P；t≥1进入DA-LS。因此当前动态V不直接进入候选scorer。

外环反馈顺序：

1. t≥1，`classical_joint_unrolled.py:1798–1812` 取上轮阻尼x_soft、当前H列功率和sigma²，重算有限星座mu/v。
2. `1817–1837` 以pilot+mu构造当前支撑A；协方差臂形成C并更新增益。
3. `1907`附近重建H并作通道阻尼，`1948–1970` 用H和标量sigma²执行检测；BP没有接收新C/V参数。
4. `1984–1987` 对BP输出均值作符号阻尼；`1989–2001` 经独立均值投影更新sigma²；进入下一外环。
5. `budgeted_support_eval.py:176–187` 模型结束后取H/sigma，再执行末次BP→demap_llr→一次decode_llr调用。LDPC内部最多50轮是码图迭代，不是接收机外环反馈。

末次BP通过动态属性 `afb.mp_detect_bp` 调用。`e1_ldpc_coded_eval.py:63–77` 明确导入patch链会落到Torch的NumPy shim；当前静态导入链支持此判断，但本次没有执行import或实时查询callable identity，不能冒称已运行核验。未来运行manifest须记实际绑定函数/module/hash及设备。末次BP计算不能因名称afb而漏记GPU/传输成本。

## 2. 三种方差必须分名

| 名称 | 来源与当前使用 | 边界 |
|---|---|---|
| BP Gaussian `var_post` | `mp_detect_bp_torch.py:125–147` 以各观测消息精度及先验精度合并，var_post=1/prec_post，mu_post=mean_post×var_post | 是Gaussian工作后验矩；不是最终有限星座p的中心二阶矩。外环`classical_joint_unrolled.py:1955–1959`丢弃该var，只留mu_post |
| DA-LS工作高斯方差 | `_qpsk_soft_decision`，`classical_joint_unrolled.py:358–380`：sigma²/max(||H[:,n]||²,1e-10)；作用于阻尼后的x_soft | 是重新构造的标量工作模型；没有沿用BP var_post，不是估计误差的真条件方差 |
| 有限星座v | 同函数`381–390`，p=softmax(-距离²/工作var/T)，mu=sum p·s，v=sum p·|s-mu|² | mu/v必须来自同一p；当前星座已乘sqrt(1-rho)，v已含实际数据功率 |

BP内部还存在边消息的有限星座投影（`mp_detect_bp_torch.py:109–123`）及var_new，与最终Gaussian var_post不是同一接口。该内部投影指数分母是 `2*var_ext`，DA-LS投影分母是工作var（无2）。这是源码事实和将来概率一致性契约的审查点；本次不能据此直接宣称实现bug，或在补旧V(T1)时顺手改公式，破坏历史配对。

`e1_ldpc.py:194–230` 的demap按复Gaussian约定使用 `4*amp*Re/Im(mu)/var`，amp=sqrt((1-rho)/2)，LLR剪裁±20。输入是末次BP的Gaussian mu/var，不是DA-LS有限星座v。其说明采用Gaussian近似；不要仅凭变量名“posterior”声称有限星座精确边缘分布。

## 3. C的冻结范围及实际目标

`residual_data_covariance`（`classical_joint_unrolled.py:268–274`）计算 `H diag(v) H^H + sigma²I`，不重复乘(1-rho)。检查v有限非负、长度匹配、sigma²正数。

`soft_gain_update`（`277–298`）对一次调用传入的C作Cholesky，将A及y全部右端项联合求解，形成sigma²缩放的加权Gram/RHS，并加入与旧g的proximal正则项。C在本次求解内固定；`1834–1837` 每个DA-LS外轮都使用当时H/v/sigma²重新构造。它不等于整帧冻结C，也未对C依赖g求导；不能承诺一般EM或整机FER单调。

`1578–1581` 只接受mean/jsoft/covariance，并禁止非mean入口与oracle数据override组合。`1814–1819` 的oracle_data只替换DA-LS均值，不替换最终检测结果/译码输出；当前oracle与V不能组合，符合单入口诊断边界。

noise_feedback（`1989–2001`）重新调用软投影，但没有传dals_temperature，因此为T1；更新的是残差功率混合。当前温度控制只对DA-LS均值/方差入口生效，不能描述为“所有软信息统一温度”。

## 4. 当前缺口与FB-01交接

- 没有逐轮V驱动F2P/scorer或直接有色C驱动BP接口；只有通过H/sigma的间接闭环影响。
- 没有SISO译码外信息输出接回接收器。`e1_ldpc.py:242–284` 返回硬码字和syndrome通过标志；内部tot/外信息未作为接口返回。需新设计才能做turbo，不能用oracle_data替代证明。
- 均匀先验方差GLS政策当前未在dals_mode列举，FB后续实现应与dynamic共用构造/求解，只改变v来源，不另写一套接收器。
- 当前observer携带logits/p/mu/工作方差/星座（`classical_joint_unrolled.py:383–387`）；完整同状态重放还需明确捕获H、mu、sigma、旧g、A、支撑及轮次，不能仅从聚合可靠性JSON反推这些状态。
- `budgeted_support_diagnostics.py:126–169` 已有NLL/Brier温度重评分和方差分箱；缺直接高置信错误字段。现有绝对0…0.5分箱不能跨rho照用；后续按v/(1-rho)固定分箱，observer开/关等价另须实际验证。

## 5. 旧固定壳V(T1)：可复用配置与陷阱

权威既有运行记录位于 `.trellis/tasks/09-06-minimal-repair-mechanism/research/runtime/capacity-dev-batch.json` 的runs[].cmd；rep0/1/2每个64帧、start0、split dev、SNR8、active-cap40，旧接收器k_leak=2，所以nomination8。源码快照记录source-v3，不使用后续direct40接收器扩展0。

可复用位置：

- `research/launch-capacity.py:5–16,35–40` 保存原远端source-v3、checkpoint、prior路径及dev调用；不是本次可直接重跑的授权。其receiver helper只有len(arms)>1才加feedback-calibration，若补单一covariance臂不可照搬此条件，需显式传反馈记录。
- `runtime/capacity-dev-rep0/status.json`（以及rep1/2）为原配置；对应frames.jsonl为原配对输入/输出、旧三格结果。原批次只有baseline、temperature_mean、covariance且使用T2。
- 旧prior为远端 `outputs_budgeted_support_repair/s4_20260906/prior-cap40/cache_snr8.pt`，本地`runtime/fixed-prior-hashes.json`保存hash；`capacity-dev-rep*/calibration.json`记录nomination_cap=8。cap40不能据名字误装nomination40 prior。
- `runtime/fixed-feedback-calibration.json`实际selected_temperature=2、active_cap40、nomination_cap8；用于旧M(T2)/V(T2)，不能直接拿来跑V(T1)。
- `runtime/feedback-calibration.json`实际selected_temperature=1，是旧真值容量域校准；可参考T1配置形状，不能冒称它是固定壳校准选择。`launch-capacity.py:9`引用identity-temperature.json，但当前本地runtime清单没有该同名文件，远端是否存在本次未查询。
- `budgeted_support_eval.py:285–294` 即使单covariance臂也强制要求feedback-calibration，校验split=D_cal、SNR匹配后读取selected_temperature。补格应登记明确的“固定T1归因控制”记录，而非修改原T2文件或伪装新增温度校准；保持同prior/码矩阵/随机流/源版本，复核同帧hash与t0初始化。

本次仅核实旧记录的配置位置和缺格；未新扫描全部历史/远端run作“全球不存在V(T1)”断言。正式补格前由运行主会话核验输出命名空间与既有run，避免重复投递。

## 6. 本次行号版本

```text
classical_joint_unrolled.py 59af54ccdc830e5dfa69e8c88a004e7d0703f24793e7d6af0b26b6e81c282489
budgeted_support_eval.py 1a06c9ec49dc93528cbf3b219410d9f9b8b973cd5199d3afb0d6f57340f18284
mp_detect_bp_torch.py 3955d596d2cc90eae29e1cb5f9cc86a286e5fc9e9afc8b2e3dcb18dac4cddbe9
e1_ldpc.py daec23e59268b141141f50eb87f61a15d3a75b3820777a419651450dec7f8657
decision_gateA.py c1ebdfa5189829d8e8236c46d2c482a0247249f3bbc6dc02adc1d989a6f468a5
```

这些hash对应本地读取时内容，不等同远端已冻结source-v3。后续修改/执行须分别记录新源码及旧回放快照，不能仅记git HEAD代表当前脏工作树。

## 主会话复核补记

当前源码已加入 A0 bypass：仅修复臂构建初始 H0/scorer；纯 A0 跳过该准备。上述 V→DA-LS、每外轮重算 C、单次求解冻结、terminal-only LDPC 与独立 T1 noise feedback 入口仍成立。主会话通过 rg 和源码阅读复核，未将静态入口图当作运行绑定或数值验收。
