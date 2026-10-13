# Research: 捕获性能与成本先导研究的独立源码准入

- Query: 核验数学实现、无 truth 估计器边界、公平计时、工作量和异常记录、配置/源码绑定、输出与远端 dispatch 是否符合冻结 PROTOCOL。
- Scope: internal；源码静态审查及小型确定性工程测试，无科学试验、SSH 或 Git 操作。
- Date: 2026-10-07
- Active task: `.trellis/tasks/10-05-method-advantage`
- CSV: `.mission/20261007-acquisition-performance/20261007-acquisition-performance.csv`

## Findings

### 最终结论：PASS，限定冻结 D/P/A 开发先导源码

SA1、SA2、SA3 均已关闭。数学核心、D/P 实现、有限范围的独立 A 审计及 dispatch 通过本轮源码准入；PROTOCOL 的 F1–F4 修复及 config 字节 SHA 已核实。主线程报告最终统一 16/16 确定性工程合同、Ruff、bash-n、CLI import inventory 均通过；本代理另有此前 7 项核心合同的独立运行证据，未重复运行全部测试。

准入仅适用于本文末尾哈希表所列版本及冻结的 3072 新观测、D/P/A 预算和作用域。可由主线程继续既有提交、打包及远端执行流程；本报告本身未提交、部署或运行科学阶段。下文早期 findings 保留审查历史，其待修状态由对应 follow-up 覆盖。源码 PASS 不等于性能 gate、创新目标或生产放行通过。

### 已读文件与责任范围

- `experiments/afdm_acquisition_performance_20261007/core.py`：物理生成器、FFT 四阶筛选、稳定 mixture profile likelihood、纯观测估计器。
- 同目录 `study.py`：D 码设计、P 配对研究与汇总、阶段入口。
- 同目录 `protocol.py`、`thread_binding.py`、`STUDY_CONFIG.json`：旧 recorder 适配、线程约束、冻结数值配置。
- 同目录 `test_core.py`：7 项确定性合同。
- `afdm_sp_joint_unrolled/outputs_acquisition_performance_20261007/dispatch/{pack_source.py,bootstrap_remote.py,harvest_remote.py}`、`launch_v1.sh`、`run_contract.json`：与前一轮 phase-information 同名文件作 diff，并检查当前全文。
- 仅为核实实际复用接口，读取 coherent-structure / efficient-information / higher-order-information 的 `protocol.py`，phase-information 的 committed-source、array-hash、paired-interval 函数及旧 thread binding。未重新加载生命周期或服务器规格。

## 必须关闭的问题

### SA1：逐臂生成失败可能少记已完成工作

当前 `pilot` 用 dict comprehension 一次生成三个 waveform，再把 dataset/vector/scalar 计数整体增加 3 倍。若第二或第三次 `simulate` 异常或超时，前一臂已产生观测，`partial_work_counts.json` 却仍未计入本组任何生成工作。

修复应逐臂执行并明确记录 entered/completed。建议每臂开始前记录在途操作及该次保守工作量、返回后立即增加已完成 dataset/vector/scalar 计数；失败时保存两种状态，不能把尚未完成的操作假称成功。旧 recorder 会保留全额 reservation，但这不替代新 pilot 自身对已完成工作的准确记账。

### SA2：当前组完成的估计与计时在后续失败时丢失

当前 `estimates`、`arrays` 只在九个调用全部成功后写盘。若组内第二至第九个估计出错，已有成功调用的 output/score/timing 仅在内存，异常分支只写计数。这不符合“保存每个错误、tie、所选参数、score grid 和耗时”的冻结协议。

修复应保存当前组已完成部分、失败的 operation/algorithm、entered 与 completed 计数；失败组必须显式 invalid partial，不得进入成功组汇总或丢弃后继续跑幸存组。可在异常边界写 partial NPZ/JSON，保持正常路径的完整调用计时边界不变。应加一个无需随机新数据的故障注入工程合同，以确认第二臂/后续估计失败时保存的计数与已完成结果。

### SA3：完整独立审计尚未进入已读版本

`audit.py` 未完成且未审。最终准入需要其对原始数据哈希、生成确定性重放、设计/评分重算、计数、dominance 和门槛的独立验证接口完成。主程序已在源码/线程清单冻结前导入 audit，这个位置合理，但不能把未读未完成代码作为已准入部分。

