# 物理结构 oracle 接口研究

范围：仅源码与既有 Phase-0 JSON 的只读核查；没有新增仿真、拟合或接收调用。下述实现建议不是已运行结构实验，也不自行冻结新参数。

## 已有真实接口

- `afdm_sp_joint_unrolled/afdm_env.py:576`：每条物理径先对 `m=-k_leak..k_leak` 的 Dirichlet 权重能量归一化，再按 Doppler 边界裁剪、按相对峰值功率剪枝；不是先裁剪再重新归一化。`597` 行发射系数为 `g_i_raw * alpha`。
- `afdm_env.py:448` 的 `gen_h_daft` 用 Python 相位约定和整数位移逐径复数 `+=`，相同原子先相加。`618` 行对合成 H 作共同 Frobenius 归一化；`629` 行保存 `g_i=g_i_raw*fro_scale`。
- `budgeted_support_diagnostics.py:80` 的 `physical_cluster_weights(system, params, rounded=False)` 已精确实现上述 L，维度 `515×P_phys`，保留重叠行、重复/零路径槽。只需传 `taps,l_i,k_real`，不应把包含真实增益的整个 params 暴露给拟合层。代数为 **g=Lh，h 是归一化后的未知物理增益**；原始增益到归一化 g 的公共缩放依赖叠加，因此不能冒称对原始增益全局线性。
- `representation_ledger.py:41` 的 `merged_truth_ledger(params,2,threshold=0)` 先复数合并再判定非零。以其合法列、`delay<=102`、`above_threshold=True` 构造 S_true；不能以未合并泄漏条目并集代替，尤其是完全相消。阈值零是现有精确非零语义；若改成显著能量阈值，须先冻结，不能看结果后选。
- `afdm_baselines.py:42` / `classical_joint_unrolled.py:90` 构造 `Phi[:,i]=G_i pilot_scaled`，列顺序 `i=5*delay+doppler+2`。这里没有将列改成单位范数。传入已含 `sqrt(rho)` 的实际 DAFT pilot，不再乘一次。若未来用单位范数字典，L 必须同步左乘列范数对角矩阵，不能原样套用。
- `budgeted_support_diagnostics.py:104` 的现有 `fit_physical_cluster` 是全 L 拟合，会恢复 I 之外的原子，**不能直接用于此次 no-added-support oracle**。可复用 L 构造和 SVD-LS规则，另写很小的受限接口；不复制物理生成器。

既有 `evidence/pilot-geometry.json` 的 `Phi_spectrum` 为 shape `[1024,515]`、rank 515。这是实际既有数值证据；不是本次重新验证。每次受限拟合仍应记录数值秩与阈值。

## 同观测、同 I 的拟合设计

诊断容器先取最终 B_star 原子 ID 列表 S0，形成有序唯一 `I=sorted(S0∩S_true)`，将四臂同一个 `I` 与其 hash 固定。各臂都允许去掉假原子，因此该公共改善不能归因给 M_link；不得增加遗漏原子。

第一版建议仅用共同原始 `y` 和 `Phi_I=G_I pilot_scaled` 作 pilot LS。未知叠加数据仍在 y 中，是所有臂共享的干扰；不向拟合器提供 `data/noise/Htrue/info/g_i`。若选择使用同状态软均值，必须四臂一起改为 `G_I(pilot+mu_soft)` 并冻结同一 mu；不能仅链接臂免费获得可靠软数据。

| 臂 | 拟合接口及含义 |
|---|---|
| M_free | `g_I=argmin ||y-Phi_I g||²`，复杂系数数为 `|I|`。 |
| M_group | 输入额外 incidence `J_p={i∈I:L[i,p]≠0}`，但每个唯一原子仍只有一个自由复杂系数。**仅告知分组而做普通 LS，严格退化为 M_free**，这是合法空机制控制，但不能宣称已经比较强经典组先验。若需非平凡经典组先验，先冻结如 `||y-Phi_I g||²+lambda Σ_p w_p||g[J_p]||₂` 的重叠 group-lasso、权重/λ/求解精度/成本；不能重复创建同一原子的潜变量后暗增自由度，也不能现场调 λ。现协议尚未给这些参数。 |
| M_link | `L_I=L[I,:]`；只估未知 h，目标 `||y-Phi_I L_I h||²`，最终系数只写回 I。重叠行同时接收多个路径贡献。 |
| M_sham | 用下述固定错模板，同 `I`、同组 incidence、同槽数、同链接秩；目标 `||y-Phi_I L_sham h||²`。 |

