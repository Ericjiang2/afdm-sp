# GOV-02 / OPS-01 资源证据复核（2026-09-06）

范围：只读本地已归档原始件及 launcher，未连接 deinlab、未启动远程任务、未修改 CSV 或代码。主任务为 `09-05-budgeted-support-repair`。本报告不确认新增预算或记账口径变更；新增 S1 最多 1 小时仍待明确接受。

## 结论与阶段账本

S1/S2 账本仍不完整；不得把并集口径的名义余额当作已核实可调度余额。S1 既有连续历时超限必须保留。S3/S4 有可重算的旧 S4 批次记录，但现有账本仅声明首个已记录 smoke 至最后批次的范围，不能独自证明整个阶段无其他费用。不存在由本次研究确定的精确阶段可调度余额。

| 阶段 | 原阶段上限 | 已有证据（秒） | 未扣缺账的算术余额（秒） | 限制 |
|---|---:|---|---|---|
| S1 | 3600 | 4 项有起止作业的机器/GPU窗口并集均 1500.439437866211；逐作业和 1623.2715837955475 | 并集口径 2099.560562133789 | 不是可调度余额；preflight 至 budget 末尾至少 4281.790248 秒，超原 1 小时 681.790248 秒 |
| S2 | 14400 | 45 项机器窗口并集 3272.294844150543；GPU窗口并集 3060.328550338745；逐作业和 9519.161129236221 | 机器 11127.705155849457；GPU 11339.671449661255 | exact_remaining=null；最早至最晚已记账作业连续跨度 6249.277240276337 秒亦须保留 |
| S3/S4 | 28800 | 旧 S4 十批、46 子作业；首批开始至末批结束 2034.971614599228（33.916194 分钟） | 扣这段已记录连续历时 26765.028385400772（7.434730 小时） | 只是已记录范围的算术余量；缺全阶段完整性声明及 CPU 核小时；没有独立 S3 全量账本 |
| S5—S7 | 86400（合计） | 本次证据集未包含正式运行账本 | 未确认 | 不将“没有找到账本”写成实证零消耗；无可行费用表不开 Dtest |

S1 六项无绝对起止 `.time` 合计 541.73 秒，其中显式 CUDA 五项共 462.45 秒。它们是独立作业，不能丢弃，也不能臆定与已有窗口不重叠。其机器窗口并集对“已发现子集”仅能界于 1500.439438—2042.169438 秒；这不是完整 S1 的界。

仍缺：S1 cuda-preflight 仅有开始、smoke-ach 缺起止/时长、六项 `.time` 缺绝对开始；S2 soft-cpu-repeat-investigation 缺开始/时长、两次 CPU lstsq 探针合计 4.071769884 秒无绝对时间；本地测试、部署准备、生成状态前失败尝试未纳入服务器记录。GPU 作业保留窗口不是 GPU 核心利用率积分。跨阶段并行不能直接相加成全机占用，也不能以重叠抵扣各阶段预算。

## 原始件与复算依据

以下路径相对项目根；旧件均未修改。

- 父方案：`.trellis/tasks/09-05-budgeted-support-repair/research/next-execution-plan-20260906-v2.md:186–205`。首包同时 ≤2 GPUh、≤2 单机忙碌小时，且分别在 S2 原4h、S3/S4原8h经核实余额内划拨，不跨借；新口径及 S1 新增包需要后续明确接受。
- S1/S2 审计：`.trellis/tasks/09-06-minimal-repair-mechanism/research/resource-ledger-audit.json`、同名 `.md`，快照 `2026-09-06 02:06:04 UTC`。JSON `stages.*.rows` 保留每项 evidence 路径、开始、elapsed、设备；`exact_remaining_seconds` 均 null。
- S1 原始 preflight：`.trellis/tasks/09-05-contract-and-baseline/research/runtime/cuda-preflight.json`，开始 `2026-09-05T23:20:24.722173+00:00`。审计 budget 子作业结束 `1788653337.4988124 + 1369.013608455658 = 1788654706.512421`；减 preflight 开始得到约 `4281.790248` 秒。
- S1 既有 launcher 原始批次：同 task `research/runtime/geom-cpu-batch.json`、`thread-probe-batch.json`；budget 子作业记录来源保存在审计 JSON（`budget-1024-batch.json`）。
- S4 摘要：`.trellis/tasks/09-06-minimal-repair-mechanism/research/s4-run-ledger.json`。十份实际批次均在其 `research/runtime/`：`cal-batch.json`、`capacity-dev-batch.json`、`capacity-fit-batch.json`、`capacity-prior-batch.json`、`capacity-prior-smoke-batch.json`、`capacity-smoke-batch.json`、`capacity-validation-batch.json`、`entrances-dev-batch.json`、`entrances-smoke-batch.json`、`smoke-batch.json`。
- 本次用 `/opt/anaconda3/bin/python` 重新读取所有上述十个 S4 批次：开始和 elapsed 与汇总完全相等，均 complete=true，子作业共46且全部 exit_code=0。`max(start+elapsed)-min(start)=2034.971614599228`；批次 elapsed 之和 `1171.6800773143768`。子作业 elapsed 和 `2939.6495451927185`；对子作业起止区间排序合并后机器窗口并集 `1143.6177535057068`。这些只是辅助审计，不能用较小并集替换旧连续历时。
- S1/S2 使用同样区间合并算法重新算得表内并集，与原 JSON 一致。区间为 `[started_at, started_at+elapsed_seconds]`；重叠或相接取并集。没有以文件 mtime 代替开始/结束。

