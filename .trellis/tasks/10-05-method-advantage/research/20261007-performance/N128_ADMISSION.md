# N128/T2 源码准入审查

2026-10-07。**最终结论：GO，源码准入通过。** 主计算和冻结协议一致；初审发现的两项执行证据缺口已由源码所有者修复，审查者复核变化并完成针对性测试。仅允许将本次所审字节提交、冻结为隔离快照后执行协议内D/P/A；本次未运行科学任务。本报告不评价07科学结果，不改变四轮性能FAIL或尚未达成的联合目标。

## 范围与独立性

审查者未参与07实现。主线程实现core/study/dispatch，另一实现者负责audit/design_check。复用既有项目与服务器约束；本次实际读取N128_PROTOCOL、N128包全部源码/配置/固定测试、dispatch三脚本及import inventory、launch/run_contract，并追踪所复用的design/generator和不可变记录器依赖。没有启动设计、采样、完整审计、SSH或新的科学探测。

源码尚未提交：本次只判断待提交字节的实现是否可以进入提交/打包流程。最终执行还必须由pack_source从同一commit提取全部内容，远端bootstrap核验清单和外部控制脚本，记录隔离snapshot commit；源码审查不能冒充已经完成这条部署证据链。

## 初审发现

1. `dispatch/harvest_remote.py`在盘点文件之前要求D/P/A均complete。D检查失败或P超时会立即raise，无法通过该脚本回传failed attempt、partial文件和预留记录。需始终盘点并打包已有阶段，明确报告缺失/未完成阶段，保持失败状态；不能只有成功路径才能收集证据。
2. `design_check.load_verified_design`仅检查D attempt的status；`audit.calculate_audit`对P也如此。D内码/设计/审计结果虽互相绑定，消费的D/P文件未与阶段完成时的`attempt.artifact_sha256`相连。A末尾给当前文件重新计算hash不能补上该来源证明。需在消费前核对complete、exit0与所用文件的完成时hash，覆盖D codes/design/design_audit/results和P records/results，以及所用source identity等证据。无需重复设计、积分或获取计算。

初审按派工只写本报告并通知主线程，未修改科学源码或dispatch。两项均已修复：

- 主线程修改harvest：总是盘点已有注册stage，`all_required_phases_complete`、`missing_successful_phases`与`unfinished_stages`显式表示缺失或未完成；缺失attempt时墙时/RSS用None，已知墙时单列，不以0冒充未测量。已有partial文件进入哈希清单与回传包，source manifest仍核验。
- 原审计实现者增加统一`verify_stage_completion`：严格要求complete、整数exit0，所消费路径必须在stage内，按准确路径或唯一`execution/<stage>/<relative>`后缀匹配完成时SHA256，拒绝basename误配、多重匹配和变更字节。P消费D之前绑定六类设计/源码/注册文件，A消费P之前绑定records/results/registration/source identity；P records再通过逐组文件及数组hash覆盖所有原始输入和估计数组。没有另建来源路径或重做科学计算。
- 审查者实际运行四项针对性fixture：远端路径复制/错误exit/缺失与重复匹配，D六类文件tamper和保存审计拒绝，P四类文件tamper先于结果/观察消费，failed与unfinished两分支回传。全部通过；这些是合成文件和mock的工程检查，不是N128设计或性能证据。

最终没有未修复的源码准入问题。

## 已核实的协议与实现

