# COLLAPSED-MATH-01 独立审查

日期：2026-10-07。任务：`.trellis/tasks/10-05-method-advantage`。
CSV：`.mission/20261007-sp-fractional-trans/20261007-sp-fractional-trans.csv`。

review_actual_model: unavailable_from_current_tool_metadata
review_actual_reasoning: unavailable_from_current_tool_metadata
validation_limited: model parity unknown

## 当前结论与绑定

**协议 PASS；冻结源码静态准入 PASS；冻结字节的一次运行准入 GO。**
本结论仅适用于末节绑定的 COLLAPSED-MATH-01 一次受限运行；启动前由主线程
按原计划再做即时资源、进程和字节检查。两处协议工作量歧义已修复，源码及字节
增补审查均无阻塞。GO 不代表数值验收通过，不授权重试或 receiver 运行。

审查对象：`COLLAPSED_MATH_PROTOCOL.md`。
SHA-256：`adb1299d8caf9751d377c15128feeefdd4ca6d637a799c1a25e88bc868740b05`。
数学依据沿用已完成的 `COLLAPSED_GAIN_REVIEW.md` 与
`PHASE_ORIGIN_REVIEW.md`，本轮不重复执行其审查或任何科学计算。

## Findings (fixed)

- File: `COLLAPSED_MATH_PROTOCOL.md`
  - Issue: 候选返回导数的表述可能被理解成 45 个候选都计算解析导数，
    与固定工作量中的 9 个解析导数不一致。
  - Fix: 作者明确仅 offset=0 的 9 个候选请求并计算解析导数，其余 36 个不计算。
    已核对当前绑定文本。
- File: `COLLAPSED_MATH_PROTOCOL.md`
  - Issue: 45 项 gauge 检查是否新增 gain 求解，以及准备阶段费用是否包含在
    45 次 canonical 参考内，原表述不够明确。
  - Fix: 作者明确另做 45 次 gauge gain solve；Schur 准备、初始统计和 full C
    identity 多右端求解等费用另列，最终配置随源码冻结确切次数。已核对当前文本。

## 工作量与执行边界

| 项目 | 冻结数量与核对结果 |
| --- | --- |
| 输入 | 原 MATH-01 的 attempt.json，加 N8/N16/N1024 各 3 文件，共 10 文件，逐 SHA 绑定 |
| 案例 | 3 个 N，各含 P=1、P=2，共 6 案例；P=1 取原第一条路径 |
| 坐标 | 3×(1+2)=9；各坐标始终从同一基点独立出发 |
| Schur 候选 | 每坐标固定 5 个 offset，共 45 次；无自适应加点或选择 |
| 全量参考 | 每候选一次独立 canonical PathMoments/source/gain_statistics/共享求解，共 45 次 |
| 独立物理参考 | 仅 P=2 原基点；2×(8+16+1024)=2096 次 basis Channel.apply，另有 6 次均值响应 |
| 导数 | 9 个基点解析导数；每点两层中心差分，共 18 对，复用注册的参考值 |
| Gauge | 45 次矩阵旋转及 45 次额外共享 gain solve，不计为独立物理参考 |
| Gaussian 检查 | 每 N 一次，共 3 次；局部等权 Gaussian Fisher/MF 比值，不是实际 SP 后验方差 |
| 旧组件 fixtures | 指定 3 个 DataAndGainContracts，各执行一次，独立保留其运算及拒绝步证据 |
| 额外准备 | Schur A/b_−/factor/A⁻¹、初始统计、full C identity 求解等按实际另计，确切次数待源码冻结 |
| 接收机与样本 | 新 observations、新 independent blocks、receiver、decoder、完整 backend 执行均为 0 |

复用 P=2 第一列物理统计得到 P=1 的 R/f 是一致的，不增加物理调用。
P=1 必须依自身 C0=I/P 重新构造 precision 并求解 m/C，不能截取 P=2 的
m/C 当作 P=1 解；两案例的 prior precision 不同。

source 的 owner 绑定必须保留。完整参考应由自己的 canonical op 构造 source，
不能复用 candidate 单列实现制造自洽，也不能把参考值反馈给候选或缓存策略。
候选接口固定 source 和其余 ν，不修改 receiver 状态；仅按请求计算基点导数。

协议保留原 Pd=.55、σ²=.7 和 C0=I/P；不换成 receiver 的 Pd=.5。
越界明确失败，不截断。N1024 的独立物理参考采用逐 basis 流式累加，
不构造 N×N 稠密矩阵。完整参考、共享求解、identity 多右端恢复 full C 的
O(P³) 工作不能隐藏在单候选 O(PN+P²) 表述中。

## 验收与资源

验收覆盖物理基点 R/f、候选 R 列/b、完整 m/C、Schur 含固定块常数的
score、直接 trace/entropy 形式、Hermitian、precision residual、s≥P、
P=1 退化式及 gauge 协变/不变性。差分两层均验收，不按误差挑层。

