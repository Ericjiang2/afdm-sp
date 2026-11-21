# 固定容量 A2 / M / G / V 接口研究

状态：只读代码研究，未改实现、未跑实验。依据 S1 `research/contract.md`、`baseline-map.md`，当前 `budgeted_support_eval.py` / `classical_joint_unrolled.py` / `loop9_cache_features.py`。代码正在由 main 更新，以下以符号名和语义定位为准。

## 建议：首批用解析保守上界，零新增剪枝算法

最小、可审计的容量配置：

`B = min(2*k_leak+1, 2*k_max+1)`

`K_prop = floor(K_cap/B)`，要求 `1 <= K_prop <= Q`。

每个提名最多扩展 B 个唯一整数原子；故唯一提名不超过 K_prop 时，现有 `expand_cluster_support` 自然保证 `K_active <= B*K_prop <= K_cap`。边界裁剪和重叠合并只会减少实际数量。原始提名、F2P、完整簇扩展都复用现有实现；不新增第二版 prune，不删除既定簇成员。

| K_cap（parent 候选） | 当前 B=5 时 K_prop | 必须显式设置 protect_added |
|---|---:|---:|
| 8 | 1 | 1 |
| 16 | 3 | 2 |
| 24 | 4 | 2 |
| 32 | 6 | 2 |
| 40 | 8 | 2 |

`protect_added=min(2,K_prop)` 不是可省略的小事。当前 `apply_f2p_refinement` 把保护集合全保留，`n_to_pick=max(0,n_paths-len(protect_pos))`；当 n_paths=1 而保护2列时，最终会返回2列。仅改 n_paths 不能证明容量约束。用既有 `set_refine_config(...,protect_added=min(2,K_prop))` 可避免此边界，无须修改历史 F2P 语义；K_cap=8 适配标签需记录保护数量改变。

本方案是固定**上限**，不保证每帧恰好使用 K_cap；当前 A2 原 oracle nomination 常为约20–30，因此 K_prop≤8 会明显改变初始化。它是最低实施成本的合法公平骨架，不能未经 D_cal 比较就自动称“最佳等预算强基线”。如果 D_cal 显示保守上界损失严重，再单独登记更充分使用容量的策略，不能悄悄把 K_prop 调大而保留虚假的 K_active 保证。

## 1. 两处真值容量入口必须同时清除

`budgeted_support_eval.run_frame` 当前：

- `sparsity=int(frame['params']['P_actual'])`；
- `cfg.n_paths=sparsity`，控制 Torch OMP 及 F2P 最后提名剪枝；
- 外部 `afb.omp_sparse(y,Phi,sparsity)` 先生成 Hhat0，供 achievable scorer 的协方差闭包。

部署配置必须提供不可逐帧变更的 `K_prop/K_cap`。两处 OMP 共用它，不能只改 `cfg.n_paths` 而让 scorer 仍从模拟 P_actual 获益。`P_actual` 可以继续出现在离线报告字段、物理真值评估中，不能进入任何部署分支。

建议保持历史回放路径明确标记 `capacity_source=simulator_expanded_tap_count`；固定路径标记 `capacity_source=frozen_Dcal`，附配置哈希。固定配置不应通过 `diagnostic_support_override` 注入，也不需要 `oracle_support`；这些已有 API 明确属于诊断。外部 OMP 与 Torch OMP 同样的上限不保证相同 picks（数值域不同），现行 A2 就是双初始化；必须计全部成本。

## 2. 精确校验位置与现有 API

| 接口/位置 | 作用与最小约束 |
|---|---|
| `ClassicalJointConfig.n_paths` | 原 OMP 最大提名数，也是 F2P 最后提名 cap；固定后代表 K_prop，不能称实际 K_active |
| `CandActiveRelHead.set_refine_config` | 保持 rounds=2、M=96、defer_prune=True；protect 按上表设置 |
| `apply_f2p_refinement` 返回处 | 可验证唯一、合法且 len(S)<=K_prop；临时 union 仍允许至 K_prop+8，属于额外求解成本，不是最终支撑 |
| `forward` t=0 的 `expand_cluster_support(...)` **紧接返回之后、observer 之前** | 最直接的 K_active 硬验证点。验证 delay/doppler/gains 同长度、唯一 (l,k)、numel<=K_cap；违规报错，不能悄悄截前 K_cap 个 |
| `diagnostic_support_observer` | 可只读记录 raw / selected / expanded；适合记录提名和扩展后数量，不是部署约束本身 |
| `reconstruct_H_torch` 与随后 DA-LS | 当前固定支撑不再增长；初始合法则 M/G/V 改均值/增益/目标不会增加路径数 |
| `off_support_corr` / additive correction heads | 可在支撑外添加 H_corr；固定 A2 家族需确认禁用，仅核对 support_delays 不能约束这些额外分支 |

C2-rel 当前配置的 A2/M/G/V 应只保留相同支撑修复 head；M/G/V 在 t>0 的软反馈路径不改变 t=0 提名。检查四臂 t=0 的 raw support、repaired support 和 expanded support 完全一致是有区分力的公平性证据。

K_active 统计应包括初始增益为0的邻居，因为之后 DA-LS 可激活；不能只数当前非零 gains 或 `abs(H)>threshold`。后者应另报 BP edge count / degree，不与容量互换。

## 3. 如果需要用满容量，不能靠现有配置偷偷实现

