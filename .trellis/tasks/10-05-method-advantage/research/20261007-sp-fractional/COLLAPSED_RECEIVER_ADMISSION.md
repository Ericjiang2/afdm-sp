# COLLAPSED-RECEIVER-01 源码与运行准入审查

日期：2026-10-08。任务：`.trellis/tasks/10-05-method-advantage`。
CSV：`.mission/20261007-sp-fractional-trans/20261007-sp-fractional-trans.csv`。

review_actual_model: unavailable_from_current_tool_metadata
review_actual_reasoning: unavailable_from_current_tool_metadata
validation_limited: model parity unknown

## 当前结论

**冻结源码静态准入 PASS；本报告末节绑定的一次 ENG 运行 GO；DEV 尚未 GO。**
源码及 ENG 字节审查无阻塞。实际搜索、receiver、fixtures、数值一致性和完整成本
尚未运行验证；DEV 必须先取得本次 ENG 原件审计 PASS，再完成独立 DEV 字节准入。
原默认两臂的输出逐值复核仍留在 DEV 封口后的独立 raw 审计。

本轮只审冻结源码、三个部署脚本及回传脚本的参数化差异，未 SSH、未生产 import、
未执行任何科学计算或 fixtures。没有修改源码、原件、STATE 或 CSV。
按主线程最新所有权要求新建本报告，未修改 blind_invariants 的纯协议报告
`COLLAPSED_RECEIVER_REVIEW.md`。

## 依据与冻结身份

继承协议 PASS，不重复其数学论证：
`COLLAPSED_RECEIVER_PROTOCOL.md` SHA-256
`a2e1d817dca07fc07db764f16e828edf5e7a7a2065cab610ed8009b227ffc741`；
纯协议报告本轮读取版本 SHA-256
`1cff711ad0a2f340abdd9d47b830fa7e81ae2647d1887e6c2331df85eb44fbc7`。
已完成的 `COLLAPSED_MATH_RAW_REVIEW.md` PASS 为前置证据，本轮没有重复其原件核验。

source commit：`62508b84d64be5e3504ad9a2e14ea0e77a4fa60c`。
下列六文件均以 `experiments/afdm_sp_fractional_receiver_20261007/` 为前缀，
工作区逐 SHA 匹配 `dispatch/collapsed-receiver-source-ready.json`：

| 文件 | SHA-256 |
| --- | --- |
| `collapsed_gain.py` | `25e9e351df7c84ff4bd094bc1f735bb9666569fe84fcd828160993ffaba55a2d` |
| `receiver.py` | `5c9c7ea28b708b41bb74df94a001db10adae73010a6470a354d30eb674ee3a00` |
| `runtime.py` | `8df7e4c41fc9a9db26edba65462846951864660e15efb8054a3d2ca0bf59ce75` |
| `study.py` | `bebacf95b3b20aecf541574f336409cb2c4e28f53746d476c74a60859624afb1` |
| `local_search.py` | `08b9b87565e7c337fdc7740551a6e380d6c1699823b2e34536e2c27fd8b70a88` |
| `collapsed_engineering.py` | `c048943e80ec6fb21ff24f7a84f045ae5258adada7542fd3c4a3b815def2f47b` |

已读取本地 source manifest：68 Python 文件；其六个修改文件与 READY 相同。
manifest SHA：`a947fd80fa841839cd710651abe44f6d0833449ac98c95af6573249479d15eac`。
其中登记 snapshot `36dc6e527df93fa7494436d1b47a1238fa4b4554`、archive SHA
`ef85fd4662811500c01812c9130c718713b0aa25273313689aedd27eb03c7650`。
本节只记录 manifest 身份，不冒称已完成整套 snapshot/tar/远端部署字节准入。

## 源码检查

### 原路径兼容

以已审 `d3b2f1d8008db8db0f2cf1adf31dc5b39e4c49e3` 为基线查看实际差异。
fixed/adaptive 原配置路径保持原三臂、24 calls、20 sweeps；adaptive 的 quadrature
参数和值不变。默认 `receive_population`、`score_population` 仍为原 `runtime.ARMS`。
scalar 实际仍执行自己的完整 F1、两轮 refine、20 detector iterations；新配置用
`sweeps.f1_scalar=None`，另写真实 detector/refinement 次数，没有把 scalar 记成 0 计算。

