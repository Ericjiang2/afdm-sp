# COLLAPSED-MATH-01 独立原件审计

日期：2026-10-07。任务：`.trellis/tasks/10-05-method-advantage`。
CSV：`.mission/20261007-sp-fractional-trans/20261007-sp-fractional-trans.csv`。

review_actual_model: unavailable_from_current_tool_metadata
review_actual_reasoning: unavailable_from_current_tool_metadata
validation_limited: model parity unknown

## 结论

**PASS：冻结的 6 个保存数学案例、全部 45 候选及原件账本通过独立核验。**
未发现阻塞。实际一次运行完整退出，工作量、数值门槛和资源预算符合注册。
该结果不证明 BER 改善、实际 SP 后验校准、接收机加速或 Transactions 目标达成。
6 cases 是原数学 fixtures 的 N/P 组合，不是 6 个新增独立通信样本。

本代理仅读取回传原件，使用标准库 NPY/ZIP 解码和保存小矩阵代数重算。
没有生产 import、SSH、Channel/receiver 调用、求积、新仿真或实验重跑。
源码与一次运行准入沿用 `COLLAPSED_MATH_REVIEW.md`；没有修改原件、源码、STATE 或 CSV。

## 原件及身份

本地根：`.mission/20261007-sp-fractional-trans/evidence-collapsed-math/`。
远端根：`/data/guoyikun/afdm_sp_collapsed_20261007_math01_d3b2f1d8`。
stage：`artifact/execution/COLLAPSED-MATH-01`。

| 绑定对象 | SHA-256 / commit |
| --- | --- |
| source commit | `d3b2f1d8008db8db0f2cf1adf31dc5b39e4c49e3` |
| snapshot commit | `118703423cbe93a8a817b3808287d640594fd97f` |
| source archive | `3b4af7e3abb06cb1b3ccfd1135f628fb2d765a0a2355bd4b6afef03a5a70bd5d` |
| `artifact_manifest.json` | `e14418d94f8e374c8b55169e6e0bed7b5320943db1f33e9442dd68584627fc4b` |
| `artifact-small.tar.gz` | `ea501c0bac95a1a4424498af9f49f86d03d1d2549d8abae22b94b85ad4c10265` |
| stage `attempt.json` | `cd7ce97e6e49fea4d58d1a585981cea92f835ff2ad40461ee3fa34cee655647a` |
| `collapsed_complete.npz` | `969101271d2e92c1609dcc219e43ecd37d2edcfed6bbf115c45d7873c5b09b5f` |
| `collapsed_summary.json` | `ec365ac8d4cf8c03abdbf18dde12008aca0f4ca40a289d9a3191b74a1fdca209` |
| `run_contract.json` | `3d33a84103cf24c870350009c72461784000f69b2703cc142cbeea74731fe028` |
| `launch.sh` | `1f912dbe49d84411d7e86732abadf611f19418d53457eea0366010ca0cb1937e` |

逐一重算全部 **208 文件、4,468,187 bytes** 的 SHA-256、MD5、大小与远端路径，
并核对完整文件集合。最大单文件 763,875 bytes，全部 copied，无跳过大件。
归档所有文件成员与 manifest 精确对应，逐文件内容哈希一致，无重复文件成员。

attempt 为 `complete/exit_code=0`，其 199 个原件绑定恰好覆盖 stage 中除 attempt
本身外的全部文件。registration 的 config/_config、argv/_argv、snapshot HEAD、
120 秒 deadline 和源绑定一致。77 个 source snapshots 对应 66 Python 源、10 个原输入
和合同；逐 SHA 匹配注册，Python 快照还与已审工作区字节相同。
input_identity 完整匹配原 10 文件，无新增输入。

解析全部 61 个 stage 原始 NPZ，检查证据 identity、数组成员引用、ZIP 成员唯一性；
NPY 解码保留 C/F 布局、dtype 和 shape。45 candidate 原件、6 case 原件、3 physical、
3 Gaussian、3 fixture 与 complete/summary 中对应树精确一致；保存后新增的 raw_sha256
和 save_seconds 单独核对。`results.json` 的摘要部分与 `collapsed_summary.json` 一致。