- 模型为N128/T2/SNR5、s5、CP32、frame stride160，物理gain跨两帧共享，fresh iid QPSK与已冻结生成器一致。delay0…31、CFO0…127、ρ∈[.75,1.25]及均匀相位不变。
- 96点有效gain网格为3个半径×32个C4商空间相位，步长π/64。N128 Weyl cocycle `exp(2πim/128)`在该网格中只是相位置换；物理gain输出另乘延迟修正`exp(5πi l²/128)`。不声称连续gain ML/MAP。
- SCREEN512与FULL两臂使用同一网格和4096标签全集；512/4096=1/8，等于此前128/1024比例。筛选稳定排序后按hypothesis索引排序，重排及精确并列规则一致。每个完整调用独立构造变换/模板，无跨调用缓存。
- D复用旧129个quadratic候选与最早argmin规则，随机码仅128次uniform设计draws，seed2026100706；主值四次方根约定不变。独立forward FFT重算130项，在D结束前完成。生产与检查各528320个几何值，共1056640，全部计入D60秒；P先加载通过的D审计回执，A不重复几何。
- P固定seed2026100707，256配对组按delay、CFO、ρ、phase、states、实噪声、虚噪声顺序抽样；两码共享外生变量。每组四次完整调用按group mod4轮转，合计512波形数据集、1024个128维观察、131072个复标量、1024次获取、2359296个似然候选、226492416次gain评价。
- A独立矩阵重建全部Y、直接模板和核查全部fourth分数、hash/选择/并列/gain映射/计数/子集似然一致性；固定4组×2码×2候选共16次显式96gain mixture检查。其余似然仅通过保存结果与子集关系核对，不能称全量独立重算。A没有RNG、生成器、估计器或新码搜索调用。
- 配对改善≥10pp且探索性区间下界>0、random SCREEN错误≤64/256、完整调用速度比≥3、bad方向CP上界≤2%即x≤1、FULL目标支配及独立审计全部保留。独立CP用二项分布求逆，不调用producer的beta.ppf。反向discordance另报。
- 冻结预算D60/P3000/A180，总3240秒，CPU1/CUDAhidden、2GiB、512MiB，注册总观察1024/总几何1056640；run_contract与STUDY_CONFIG一致。记录器拒绝已有stage、保留失败预留，并绑定执行source与快照。失败回传修复及验证见上文。

## 已完成验证

- 主线程报告23项固定工程fixtures通过；本审查逐一阅读其范围，没有重复等效运行，也不把fixtures计作性能证据。
- 审查者实际运行系统Ruff：PASS；launch的bash语法：PASS。
- 修复后的16个Python文件静态编译：PASS；冻结配置SHA256、两seed、观察/几何/似然计数、总预算和筛选比例的标准库核对：PASS。
- 本轮未执行独立静态类型检查，当前执行环境未提供mypy/pyright命令；静态编译仅证明Python语法有效，不声称类型检查通过。
- 未运行科学D/P/A；未生成或选择N128码，没有07性能结果。最终针对性4项测试、Ruff、bash-n、静态编译均通过；原23项固定fixture不重复全套运行。

## 最终审阅字节

以下为修复后实际复核的关键文件SHA256；源提交和远端快照编号待主线程部署回执绑定。本GO不覆盖随后未经复核的实现变化。

|文件|SHA256|
|---|---|
|`experiments/afdm_acquisition_n128_20261007/STUDY_CONFIG.json`|`4739de548098875d1ddb877be836053511a89100738f8f7cdf7103883ba5e5af`|
|`experiments/afdm_acquisition_n128_20261007/core.py`|`b4383b44e4297a2310d0713736661c197316cef94193e3e835cf9e566a7e5a65`|
|`experiments/afdm_acquisition_n128_20261007/study.py`|`8830e267f124184bcc4928d06f896d7c981e9eef0d34e48fbfd13f17e248ab91`|
|`experiments/afdm_acquisition_n128_20261007/audit.py`|`6f3b6356a17ed8bf3977b3557cadeb0645271ef690c3e6731b7b4e7193c0b0f7`|
|`experiments/afdm_acquisition_n128_20261007/design_check.py`|`fd93a98d8330cdfc6e42bbddfbd7764191989ebe3573c67eb9f9b701848f019e`|
|`experiments/afdm_acquisition_n128_20261007/protocol.py`|`eb318f61229f8459876c60a3719e7370f3ee6b3566f520f4eddf603d321e0dc3`|
|`afdm_sp_joint_unrolled/outputs_acquisition_n128_20261007/dispatch/pack_source.py`|`98da13950de50a0832072f00da32cb55b648e3342e5a11bb6451304bde4b9b45`|
|`afdm_sp_joint_unrolled/outputs_acquisition_n128_20261007/dispatch/bootstrap_remote.py`|`7249700c7b3d87d0b7ce60f1bc8ff1235f380a1e3ce29a0fe5c4f20fb938ce82`|
|`afdm_sp_joint_unrolled/outputs_acquisition_n128_20261007/dispatch/harvest_remote.py`|`5f4b3d681ae75200ec101d9b97fc755bcec9d9853554bd03d76f498499708db6`|