原 vb_point/vb_continuous 的 gain-before → Doppler → gain-after → 三 data steps
分支和 20 sweeps 保留。MomentFactory.snapshot 扩展汇总新 owner 工作键；
原 PathMoments 仅有的三种变换键仍按原方式求和。
这属于源码兼容核对，不是新的逐位输出复现声明。

### 局部搜索与 collapsed 状态

两局部臂共用 `local_search.maximize`：当前值 ±.75 并与 [-3,3] 相交；
显式按 previous/lower/upper 顺序评分，再调用一次 bounded 搜索。
`xatol=1e-4`、`maxiter=32`；每次 callback 先检查 35 次总评分上限。
完成时再核 optimizer success、有限性、窗口、nfev≤32、nfev 与实际内部调用数一致，
终点必须对应已记录的 value/score，没有额外免费终点评分。
选择只用严格 `>`，常数势保留 previous。失败保留 trace 和计数，不重试或加密。

local point 使用与原 PointOptimizer 相同的 Fourier 条件势，去掉与 ν 无关的
第零项；五个 sweeps 各保留 gain-before、固定 gain 的顺序 Doppler、gain-after
及三个原 data steps。

score-only 在原 evaluate 的同一 column/u/v/s/t/J 计算后提前返回；
不建立第二套数学公式。默认完整 evaluate 原数值路径不变。
score-only 保留有限性和 s≥P，跳过完整 C/residual；完整 winner 另调用一次默认
evaluate，started/completed 分账，并要求其 J 与已选 score 相同。
因此每坐标最多 35 次搜索评分加 1 次完整 winner，不把第 36 次当成免费缓存复用。

collapsed 每坐标按当前 factors/m/C 新建 canonical op/source，再准备 Schur 块；
接受后保留完整 winner m/C 并更新 point factor，下一坐标再次新建 owner。
未跨 owner 复用旧 SourceMoments，也未只替换旧 kernels 的 ν。
最后坐标的完整 m/C 供该 sweep 的三个原 data steps 使用；五个 sweeps 不冒称收敛。
重建 phase/FFT/完整 R/f、块 factor/identity RHS、搜索及 full winner 均有实际费用记录。

### ENG 固定回放

18 输入为原 MATH-01 十文件，加已封口 COLLAPSED-MATH-01 的 attempt、registration
和六个 case。输入哈希及原注册关联先核对；读取 reference case 数组前，先完成本 case
自己的 score-only/full 回放、保存 NPZ 并写 replay seal。对照后重新核其 seal SHA，
参考值不进入评分或搜索。

配置和控制流一致：6 个新 canonical/source、9 坐标准备、45 次 score-only、
9 次 offset=0 完整默认 evaluate；6 次非空块共享 Cholesky、12 次共享三角调用、
72 次候选三角调用、9 次完整 C 恢复、9 次 precision residual。
总候选列计算 54 次，phase/matched 项 18864、cross 项 12576；
inverse DAFT 21、ordinary FFT 6；0 derivative、0 physical basis、0 receiver。
对应 EXPECTED_WORK 会与实际账本核对，没有把 full 重算藏进 45 次评分。

三个原组件 fixtures 各一次，外加常数势/递增势端点两个真实搜索控制 fixtures，
独立记录 trace、score 次数和操作账本；没有 mock gain 求解或伪装完整接收。
default_contracts 明确只做配置和源码入口检查，不将字符串检查当成真实 seal/receiver 测试。

### DEV 四臂与 truth 顺序

固定原 4 blocks × 2 SNR，四臂各自运行 F1；工作量由臂数导出为 32 calls。
按 block modulo 4 轮转，同 block 两 SNR 保持同顺序，原三臂默认轮转仍为 modulo 3。
原 population loader 继续验证原 registration、完整 8 observation 顺序及路径白名单，
只复制 truth bytes；receiver 阶段仅解码观察量白名单。

全部 calls 完成后写不可覆盖 receiver_seal；评分先核 records 数量和全部 raw SHA，
再解码 truth。分母为每 observation 2048 bits，runtime 仍以 LLR<0 判 1。
失败调用与完整耗时保留；不以成功子集冒充完整 32 次。