归一误差分母为 max(1, reference 范数)。值/矩/不变量阈值为 N8/N16
1e-10、N1024 1e-9；precision residual 1e-10；两层差分各 1e-5；
s 下界允许误差 1e-10·max(1,P)。失败保留 partial，不改阈值、不重试。

stage CPU/wall 各不超过 120 秒；进程不超过 150 秒并保留 10 秒退出宽限；
单 CPU、CUDA 隐藏、RSS 不超过 4 GiB、输出不超过 128 MiB。所有远端写入、
cache、tmp 限 `/data/guoyikun`。工作量与这些上限无逻辑冲突，实际能否在上限内
完成只由获准的一次运行验证；预算耗尽必须如实失败。

仍需按既有流程核对 source commit、隔离 snapshot、imports、10 输入、最终
配置和 launcher 的字节绑定，再进行一次运行和独立 raw 核验。该流程已经写入
协议，不因本报告增加新的实验或接收机运行。

## Findings (not fixed)

无剩余协议问题。源码、额外工作的确切次数、最终配置和部署字节尚未审查，
属于后续原定验证范围，不能据此把协议 PASS 当成源码 PASS 或运行 GO。

## Verification

- 协议：PASS；固定工作量、输入、容差、费用和资源边界已静态核对。
- Lint：本轮仅 Markdown 报告；无源码 lint 执行，报告尾空白检查单列记录。
- TypeCheck：未执行；不以文本、AST 或 compile 代替类型检查。
- Tests：未执行；未 import 生产模块、运行 fixtures、科学数值或新仿真。
- Runtime/SSH：未执行；没有对实际耗时、内存或科学验收作运行通过声明。

## 源码 READY 后增补：静态准入 PASS

独立核对 `.mission/20261007-sp-fractional-trans/dispatch/collapsed-source-ready.json`
所列 6 文件的当前字节，全部匹配。主线程将相同字节提交为
`d3b2f1d8008db8db0f2cf1adf31dc5b39e4c49e3`。本轮没有执行隔离 snapshot
和远端部署的完整字节准入，该步骤仍按既定流程单独完成。

| 文件 | SHA-256 |
| --- | --- |
| `afdm_sp_fractional_receiver_20261007/gaussian_gain.py` | `c88a7927c80b50d20aab75e322804e45152add4483d80d5ce4bdae5098688441` |
| `afdm_sp_fractional_receiver_20261007/collapsed_gain.py` | `c136b65a385331df2d75a49a5b6f8a282f8b75a34e291a058bda3fe1ad8e12a1` |
| `afdm_sp_fractional_receiver_20261007/collapsed_diagnostic.py` | `15a21224f0073460f873e6275543b03fe14ff6f0c5af6a4477224731430abcf3` |
| `afdm_sp_fractional_receiver_20261007/receiver.py` | `e1c10e66587cf42f376a7613860597ae2e7470c9dea209ccae7dfe32fa73c3f1` |
| `afdm_sp_fractional_receiver_20261007/protocol.py` | `2c859980fc1bed30dbc51d271f83b484eff567e13f767b5d46a6562b908f2eb8` |
| `afdm_sp_fractional_20261007/moments.py` | `5a415b78c8a824bff77c0aafa0baf9599020ec4f132b875bd702573baaa1d6a2` |

表中路径均以项目 `experiments/` 为前缀。对旧文件使用
`7757cd504c2a9539efb1b20e49a87f8a4a74120a` 到当前提交的差异核对；
同时读取实际被调用的 runtime observers、三个原 fixtures、共享 recorder 及输入路径枚举。

### 公式、复用与旧路径

- `prepare_gain_column` 通过同一 owner 的 `_source` 验证，复用 canonical
  `_cross_source`，核中共轭方向与完整 `gain_statistics` 的列一致。
  source、基点和准备数组保持只读；candidate 不改变 op 或 receiver 状态。
- Schur 的 A、b_−、factor、A⁻¹ 每坐标准备一次，块求解显式保留原 P 的 prior
  precision。s/t、完整 m/C、常数项、logdet、解析导数和 envelope 导数与已审公式一致。
  P=1 使用空其余块并按 P=1 precision 求解；独立物理参考仅复用 R/f。
- `gaussian_gain.solve_gain` 的默认有效输入路径保留旧 gain_update 的 precision、
  [I,b] 组合 RHS、一次 Cholesky、两次 triangular solve、residual 和返回字段顺序。
  默认不新增 logdet/residual 费用键；旧 gain 计数键及调用顺序保持。
  新接口额外拒绝无效尺寸、噪声及 scalar prior，没有 jitter 或静默回退。