## 数学核验

全部 P≤2 系统使用独立显式逆/行列式和 Python 复数收缩重算，没有调用生产求解器。
覆盖 9 个块准备的 A、A⁻¹、b_−、z、固定常数；45 候选的 precision、b、s/t、J、
完整 m/C、logdet、含常数 score；96 个共享求解的矩阵、Cholesky 乘积和残差；
90 组直接 trace/entropy 项；45 个 gauge 旋转及 m/C/score 关系。
其余坐标 R 子块与 f 分量保持原基点，P=1 按自身 prior 求解，没有截取 P=2 的 m/C。

9 个基点解析导数的 s′、t′、J′、dΛ、db、envelope 独立重算；18 对差分既从保存的
完整 score 重算，也从独立显式求解所得 score 重算。两层均通过原 1e-5 阈值。
1344 项 case 检查的完整结构、原阈值及通过状态均核对；另核 3 项 Gaussian 检查。

| N | P | 候选 | case 检查 | 最大两层差分归一误差 | 最大 full C 对参考误差 |
| --- | --- | --- | --- | --- | --- |
| 8 | 2 | 10 | 288 | 5.4834738472e-8 | 3.1047677313e-17 |
| 8 | 1 | 5 | 160 | 6.1019279241e-8 | 1.3877787808e-17 |
| 16 | 2 | 10 | 288 | 4.3751064854e-8 | 1.9640527366e-17 |
| 16 | 1 | 5 | 160 | 5.6599865461e-8 | 6.9388939039e-18 |
| 1024 | 2 | 10 | 288 | 6.4580241377e-8 | 3.2538539423e-19 |
| 1024 | 1 | 5 | 160 | 6.4264215699e-8 | 3.2526065175e-19 |

保存检查中的最大非差分归一误差为 **2.3831294261713214e-15**。
独立 Python 标量复数运算的对应 b_i 比较为 **2.453343274533206e-15**；
NumPy 与标量运算存在非零末位差异，均远低于冻结阈值，没有声称逐位相同。
独立求解 score 后差分的最大误差为 6.45758004846897e-8；
直接重算保存 score 的差分最大值为 6.45802413767882e-8。
没有改容差、选差分层或删除候选。

基点物理 R/f 对 canonical 的最大归一误差分别为
8.922762001730405e-16 / 1.4822905212484144e-15；完整 score 对参考最大
3.275019240160784e-16。独立重算 precision residual 最大
3.34783397746426e-16，低于 1e-10。最小 s 为 9.5320554610742，
最小 s/P 为 5.260548900931954，全部满足 prior 下界。

### 物理参考和 Gaussian 检查的边界

用保存的均值响应和 variance Gram 重新组成 R，并结合绑定的原 y 重算 f；
核对 variance 对角线等于原 variance 之和、R 对角线等于原软数据能量、
Hermitian/PSD 及最后一组 basis 响应的单位范数。没有构造 N1024 稠密算子。
保存的逐 basis 进度和计数分别为 16、32、2048，共 2096 次，另有 6 次均值响应；
与实际 operation observer 的 2102 次 Channel.apply 一致。

**原件保留的是全部 basis 的累加统计和最后一组 basis 响应，不是每次 basis 的完整输出。**
本轮验证保存统计的代数一致性、源码绑定和全部调用计数，没有声称独立重放全部物理 basis。
这是当前协议的保存粒度，未扩张成新仿真要求。

三项 Gaussian 检查独立核有限和 Fisher、2×2 逆及比率公式，N=8/16/1024 的保存比率为
0.3 / 0.2741935483870965 / 0.2503663898387885。
这是等权局部 Gaussian Fisher/MF 示例，不是实际 SP 后验方差测量。

## 计数、fixtures 与预算

逐 candidate 增量、case core/reference/gauge、PathMoments source 账本和物理账本
独立求和，**全部 70 个计数键**与 complete/summary 完全相同。
P=1 的零增量键在候选 delta 中省略、在总账中保留的语义也一致。