旧 90% point 错误门、不得差于 scalar、1.25 倍 scalar 中位完整 wall 门保持。
point 零错误标 inconclusive。匹配控制额外保存逐 block/SNR 的错误数、硬判变化、
纠正/新增错误、完整 wall/CPU 差；只有 collapsed 总错误严格更少才记匹配改善。
旧 scalar/point 逐值复现被明确标为待封口后独立 raw 比较，不静默替换原基线。

ENG/DEV 分别显式传入 120/240 秒 wall cap，config 与原已审 protocol guard/recorder
绑定一致；进程预算分别为 150/270 秒及 10 秒宽限。DEV 仍需 ENG 原件审计 PASS，
本次源码结论不提前授予任何阶段运行 GO。

## 部署与回传脚本窄审

以下路径以 `.mission/20261007-sp-fractional-trans/dispatch/` 为前缀：

| 文件 | SHA-256 |
| --- | --- |
| `build-collapsed-receiver.py` | `b18c9b1cd3658873d2db8d2b22b80baad7aa72b1f9fe039043eea306c97db755` |
| `prepare-collapsed-receiver.py` | `7ec91f287197fa9a08e1a7205d3a0875b1e072cad634d508e4b1e6caf073876f` |
| `preflight-collapsed-receiver.py` | `c7293389c9811708c88be3e319587934e998b6d7335006551abcaa1aea552e8a` |
| `harvest-collapsed-receiver.py` | `ebda9c9fd73ee287a4f6f5a8628bf9cc4d0a02f88ae10489c76afd6aee9788ff` |

前三脚本未发现明显执行风险：按明确 source commit 独占建立 snapshot/archive；
ENG 18 输入和 DEV 16 个旧 population 文件分别绑定；import-only 获取配置/清单后
检查 whitelist；只生成对应 launcher，不启动科学运行。launcher 写入都在阶段专用
`/data/guoyikun` 根内，线程/CUDA/timeout 与已审协议一致。preflight 核 source/input、
Git、已有 attempt、进程及合同/launcher/archive 哈希，最终仍由独立字节准入判定。

harvest 仅定点核对相对已用数学回传脚本的差异：增加 engineering/development
受限参数，从对应合同读取 root/stage，输出到各自独占目录；回传核心未变化。
本轮未执行这些脚本，不重复旧回传核心的等价审查。

## Findings (fixed)

未发现需要修复的源码问题；本代理仅创建本准入报告。

## Findings (not fixed)

无源码阻塞。实际 SciPy 搜索、回归数值、完整 receiver 输出和预算仍待各自获准运行
及原件审计；尚未完成分阶段远端字节准入。模型/effort 元数据限制如上，不声称能力已证相等。

## Verification

- 六个 READY SHA 与本地 source manifest：PASS。
- Ruff：PASS，六源及四个部署/回传脚本。
- AST / 内存 compile：PASS，同上十文件；没有 import 或执行模块。
- commit diff --check：PASS，六个源码的已提交变更。
- TypeCheck：未执行，mypy/pyright 未安装；AST/compile 不替代类型检查。
- Tests / 科学 Runtime / SSH：本轮未执行；不将静态默认合同视为运行验证。
- 规范：复用此前已加载的 working prior、完整成本、冻结证据与 bounded-study 约束；
  固定搜索/科学工作量留在任务协议与配置，未发现必须追加全局 spec 的独立合同缺口。

## ENG 冻结字节准入：one-run GO

日期：2026-10-08。只核本地回传字节及已登记配置，没有 SSH、生产 import 或科学计算。
材料位于 `.mission/20261007-sp-fractional-trans/control-collapsed-receiver/engineering/`；
source manifest 位于其父目录。源码仍为前述 `62508b84` 提交及 `36dc6e52` snapshot。

| ENG 材料 | SHA-256 |
| --- | --- |
| `remote-imports.json` | `2442f339c6acd4b13473618a50aa2a87cb7c6476a6c693de7c174339dfca3ea7` |
| `remote-config.json` | `58ef9541631688a4070a57181efa600e2e9b1835cd900eed26861be650ca737c` |
| `input_manifest.json` | `dce61874e1908dbd20d3287d36347032449d301a877e5a13f5d35a9ebc625f3a` |
| `run_contract.json` | `50c966fb306d1bc227b3edd11fcf1f3fdbed47c6c4775ef22c8b1457117e88e8` |
| `launch.sh` | `e458e261ee6dd44cbd143743847aa50304a3a655f44cc680cacbad052627b7c7` |
| `byte-preflight.stdout.json` | `bf02997f828756570ac9c1c08bdd7d60827c075fe8b2de0a38d14013334e7083` |
| source archive | `ef85fd4662811500c01812c9130c718713b0aa25273313689aedd27eb03c7650` |

