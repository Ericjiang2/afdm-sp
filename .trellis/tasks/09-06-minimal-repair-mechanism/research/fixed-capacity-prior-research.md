# 固定提名容量 achievable prior：精确调用链

只读研究；未改代码、未运行。行号按本次读取，main 并行编辑后可移动。`e1_harvest.py` 在当前项目不存在；实际入口为 `decision_harvest.py`。

## 1. 当前两条入口汇合于同一 harvest_frame

磁盘缓存路径：

`S2 research/launch-calibration.py:32–40` → `python -m afdm_sp_joint_unrolled.decision_harvest` → `decision_harvest.main:333–359` → `run_harvest:251–330` → `harvest_frame:141–248`。

E1 在线建立离线 prior 路径：

`e1_ldpc_coded_eval.py:255–259 _gateA_lookup_for` → `decision_gateA.py:50–77 calibrate_fine_prior` → **同一个** `decision_harvest.harvest_frame`（GateA 第39–40行导入）。

`loop9_cache_features.py` 只向这条路径提供 `_make_config_a`、`_oracle_dictionary_support`、`_build_features_np`、`_pad_v_to`；其 `_harvest_frame` 不在当前 prior 缓存调用链上。最小改动无需动训练缓存的 `_harvest_frame`。

在线 scorer 路径：

`budgeted_support_eval.load_prior:35–48` → `decision_bound.build_fine_prior:47–96` 得到 lookup → `run_frame` 用固定 OMP 的 Hhat0 调 `decision_gateA.make_genie_lambda:150–168`。工厂虽名 genie，实际传 Hhat0，构造 `(1-rho)Hhat0Hhat0ᴴ`；每轮 sigma²、普通 LS 残差与候选重算 whitened T/q，再从 lookup 取 pi/sh2。**缓存 T_genie/T_realiz 都不参与当前 build_fine_prior**。

## 2. 最小语义改动位置

建议给 harvest 与 wrapper 增加 keyword-only `nomination_cap=None`。None 明确保留旧回放逻辑；固定模式传1/3/4/6/8，不通过修改 sys_obj._P_actual 实现。

| 文件/行 | 当前用途 | 固定模式最小处理 |
|---|---|---|
| `decision_harvest.py:151` | 读取 oracle-expanded `sparsity` | 分离 `truth_count` 与 `receiver_cap`；cap验证正整数≤Q |
| 同文件 :163 | `omp_sparse(...,sparsity)` | 仅改此入参为 receiver_cap，后续 s_omp/g_ls/r0/Hhat0 自然适配 |
| 同文件 :170–171 | `_oracle_dictionary_support(...,sparsity,return_gains=True)` | 真标签用完整字典上限 Q 或至少完整展开条目数；**绝不传固定 nomination_cap** |
| 同文件 :176–179, :211–226 | 候选/最近邻特征与标签 | 复用原算法；fixed OMP 已传播，不重写几何/候选实现 |
| 同文件 :233 | raw['sparsity'] | 保持“接收器 nomination”语义用于下游，另显式记录 truth_label_count / capacity_source |
| 同文件 :251–253, :279–280 | run_harvest 参数与调用 | 转发 nomination_cap |
| 同文件 :318–321 | cache config/argv | 存容量/标签/采样域字段，见下节 |
| 同文件 :333–359 | CLI | 新增 --nomination-cap 并转发；打印实际 cap |
| `decision_gateA.py:50,61–62,76` | 直接校准 wrapper | 可同参数转发，并在 metadata 记录；旧 E1 调用不传参数仍回放旧数据 |
| `budgeted_support_eval.py:35–48` | loader + prior factory | fixed 模式要求匹配 cap/标签域；数据字段和 build_fine_prior 算法复用 |
| 新版本 launcher | 冻结 source，启动 CLI | 每 cap 用独立目录/状态/日志；不覆盖既有 S1/S2 snapshot |

truth helper `loop9_cache_features.py:78–111` 会合并重复 (l,k) 的复增益，再按 |gain| 排序取 top_count。传 Q 可保留所有合法字典原子，而无需知道当前 receiver capacity。当前 helper 不专门过滤合并后恰为零的 gain；若新契约把精确抵消列定义为不活跃，应明确过滤并测试，不能不记版本地改变旧标签。固定容量改造的核心要求是**不因 K_prop 变小而裁剪真标签**。

不需要更改 `make_genie_lambda`、`build_fine_prior` 的概率模型。只需保证部署 Hhat0 的 OMP 使用同 cap。F2P 第二轮的 S 比第一轮更大，prior 当前仅由初始 OMP 状态校准：这是已有的跨轮迁移近似，固定 cap 后仍需标明；本次无需另造每轮 prior。

## 3. cache 最小域与装载约束

保留现有字段：N、v_mean、p_paths（生成器物理路径分布）、tau_ms、fs_factor、rho、sigma2/SNR、l_max、k_max、M=96、n=400、seed列表及seed_base。固定接收器 cap 与物理 p_paths 必须是不同字段。

新增最低字段：

