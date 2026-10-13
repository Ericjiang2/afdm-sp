# COLLAPSED-RECEIVER-ENG-01 独立原件审计

日期：2026-10-08。任务：`.trellis/tasks/10-05-method-advantage`。
CSV：`.mission/20261007-sp-fractional-trans/20261007-sp-fractional-trans.csv`，COLLAPSED-RECEIVER-01。

review_actual_model: unavailable_from_current_tool_metadata
review_actual_reasoning: unavailable_from_current_tool_metadata
validation_limited: model parity unknown

## 结论

**ENG raw PASS，无阻塞。可以准备 DEV 的独立字节准入；本报告不是 DEV 运行 GO。**
45 次 score-only、9 次完整评估、9 个坐标准备、6 个保存 cases、3 个原 fixtures
及 2 个搜索控制均符合注册，原件完整且资源未超限。

本轮使用标准库 NPY/ZIP 解码、保存数组比较和 P≤2 显式代数；未生产 import、
未调用 NumPy/SciPy、未 SSH、未运行新仿真/receiver/物理 basis。
只创建本报告，不修改源码、STATE、CSV、原件或其他代理文件。
已闭环的数学审计不重跑；相同旧 fixture 原件复用其已审结论，并核对新旧 payload 完全一致。

## 原件身份与完整性

本地根：`.mission/20261007-sp-fractional-trans/evidence-collapsed-receiver-engineering/`。
远端根：`/data/guoyikun/afdm_sp_collapsed_receiver_20261007_engineering_62508b84`。
stage：`artifact/execution/COLLAPSED-RECEIVER-ENG-01`。

| 对象 | SHA-256 / commit |
| --- | --- |
| source commit | `62508b84d64be5e3504ad9a2e14ea0e77a4fa60c` |
| snapshot commit | `36dc6e527df93fa7494436d1b47a1238fa4b4554` |
| `artifact_manifest.json` | `79a2927c60815ca0572b5d8291d6062ed482105ea118c99e72720abe7f4044e6` |
| `artifact-small.tar.gz` | `0f181bd1256fb4805d2f322e4c362d44b35126fe04b1c612aa21755049a98eeb` |
| stage `attempt.json` | `1939e0f789ccefceeb7ee0225f89d7775ab4c3432bea5c9d7b63e29d84869d5e` |
| `collapsed_engineering_summary.json` | `36883f083e93992e30500941defbeefb7a7064f3e9695c78e4cb7861096ccee3` |
| `collapsed_engineering_complete.npz` | `991c1f87a5a49be27eff427572524f5563f7602e79b1503d2d54014e17901ebf` |
| `run_contract.json` | `50c966fb306d1bc227b3edd11fcf1f3fdbed47c6c4775ef22c8b1457117e88e8` |
| `launch.sh` | `e458e261ee6dd44cbd143743847aa50304a3a655f44cc680cacbad052627b7c7` |

独立核对全部 **133 文件、3,415,291 bytes** 的 SHA-256、MD5、大小、完整集合和
远端路径；最大单文件 763,875 bytes，全部 copied。tar 文件成员集合无重复、无漏项，
每个成员内容 SHA 与 manifest 一致。

attempt 为 complete/exit_code=0，124 项哈希恰好覆盖除 attempt 自身外的 stage 文件。
87 个 source snapshots 对应 68 Python、18 输入及合同，逐项匹配 registration；
源码 snapshot 与已审工作区字节相同。config/_config、argv/_argv、HEAD、120 秒 deadline
与准入合同一致，合同及 launcher 与 control 副本逐字节相同。

input_identity 完整匹配 18 输入清单；其中原 COLLAPSED-MATH 的 attempt、registration
及六 case 快照还与本地已审旧原件逐字节比较相同。
新 complete 与六 replay、六 comparison、三个 fixture、两个 search 原件的对应树一致；
summary 与 results 对应字段一致。NPY 检查 dtype、shape、C/F 布局和数组引用，
ZIP 检查成员唯一性，没有 pickle 或隐含数组遗漏。

## 回放与独立代数

六个 replay seal 的路径、SHA、reference_arrays_read=false 与实际 replay 对应；
comparison 同时绑定 replay 和旧 case SHA，符合已审源码先保存/封口自己的回放再读
reference case 的顺序。每个坐標固定五个 offset，只有 offset=0 另存一次 full。

| N | P | score-only | full | comparison 数 | 最大保存检查误差 |
| --- | --- | --- | --- | --- | --- |
| 8 | 2 | 10 | 2 | 56 | 1.6724332293e-16 |
| 8 | 1 | 5 | 1 | 28 | 0 |
| 16 | 2 | 10 | 2 | 56 | 1.3445310595e-16 |
| 16 | 1 | 5 | 1 | 28 | 7.5814931517e-17 |
| 1024 | 2 | 10 | 2 | 56 | 2.3280848805e-16 |
| 1024 | 1 | 5 | 1 | 28 | 2.3797078021e-16 |

逐项重算全部 **252 comparisons** 的误差与通过条件：

- 45×4=180 项 score-only 的 s/t/J/reduced_score 对旧保存结果差异均为 0。
- 9×7=63 项 full 的 m/C/precision/s/t/J/reduced_score 对旧保存结果差异均为 0。
- 9 项 precision residual 最大 2.3797078020842505e-16，低于原 1e-10。