| 工作 | 实际完成 |
| --- | --- |
| PathMoments/source / 初始统计 / 坐标准备 | 51 / 6 / 9 |
| Schur candidate / canonical reference / gauge | 45 / 45 / 45 |
| 非空块 / 空块 / 候选向量求解 | 6 / 3 / 30 |
| 共享 Cholesky | 96 = 6 块 + 45 reference + 45 gauge |
| identity / matched RHS | 156 / 96，共 252 列 |
| 共享 / 候选三角调用 | 192 / 60，observer 共 252 |
| 解析导数 / 中心差分对 | 9 / 18 |
| basis / mean apply | 2096 / 6 |
| 直接 entropy / covariance slogdet | 90 / 90 |
| 实际 FFT / IFFT / eigvalsh | 2153 / 2213 / 51 |

诊断的 O(P³) 工作完整保留：45 次候选 residual（390 乘法项）、9 次 derivative trace
（51 项）、96 次共享 residual（792 项）、90 次 entropy Gram（510 项）和 270 次
gauge 矩阵乘法（1530 项）。这不支持把整个 evaluate 宣称为 O(PN+P²)。

三个指定旧 fixtures 各执行一次，tests_run=1、errors/failures 均空，运算账本与
counter events 求和一致。第三个 fixture 的 3 个 data steps、6 个 proposals、
3 个拒绝全部保留；逐项重算目标增量、equation (8) residual、接受目标衔接及保存
log 概率的归一化，均通过。前两个 fixture 没有保存其完整返回矩阵/系数轨迹，
其回归通过证据是绑定的 unittest 断言执行结果和组件计数；不冒称本轮重算了缺失轨迹。

| 资源 | 实际值 | 注册上限 |
| --- | --- | --- |
| recorder stage wall | 2.4498892871197313 秒 | 120 秒 |
| recorder stage CPU | 1.834418694 秒 | 120 秒 |
| callback wall / CPU | 2.3937406758777797 / 1.783398434 秒 | 包含在 stage 内 |
| 完整进程 wall / CPU | 5.35 / 4.75 秒 | wall 150 秒，退出宽限 10 秒 |
| 完整进程峰值 RSS | 444356 KiB = 455020544 bytes | 4 GiB |
| 回传 artifact 总量 | 4468187 bytes | 128 MiB |

进程 `exit.txt` 和 GNU time 的 exit status 都为 0。registration、runtime preload 和
actual_work 的 BLAS/OpenMP/Torch 线程绑定一致，均为 1，CUDA 隐藏。
preload 1.7711409209 秒；callback 前进程年龄约 2.65 秒，完整进程计时包含启动开销。
stage 输出大小与 attempt 的保存时点核对一致。新 observations、independent blocks、
receiver、decoder、完整 backend 均为 0，fixture 操作与数学主账分开。

## 结果文字与副本

核对 `results/afdm_sp_fractional_receiver_20261007/COLLAPSED_MATH.md`，审阅版本 SHA：
`ac520c8e527f7a74a5cfc47dd0597644e12f0fcf37cd4f48acce51d5aaadc881`。
其数字、工作量、资源和科学限定与原件一致；当时“独立原始审计进行中”可由主线程在
本报告交付后更新为完成。本代理没有修改该结果文字。
同目录 manifest、summary、contract、launch、resource 五个副本均与原件逐字节一致。

## Findings (fixed)

无原件或科学实现问题需要修复。本轮仅创建本报告。

## Findings (not fixed)

无阻塞。上述物理逐 basis 与前两个 fixture 的保存粒度限制已明确，不作为缺失数据
重新生成的理由。模型能力是否相等仍不可由当前工具元数据确认。

## Verification

- 原件完整性、身份、嵌套副本、计数、资源：PASS。
- 保存小矩阵、Schur、trace、gauge、导数及两层差分独立代数核验：PASS。
- Tests：冻结运行中的 3 个指定 fixtures PASS；本轮未重新执行生产 tests。
- Lint：沿用已审冻结源码的 Ruff PASS；本轮仅 Markdown，检查尾空白。
- TypeCheck：未执行，mypy/pyright 未安装；标准库原件审计不替代类型检查。
- Runtime：有已完成一次受限运行及原始证据；本轮没有新的科学运行或 SSH。