- `capacity_source=fixed`、`nomination_cap=1/3/4/6/8`。
- `label_scope=full_aggregated_in_dictionary_support`，标签规则版本；不得把 requested physical p_paths 当真标签上限。
- `candidate_rule=pilot_mf_topM_off_initial_omp`，`feature_stage=initial_omp`。
- `data_mode=iid_qpsk`：当前 harvest 不编码 LDPC，生成 data_idx∈{0,1,2,3}。这是传统 prior 校准域；不能把它写成 coded D_cal。若未来需要 coded prior，属于新采样规则，复用主 frame generator、明确新版本。
- `phase_convention=python`、c1/c2、pilot/dictionary hash；既有 schema 缺这些，固定模式补齐更容易检测系统配置漂移。
- source manifest / file hashes、split=D_cal、独立子集标识、输入 H/data/noise/y 哈希（或可验证逐帧 manifest）、attempted/accepted/skipped。种子相同不意味着样本没变，光存 seed 不足以跨版本证明身份。

K_cap、k_leak、protect_added、rounds、addcap、BP/LDPC 参数 **不直接参与这个 initial-OMP prior 的拟合**。它们需存在 receiver manifest，不能假装都必须重新拟合 prior。缓存记录 K_cap 与策略便于追踪可以，但 loader 的计算相关匹配核心是 nomination_cap + 初始候选/字典/输入分布。比如不同 k_leak 却同 K_prop 时，initial-OMP prior 可共享，接收器仍需独立温度与性能验证。

loader 固定模式检查：

1. 当前 n=400、M=96、shape=(400,96)、有限、unique400 seeds 的原 gate 保留。运行不足400则拒绝，不从其他 cap 拼帧。
2. 要求 fixed capacity metadata 且 cap严格相等；缺字段的旧缓存不是 fixed。legacy 模式可继续按旧边界读取，避免破坏历史回放。
3. 标签 y∈{0,1}、g_nn/genie_gain_sq≥0；dl/dk整数且范围符合字典；p_real>0且≤nomination_cap（OMP可能提前停）。若保留 mask，mask行和应等于p_real。
4. 校准源 schema/label_scope 一致；不可声称 full labels 却装 top-K_prop 截断标签。
5. build_fine_prior 仍用 gain_edges=1/3、2/3 分位数，min_count=30、min_act=8；记录这些参数和分箱统计。训练候选数400×96只用于估计先验，不能当38400独立帧做端到端置信区间。

## 4. 运行调度与可避免的成本

现 launcher 固定 SOURCE=`s0s1_20260906/source-trace-v1`，该快照没有新参数。需新的不可变 snapshot；不能改旧source让旧 run manifest 指向不同代码。

同一 SNR 的五 cap 可共享同一批独立 D_cal 信道/data/noise seeds，再分别由各 cap 生成初始 OMP 状态，便于比较；它们是**配对的400簇**，不是2000独立帧。与当前 temperature fit/validation、D_dev/D_test 的身份去重仍需通过。使用现 `seed_base+snr` 属 legacy seed scheme；若保留，manifest 如实写，不冒充完整五元 SeedSequence 原生流。

现 `harvest_frame` 每帧计算 true-H 和 Hhat0 两次 dense Cholesky。当前 prior loader 仅消费 dl_nn/dk_nn/g_nn/y/genie_gain_sq，因此这两次分解不是 prior 拟合所必需。最低代码改造可原样保留，容易校验；若CPU预算使五cap过慢，可在**同一 harvest_frame** 中增加显式 `prior_only` 产物模式，先共用生成/OMP/候选/几何/标签部分，再跳过 whitened统计。不能复制整段 harvest，也不能给没算的 T/q 填0伪装完整缓存。prior-only schema 必须与完整cache区分；现 load_prior 无需 T/q，可接受该明确模式。

现 `run_harvest` 最多3*n次尝试，结束即保存，可能 n不足；fixed运行宜在保存成功标志前显式要求 kept==n_frames，保留失败/不足状态。空 buf 会在 np.stack 失败，不能吞掉。当前 calibration wrapper 的最大尝试为20*n，两入口须分别记录真实 attempts，不悄悄换采样规则。

## 5. 最小有区分力验收建议

- 同一模拟帧拥有多个真原子，nomination_cap=1；未被提名但在 topM 中的其他真原子仍 y=1，完整gain保留。与“把全部 sparsity 换1”的错误实现形成反例。
- 不同 nomination caps 下，H/data/noise/pilot/y 输入哈希相同，receiver s_omp大小受各自cap限制；truth集合与完整gain相同，missed只因s_omp变化。
- None/default 与旧 source 的固定小样本 cache 必需字段一致；明确数值域，不以CPU微漂移掩盖标签/seed差异。
- 若新增 prior_only，其五个拟合字段、candidate IDs、p_real 与完整 harvest 同帧一致；不能只比较 build_fine_prior 的最终近似结果。
- 装载错cap、标签截断schema、错误字典/pilot、不足帧数、重复seed或输入哈希碰撞：均失败。

结论：主要代码触点是 decision_harvest（新参数/标签分离/metadata）、GateA 转发、fixed loader、版本化launcher。loop9 的训练 harvest 不在当前路径，无需扩散改动；fine-prior 模型和 achievable scorer 工厂均可复用。