唯一 stage：`COLLAPSED-RECEIVER-ENG-01`，kind=`engineering`。
唯一执行根：`/data/guoyikun/afdm_sp_collapsed_receiver_20261007_engineering_62508b84`。

### 字节检查结果

- 全部 68 Python 文件：工作区 = source commit = 隔离目录 = snapshot Git tree =
  tar 文件字节；SHA/大小与远端实际回执一致。六个 READY 文件未漂移。
- snapshot HEAD 匹配、工作区干净，完整 Git 文件集合等于 68 文件白名单；tar 无重复
  成员、路径逃逸或链接成员，除 `.git` 元数据外没有额外文件。archive 本地 SHA 与
  manifest、contract、远端回执一致。
- 18 输入完整匹配原十文件绑定及已审 COLLAPSED-MATH 的 attempt/registration/六 case。
  后八项还与本地已审原件逐 SHA/大小比对；全部 86 source/input 项与回执匹配。
- imports 恰好为 68 个唯一白名单路径。两份原始 import-only stdout 与规范化
  remote-imports/config 一致，exit=0、stderr 为空；不是数学/fixture 执行证据。
- config 与合同逐字段相同；18 saved_input_paths 无重复遗漏。
  6 cases、45 score-only、9 full、3 原 fixtures、2 搜索合同、70 搜索评分总上限、
  0 physical/derivative/receiver/new observations 均符合协议。
  replay_exact_work 还与冻结源码 EXPECTED_WORK 的 AST 字面量逐项比较相同，
  未通过执行生产配置函数来冒充静态验证。
- 实际 launcher 与远端 SHA 一致，本地独立 `bash -n` PASS；只有一条 ENG 调用，
  固定原 math-attempt、variant=collapsed、stage 和 artifact-root。
  120 秒 stage CPU/wall、150 秒进程及 10 秒宽限、单 CPU/CUDA 隐藏、4 GiB/128 MiB
  与合同一致；runtime/cache/tmp/artifact 都位于该专用根。
- 远端标准库 preflight 为 PASS，记录无匹配的并发科学进程，source/input、Git 和
  不存在旧 attempt 均通过。其记录的预检解释器是 `/opt/anaconda3/bin/python3`
  （3.11.7）；这是字节预检环境，不作为科学进程解释器证明。launcher 与 import-only
  命令按既定脚本显式激活 AFDM，实际运行解释器由后续 registration 记录。

### 准入范围

允许主线程在原计划的即时资源、进程和字节检查仍通过后，按上述绑定 launcher
进行**一次 ENG**。失败保留完整 partial，不自动重试，不启动 DEV 或新 receiver。
只有本次 ENG 实际完成、原件审计 PASS，且 DEV 自身 source/input/config/launcher
字节独立准入完成后，才能进入一次 DEV；本报告当前不授予该权限。

Findings (fixed)：本次无新增问题。
Findings (not fixed)：无 ENG 字节阻塞；实际回放/搜索合同/fixtures 和预算仍待该次运行证明。
Verification：字节、配置、导入回执核对 PASS，launcher bash 语法 PASS。
没有重复源码 lint 或旧数学 raw 审计；TypeCheck 限制不变。科学运行尚未发生于本审查阶段。

## DEV 冻结字节准入：one-run GO（2026-10-08 追加）

本节更新此前“DEV 尚未 GO”的阶段状态；前述源码及 ENG 审查保留为历史记录。
**DEV 字节准入 PASS，允许绑定的一次 COLLAPSED-RECEIVER-DEV-01。**
前置 ENG 原件审计已 PASS，报告 `COLLAPSED_RECEIVER_ENG_RAW_REVIEW.md` SHA-256
`82ec09446ebdca18de88dede09b4cb6487a3d9d82664e32f00226cde7686c327`。
本轮复用源码和 ENG 审查，仅核对 DEV 新材料；没有 SSH、生产 import 或科学运行。