- `continuous.count` 和 `scipy.linalg.solve_triangular` 使用动态模块查找，
  现有 component/operation observers 可以捕获；receiver 保留观察器要求的旧 alias，
  没有在新模块保存绕开 patch 的 count/triangular alias。
- canonical 参考每次新建 op/source，候选不读取 reference。物理参考逐 basis
  `Channel.apply` 累加非均匀 variance Gram，无 N×N 保存；gauge 明确是代数旋转检查。

### 确切工作量与资源链

配置与控制流吻合：6 案例、51 次 PathMoments/source 构造、6 次初始统计、
9 次坐标准备、45 候选、45 完整参考、45 gauge 求解、9 个 offset=0 导数、
18 个固定差分对、2096 次 basis apply、6 次 mean apply、3 个 Gaussian 检查及
3 个各一次的旧 fixtures。fixtures 在数学操作观察器结束后另开观察器分账。

共享 solver 共 96 次，即 6 次非空 Schur 块 + 45 次 reference + 45 次 gauge；
包含 156 个 identity RHS 与 96 个 matched RHS，共 252 列、192 次三角调用。
30 个非空块候选另有 60 次向量三角调用。配置中的矩阵乘法项数逐项吻合：
候选 residual 390、9 导数 trace 51、共享 residual 792、90 次直接 entropy Gram
乘法 510、270 次 gauge 矩阵乘法 1530。完整 `evaluate` 含 O(P³) residual，
请求导数时另含 O(P³) trace；不能称完整诊断 evaluate 为 O(PN+P²)。

`protocol.run` 将显式 wall cap 限于原 kind 上限内，并要求 config/contract 同值；
diagnostic 明确传入 120，ResourceGuard 与 recorder 都接收该值。
未传值且旧配置没有 override 时沿用 engineering=180、development=1800；
非法或隐含不一致 override 明确拒绝。CPU cap 不得超过有效 wall cap。
receiver/decoder/new observation 等注册与实际 guard 计数为 0；三 fixtures 不调用完整 receiver。

固定网格越界、计数不符、比较失败、非有限数或预算耗尽均显式失败；保留候选及 partial
证据，不选层、不改容差、不自动重试。共享 recorder 保留既有独占 attempt 和 deadline。

### 部署脚本窄审

仅静态读取以下脚本，没有执行其中的 Git 建库、SSH、上传、导入或 launch：

| dispatch 脚本 | SHA-256 |
| --- | --- |
| `build-collapsed-math.py` | `432516563545a4610ecb5b33d6698388b801c9d441bdc5c80df6e8e222bbe6e8` |
| `prepare-collapsed-remote.py` | `93e7a6c3cf086cdf3ef997cf85a74c5be27ea5b5a8a1a61fbcc6334b10a53999` |
| `preflight-collapsed-math.py` | `7ccaf0f2d9f39b5ed101d806df45d6926f97bf7851a4ff5c2ed75be6c9fca30a` |

未发现明显执行阻塞：snapshot 从明确 commit 读文件；新目录及归档独占创建；
部署核 archive SHA，import-only 两个分支在 calculate 前退出；只生成 launcher，
不触发数学运行。生成的 launcher 具有 150 秒 timeout、10 秒终止宽限、单线程与
隐藏 CUDA，runtime/cache/tmp 在专用 `/data/guoyikun` 根内。
preflight 对 source/input、Git snapshot、干净工作区和已有 attempt 做拒绝检查，
输出 contract/launcher/archive 哈希供后续独立比对。此静态窄审不代替字节准入或服务器实况检查。

### Findings 与验证增补

- Findings (fixed)：源码未发现需修复问题；本代理仅更新本报告。
- Findings (not fixed)：无源码阻塞。完整字节准入和数值验收尚待执行。
- Lint：PASS；独立执行 Ruff，覆盖 6 源文件及上述 3 个部署脚本。
- AST / 内存 compile：PASS，同样覆盖 9 文件；没有导入或执行其模块。
- TypeCheck：未执行；mypy 与 pyright 均未安装，AST/compile 不作为类型检查。
- Tests / Runtime / SSH：本轮未执行；三个旧 fixtures 和新诊断的数值断言只核源码，
  不报告运行通过。实际时间、内存和数值误差须由原定受限运行给出。
- 规范：补读 backend index、quality 占位规范、bounded mathematical studies、
  structured inference；research diagnostics 仅核对本任务相关条款，不声称全篇已读。
  当前改动仍受既有 working-prior、独立参考、完整费用和冻结证据合同约束，未发现必需的
  `.trellis/spec/` 同步缺口；固定科学网格保留在任务协议与配置。

模型和 reasoning 元数据限制保持本报告开头的原记录，不声称独立审查模型能力已证相等。

## 冻结部署字节增补：one-run GO

本次只审本地已回传材料，未执行 SSH、生产 import、fixture、求积或其他科学计算。
未重跑前述源码审查。控制目录为
`.mission/20261007-sp-fractional-trans/control-collapsed-math/`。