9 份 Schur 准备除耗时外与旧准备完全一致。另用保存 A/u/b_i/z 重算 v、s/t/J/常数，
score-only 的独立 J/完整 score 最大归一差异为 1.9976814942684384e-16。
对 9 个 full 用显式逆重算 C/m 和 precision residual；C、m 最大归一差异分别为
1.5530983274861615e-17、3.400456267939448e-17，独立残差最大
2.379707802084251e-16。全部保留原 N8/16=1e-10、N1024=1e-9 阈值。
score-only 没有完整 covariance/residual 字段，所有回放均无解析导数。

## 实际工作量与搜索控制

逐候选 delta、case counts、source work 独立重建并求和，与 complete/summary 总账
逐键一致，且满足注册 replay_exact_work。P=1 的零增量省略与总账保留语义一致。

| 工作 | 实际值 |
| --- | --- |
| canonical/source / 初始统计 / 坐标准备 | 6 / 6 / 9 |
| 非空 Schur 块 / 空块 | 6 / 3 |
| score-only / full / 总候选列 | 45 / 9 / 54 |
| 共享 Cholesky / 共享三角调用 / RHS 列 | 6 / 12 / 12 |
| 候选向量求解 / 候选三角调用 | 36 / 72 |
| full covariance / residual 检查 | 9 / 9 |
| candidate phase / matched / cross 项 | 18864 / 18864 / 12576 |
| inverse DAFT / ordinary FFT | 21 / 6 |

独立 operation observer 为 6 eigvalsh、6 Cholesky、84 triangular、21 IFFT、6 FFT，
与组件账相符；主回放无 Channel.apply、无 derivative、无 receiver。
full residual 的 78 个乘法项和共享 residual 的 12 项另计，没有藏在 score-only 费用里。

两个控制各有 **3 个显式 + 21 个 bounded callback = 24 次评分**，合计 48，低于总上限 70。
保存的每个调用均在 [-.55,.95]，score 与该控制的确定性势逐值一致；nfev 与内部调用数
一致，optimizer success，返回终点对应真实已记录评分。按 previous/lower/upper/result
顺序重新执行严格增大选择，常数势选 .2、递增势选 .95，与原件一致。
这验证搜索控制与计费，未执行接收性能实验。

## Fixtures 与静态默认合同的边界

三个指定原 fixtures 各 tests_run=1、passed=true、errors/failures 为空。
其 decoded payload（操作、counter events、计数、已捕获数值轨迹）与先前已审
COLLAPSED-MATH fixture 原件完全相同；事件求和也与各自组件计数相同。
第三个 fixture 仍为 3 data steps、6 proposals、3 rejected，未丢弃拒绝工作。

前两个 fixture 没有完整返回矩阵/系数轨迹；通过依据仍是绑定 unittest 执行结果及
组件证据，不冒称本轮重建缺失轨迹。13 项 default_contracts 全部为 true，但它们
是配置和源码入口检查；**不是实际 receiver、真实 seal 执行或旧 LLR/hard 复现证明**。
旧 baseline 的输出逐值审计须等 DEV 封口后完成。

## 完整预算与解释范围

| 资源 | 实际 | 上限 |
| --- | --- | --- |
| recorder stage wall / CPU | 1.1238191549200565 / 0.963963819 秒 | 各 120 秒 |
| callback wall / CPU | 1.0795295950956643 / 0.925050923 秒 | 包含在 stage 内 |
| 完整进程 wall / CPU | 4.02 / 3.87 秒 | wall 150 秒，宽限 10 秒 |
| 完整进程峰值 RSS | 442756 KiB = 453382144 bytes | 4 GiB |
| 全部 artifact | 3415291 bytes | 128 MiB |

exit.txt 与 GNU time 均 exit 0。实际科学进程记录 AFDM 环境 Python 3.10.20；
BLAS/OpenMP/Torch 单线程、CUDA 隐藏，registration/preload/actual_work 绑定一致。
preload 为 1.7941981079 秒，完整进程计时包含启动开销。
stage 输出大小按 attempt 的保存时点核对一致；新 observation、independent block、
receiver、decoder、完整 backend 均为 0。

本结果仅完成 ENG 工程回放与控制合同验证，不说明四臂32次接收成功、BER改善、
后验校准或完整接收成本通过。可以进入 DEV 准备；DEV 运行仍需自己的独立字节 GO。

## Findings (fixed)

无原件问题需修复；本代理仅创建本报告。

## Findings (not fixed)

无 ENG 阻塞。上述 fixture 和静态合同证据边界保持明确；不新增科学重跑。
实际 review model/effort 元数据仍不可得，不声称审查能力已证相等。

## Verification

- 原件完整性、身份、252 comparisons、保存小矩阵代数、全部计数和预算：PASS。
- 原运行的三个 fixtures、两个搜索控制、13 项明确标注的静态默认检查：PASS。
- Lint：沿用冻结源码已审 Ruff PASS；本轮仅检查报告尾空白。
- TypeCheck：未执行，工具未安装；原件审计不替代类型检查。
- Tests/Runtime：核验已完成 ENG 的真实原件；本地没有重新执行生产测试、科学 import 或 SSH。
