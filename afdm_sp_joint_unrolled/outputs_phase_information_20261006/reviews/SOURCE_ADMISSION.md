# 源码准入：PASS / GO

**状态：PASS / GO。** 冻结协议、dispatch/control 和 READY 科学包均已完成必要审查，无已确认阻塞项。主会话可先提交下面绑定的 bytes，再按既有批准协议打包、建立独立快照并执行这一有界 pilot；本准入不代表 pilot 已运行、设计获益通过、首创认证或生产晋级。本审阅者没有 SSH 或科学运行。

审阅者：`/root/important_final_review`；日期：2026-10-06。唯一任务 `.trellis/tasks/10-05-method-advantage`，本轮 Mission `20261006_20-14-46-afdm-phase-information`。复用此前加载的生命周期和服务器约束，没有初始化新任务、派发代理或重审由 Claude 承担的新数学稿。仅编辑本 SOURCE_ADMISSION；主会话/实现者保有其他文件所有权。先前六项静态内容的 SHA256 未变，本次直接复用，只补 READY 源码审查。

## 已审协议：模型、观测计数与成功口径

模型是**完整、未截断、单径、共同零 delay 的宽 CFO 用例**：Y_n=h·exp(2πiνn/N)·[RFᴴCS]_n+noise_n，h 为未知单位模复增益，QPSK 源独立。整数 CFO 覆盖 [−N/2,N/2)，小数部分覆盖 [−.5,.5)，整体按模 N 比较。协议明确这个用例不同于原有窄 Doppler prior，不允许将此范围变更静默引入生产。

计数按所有生成波形的观察向量计算：

- N∈{16,64}、T∈{1,4}、SNR∈{10,20}，共 8 个固定 cell；每 cell 128 个独立配对组，共 1,024 组。
- 每组 c₂=0、1/(10N²)、1/(8N) 三种波形，合计 3,072 个波形/试验数据集。
- 新 N 向量数为 `3×128×2(SNR)×2(N)×(1+4)=7,680`。
- 复标量数为 `3×128×2(SNR)×(1+4)×(16+64)=307,200`。
- 不能将配对共用 S/标准噪声误记成只生成一份波形，也不能将 307,200 标量当作 307,200 个 N 向量。局部固定数组契约不增加科学样本；协议禁止新增 noiseless sweep、重抽样和事后挑选。

run_contract 明确 7,680 新观察、0 geometry probes、300 秒单次及累计预约、2 GiB 进程 RSS、256 MiB 输出、1 worker/1 thread、GPU 关闭，receiver/decoder/CONF 为零。其 remote_output 与本轮独立输出根一致。

公平性与证据层级已明确：

1. 估计器只接收 Y、已知 R/C、N/T；r、δ、φ、源和标准噪声作为评测/复算原始量保存，不是估计器输入。
2. 计算比较仅在 current c₂ 下，用相同数据比较三次目标评估与 64 点网格，并为两者都计最终变换和整数相关。64/3≈21.33 是目标评估次数之比，不是自动成立的运行时间加速；完整耗时和误差必须另报。
3. 三种 c₂ 的比较是波形干预，不能称作不改变波形的算法改进。c₂=0 的整数 tie 预先承认，最小索引 tie-break 与全部误差保留，不将 tie 伪装成可识别。
4. 计算门是每组 analytic J 不劣于 grid J 的相对 1e−9 检查及至少 10 倍目标评估减少；目标值更优不证明 CFO 误差支配。
5. 设计门是八个 cell 等权的配对灾难错误下降至少 .10、独立组配对正态 95% 区间下界大于零。该区间预先标为探索性近似，不给 confirmatory p-value；不通过时不得调参或挑 cell 后重新声称获益。

这里审查的是协议的一致性与可执行边界，不代替新数学稿的正确性审阅。三点评估的谐波最小化符号、整数相关方向和返回值规范已在 READY 代码中逐路径核对，见下文。

## 已审 dispatch/control

### pack_source.py

- ROOT=脚本 parents[3] 实际指向项目根；MISSION=parents[1] 实际指向本轮输出根。已按实际文件路径核实，不因变量名 MISSION 推测目录。
- 从 `dispatch/import_paths.json` 的 `all_paths` 取项目依赖，并加入新包所有 `.py` 及实际存在的父包初始化文件；READY 后清单已核对为 12 个实际 runtime 项目文件，全部存在；加新包测试及真实父包 initializer 后预期打包 16 个项目 Python 文件。
- 每个源文件与五项 control 都通过 `git show HEAD:<prefix><path>` 提取，再与工作树 bytes 比较；不一致显式失败。因此打包物不是未提交源码的工作树复制。
- 科学配置的原位置为新包内 `STUDY_CONFIG.json`，包内映射为 `frozen_control/STUDY_CONFIG.json`；最终 launcher 从远端 `control/STUDY_CONFIG.json` 读取。此路径串联在静态代码上相容，实际配置 SHA256 已与 config.py 硬绑定核对一致。
- tar 以 `xb` 独占创建，包含逐文件 SHA256 manifest 和本地 commit。没有为未提交内容设置旁路。

