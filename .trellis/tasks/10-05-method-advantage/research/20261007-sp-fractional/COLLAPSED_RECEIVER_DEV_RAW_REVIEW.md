# COLLAPSED-RECEIVER-DEV-01 独立原件审计

日期：2026-10-08。任务：`.trellis/tasks/10-05-method-advantage`。
CSV：`.mission/20261007-sp-fractional-trans/20261007-sp-fractional-trans.csv`，
行：COLLAPSED-RECEIVER-01。

review_actual_model: unavailable_from_current_tool_metadata
review_actual_reasoning: unavailable_from_current_tool_metadata
validation_limited: model parity unknown

## 结论

**原件完整性、执行合同与保存数值审计 PASS；科学筛选门限 FAIL。**
32 次调用完整且无失败。旧 scalar/point 的 16 次调用，LLR 和硬判共 32 个数组
与指定旧封口基线逐字节一致。collapsed 相对匹配 local point 净减少 11 bit，
但相对 point 的错误比为 0.9863420428（要求 ≤0.9），相对 scalar 的完整 wall
中位数比为 1.9741324261（要求 ≤1.25），故不能进入 CONF/Trans，也不能宣称方法优势成立。

范围严格限于原 4 blocks / 8 observations 的经典 adaptation 开发筛选。
本轮只用标准库读取 JSON、NPY/ZIP、tar 与保存数组做小矩阵代数；没有 SSH、
生产 import、新仿真、receiver 或物理 basis 重跑。只创建本报告，不改源码、
CSV、STATE 或原件；继承已完成的源码、ENG 和 DEV byte 准入，不重复其审查。

## 原件与冻结身份

原件根：
`.mission/20261007-sp-fractional-trans/evidence-collapsed-receiver-development/`。
stage：`artifact/execution/COLLAPSED-RECEIVER-DEV-01`。
旧基线：
`.mission/20261007-sp-fractional-trans/evidence-receiver-adaptive-development/artifact/execution/RECEIVER-ADAPT-DEV-01`，
核其 receiver_seal 对应 raw SHA 后读取 16 个 scalar/point calls。

| 原件 | SHA-256 |
| --- | --- |
| artifact_manifest.json | e320b6d067f314fbb9b35a14ed1cb6b156eca81a68826e80d5cd46fa9ce5a331 |
| artifact-small.tar.gz | 641294e2bd3a294c47a589bb68dc568f6fe4792b5fa4c7cca537ed09ed96b1da |
| attempt.json | b7ae5580ebba0a4d603b09b1043183092dbba4cbb1a3db0c2279b1b366e00a89 |
| results.json | bd51b2f01da7d5d6e93faf80ad96209234792428b535e93b36965f2509c9fac4 |
| receiver_seal.json | 0ae8b5da0f8ddf15223a39b43c91bebe5202c6cf79b4d1a96f97e88ae94e933e |

212 文件、68,802,194 bytes：独立核对完整文件集合、SHA256、MD5、size、
remote_path、copied；tar 的 212 个文件成员内容与本地逐字节一致。
attempt 为 complete / exit_code=0，203 项 artifact hashes 精确覆盖 stage
除 attempt 自身的文件。85 个 source_snapshot 逐 SHA 对应 registration，
构成为 68 Python、16 原 DEV 输入、1 contract。合同 84 绑定与 registration 的
源码/输入完全一致；源码 snapshot HEAD 为
`36dc6e527df93fa7494436d1b47a1238fa4b4554`，source commit 仍为
`62508b84d64be5e3504ad9a2e14ea0e77a4fa60c`。

registration config/_config 与获准合同逐字段相同，argv/_argv 相同，
stage 与 240 秒 deadline 相符；回传 contract/launcher 与准入版本逐字节一致。
NPY parser 检查格式、dtype、shape、数据长度、C/F order；ZIP 检查 metadata
identity，无重复或未引用数组成员，不使用 pickle。

## 输入、32 calls 与 truth 边界

16 个源输入的 snapshot 哈希与准入白名单一致。实际观察量与 truth 复制账为
12 个唯一数据文件、348,644 bytes；每项 SHA/大小均与合同源输入匹配。
population 记录新 observation/block、generator、observed/truth 解码为 0；
该数值描述准备阶段，后续 receiver 正常解码观察量、scorer 解码 truth。