## 已通过部分

### 数学与无 truth：PASS

`simulate` 对行 chirp 后时域信号作循环 delay，并施加包含帧间间隔 L 的物理 CFO 相位，符合 PROTOCOL。nominal σ² 与隐藏 ρ 独立，QPSK 映射为指定四点。

`fourth_scores` 的 shifted index、conjugate(v⁴)、N×ifft 和 4l 抽取正确。`ambiguity_objective` 表面使用 conjugate(w_shift conjugate(w)) 配合 ifft，等于目标 FFT 系数的共轭，其模长正是所需 |A(k,4d)|，没有符号错误。

`profile_likelihood` 的 demodulation、√2/σ² 缩放、双 logaddexp 减 2log2 和每坐标 ρ²/σ² 项正确。批量大小 16 只限制内存，不改变候选集合。SCREEN 先稳定选 top32，再按 global hypothesis 排序，随后 argmax 实现全局 θ 索引优先和 gain 索引次优先的 tie 规则。FULL 遍历同一固定 gain grid 的全部 θ。

纯估计器 `estimate(y,v,sigma2,method)` 无 truth 参数、不读隐藏文件、不用全局真值；真值仅在外层生成和事后错误标注。没有缓存跨调用预处理。返回 gain 已按 exp(+πis lhat²/N) 转换到物理 gain 的 C4 等价代表，FOURTH 返回 None。

### 协议定义与统计：PASS

F1–F4 已在当前 PROTOCOL 中修复：星座映射、nominal SNR、物理 gain 商相位和异质 Bernoulli x≤1 门槛均明确。`summarize` 调用已读取的 `paired_interval`，其 SE 正是四个固定 cell 内样本方差的等权组合；CP 字段只标为 binomial reference。坏/反向 discordance 单独记录、联合 gate、cell 可用率均实现。

### 配对设计与完整成功计数：PASS

D 使用 129 个预注册 quadratic candidates（含 current）与一次 fixed-seed random arm，argmin 的低索引 tie break 正确。没有 observation-dependent 调参；代码字节和设计 objective 被保存。

P 按 N、SNR、组顺序抽取 l、ν、ρ、φ、state、real noise、imag noise；三臂共享同一组 exogenous variables。成功结束要求恰为 256 paired groups、768 datasets、3072 N-vectors、147456 complex scalars 和 2304 acquisition calls；不完整 cell 不允许汇总成功幸存样本。核心问题仅为上述异常途中计数，而不是完整成功路径。

### 公平计时：PASS，附一项非阻断补充

计时从 `estimate` 入口前到完整返回后，包含验证、去 chirp/FFT、模板构造、筛选/likelihood 与输出构造；hash/真值错误标注和磁盘在计时外，三个方法一致。FULL 和 SCREEN 各自付费预处理，FULL 不额外计算无用四阶筛选，有利于强基线。

每组九种 arm/method 顺序循环旋转；总时长比及各 cell 比已记录。协议另要求 mean per-cell ratio，当前可从四个已存 ratio 直接计算，但建议加显式字段避免报告时遗漏。这不影响 3× 总时长 gate。

入口自己的 timer 开始于 main、不能包含 import；新增 launcher 的 `/usr/bin/time -v` 补充含 import 的整进程成本，因此该边界已经有正确报告通道。不得把 entry-to-callback-end 当完整 process startup 时间。

### 配置、源码与线程绑定：PASS（静态接口）

已独立核对实际 `STUDY_CONFIG.json` SHA-256：

`3d665efd526a68bad2be1f9ccf1f41aaf1f21bbd56df91c9b5b7b2c93011198a`

它与 `study.CONFIG_SHA256` 一致，main 在加载后拒绝字节不符。`protocol.run` 绑定已加载 project Python、整个新 package 和配置/阶段依赖；新适配器不修改旧模块文件。复用的 committed-project 检查针对 Python HEAD 字节；pack_source 又从同一本地 commit 提取 Python、配置和控制文件，拒绝工作区不一致。

旧 recorder 保留不可覆盖 stage、资源 reservation、源码 snapshot、运行前后 source hash、异常 attempt 和线程池复核；新 package reexport 的 thread binding 接口匹配。main 在清单冻结前预加载 audit 和数值依赖，实际远端清单仍需由运行 receipt 证明，本报告不冒充运行证据。

## Dispatch 与资源边界