### bootstrap_remote.py

- 根目录固定在 `/data/guoyikun/.../outputs_phase_information_20261006`；独占创建新的 `source_v1` 和 `control`，不覆盖既有科学快照。
- 提取只接受普通文件；拒绝越出 snapshot 的路径，逐文件独占写入，核对 manifest SHA256。
- 外层 bootstrap、harvest 和 launcher 必须与提交包内 frozen_control bytes 相同。
- 在新 snapshot 内建立独立 Git 仓库，禁用全局/系统 Git 配置及模板；本地 commit 与远端快照 commit 的差异通过 DEPLOYMENT 明确记录。
- 控制文件从已验证的 snapshot 复制，所有目标和部署记录均位于该 data 根。

### launch_v1.sh

- 从固定输出根进入独立 source_v1，使用既有 AFDM Conda 环境。
- TMPDIR、XDG/MPL/Numba/Torch cache 均设于 `/data/guoyikun/tmp`；禁止 Python bytecode 写入；数值线程环境均为 1，GPU 隐藏。
- 调用 `experiments.afdm_phase_information_20261006.study`，固定 stage=`pilot_v1`、wall-seconds=300，artifact/control 路径匹配本合同。
- tmux `g_*` 会话的实际创建由主会话负责，本 launcher 没有声称自己创建 tmux；最终执行记录应保存真实启动方式。

### harvest_remote.py

- 成功相位要求为 `pilot`；遍历 execution 下所有 registration，不只选择最好的一次结果。所有完成/失败 attempt 都进入资源统计和文件清单；尚无成功 pilot 时显式拒绝成功收证，不能把失败说成完成。
- 对阶段内文件逐项记录绝对路径、bytes、SHA256、MD5；重核 snapshot manifest。
- 每个回传文件必须严格小于 10,000,000 bytes；可包含小型 NPZ，较大文件留在远端并保留完整路径和哈希。这里不是“禁止所有 NPZ 回传”，也不是宣称小包总大小必小于 10 MB。
- 输出 inventory/resource/tar 均在 data 下独占创建。最终收证必须在科学进程结束后由主会话执行；READY 后已核 recorder：complete 和 invalid_partial 都有明确状态、耗时、保留预约及文件哈希；成功收证须在进程结束后进行。

## READY 科学包逐路径核对

### 数据生成、真值边界与完整样本

`study.calculate` 仅在协议的提交来源检查、资源预约和 registration 完成后调用 default_rng(20261006)。按 N、T、SNR、group 固定顺序抽取整数 CFO、小数 CFO、gain 相位、QPSK、实/虚标准噪声；每个组中三种波形共用这些外生量，但按各自 C 重新 IFFT 并生成各自真实 Y。它不是把同一份 Y 换标签作为三波形对照。

每生成一种波形前检查剩余观察预算，随后记录 T 个 N 向量和 T×N 个复标量。最终精确核对 1,024 配对组、3,072 数据集、7,680 N 向量、307,200 复标量、4,096 次估计器调用与 7,680 次生成 IFFT。生成器没有调用额外 geometry 或隐藏 noiseless sweep。

每组先独占保存 raw.npz，含 S/符号标签、标准噪声、r/δ/φ、gain、噪声方差、三种 Y 和 R/C；随后才调用估计器。`estimate` 只收到 Y、已知 R/C 和固定数值设置，真值只在返回后进入误差评分。current 的 analytic/grid 引用同一观察对象，并记录相同 Y 内容哈希；其他波形单独记录自己的 Y 哈希。

每组记录所有四个估计值、flag、目标值、耗时、计数和 raw/estimate 文件哈希。任何不完整 cell 都拒绝汇总，成功结果必须保留全部 1,024 组，不选择 survivors。异常时保存 partial_work_counts，传播至 invalid_partial；未完成组的已落盘原始观察仍保留。部分失败不能被当作完成估计器的完整操作计数或成功性能结果。

### 三点与整数相关、退化路径

`core.fractional_scores` 使用正交归一化 FFT 对 dechirp 后的 T×N 数据计算 mean_t sum_s |F D(−a)z|⁴。analytic 只评估 0、1/3、2/3；谐波系数取 mean[J(a) exp(−2πia)]，若非 flat，最小点 `(π−arg(harmonic))/(2π) mod 1` 的符号与这个系数约定一致。grid 使用同一目标在 64 点评估，没有真值初始化。