receiver_seal 完整覆盖 4 blocks × 2 SNR × 4 arms，顺序按 block modulo 4
轮转，同 block 的两个 SNR 使用相同顺序。每次 started identity、outcome、
raw identity/status、operation ledger 和 seal SHA 一致，无缺失或失败调用。
seal 记录 truth_payloads_opened_for_scoring=0，scores 绑定同一 seal SHA；
tar 保存时间满足所有 call raw ≤ seal ≤ scores。结合此前已审冻结代码中的
“全部封口后评分”路径，未见边界违例。原件没有系统调用级文件读取日志，
因此这不是对实际读取时刻的独立 syscall 证明。

全部 32 组 LLR 均有限、长度 2048；独立按 LLR<0→1（零为0）重算硬判，
再与原 truth coded bits 逐位比较。scores、results、每调用错误数与完整时间一致。
24 组 VB 输出另从保存 log_q 重算 QPSK bit marginals 与 probabilities：
LLR 最大相对误差 2.3146539823521617e-17，概率最大 1.249000902703301e-16。
没有以 BER 汇总相等替代旧输出复现：旧两臂 16 calls 的 32 个 LLR/hard_bits
数组 header 和数据字节全部相同。

## 错误数与完整耗时

每臂分母为 8×2048=16384 bits；四臂使用相同观察量，不视为额外独立样本。

| 臂 | 总错误 | 完整 receiver wall 中位数（秒） |
| --- | ---: | ---: |
| f1_scalar | 1755 | 0.5859166564187035 |
| vb_point | 1684 | 1.6440407334594056 |
| vb_local_point | 1672 | 0.7517338219331577 |
| vb_collapsed_point | 1661 | 1.1566770704230294 |

| block | SNR | scalar | point | local point | collapsed |
| --- | --- | ---: | ---: | ---: | ---: |
| 0 | 6 | 263 | 260 | 240 | 235 |
| 0 | 8 | 180 | 151 | 154 | 152 |
| 1 | 6 | 250 | 253 | 250 | 256 |
| 1 | 8 | 155 | 159 | 170 | 159 |
| 2 | 6 | 272 | 279 | 274 | 271 |
| 2 | 8 | 206 | 165 | 164 | 158 |
| 3 | 6 | 258 | 253 | 266 | 270 |
| 3 | 8 | 171 | 164 | 154 | 160 |

匹配配对差均由保存硬判与 truth 重算，wall/CPU 为 collapsed 减 local：

| block | SNR | local错 | collapsed错 | 错误差 | 硬判变化 | 纠正 / 新增错 | wall差秒 | CPU差秒 |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| 0 | 6 | 240 | 235 | -5 | 13 | 9 / 4 | 0.402323848 | 0.395252847 |
| 0 | 8 | 154 | 152 | -2 | 10 | 6 / 4 | 0.403401849 | 0.397070539 |
| 1 | 6 | 250 | 256 | 6 | 22 | 8 / 14 | 0.413068355 | 0.405987854 |
| 1 | 8 | 170 | 159 | -11 | 27 | 19 / 8 | 0.403698306 | 0.396654835 |
| 2 | 6 | 274 | 271 | -3 | 5 | 4 / 1 | 0.401729140 | 0.397635889 |
| 2 | 8 | 164 | 158 | -6 | 16 | 11 / 5 | 0.391582381 | 0.385073582 |
| 3 | 6 | 266 | 270 | 4 | 16 | 6 / 10 | 0.404403688 | 0.397308700 |
| 3 | 8 | 154 | 160 | 6 | 14 | 4 / 10 | 0.408366989 | 0.394530334 |

共 123 次硬判变化，纠正 67、新增 56，净少 11；8 观察量中 5 改善、3 变差。
collapsed 全部配对均更慢，wall 中位数为 local 的 1.5386790333 倍。
matched_control_improvement=true 的严格总错误语义正确，但它不代替主筛选门限，
也不构成独立确认或统计显著性结论。相对 scalar 错误不劣一项通过，其余上述
错误比例与时延门未过；point 非零错误，不触发零错误 inconclusive 分支。

## 保存轨迹、搜索与完整计费

scalar 的 8 calls 各保存 20 detector iterations/states/trace；point 各 20 sweeps。
两个新臂各 8 calls、每 call 5 sweeps、每 sweep 8 顺序坐标和 3 data steps：
各 320 次搜索、120 次 data steps。每个坐标 previous 连续承接上次 selected；
collapsed 保存的 base_dopplers 与当时整组状态逐值一致，最终 factor 与完整
winner m/C 一致，没有用最终状态冒充中间状态。

640 次共享搜索逐个核对边界 ±.75∩[-3,3]、前三显式次序、一次 bounded、
nfev、终点已有评分、候选次序和严格提升/tie 选择。每坐标实用 9–13 个评分，
均 ≤35；collapsed 每次另存一项 full winner，J 与 selected_score 精确一致，
未把 full winner 隐藏到搜索缓存。无失败/重试轨迹。