相对旧 phase-information 脚本的变更限于新路径、package、配置实际包路径副本、manifest 独占写及 harvest 要求 D/P/A 都 complete。bootstrap 拒绝覆盖 source_v1，验证 tar 内 regular files 与路径、manifest digest、外部控制文件和 frozen 字节一致；使用隔离 snapshot，不覆写旧远端源码。这里只读取脚本，没有执行其 Git/SSH/写盘操作。

launcher 的路径、临时/cache 路径、conda AFDM、CUDA 隐藏及线程环境与所给合同一致；顺序执行 D/P/A，失败会因 `set -e` 停止。**小修订建议：EXIT trap 当前安装在 conda activate 后，激活失败不会留下 launcher_exit receipt；应在 study_output 已确定后、source/activate 前安装。** 完整数值阶段不会因此误判成功，但失败归档应覆盖启动失败。

A 把 P 文件纳入 source_snapshot 的确会复制一次 P raw/score/artifact，不是递归无限复制：列表只扫描 P，A 不扫描自己。按成功路径保存的 profile score（不是全 gain tensor）估算，P 的 score/hypothesis/best-gain 原始数值 payload 约 20.25 MB，raw payload 约 3.55 MB；复制一次再加 JSON/source/NPZ headers，距离 512 MiB 有明显余量。此为静态尺寸估算，不是实际 output/RSS 测量；旧 recorder 仍须核对真实累计 bytes 与 whole-process RSS，触限不得追加重试。

## Validation

在明确允许的小型确定性工程范围内独立执行：

`PYTHONDONTWRITEBYTECODE=1 /tmp/afdm-shared-channel-env/bin/python -m unittest experiments.afdm_acquisition_performance_20261007.test_core -v`

结果：7/7 通过，unittest 显示 0.027s。覆盖 dense 物理模型与有效坐标、全部小格点 FFT/direct sum、四分量 Gaussian 显式 likelihood、C4 连续帧、无噪声 gauge recovery、SCREEN 子集/FULL dominance、tie 与无 truth 输入边界。这些是确定性合同，未产生随机科学性能样本。没有重复运行科学 D/P/A。

主线程报告 ruff 与 bash-n 已通过；本代理未重复执行这些检查，也不把其报告列为本代理亲验。故障注入与 A 的新增合同待修订后补核。

## Caveats / Not Found

- 当前不完整准入的具体原因只有 SA1、SA2 和未完成的 SA3；mean cell ratio/启动 trap 是可直接完善的小项。
- 未执行 Git、pack/bootstrap/harvest、SSH 或任何科学仿真。最终提交/打包 source hashes 和远端运行 receipt 仍由主线程负责。
- 这是先导开发源审查，不是性能证据、生产放行或新颖性认证。有效经典适配可保留，但不能把未观测的性能成本 gate 写成已通过。

## Follow-up: SA1/SA2 修复与小项关闭

2026-10-07 已针对性复读当前 `study.py`、新增 `test_failure_records.py` 和 launcher 变化：

- SA1 已修复：按臂进入生成前计 attempted_observation_vectors，生成返回后逐臂计完成 datasets/vectors/scalars，保留已完成 Y；异常 raw prefix 可落盘。
- SA2 已修复：估计 entered 与 completed 分开，异常保存 partial_record（失败 operation、已完成估计、timing、计数）及 partial_estimates/partial_raw，已有完整文件不覆盖；异常继续抛出，不将该组加入成功组。
- 两项故障注入合同分别固定第二次生成失败、第二次估计失败，使用 FixedGenerator 确定性 mock，无新科学采样；测试明确核对完成/尝试计数、已完成 waveform 和 score 保存。主线程报告两项先失败复现后修复通过，本代理核查其源码和断言，不把主线程运行误称为本代理亲验。
- mean_cell_speed_ratio 已显式加入 summary。
- EXIT trap 已移到 study_output 确定后、cd/source/conda activation 前，启动阶段失败记录范围得到补齐。

**当前状态更新：数学核心、D/P 实现及 dispatch 已通过本轮针对性源码审查；完整 D/P/A 准入仍只待 SA3（独立 audit.py 完成并核查）与最终统一源码冻结。** 无需再次扩大数学或实验设计审查。

## Final follow-up: SA3 关闭，独立审计与方差直觉通过

