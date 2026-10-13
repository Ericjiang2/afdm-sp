# CWORD-01：固定支撑码字 profile 可行性合同

本合同只检验已暴露 G1 开发集上的两个候选排序诊断，不产生有限合法列表或译码性能。32 个物理块在 7/8 dB 各有旧 ridge `.1` 完整 F；先读取并哈希核对全部 64 个 F 与旧 G1 物理 A 的配对，固定只在失败的 15 个工作点评分：7 dB 的 2/4/9/11/14/15/17/18/22/25/26/27/31，8 dB 的 15/25。工程点取 (2,7)、(15,8)，它们属于原 15 点；剩余 13 点只在工程守卫通过后计算。分析仅作描述，15 点不视作独立确认样本。

## 旧输入身份和物理映射

- 旧 G1 物理 A 为 `G1_PROPAGATION`，工程/开发 summary 在 `outputs_trans_next_20260913/runs/g1-strong-engineering-v1/engineering/summary.json` 与 `runs/g1-strong-development-recovery-v1/development/summary.json`。A 的 `raw` 有真 `coded(2048)`、`info(1024)`、`pilot/data/y(1024)`、真 `H(1024×1024)`；用原 `supplement_g1.reuse_at_snr` 生成配对 7/8 dB 的实际 `y`，核对旧 ridge F 的 `physical_record_sha256` 和观测哈希。
- 固定 ridge F 来源为 `outputs_dirichlet_shrinkage_20260914/{engineering,development}/summary.json` 中 arm=`ridge` 的 64 个实际完整 F。每个 F 保存 `state.H(1024×1024)`、`decoded(2048)`、`info_hat(1024)`、`dals[0..8]` 与最终 K24 支撑。真码字只来自物理 A，作为 oracle 排序参照；实际译码结果只来自 F。旧 summary/环境、F/A记录与 NPZ 必须按各自 SHA 守卫。旧 ridge **生产**源为 DIR_ROOT/source-v4 manifest `50fb12ce...`；本诊断**分析**源为 CE_ROOT/source-v4 manifest `176cfd68...`，两快照的 `classical_joint_unrolled` 等文件不同，分别绑定，不称同一源码。
- 旧码配置由 `runs/refs-v1/development/environment.json` 的六个 `CODE_KEYS` 数组哈希绑定；用冻结 source-v4 的 `e1_ldpc.build_code` 重建并核对。`qpsk_map(bits,scale=√(1−ρ))` 将 `[all I bits, all Q bits]` 映射至 N1024 复数据，ρ=.5；真码字映射须与保存 `raw.data` 数值一致。syndrome=`H_code@bits mod 2`，另核 `extract_info(decoded)==F.info_hat` 与 `encode(code,raw.info)==raw.coded`。

## 候选和分数

每个失败工作点保存三种位向量且绝不互相替换：`true_c` 原真合法码字；`decoded_raw` 为原实际输出，可能 syndrome 非零，仍可映射信号但必须标 `invalid`，不得算合法列表覆盖；`reencoded_info_hat` 是原 F 的 `info_hat` 经同码系统重编码所得合法错误候选。记录三者的 SHA、syndrome、信息/码字距离、重复身份。若两错候选逐位相同，复用同一 profile 求解并明确减少实际 refit 次数。

对同一工作点的三个候选采用相同观测 `y`、pilot `p`、实际最终 K24 支撑 `S`。固定 H 对照用 **旧 ridge 实际终端** `F.state.H`：`L_H(c)=||y−H_terminal(p+d(c))||²`。末次 DA-LS 保存的 H 在求解前，不能代替实际终端 H；后者还有阻尼/稀疏处理。块 2/7 的终端 H 与 t9 审计 H 相差约 4.69%，与从末次 `g_solution` 直接重建的纯支撑 H 相差约 4.82%，需逐工作点保存这两种差距。若将同一固定信道的 ridge 系数惩罚加进 `L_H`，它是对所有候选相同的常数、排序中抵消；这里显式不加。

profile 诊断使用分析快照 `A_c=build_A_for_DALS_torch(N1024,S,p+d(c),c1,c2,W2)`，`g_c=(A_cᴴA_c+λI)⁻¹A_cᴴy`，`J(c)=||y−A_cg_c||²+λ||g_c||²`。先在每个目标把分析算子于旧 t9 的同一 `p+mu`/S 上重建，和旧生产保存的 complex64 `A_t9` 比较；相对偏差必须不超过事先 `2e-6`，否则停止。块 2/7 的独立只读核验偏差为 `5.55e-8`。`λ=.1·||A_saved_t9||_F²/K24` **仅由旧 ridge 同帧 t9 已保存设计决定**，对真/原输出/重编码候选共用；绝不按候选 A 或真数据改尺度。冻结 λ 应与旧 t9 `Q=.1·scale·I` 按事先 complex64 相对数值容差 `1e-6` 核对（块 2/7 旧 Q 相对偏差 `4.12e-8`）。它是新的零中心惩罚 profile，**不包含**旧 CE 的 previous/proximal 项，也不冒称重跑原 CE。旧 DIR 在线 Q 随每轮实际 A 缩放；这里刻意固定同一帧 λ，区别须报告。

保存每候选 `A_c/g_c`、残差平方/惩罚平方、闭式 `yᴴy−yᴴA_c(A_cᴴA_c+λI)⁻¹A_cᴴy` 与直接 objective 的闭合、Hermitian/rank/条件数/法方程相对残差。秩亏、λ 非正、非有限、输入哈希漂移立即失败；不静默 pseudoinverse。排序 margin 定义 `score(decoded_raw)−score(true_c)` 和 `score(reencoded_info_hat)−score(true_c)`，**正值表示真码字较优**。分别存固定 H 与 profile 的 margin、符号翻转、改善/恶化；原输出无效者仅计非合法诊断，不放进合法候选覆盖率。固定 H 和 profile 的分数来自不同模型，比较只限同一错/真对的排序，不把数值差叫可归因的 FER 或 CE 增益。

资源上限：0 新完整 receiver F/BP/LDPC、0 新物理块和 0 真值支撑改写；每个唯一候选一次候选信道线性 refit，最多 15×3=45 次，工程≤6、开发≤39，另计矩阵/编码/固定 H 分数与只读 audit 代数检查。方向累计≤7200 秒、≤20 GiB，deinlab CPU 1 线程，所有远端写入 `/data/guoyikun/` 的新 root，旧 source/raw/F/A 不改。audit 从保存方程/原输入验证，不重复已完成候选 refit，也不额外生成码字列表。

若诊断排序不改善，结束本方向可行性；若改善，只能提议下一关冻结无真值有限合法列表覆盖与同列表固定 H/常规重启公平对照，不能将这 15 个真码字诊断冒充部署结果。