local 的 3547 个评分全部从保存 Fourier coefficients 按注册噪声方差重算，
最大相对误差 3.060021337930955e-15。collapsed 的 3501 score-only 加
320 full，共 3821 候选，全部从保存 A/u/v/z/b_i 重算 v 解、s/t/J/reduced score；
J 最大相对误差 5.4742037178258644e-15。320 个准备的 A×inverse_A 和 A×z，
及 320 个 winner 的 precision×C、precision×m 均通过 1e-10 检查；
最大 winner inverse 误差 3.002210203427387e-16、mean 误差
3.165227417483918e-16；保存 precision residual 最大
4.655606390323384e-16。此检查验证保存充分统计量后的代数一致性，不重算物理算子。

| 完整后端账（8 calls 合计） | local point | collapsed |
| --- | ---: | ---: |
| searches / score-only | 320 / 3547 | 320 / 3501 |
| full winner | 不适用 | 320 |
| gain updates / Cholesky | 80 / 80 | 320 / 320 |
| shared triangular calls | 160 | 640 |
| shared RHS columns | 720 | 2560 |
| candidate vector RHS / triangular | 不适用 | 3821 / 7642 |
| full covariance / residual checks | 不适用 | 320 / 320 |
| source preparations | 338 | 538 |
| path moment builds | 160 | 360 |
| inverse DAFT / ordinary FFT | 934 / 378 | 1654 / 578 |
| forward DAFT | 258 | 258 |
| data proposals / rejected | 178 / 58 | 178 / 58 |
| data objective evaluations | 218 | 218 |

collapsed 初始 pair terms=18,350,080；candidate phase/matched 各 3,912,704，
cross=27,388,928；full residual matmul terms=184,320，
shared residual terms=125,440。候选 source/work delta 全量相加与后端总账一致；
共享 Cholesky/RHS/三角、坐标准备和 full winner 的数量由实际轨迹交叉重建，
operation observer 的 Cholesky 与三角调用也匹配。source/FFT/DAFT 账按实际
proposal 数量逐 call 核对，最终 sweep 到 export 的增量仅为各 4096 的
bit marginal rows 与 probability entries。

全部 VB 的 991 项 data proposals 核对状态、接受判据、objective increment，
每步只接受最后一项，拒绝工作计入账。point 拒绝155；两个新臂各拒绝58。
没有重新执行 data-step 的物理 Gram 运算，不将保存标量一致性称为完整接收机重放。

## 资源与停止条件

- 32 calls 完整 wall 合计 33.42116689682007 秒、CPU 合计
  32.586379208000025 秒；独立求和与 results 相同。各 call 完整 wall
  包含 ready 和 raw save，未仅比较 backend 时间。
- population copy/load 单列 wall 0.025604957016184926、CPU
  0.025572528999999733 秒；preload 1.73597647016868 秒。
- callback wall 46.57258303905837、CPU 45.735814441 秒；
  attempt stage wall 46.68251123209484、CPU 45.84294783799999 秒。
  多余时间仍计入完整 stage，并未以 receiver 小计充当进程成本。
- GNU time 完整进程 wall 49.65 秒、CPU 44.56+4.27=48.83 秒；
  最大 RSS 515744 KiB=528121856 bytes；exit.txt 与 GNU time 均为 0。
- 实际 AFDM Python 3.10.20；BLAS/OpenMP pools 与 Torch 单线程登记，
  CUDA 隐藏。240 秒 stage、270+10 秒进程、4 GiB memory、128 MiB
  output 上限均满足。新 observation/block、decoder、backend fixture 为0。

## Findings (fixed)

无原件问题需要修复；仅创建本报告。审计脚本中的 schema/噪声缩放/计数解析
按原件定义校正后，最终全量检查 PASS；未修改任何生产数据来满足检查。

## Findings (not fixed)

无原件完整性或合同阻塞。科学门限未通过是有效结果，不是需修复的实现故障。
模型/推理元数据不可得，不能声称审查能力对等已获证明。truth 读取时刻的证据
边界如上；保存数组检查也不替代新独立样本、物理算子重跑或 CONF/Trans。

## Verification

- Raw hashes/archive/attempt/snapshot/inputs/seals：PASS。
- 32 calls、硬判/错误、16 旧调用逐值复现、配对差与成本：PASS。
- 保存 log_q、Fourier 和 Schur 小矩阵代数检查：PASS。
- Lint / TypeCheck：本轮只有审计文档，不适用；此前类型工具不可用限制不变。
- Tests / 新科学执行：未运行；本轮验证来自上述已落盘原件。

