# REP-01/02 与 WIRE-02 只读接线研究（2026-09-06）

范围：读取当前CSV三行、父v2 B1-a及现有实现；未改代码/CSV、未运行实验。主会话正在改WIRE-05，共享接收机不可据本文旧行号覆盖。结论：现支撑观察仅记录t=0前后，容量trace已有outer/final集合但不等于实际BP图；E_repr有解析投影及共享重建器denseLS测试，尚缺独立生成器验证和真实runner记录。最小方案应补事件和检测器内观察入口，复用原求解/剪枝路径。

## 现接口与缺口

- `budgeted_support_eval.run_frame` 的 `observe_support`（约161）仅写raw、final_nomination、expanded。`ClassicalJointUnrolled.forward` 在t=0的expand后调用一次（约1842），t>0不再触发。它不能单独回答每个refine round的pool/selected/protected/pruned。
- `forward.check_capacity`（约1617）已记录initial、temporary、outer、final的atom_ids、unique_count、limit；`observe_temporary`传入repair，可复用字段而不再计算一套容量。temporary的iteration是refine轮号，不应误称outer轮号；事件应明确 `outer_iter=0, repair_round=rr`。
- `CandidateActiveSupportRel` 的F2P迭代方法（约1280—1378）已有真实的S、cand_cols、adds、added_hist、protect_cols、kept_S。观察必须在这些值实际形成处截取，不能事后从raw/final集合反推选后被剪的顺序；空池、无adds、无需剪枝的early return也要发明确事件。
- `budgeted_support_diagnostics.project_channel_on_support`（约31）给整数唯一原子的解析Frobenius投影；`perfect_gain_hook`在oracle_gains臂复用，不改变支撑。`physical_cluster_weights`/`fit_physical_cluster`（约81/104）是按物理路径组合基底并对**观测pilot y**拟合，后者不是H_true的E_repr求解，不能替代。
- `loop9_cache_features._merged_dictionary_coefficients`（78）已按复系数合并字典列，`decision_harvest`全truth记录已调用；REP应复用它，不能回到按绝对值相加或先阈值后合并。
- `test_budgeted_support_diagnostics.test_projection_matches_dense_ls_even_when_row_offsets_alias`（105）已有dense torch.linalg.lstsq，但基底也由`reconstruct_H_torch`构造；能检验投影求解公式，不能独立排除同一个重建器的相位/索引错误。

## 实际BP图必须在检测器内部记录

真实路径有两层：

1. outer：`ClassicalJointUnrolled.forward`（约2004/2010）→ `mp_detect_bp_torch`。
2. 末次：`budgeted_support_eval.run_frame`（约205）→ `afb.mp_detect_bp` → `eval_classical_joint_unrolled._fast_bp_numpy_shim`（约51）→ 同 `mp_detect_bp_torch`。这个全局shim在import时安装，不能只改`afdm_baselines.mp_detect_bp`原始函数就以为末次覆盖。

`mp_detect_bp_torch`先把H转换到complex128，再执行 `mask = H.abs() >= threshold`、nonzero、h_vals（约45）。因此在caller原complex64 H上另算mask可能在阈值边界不同；必须复用检测器实际mask/row_idx/col_idx/h_vals。新增可选 `graph_observer=None`，默认路径只增加Python空判断，不能重复计算影响既有结果的掩码。让outer两个soft/hard调用分支及shim都透传。若numpy原始BP也允许成为真实后端，应同样在其已有mask处透传观察，否则runner明确锁定torch后端并记录backend。

每次记录：frame/run/config身份hash、arm、stage=`outer_bp`或`final_bp`、outer_iter（末次单独null/final标签）、threshold数值及`>=`、实际H dtype/shape、H hash、E、行列完整度向量（或可核验的其hash+mean/max/zero_count）、舍弃项平方F范数和全H平方F范数、二者比值。零H分母为0时显式标`zero_channel/undefined`，禁止用epsilon产生伪精确损失。E应同时等于行度和与列度和。

图阈值损失定义为实际输入H与实际阈值H_graph之差；它不同于H_true表示损失，不把两者混成一个误差。阈值相等元素必须保留。H_corr、oracle channel override之后的H才是实际图输入；不能对支撑重建的中间H计图。

该路径约定10outer时，断言每arm恰有outer索引0..9及额外1个final BP记录；cfg.pic_iter=20是每次BP内部迭代数，不能记录200个“outer”。若真实early-exit打开，记录已执行轮数和明确退出原因，不能伪造缺失轮；当前WIRE02验收要求10轮smoke应冻结early-exit关闭。final K取接收机最终支撑并校验≤40，不用E/N猜K。