最终 X 按选定 a 重新计算；整数相关为 `ifft(fft(m)·conj(fft(w)))`，其 r 项正是 Σ_s m_s·conj(w_(s−r))，与返回 CFO=a+r 的方向一致。旋转 QPSK 的四次方公共负号和未知 h 相位被模长评分消去，不需要输入 gain 或符号。

flat 阈值与 near-tie 阈值完全使用冻结配置；flat 时 a=0、整数 exact maxima 取最小索引、并保存 `identified=false`。这属于预先规定且显式标记的退化行为，没有伪装成成功辨识。零 c₂ 的全部整数等价结果和误差都保留。输入非有限、非单位 chirp、目标/相关非有限等路径明确抛错，不 silent fallback。

误差函数 `(estimate−truth+period/2) % period−period/2` 分别用于周期 1 与 N；负小数 CFO 和 r+δ 越界均按同一模规则处理。灾难错误严格按 |full_error|>.5，未将 near-tie 样本丢弃。

### 计费、配对统计与科学门

current analytic/grid 的调用先后按全局组奇偶交替。计时包含估计器验证、dechirp、分数搜索、最终 X、四次矩与完整整数相关；共享数据生成和 I/O 不在估计器计时内。零/设计波形的计算单独保留，不借用 current 数据结果。

每个 analytic 估计记录 3 次搜索目标＋1 次最终目标，FFT 向量数为 4T+3；grid 为 64＋1 次目标、65T+3 个 FFT 向量。相关的模板 FFT、数据 FFT、IFFT 三项都计入，没有共享模板缓存。按整个冻结网格，完成运行预期为：

| 计量 | 预期值 |
|---|---:|
| CFO 估计器调用 | 4,096 |
| 估计器搜索目标 | 74,752 |
| 含最终目标的目标总数 | 78,848 |
| 估计器 N 向量 FFT/IFFT | 209,408 |
| 数据生成 N 向量 IFFT | 7,680 |

这只是从固定循环得到的预期计数，不是执行结果。3/64 搜索比为 64/3，包含最终目标后为 65/4；代码同时报告完整耗时比和误差，不将目标减少自动称为同倍墙时加速，也不称为超过已有经典三点评估方法。

每个 cell 单独保留四方法的 count、RMSE、灾难数/比例、flat/tie、计时和操作计数。设计差值按同组 current−designed 灾难指标配对；方差使用每 cell 的 ddof=1 样本方差，除以 cells²×groups，再按冻结正态分位数给区间，符合协议。统计是探索性正态近似，不提供确认性 p-value。

设计门与计算门独立。设计门未通过时只返回 false，不重采样或调参；analytic 目标不满足冻结逐组支配条件时，先保存全部组、summary、work_counts，再显式使阶段失败。目标更优不被解释为 CFO 误差支配。

### 来源、运行资源与既有协议复用

config.py 硬绑定 `9603b3320d50c1d81256f31cc710f743b08ce3aee48d840aa89fb4fbc1678b68`，任何不同配置 bytes 都在运行前拒绝。12 项 runtime 清单包含动态使用的两个旧 recorder 和线程检查依赖；pack_source 再加测试与实际父 initializer。旧六项静态哈希未变。

`committed_project_sources` 对全部绑定项目 Python 使用 HEAD / git ls-files / git show，拒绝未提交或与 HEAD 不同的源码；不只检查新包。配置和 run contract 由已审 pack/bootstrap 的 committed-byte 路径提供，且在 recorder 中再次哈希登记。私有 adapter 不修改旧模块的全局任务位置。

复用的 recorder 有任务锁、独占 stage、累计观察/墙时预约，失败消耗其完整预约；300 秒 alarm、全过程单线程限制、前后有效线程池核对、2 GiB 累计 RSS检查和256 MiB输出检查均沿真实调用链落实。这里 RSS/输出是检测并判失败的门，不声称具有内核级硬内存限制。异常有 invalid_partial、耗时、保留观察数和 artifact 哈希；没有重试采样机制。

## Findings (fixed)

无新增源码修复。本代理在冻结协议、dispatch/control 和 READY 新包中未发现需要阻塞本 pilot 的已确认缺陷。

## Findings (not fixed)

无源码准入阻塞项。当前没有 pilot 执行结果、设计收益、计时优势或最终统计结论；这些须由同一冻结配置的实际运行及独立结果审计获得。宽 CFO 用例、单径零 delay、波形干预和64点网格参考限制必须保留，不能晋级为一般原窄先验下的性能或新方法首创。

## Verification