拟合层建议只收 `(y,Phi_I,I,basis_or_incidence,registered_solver_config)`。真值容器可生成 basis，但不把真实增益作为初始化、正则中心或答案。拟合后 `Hfit=system.gen_h_daft(g_I,I//5,I%5-2)`，不再 Frobenius 归一化 Hfit。终端重放固定同 detector 与 B_star 末端 sigma/scale；是否 Hfit 同时用于取消与检测须提前统一。

秩：分别记录 `rank(L_I)`、`rank(Phi_I)`、`rank(Phi_I L_I)`、奇异谱、零槽、组大小与重叠度。受限后并不保证 `Htrue` 可精确重建；误差包含共同遗漏。对 rank-deficient 链接用预定 `eps64*max(shape)` 的 SVD 最小范数解/秩 r 的可辨基，不把 h 的每个槽当成可辨参数。M_link/M_sham 应维持同 r；**不要把 M_free 也投影进 span(L_I)**，那会把自由模型偷偷变成链接模型。I 为空时共同零维模型须明确记不适用/零拟合与终端调用计费，不能删帧。

## 可固定且严格保秩的 sham

建议在任何结构结果之前冻结全字典确定性单位相位向量，例如 `d_i=exp(2πj frac((i+1)*sqrt(2)))`，取 `D_I=diag(d_i:i∈I)`，定义 **L_sham=D_I L_I**。

这个规则不读取 y 或真实增益，不按每帧表现重抽；每个原子行乘相同单位模相位，故保持：

- 每列/每组非零成员数、行重叠 incidence、原物理槽数；
- 所有系数幅度、列范数；
- `L_sham^H L_sham=L_I^H L_I`，因此代数秩和全部奇异值相同。

它一般破坏同组相对相位，作为**非物理错关系负控制**；不要称其仍是合法 Dirichlet 物理路径。单纯列置换或整列相位旋转只重参数化 h，完全不能产生 sham；禁止使用。

必须检查可辨子空间投影差 `||P_span(L_I)-P_span(L_sham)||`，并报告双方 `rank(Phi_I L)`。当 Phi_I 满列秩时，后者代数秩都为 r，但条件数可不同，须报告而非偷偷白化不同算子。若组只有一个成员，或 span(L_I) 已是整个 C^|I|，该 D 可能仍不改变拟合子空间；此时明确 `sham_nontrivial=false`，属于没有可测试链接约束，不能继续重抽直到出现有利负控制。秩数值门附近要显式标不确定，不任意截掉不同奇异方向来假装公平。

## 实现前的证据与预算缺口

1. `direction_data.py` 的 `_truth['params']` 含构造 L/S_true 所需物理参数，但 `direction_run.frame_record` 的终端 NPZ 目前只存 Htrue 等数组，**没有 `taps,l_i,k_real,l_exp,k_exp,chan_coef_exp`**。仅有现有磁盘终端快照不能唯一恢复物理槽，尤其重叠时。未来结构容器须在同一生成时把这些字段单独保存为 truth-only primitive arrays；或按冻结新 campaign RNG重生纯生成器并验证 H/info/coded/noise hashes 完全一致，成本单独计账。不得由 Htrue 任意分解来伪造真实组。
2. M_group 的非平凡目标尚未冻结；与 M_free 重复执行普通 LS 不能代签“强经典组先验”。这应在结构合约中明确裁决。
3. 主会话已进一步核对 M-02 为“**最多**256块×3 SNR×4臂”，不是强制256。COST-01 已从同一 `structure_CE` 总 cap 扣 **6次** `purpose=engineering_cost_probe`，不能移账或重命名结构结果。可在任何结构结果之前冻结 **mechanism block0..254，共255配对块×3×4=3060 CE**；再预留 **4次CE工程接线烟测**，总计 `6+4+3060=3070≤3072`，仅余 **2次失败余量**。这是上限内事前确定的完整样本合同，不能在看到结果后从256帧删1帧，也不能用剩余额度追加至显著。四臂/三SNR均保留这同一255块；工程烟测另用engineering split。该样本/调用配置仍应在结构合约及共享ledger中明确冻结后执行，本文不代替实际reservation。`structure_terminal` 独立3072 cap须单独核算：主块3060次加工程接线重放（若4次则3064），不能把terminal额度抵扣CE。
4. 最终以共享 `resource-ledger.json` 的累计记录为准，上述3066仅针对本任务明确告知的6次CE消费；若有其他失败/探测，余额进一步减少。