2026-10-07 已完整读取最终 `audit.py`、`test_audit.py` 和 `INTUITION.md`，未重审已关闭条款。SA3 判定 PASS，具体证据如下。

### 审计的独立性及真实覆盖范围

audit 没有导入生成器、estimate、生产评分或生产 summary，没有 RNG 或 estimator 调用。其复数傅里叶矩阵按定义构建，通过 dense matrix 与显式循环索引重建所有 768 waveform datasets 的 3072 个保存 N-vectors；这与源实现的 FFT/roll 是独立计算路径。CFO 时钟、s=5 行 chirp、QPSK mapping、nominal 噪声缩放均正确。

每组 source array 的 dtype/shape/content hash、文件 hash、per-group record 与总 record 的一致性、候选集合、输出参数、gain gauge、tie 数、调用耗时和 truth error 标注逐项检查。FULL/SCREEN 使用的同一 shortlist profile 与 gain index 逐项交叉核对；全部 FOURTH/SCREEN 的格点评分另用 dense Fourier + direct delay matching 重新计算。hypothesis top32 的稳定顺序、FULL 全集合、profile argmax 和 gain 范围没有漏掉 global index 的 tie 约定。

独立 `direct_mixture` 对四 Gaussian component 使用减去最大 logterm 的 log-sum-exp，再恢复共同能量项，常数及指数正确。该路径与生产 cosh 公式不同。检查只覆盖每 cell 第一组、每个 arm 的 FULL winner 和下一个候选，共 4×3×2=24 候选，每个检查 48 个 gain；不会伪称全量重新算过全部 likelihood。选择这 24 项是预定 spot rule，完整 saved grid 的 argmax/shortlist/相互一致性仍是全量检查。

设计部分核对 codes 文件与两份 receipt、全部数组 hash、129 个固定 candidate 值、saved objective 的最低索引 argmin、选中 quadratic code 公式和所有臂单位模。**没有独立重算 163280 个设计 ambiguity 值，也没有重新抽取 random code 或 replay RNG seed。** 这一限制在 audit scope 明说，符合 A 的 0 新观测/0 新 geometry 预算；此前数学源码审查已经核验设计目标实现，不能把 saved-grid selection audit 包装成额外设计实验或全量设计值重算。

### 计数、统计与失败语义

逐项遍历重建 256 组、2304 次已保存 acquisition 输出；likelihood hypothesis 总数 516096、gain-grid evaluation 总数 24772608 正确。这些是核查源 P 的已完成计数，A 自身不调用 estimator。新的 explicit-mixture spot 运算如实列在 audit checks，不冒充新科学样本。

`independent_summary` 使用独立 Python 标量求和与组内方差计算 equal-cell mean/SE/normal CI，重新计算 bad/reverse discordance、3×总时长比、mean cell ratio、各 cell usable gate 及联合 gate；没有复用生产 summarize/paired_interval。CP 未被重算为所谓精确分层区间，正式非劣 gate 仍是 x≤1。源 P 的 dominance 是允许失败的科学 gate，而非直接判源损坏：audit 验证记录与 scores 所蕴含的布尔值一致，随后忠实重算联合失败结果，正确。

任一 complete source、hash、目录/组顺序、shape、finite、score、count 或 summary 合同不满足都会抛 ValueError；不会返回 audit_pass。通过时明确 new_observations=geometry_probes=acquisition_calls=0，复用 recorder 对 A 的零新数据合同可正确验收。结果由独占创建的 audit.json 保存。

7 项 audit fixtures 覆盖 hash dtype/shape、saved tie/gain selection、FOURTH unavailable gain、四 Gaussian normalization、分层 gate/incomplete cell、损坏 design hash、未完成 source。主线程最终统一报告为 core7+failure2+audit7=16/16 PASS，并报告 Ruff、bash-n、CLI `--print-imports` PASS，18 个实际 runtime project 文件清单已保存。该统一运行由主线程完成，本代理只补独立源码审查，不重复测试。

### INTUITION 四阶复方差：PASS

固定复数 a、η~CN(0,σ²)，

`(a+η)^4−a^4 = Σ_(r=1)^4 binom(4,r) a^(4−r) η^r`。

proper Gaussian 有 `E[η^r conjugate(η)^q]=0`（r≠q），且 `E|η|^(2r)=r!σ^(2r)`，所以复方差为