当前没有通用的“扩展后受限、仍保护新增列”的 API。不要在实验 runner 复制 F2P 的保护/LS/剪枝，再假装还是原 A2。

可登记的第二阶段选择（不是首批默认）：在主实现中抽取并复用原 final prune+refit 核心，允许对扩展后字典列施加 K_cap。但这是一个新的、必须同施于所有比较臂的容量适配：

- F2P 当前不返回 protected-added 的 metadata；若第二次 prune 仍承诺保护新列，需显式传递，不能从最终零/非零 gains 猜。
- 扩展邻居初始增益为0；直接按现有 gains 大小剪掉邻居会使 cluster expansion 几乎失效。扩展后先 pilot-LS 再排名则增加求解，也改变初始 H，需要记录并重新量预算。
- 若 K_prop=K_cap 且全部提名都保护，扩展邻居没有空位，实质接近禁用扩展。若只保护 top2，原 OMP 提名可能被删除，与“保守保留原列”的 B0 语义冲突。
- 动态丢提名直到扩展能装下也属于新增接受/剪枝规则，会改变 scorer 完整动作；不能通过仅验证最终数量声称动作目标下降。

因此先用解析保守配置获得合法的完整管线，随后根据 D_cal 证据决定是否值得引入新容量策略。若保守方案性能差，不能拿它作方便击败的弱 A2；S5 需标记强基线适配尚未充分。

## 4. D_cal 选择、缓存与隔离

1. parent 已给 K_cap 候选 `{8,16,24,32,40}`。上述映射令 K_prop 无额外自由搜索维度。保持 M=96、rounds=2、add≤4、相同 rho/LDPC/检测器、禁用支撑外增益补偿。
2. 在运行前冻结容量选择指标/样本/代价限制。例如先在 D_cal-fit 运行 A2 五容量，以固定 FER→info BER→小容量的字典序选择；排序只是建议，root 需先登记。再在独立 D_cal-validation 检查可靠性/护栏，不在看 validation 后继续改容量。
3. 为隔离 M/G/V 收益，四臂共用冻结容量。若容量只按 A2 选择，明确是基线导向选择；不要替每臂私下选不同上限后仍声称同容量因果对照。允许的预算优化应在 S5 另登记。
4. 温度依赖轨迹分布；现有 oracle 容量下选出的 T 不能自动称为固定容量校准。先冻容量/先验，再在其 D_cal-fit 轨迹上按既定规则选择 T；固定容量 validation 要递归运行。已看过的 validation 若被用于下一轮选择，重新标记 fit，并保留独立新验证分割。
5. SNR8 的选择只支持该工作点。若正式范围覆盖7/8/9、15/20或压力条件，必须先冻结 SNR/条件汇总规则，使用相应 D_cal；不能取每个 D_dev 最优容量。
6. 既有400帧 prior cache 由 `_harvest_frame` 的 oracle-expanded sparsity 生成 OMP 状态。离线使用这种标签/容量并不等于在线真值泄漏，但其特征/最近邻距离分布与固定 K_prop 不同。复用时只能标记“旧分布先验迁移”；若声称重新校准固定接收器，应复用原 harvest/fine-prior 管线、增加显式 nomination cap 并重采。
7. **避免标签误裁剪**：`_harvest_frame` 当前同一 sparsity 驱动 OMP、可选 BP、`_oracle_dictionary_support(...,top_count=sparsity)`。将其统一替换为 K_prop 会裁剪真支撑标签，制造假负例。应拆为 `receiver_nomination_cap` 与离线 `truth_label_count`；前者固定、后者依原真值支持契约，仅留在离线标签生成。
8. 校准缓存元数据新增 K_prop、K_cap、扩展策略/protect配置、capacity_source、源码哈希、split/样本哈希。现 `load_prior` 只核对 N、信道、M 等，不能识别容量失配；固定模式须明确拒绝标称 fixed 但字段缺失/不匹配的 cache，不能默默当合格缓存。

## 5. 验收建议（无实验已运行）

- 展开界的独立构造：不同 delays、每个中心 k=0、互不重叠，达到 B*K_prop；另测边界 k、重叠簇、合并重复与相消增益。零增益邻居仍计数。
- F2P 小容量反例：n_paths=1、两轮有至少两个可保护新增列；验证适配 protect=1 返回≤1。这是实际边界，不是重复实现测试。
- 双 OMP 真值隔离：固定 y/pilot/config，修改或删除 frame 的 P_actual；捕获外部 OMP 与 Torch OMP 入参，应仍同固定 K_prop，完整部署 H/x/error 不变。评分工厂不接受 H_true。
- 扩展后硬 gate：违规超限输入立即失败；None/default 历史回放仍保持旧行为，不能隐式截断改变旧证据。
- 四臂同初始化：t=0 三层支撑及初始 H 一致；仅 t>0 相应反馈入口不同。K_active 全帧全轮≤K_cap；支撑外 correction head 被禁用。
- 缓存完整性：固定容量/protect策略不匹配，hash碰撞，温度校准来自旧容量但声称新容量，全部明确拒绝。
- 单卡独占预算实测重新做；S1 oracle 容量1024帧计时不能直接转作新固定 A2 的 G2 基准。临时 F2P solves、外部 OMP、M/G/V 的全部新操作计入。

结论：最小配置只需固定两处 OMP 的 K_prop、约束 protect、扩展后硬校验；无需新剪枝。它满足容量上限与真值隔离，但“强基线足够强”和温度/先验转移仍需 D_cal 证据，不能由结构证明替代。