| 材料 | SHA-256 |
| --- | --- |
| `source_manifest.json` | `892751fb471119012be0fc7ee3bafcab393af8fa43b1a2560bca6b8abe165f5b` |
| `remote-imports.json` | `99a9d632cd3fc0d6fe0ba628df30c5ce0dc617483ed2bfc64a19e4d8395aa3d9` |
| `remote-config.json` | `4491b811dc70c5ab3b3364a82cf0f7f52c3e71b8ea235a0dd929a3fc7847a97b` |
| `run_contract.json` | `3d33a84103cf24c870350009c72461784000f69b2703cc142cbeea74731fe028` |
| `launch.sh` | `1f912dbe49d84411d7e86732abadf611f19418d53457eea0366010ca0cb1937e` |
| `byte-preflight.stdout.json` | `20c30cb8d1efa428d4b98585a473de5df446944b40f0ab23dc4fdc83a3c23197` |
| `dispatch/collapsed-source-d3b2f1d8.tar.gz`（位于同级 dispatch） | `3b4af7e3abb06cb1b3ccfd1135f628fb2d765a0a2355bd4b6afef03a5a70bd5d` |

source commit：`d3b2f1d8008db8db0f2cf1adf31dc5b39e4c49e3`。
snapshot commit：`118703423cbe93a8a817b3808287d640594fd97f`。
唯一执行根：`/data/guoyikun/afdm_sp_collapsed_20261007_math01_d3b2f1d8`。
唯一 stage：`COLLAPSED-MATH-01`，kind=`engineering`。

### 独立字节检查结果

- 66 个源码文件逐项验证：工作区字节 = source commit 字节 = 隔离目录字节 =
  snapshot commit 字节 = tar 内文件字节；其 SHA 和大小均与远端实际回执一致。
  6 个 READY 文件仍等于源码审查绑定值，未发生后续源码漂移。
- snapshot HEAD 与合同一致，工作区干净，Git tree 的完整文件集合正好为这 66 个文件。
  tar 无重复成员、绝对路径、`..` 或链接成员；除 `.git` 元数据外没有白名单外文件。
  本地 archive SHA = manifest = contract = 远端回执。
- imports 共 66 个唯一条目，恰好等于源码白名单。回传的两份 import-only 原始 stdout
  与 remote-imports/config 内容一致，退出码均为 0，stderr 均为空。代码分支在 calculate
  前返回；这只证明导入与配置获取完成，不是数学检查完成。
- 10 个原输入的完整路径集合与旧 MATH-01 一致：attempt.json 和 N8/N16/N1024 各
  inputs/arrays/checks。SHA 与前次冻结 adaptive engineering 合同中的同一批输入一致，
  并全部匹配本次远端实际回执。未打开数组进行新的数值推导。
- 合同 source/input 共 76 个条目，完整集合及每项 SHA 与远端回执一致。
  contract/config 逐字段相同；source/snapshot/root、CPU/wall/RSS/output 上限和
  全进程期限匹配，工作量与前述已审固定配置一致。
- 本地 launcher `bash -n` 独立 PASS，SHA 与远端回执一致；启动命令只有一条诊断
  调用，注册 150 秒 timeout 与 10 秒退出宽限，保留 PID、stdout、资源、退出码和时间。
  process 目录独占创建，所有新增 artifact/runtime/cache/tmp 均在上述专用根内。
- 远端 preflight 回执为 PASS，记录 Python 3.10.20、AFDM 环境解释器、无匹配的并发
  科学进程，并已通过源码/输入、snapshot、干净工作区和不存在旧 attempt 的检查。
  这是回传时状态；本代理没有把它当成启动时的即时服务器检查。

### GO 范围与未完成验证

允许主线程按原计划，在即时资源/进程/字节检查仍通过后，用绑定的 launcher
进行**一次** COLLAPSED-MATH-01。stage CPU/wall 各 120 秒，进程 150+10 秒，
单 CPU、CUDA 隐藏、4 GiB RSS、128 MiB 输出；10 个旧输入、固定 45 候选及上述
全部参考/导数/fixture 工作量不变。新 observation、independent block、完整 receiver、
decoder、完整 backend 均为 0。任何失败保留 partial，不自动重试或扩展 receiver。

Findings (fixed)：本次无新问题，无需修复。
Findings (not fixed)：无字节准入阻塞；实际数值、计数、耗时、内存与 raw 完整性
仍由这一次获准运行及后续独立 raw 审计验证。

Verification：字节/配置/导入回执核对 PASS；launcher bash 语法 PASS。
Lint 沿用前述冻结字节的 PASS，未重复运行；TypeCheck 仍未执行。
Tests/科学 Runtime 尚未执行；本次 GO 不改变该事实及模型元数据限制。