`Σ_(r=1)^4 binom(4,r)^2 |a|^(8−2r) r!σ^(2r)`

`=16|a|⁶σ²+72|a|⁴σ⁴+96|a|²σ⁶+24σ⁸`。

稿件系数及 Var(Z)=E|Z−EZ|² 定义正确。真整数变换下 symbol/C4 frame 因子的四次幂确定、|a|=ρ，T 个独立帧平均的方差确为上述值/T；各坐标独立，正确匹配后的 N 坐标和使信号均值乘 N、噪声方差乘 N。N 倍是相对于单坐标的平均增益，并非 N²/4 个相关候选同时比较后的错误率结论。稿件将其表述为低 SNR 下 shortlist 可能丢真值的运行前假设，没有冒充性能结果。

## 最终审阅版本 SHA-256

以下为本代理读取后用 `shasum -a 256` 核对的 2026-10-07 版本；源码或控制 bytes 若改变，应补差异审查并更新对应项。仅覆盖新 package/control 与本轮协议/直觉稿；被复用的旧 runtime helpers 继续由实际 import inventory、commit gate 和 recorder manifest 完整绑定，不声称此表替代其运行 manifest。

`PKG` = `experiments/afdm_acquisition_performance_20261007/`；`OUT` = `afdm_sp_joint_unrolled/outputs_acquisition_performance_20261007/`；`RESEARCH` = 本报告所在目录。

| 文件 | SHA-256 |
| --- | --- |
| PKG/__init__.py | 81aed74a61b08f631e4723d0a73961d3152005e47fd8b0dfd498dfeea03e204a |
| PKG/audit.py | b9f92f8dfcbd230645df08b4c5a2a7621a5ef1492470fd279b7cadd46a75416b |
| PKG/core.py | 68ecf535397c120e06b21f9a36d04794808d1c3e80cb4e80d6bfb82b1c9e777b |
| PKG/protocol.py | 617156277a644bb629d3dc3c2a6312dcd651956a58b5f1d273b3ae8862998bee |
| PKG/study.py | 82adf9e385e16828a802b2adf64497afcdfd3e8be64226124f06a132abe97863 |
| PKG/test_audit.py | 5388ac3956b2072ce00722bfe379e72558d139eb58c38a2edf9e8a3be6d7a1d8 |
| PKG/test_core.py | b5640065fefe9d9c3ebe3c8103a0fe3e8471dc21bbf62d7bfa7acf518d1397f3 |
| PKG/test_failure_records.py | 8a8f21be3da89fab24a86a6ec8b2a20bb13d67f46ea3a7945395315f882927a7 |
| PKG/thread_binding.py | 595aa7384f21e20ac23b965c9e6401a0290baf905207648a0dbfb344059bd13f |
| PKG/STUDY_CONFIG.json | 3d665efd526a68bad2be1f9ccf1f41aaf1f21bbd56df91c9b5b7b2c93011198a |
| OUT/dispatch/bootstrap_remote.py | 5b2a34d4e43d6bdb6e9958b4333a70b3946a76282616ed43f521c7594185a400 |
| OUT/dispatch/harvest_remote.py | e80d298047df5b1e7b24eba048987d09f062c3fd1968161f63a4c9025d579ae8 |
| OUT/dispatch/pack_source.py | 0a53090ac34a4a156afd0304e42500993c97f2b94b2ae026e48c1e467db16195 |
| OUT/launch_v1.sh | 9d4b33987697b733812806cd4b8dc0f9dbf238823d02de11a6821639713eca89 |
| OUT/run_contract.json | 124b6bf750190717491556b8371c884991e5aff9ab355eb07ba9b063defbba2a |
| RESEARCH/PROTOCOL.md | 67c34fa2676c40f52934b888119f99883fdc8e79e87dc85dd9cdefbfc47b5c53 |
| RESEARCH/INTUITION.md | 65865350d71f00a7ad07e5ed332cf6db2483a939befc6792045f25b2a8b428fb |

冻结前最后核对 launcher 的退出 receipt 改为 `launcher_exit.log`，符合既有 harvest 的 `.log` 选择规则，因而可自动带回退出码；这是文件后缀修订，不改变科学执行。上表已更新为该最终字节 SHA。

最终没有未关闭的源码准入缺陷。所有结论仍限定于冻结开发 pilot；尚无任何科学运行或性能结果由本审查产生。