## deinlab 环境与可复用入口

远端路径来自既有归档/launcher，**不是此次实时探测**：

- 项目：`/data/guoyikun/00inbox/AFDM-channel-estimation`；阶段输出根 `outputs_budgeted_support_repair/{s0s1_20260906,s2_20260906,s4_20260906}`。
- Python：`/home/guoyikun/.conda/envs/AFDM/bin/python`；preflight 记录 Python 3.10.20、PyTorch 2.5.1+cu121、CUDA runtime 12.1、hostname `liunxgpu`、RTX 4090（24564 MiB）、driver 580.173.02。预检的 complex128/64 求解通过只证明该设备线性代数检查。
- 权重：`/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk`。
- 旧 S2 prior：`outputs_budgeted_support_repair/s2_20260906/calibration-snr8/cache_snr8.pt`；旧固定容量 prior：`outputs_budgeted_support_repair/s4_20260906/prior-cap40/cache_snr8.pt`。是否满足新 direct40 输入域需另行验证，不能仅按文件名复用。

本地可复用 launcher 源：

| 源文件（相对 `.trellis/tasks/`） | 远端 frozen source | 现有机制 / 不能直接代签 |
|---|---|---|
| `09-05-contract-and-baseline/research/run-s1-budget.py`，`run-s1-thread-probe.py`，`run-s1-cpu-replay.py` | S1 旧 source snapshot | 保留旧锚点来源；不得直接重跑新增 S1 计时 |
| `09-06-bottleneck-diagnostics/research/launch-s2.py` | S2 source-v2；refs 用 v3；controls 用 v5 | 独立日志/批次/PID、2—3槽、taskset、超时杀自己进程组；旧 S1 timing complete 检查不等于新 GOV-02 预算通过 |
| `09-06-bottleneck-diagnostics/research/launch-calibration.py`，`launch-soft.py` | 各脚本固定 source | 可复用调用模式；须保留旧快照与输出 |
| `09-06-minimal-repair-mechanism/research/launch-s4.py` | S4 source-v1 | 顺序 GPU lane、CPU16—19、独立 session；明确非 G2 并发计时证据 |
| `09-06-minimal-repair-mechanism/research/launch-entrances.py` | S4 source-v2 | 最多3 GPU作业、CPU16—27、独立 session及超时 |
| `09-06-minimal-repair-mechanism/research/launch-capacity.py` | S4 source-v3 | CPU prior旧为5槽×4线程（36—55），GPU3槽×4线程（16—27）；新 OPS 起步CPU2槽/GPU2槽，不能原样继承旧并发 |

这些 launcher 的 `touch(exist_ok=False)`、日志 `open('x')` 能拒绝覆盖旧输出，子进程 `start_new_session=True` 提供连接独立性的一部分；它们没有完整证明新 OPS 要求的按不可变样本清单补缺、逐批预算核验、22 GiB峰值门及并发自适应。外层 launcher 本身也需脱离 SSH 会话，不能从子进程参数推断外层已持久化。

## 交给主任务的门控事实

1. 可先实现本地契约、费用表结构、可恢复队列；这些工作不需要将 S1 新增包推断为接受。
2. 任何新远程批次先读现存 PID/进程/产物，再登记实测 t_arm、求解计数、至少20%余量和阶段分账；缺账未解决、费用未知、余额不足时明确阻塞受影响批次。
3. SSH 的 `ServerAliveInterval=30`、`ServerAliveCountMax=3`、复用 ControlMaster 来自 v2/OPS 契约；本次未检查本机 SSH 配置或远端进程，因此不声称其已满足。
4. 补账可增量完善证据，不能删除旧超限/失败费用；新增 S1 1h及新口径仍由后续明确接受记录解锁，CSV生成或旧 go on 均不足以代签。

## 增补：用会话起止补具体缺账，建立保守可用额度

本节取代前文“账本不完整所以不能建立任何可调度余额”的过强解释：精确消耗未知，并不等于无法建立有证据的保守消耗上界。主会话现已只读确认 deinlab 仅既有 S0/S1、S2、S4 输出目录，S4 十个 batch 与本地一致，GPU 空闲且无相关存活作业；结合任务的“本轮已登记批次全部收齐”记录，可把已登记任务集作为审计范围，而不为没有具体迹象的假设隐藏任务无限预留。

### 已补回的 S2 三项工具执行起止

使用已读取的 `trellis-session-insight` 技能及 `trellis mem search soft-cpu-repeat-investigation` 定位历史；随后直接读取平台 JSONL 的 `item_completed/CommandExecution` 起止、退出码和命令。没有使用 mtime。