## 支撑账本与独立E_repr

帧级truth离线账本：P_phys=`params['taps']`，K_emit取合并前l_exp/k_exp/chan_coef_exp条目数，存原始参数hash；复数先合并后保存全部唯一列和系数，K_true(阈值)与阈值数值/单位明确分列。完整truth的零阈值规则沿用现direct prior；另有显著性阈值必须在读数据前冻结，不能看结果后选。

算法侧事件使用现repair/容量产生的真实集合：raw、candidate_pool、selected、temporary_union、protected、pruned、final。至少带outer/repair_round、capacity_limit、source=实际算法节点以及有效/empty/keep/stop原因。为避免与主会话WIRE05新事务提交冲突，新事务也用该同一事件结构报告其proposal/prune/commit/keep，不维护另一个剪枝器。A0不经过repair时应写`repair_disabled`和空动作事件，不能把缺日志当keep成功。

独立表示核验应从生成器构造原子：对S每一列解析(delay,k)，用 `system.gen_h_daft([1], [delay], [doppler])` 生成complex128矩阵，列向量堆成B；直接 `np.linalg.lstsq(B, H_true.reshape(-1), rcond=冻结值)`，保存rank、singular_values、rcond、residual和基底hash。与解析project_channel_on_support的H投影和E_repr对比，不共享reconstruct_H_torch。生成器本身先用完整合并truth系数重建H_true并验证误差，以识别归一化/碰撞/裁剪域不一致。

N=1024、|S|=40的complex128 dense B约640MiB（N²×40×16字节），再加LS工作区；不能把每帧dense核验免费塞进observer。完整dense核验先用小系统和预算允许的固定真实帧；常规记录用已验证解析投影，并明确核验覆盖帧，额外费用归S2、单列。独立dense是数值参考，不能用浮点小负差或修剪clip来藏不一致。

空S且H_true非零时E_repr=1；H_true零时比值未定义，明确保留。重复原子先按契约合并；独立dense遇到真实秩亏要记录不可辨识，不抛弃帧或谎称唯一系数。相同row displacement并不等于相同原子（已有alias反例）。如果物理路径碰撞导致无法一对一识别，单列不可辨识槽。

物理路径召回需要先冻结独立匹配协议：估计如何从整数支撑分组、delay/Doppler容差按字典分辨率、最大匹配/最小误差的一对一分配、同分规则、碰撞和零贡献槽处置。现整数支撑没有估计物理路径接口时，只能报告字典原子召回和物理路径“不可评估”，不能直接拿K/P算路径召回。系数平方加权召回称字典系数指标，不自动称物理能量。

阶段损失分列集合差：truth未入pool、pool有但未selected、selected后被pruned、final支撑下最佳H与实际H的gain差、实际BP阈值丢弃。允许同帧多标签并报告集合/分母，避免把重叠错误硬分成互斥因果百分比。E_repr为给定S的可表示性，增益错可比较||H_true-H_actual||²与最佳投影残差，但非投影/非正交情况下不宣称这些误差简单加和。无干预只写关联线索。

## 无扰动和计费的最小验证

观察器不得写入接收机Tensor、替换scorer返回值、重新采样或再次调用lstsq/BP。尽量记录已有mask/集合的脱离副本，昂贵truth/E_repr在完整接收结束后离线计算。callback输出只写日志，不进入任何部署arm。若把tensor直接传给可变callback则契约容易被破坏，建议只传只读语义的独立快照；GPU复制本身有费用和同步，必须实测观察开关逐元素一致而非“数值大致相同”。

当前runner的elapsed含observer开销。新增 `representation_observer_seconds`/`graph_observer_seconds`与离线分析费用单列，保留完整链路elapsed，不静默减掉它声称更快。GPUobserver计时涉及异步操作时用明确同步边界或CUDA事件记录；其计时本身不得用作S1/G2正式时间验收。

针对性证据：复系数完全抵消；两个原子相同行偏移但不同phase；恰等阈值/零图/稀疏图；S空/秩亏；F2P空池/无选择/保护后剪枝；10outer+final完整索引。真实direct40小批在相同snapshot/设备下observer on/off比较H_est、x_soft、sigma2、末次mu/var、LLR/decoded bits和错误逐元素一致，输入/config/hash固定，全部final K≤40；不能只比FER或错误向量代签输出无扰动。任何浮点差异按现科学契约保留并定位，不放松容差偷偷通过。

交付边界：REP-01/02静态实现与上述单测不等于WIRE-02真实验收；必须保留实际BP入口记录和小批smoke证据。现报告只给最小接线位置与契约，未运行这些检查。