- Lint：审阅者独立执行新包 Ruff **PASS**；此前 dispatch Ruff **PASS**，六项静态哈希未变，不重复运行。
- Python：新包 8 个 Python 文件 AST **PASS**；此前 dispatch 3 文件 AST **PASS**。两者均不算静态类型检查。
- Shell：复用未变化 launcher 的 `bash -n` **PASS**。
- Tests：实现者与主会话报告本次 **7/7 固定 fixture unittest PASS**，另有 compileall、CLI --help、12 项 import inventory 和 diff --check 通过。本代理已读全部七项契约并复用这些实跑证据，不重复运行或声称由自己执行。
- 配置和清单：配置 SHA256 硬绑定 **PASS**；12 runtime 文件全部存在，预期打包 16 项目 Python；固定预算/操作计数算术 **PASS**，不生成观察。
- TypeCheck：项目未配置适用静态类型检查器，未运行。
- 本审阅者未执行科学 pilot、SSH、RNG 抽样或新全稿数学复审，没有安装环境。

## 已完成静态审查的版本绑定

以下 bytes 如未改变，最终准入直接复用；如改变，仅复审差异。READY 科学包和配置绑定在下表追加；最终 commit ID 由主会话提交后写入部署/registration，本审查不预言尚未产生的提交。

| 文件 | SHA256 |
|---|---|
| `.trellis/tasks/10-05-method-advantage/research/20261006-phase/PILOT_PROTOCOL.md` | `c01230dd8590cb1933db6da066813d88233645860c8d4ca58d284bf9e38d0179` |
| `afdm_sp_joint_unrolled/outputs_phase_information_20261006/run_contract.json` | `aad984f220f1cec065f51c2ac51f47e114af727d6aafa36eba4a04860b6dec4f` |
| `afdm_sp_joint_unrolled/outputs_phase_information_20261006/launch_v1.sh` | `d1381c0c5b557c1948fe57663f6bd7c367cc6fea697ae70230e24cdfc0eed9f9` |
| `afdm_sp_joint_unrolled/outputs_phase_information_20261006/dispatch/bootstrap_remote.py` | `57a36f1a08211455d121f1e1f166fe0e1153b02812e60c79170ab240d453e41a` |
| `afdm_sp_joint_unrolled/outputs_phase_information_20261006/dispatch/harvest_remote.py` | `7807182e1d2dc23d6ab83721187f97bb253cf14b04794811ae24d106da82148b` |
| `afdm_sp_joint_unrolled/outputs_phase_information_20261006/dispatch/pack_source.py` | `fa6712200dd48110e82fd11d805b1332d4e672641ed71112158c3e199ffd2535` |
| `experiments/afdm_phase_information_20261006/__init__.py` | `e58741979080cb14191ec9af9f2feea1234bc35bbdfeaac20efe59ddd7b5b900` |
| `experiments/afdm_phase_information_20261006/config.py` | `9572477df06c8b6c64aba8841f2af63a8c145b4c5536d4d4063b35fb812a0e6e` |
| `experiments/afdm_phase_information_20261006/core.py` | `fc17e0901ffa3c12dd7244014fae5022ae7983c38b1d7450f1cf263cfe8a1447` |
| `experiments/afdm_phase_information_20261006/protocol.py` | `3e450caa2f2ac8e1cc8045cb327125c181e89adc151039a69caacc0a3a6122d2` |
| `experiments/afdm_phase_information_20261006/study.py` | `7b3278f64726e67fcc26d8924ddd49ad0c167c0781f6f9d88c04669e084176e4` |
| `experiments/afdm_phase_information_20261006/test_contracts.py` | `7d2c0de58a5b1f8f5e7fb576ccabc4f6a27bff2fda7bf0edfdd3d5adfce8f354` |
| `experiments/afdm_phase_information_20261006/test_core.py` | `b8072540ef2bbab25d62b9ddae0282fdc79c7b2a20ee2628b1de5d3ab9ea374d` |
| `experiments/afdm_phase_information_20261006/thread_binding.py` | `54238b8cf60a4bf67cfe9c28286ac360cf9935d011b4fb7315b77d5fee0de8e1` |
| `experiments/afdm_phase_information_20261006/STUDY_CONFIG.json` | `9603b3320d50c1d81256f31cc710f743b08ce3aee48d840aa89fb4fbc1678b68` |
| `afdm_sp_joint_unrolled/outputs_phase_information_20261006/dispatch/import_paths.json` | `3ec2bd050dee9691b627668aff2a9e5cc2da99d0c94fff0e0c8dd873d8c44056` |

预期包内 16 个项目 Python 文件的联合 SHA256：`54c2012d04c025f67d56be17a637cbd69f4f692a382b81e7efd16ae67bf6e31c`。算法为路径字典序排列后连接 `sha256(file_bytes) + "  " + path + "\n"`，UTF-8 编码再 SHA256；包含 12 runtime 路径、新包两测试及两个旧包 initializer。完整单文件清单由正式 pack manifest 保存。