review_actual_model: unavailable_from_current_tool_metadata
review_actual_reasoning: unavailable_from_current_tool_metadata
validation_limited: model parity unknown

材料目录：`.mission/20261007-sp-fractional-trans/control-collapsed-receiver/development/`。

| 材料 | SHA-256 |
| --- | --- |
| remote-imports.json | 2442f339c6acd4b13473618a50aa2a87cb7c6476a6c693de7c174339dfca3ea7 |
| remote-config.json | e688699fbac2602935117f7d73609455f66f91c3d331bf51707bb4d78c7cc3ff |
| input_manifest.json | 6ef792a72fd72f9654d411f7ae6ec0f9679ed4a05149f02eedf8badedec93ce9 |
| run_contract.json | d3263b137e5b9a7e0895a60610de6993de243d20c31a86bd57402d0619cce9d3 |
| launch.sh | 6bc2555f8b3a2cf6b4672edd3fce9d20337219e2baff93a5430c734f212f6e04 |
| byte-preflight.stdout.json | 19f553e9871fc8de2fede93ad97f6111ab34847e01ec8d224c4db69ba32826f0 |

### 核验与范围

- source/snapshot 身份仍为 `62508b84d64be5e3504ad9a2e14ea0e77a4fa60c` /
  `36dc6e527df93fa7494436d1b47a1238fa4b4554`。父 manifest、DEV contract 和
  preflight 一致；本地 archive SHA 重新核对为
  `ef85fd4662811500c01812c9130c718713b0aa25273313689aedd27eb03c7650`。
  不重复已完成的 snapshot/tree/tar 内容审查。
- 68 唯一 imports 恰好等于父 manifest 白名单。68 本地源码及原 DEV 16 输入
  均逐 SHA/大小核对远端回执；合同 84 绑定集合恰好等于源码和 input manifest 并集。
  输入同时与本地 `evidence-receiver-development/artifact/execution/RECEIVER-DEV-01`
  原件逐字节哈希比对，包含 4 元数据文件、8 observations、4 truth 文件，无增补。
- remote config 与 contract.config 全字段相同，saved_input_paths 完整且无重复。
  原 4 blocks / 8 observations；四臂共 32 payload calls；无新 observation、独立 block、
  decoder 或 backend fixture。按 block modulo 4 轮转，同 block 两 SNR 顺序相同。
  scalar 完整 F1/2 refine/20 detector、point 20 sweeps、两个局部臂各 5 sweeps；
  每 sweep 三 data steps。truth 仅全部 seal 后解码的既有合同不变。
- 搜索仍为 ±.75 与 [-3,3] 相交、xatol=1e-4、3 显式加最多 32 内部评分，
  collapsed 另计一次 full winner；严格提升保留 previous tie，无 retry。
  门限仍为 collapsed errors ≤.9 point、不得差于 scalar、完整 wall 中位数
  ≤1.25 scalar；point 零错误 inconclusive；匹配控制需总错误严格少于 local point。
- stage CPU/wall 均 240 秒，进程 270 秒加 10 秒终止宽限；4 GiB memory、
  128 MiB output、单线程、CUDA 隐藏。launcher 只有一条 development/variant=collapsed
  调用，原 population-attempt 固定；唯一 root 为
  `/data/guoyikun/afdm_sp_collapsed_receiver_20261007_development_62508b84`。
  process 目录独占 mkdir，AFDM 激活，退出码与 GNU time 记录保持。
- 本地 `bash -n` PASS；标准库 preflight 回执 PASS、active_scientific_processes 空。
  回执 Python 3.11.7 只证明字节预检环境，实际 AFDM 解释器仍由运行 registration 证明。

在主线程既定即时资源、进程与字节检查仍通过时，允许上述合同和 launcher 的一次 DEV；
失败保留 partial，不自动重试。运行后仍须原件独立审计四臂 32 calls、seal/truth 顺序、
旧 scalar/point LLR 与硬判逐值复现、匹配控制和完整成本，不能以本准入代替结果验证。

Findings (fixed)：无新增问题，仅追加本报告。
Findings (not fixed)：无 DEV 字节阻塞；model parity unknown 限制保持。
Verification：84 字节/大小绑定、配置、合同、archive、回执及 bash 语法 PASS；
Lint/TypeCheck 本轮无代码变更而不重复，先前类型工具不可用限制保持；Tests/科学运行未执行。