| 具体缺项 | 平台记录包围窗口（UTC） | 同步SSH耗时上界（秒） | 证据 |
|---|---|---:|---|
| soft-cpu-repeat（control/control/observed/control/observed） | 01:12:50.999—01:13:00.753 | 9.7541355（可向上预留10） | 主会话 rollout 第1641行，exit0，CPU32—35、OMP/BLAS4，stdout与归档JSON的差异及314/119完全一致 |
| 第一个 CPU lstsq 探针 | 01:42:41.223—01:42:45.362 | 4.139（可向上预留5） | CPU研究子会话 rollout 第53行，exit0，timeout60 |
| 第二个 CPU lstsq 探针 | 01:43:27.812—01:43:30.766 | 2.954（可向上预留3） | 同子会话第69行，exit0，timeout30 |

主会话文件：`/Users/guoyikun/.codex/sessions/2026/09/05/rollout-2026-09-05T21-56-19-01a071db-1910-7ba1-8650-9599767c12df.jsonl`。

CPU研究文件：`/Users/guoyikun/.codex/sessions/2026/09/06/rollout-2026-09-06T09-41-09-01a07460-65e4-7183-a441-7e021b9132f7.jsonl`。

同步SSH执行包围远端Python生命周期，包括连接/启动/收尾；按整段作为保守运行上界成立。三项均落在 S2 已知连续跨度 `00:14:47.309573—01:58:56.586813 UTC` 内。因此保持连续历时记账时无需再加这三项，更不能再称其完全无法定界。若需要未来忙碌账本，可以分别补18秒保守预留，不能冒充实际机器并集增量。

### S3/S4 的保守完整工程窗口

主会话日志可见：

- 第1802行，`01:40:52.075 UTC` 开始恢复当前上下文；第1842行开始读取父实现及 S4 interface，第1879行 `01:43:23.258` 创建 S3/S4任务。
- 第1909行开始记录失败测试，后续第1925、1935、1994、2011、2199、2207、2217等行涵盖失败/通过回归；不是只算最后31测试1.194秒。
- 第一远端 S4源码打包/部署在第1963、1970行，真实smoke开始 `01:49:53.435111`；全部十批终点 `02:23:48.406726`。
- 第2386行包括 py_compile；第2393、2404—2405行包括结果分析、回收；第2412行生成最终账本；第2422行形成最终裁决；第2429—2431行收回账本、检查diff和远端GPU。最后 `02:29:08.109` 返回 GPU0%、1MiB。
- 第1789行 `01:31:19.262—01:31:21.725` 的较早本地小系统探针是 S2 conservative 支撑保留检查，非遗漏的 S4机制实验。

由此可将 **`01:40:52.075—02:29:08.109` 整段2896.034秒** 全额计入旧 S3/S4，保守地包括准备、开发间隙、本地失败/通过测试、CPU prior、GPU作业、分析、收尾以及同时发生的其他阶段工作。它比旧 S4 批次跨度2034.971615秒更宽；绝未以union替换旧历时。按单机预算保守计入此完整工程窗口后：

`S3/S4 conservative_remaining = 28800 - 2896.034 = 25903.966秒 = 7.195546小时`。

该值是**既有已登记工作集的保守余额下界**，不是测得的精确余额。GPU也可以保守扣同样2896.034秒，而不要求先重构精确GPU并集。CPU核小时精确量仍不可由历时推导，应独立标未测；不因此推翻单机/GPU预算的保守界。旧S3未强制开发排序网络，原prd明确S3排序证据不足，本轮实现已有S4信号，不能另假定有未知S3批次。

### S2 更宽的阶段保守窗口

如果必须把本地工程、准备、所有明确探针及最后收尾也纳入，而不只扣原104.155分钟，主会话第787行记录 `00:02:05.684 UTC` 创建 S2任务，后续到共同收尾 `02:29:08.109 UTC` 都纳入，得到：

`S2 conservative_consumed = 8822.425秒`，

`S2 conservative_remaining = 14400 - 8822.425 = 5577.575秒 = 1.549326小时`。

这段覆盖原45作业、三个补回探针、本地 conservative 小系统、报告/回收，也保守包含 S4 的重叠时间；不是阶段间借用或抵扣。它是针对已登记 S2 阶段的明确有限上界，不等于用当前墙钟减任务创建时间（任务在本轮收尾后处于等待/规划，不能无依据持续计费）。如果后续发现具体此窗口外 S2 计算，只按新证据增量扣款；不存在具体证据的“可能还有作业”不能无限阻塞。

### 可操作结论

在主会话的远端目录/进程清点和上述历史窗口联合依据下，可以合理建立旧已登记阶段的保守余额：S2至少5577.575秒，S3/S4至少25903.966秒；均保留旧连续历时，不需要静默接受新union口径。新批次还必须满足实测费用、求解次数、至少20%余量、首包≤2h及其他科学依赖；S2不能因此开满2h。S1旧超限和新增1h待明确接受完全不变。
