# QUAD-DIAG-01 保存 raw 独立审计

2026-10-07。**完整性、计费及固定诊断均 PASS。8 个保存势的原 1024 层回放与
8192 参考均在原 1e-6 精度内；原 512→1024 的不一致不能被解释为 1024 本身不够准。**
这支持本批 8 例的原相邻判定被较粗层差异拖累，但不是严格连续积分证书，
不撤销 RECEIVER-DEV-01 的真实失败，也不授权放宽判定或重跑接收机。

仅用 Python 标准库解析已有 JSON/ZIP/NPY 与已保存数组，重计 φ 向量差、
logZ 差、节点/概率基本不变量、摘要和计数。没有导入 NumPy/生产模块，没有
重新评估 Fourier f、求积、导数、接收机、生成观测、仿真或 SSH；未修改任何 raw。

## 原件与身份完整性

原件目录：
`.mission/20261007-sp-fractional-trans/evidence-quadrature/artifact/`。

- 独立核验完整 **174 文件、9,431,919 bytes** 的路径集合、大小、SHA256 和 MD5。
  archive SHA 与主线程交接一致。
- attempt complete、exit_code=0；完整进程 exit.txt 与 time 的 exit status 均为 0。
  attempt 中 **163 个 artifact hashes** 全部匹配，清单完整覆盖该 attempt 除自身外的文件。
- artifact 的合同、launcher、config、imports 与独立准入控制文件字节相同；
  运行 git HEAD 为准入的 snapshot `2be28b91458d9c41572450992cf776b3c9a6ebd5`。
- registration 绑定 **56 源码＋11 旧输入＋合同=68 项**。68 个 source_snapshot 的
  编号、basename 和字节哈希逐个对应；committed 项目源码集合为准入的 56 项。
- input_identity 的 11 原输入与合同完全一致。8 case 各自保存的原 coefficients、
  sigma2、原 levels 与已审 RECEIVER-DEV-01 raw 相等；身份、源 raw SHA 和路径一致。
- 每 case 的 started、4 个 level-started、4 个 level raw、case raw、complete.json
  与 summary 一一对应。case 内嵌各 level 与独立 level 文件的数组/元数据相同，
  附加 saved_sha256 准确。此为文件及源码绑定的数据流核对，不冒称系统调用级 I/O 追踪。
- 本轮没有失败文件或 partial case，8/8 completed；参考通过前也确实保存了
  2048、4096、8192 三层，没有提前跳过某层。

## 保存数值的独立重计

原 1024 回放的保留节点/删尾边界、centered/full logZ、常数、最大密度/节点质量、
保留面板质量、dropped log mass 均与原 raw **完全相同**，11 项/case 回放检查为真。
原失败 level 没有保存其 φ 向量，所以这里不冒称与原 φ 逐字节比较。

以下 max|Δφ| 从已保存的 1024 个 complex128 值逐项相减取模后重计；
logZ 差由已保存 centered logZ 相减得到。结果与 case/summary 相符。

| block | SNR dB | 1024↔8192 φ 最大绝对差 | 1024↔8192 logZ 绝对差 | 4096↔8192 φ 最大绝对差 | 4096↔8192 logZ 绝对差 |
|---|---:|---:|---:|---:|---:|
| 0 | 6 | 3.395084e-12 | 7.617018e-12 | 5.292516e-14 | 1.136868e-13 |
| 0 | 8 | 2.085835e-8 | 7.766448e-8 | 4.996460e-14 | 2.273737e-13 |
| 1 | 6 | 4.977474e-13 | 4.547474e-12 | 5.211918e-14 | 0.000000e+0 |
| 1 | 8 | 5.528137e-10 | 4.841013e-9 | 9.864911e-14 | 2.273737e-13 |
| 2 | 6 | 8.492103e-14 | 1.136868e-13 | 6.362840e-14 | 0.000000e+0 |
| 2 | 8 | 5.075403e-10 | 2.687102e-9 | 1.977670e-14 | 0.000000e+0 |
| 3 | 6 | 2.033626e-14 | 1.136868e-13 | 1.798596e-14 | 0.000000e+0 |
| 3 | 8 | 1.001296e-11 | 7.958079e-13 | 4.941840e-14 | 0.000000e+0 |

- 参考 4096↔8192 最大 φ 差 **9.864911034464998e-14**，最大 logZ 差
  **2.2737367544323206e-13**，全部满足两项 1e-9 门槛。
  Python 标准库 complex abs 与 raw 的 NumPy 值在个别结果末位相差 1 ulp，
  例如 raw 最大值为 9.864911034464997e-14，不影响核验或阈值。
- 原 1024↔8192 最大 φ 差 **2.085834920129394e-8**，最大 logZ 差
  **7.766448106849566e-8**，均出现在 block 0 / 8 dB，全部满足原 1e-6。
- 原保存的 512→1024 两项差异仍全部超过 1e-6；已核对它们与新 case 中引用值一致。
  原 512 的 logZ 可直接与新参考比较，也全部超原门槛。
  原 512 φ 向量没有保存在这些原层记录中，因此未声称直接重计 512↔8192 φ 差。
- 各 level 节点在 [-3,3] 内严格递增，原积分基础权重为正、总和约 6；
  保存的 φ₀≈1、|φ|≤1 和有限性符合原约束。
- 参考层未人工删尾。独立数清保存的概率数组中的零项，与已记指数下溢节点数一致，
  概率和在 1e-10 内为 1。8192 层零项为 611–7466 个，保存的离散遗漏 log 质量
  上界为 −739.039736… 至 −736.608596…；这些是离散数值下溢记录，不是连续尾证书。

## 峰值摘要

独立从保存的 8192 层 reduced_log_kernel 找到 argmax，核对其 index、节点位置
和最大 log density 与 case/summary 相同。下表标准差、f″ 和 B2 为保存的诊断值；
本轮没有重新计算导数、曲率界或积分矩。

| block | SNR dB | 最大采样密度节点 | 保存的离散标准差 | 保存 f″ | 保存 B2 |
|---|---:|---:|---:|---:|---:|
| 0 | 6 | 0.892722137 | 0.010555914 | -8986.219 | 17809.769 |
| 0 | 8 | 0.894360251 | 0.008326298 | -14436.081 | 27305.535 |
| 1 | 6 | 1.079038856 | 0.008171752 | -14986.830 | 25113.299 |
| 1 | 8 | 1.081860251 | 0.006506726 | -23630.901 | 38127.337 |
| 2 | 6 | 0.862091633 | 0.011014056 | -8254.928 | 17200.291 |
| 2 | 8 | 0.859890870 | 0.008693754 | -13242.110 | 26380.889 |
| 3 | 6 | 1.051840715 | 0.010983214 | -8301.611 | 17191.153 |
| 3 | 8 | 1.054116790 | 0.008785536 | -12967.271 | 26010.260 |

这些采样点的 f′ 并不为零（约 −6.5184 至 0.7880），不能称为精确驻点。
负的采样曲率也不证明全局单峰；离散标准差不是真实信道估计误差或 BER 证据。

## 计数与成本

独立加总 8 case 计数，核对每层 work_counts、case 完成计数及总 summary：

| 项目 | 实际值 |
|---|---:|
| case / levels started / completed / saved | 8 / 32 / 32 / 32 |
| NumPy 原规则 / SciPy 参考规则 | 8 / 24 |
| density nodes started / completed | 122880 / 122880 |
| phase entries started / completed | 125829120 / 125829120 |
| Fourier contraction terms | 125706240 |
| characteristic contraction terms | 117667840 |
| derivative probes started / completed | 8 / 8 |
| derivative phase / contraction terms | 8184 / 16368 |
| B2 bound terms | 8184 |

每 case 的 primitive record 为一次原 NumPy leggauss 的 eigvalsh、order=64。
新观测、独立 blocks、receiver、decoder、边界拒绝、有效 payload 和 backend fixture
在实际 guard 计数中全部为 0；preload 构造 LDPC/model 计数为 0。
registration、preload、actual_work 的 BLAS/OpenMP/Torch 有效线程均为 1，CUDA 隐藏。

| 成本口径 | 实际值 |
|---|---:|
| attempt stage wall / CPU | 6.091920980 s / 5.438884376 s |
| stdout 打印时 stage wall | 6.092301098 s |
| 8 case wall / CPU 合计 | 5.875759695 s / 5.225513978 s |
| 32 level wall 合计 | 4.204977117 s |
| 32 level 保存 wall 合计 | 0.706324477 s |
| preload wall | 1.890697684 s |
| 完整进程 wall / user+system CPU | 9.02 s / 8.37 s |
| 峰值 RSS | 675844 KiB = 692064256 bytes |

stdout 比 attempt 稍晚取时，不是计费冲突；各子项不是互不重叠的额外费用，
不能再次相加到全进程时间。stage/preload/其他保存与账本开销均未从总成本中删除。
内核 180 秒、全进程 210 秒、4 GiB 和 128 MiB 边界均未超限。

## 结论与限制

本次诊断更正的是失败原因的解释：对这 8 个已保存首坐标势，原 1024 规则已经
与较细参考足够一致，而原规定要求它与 512 层一致，因而仍会被正确按原合同拒绝。
“相邻两层不一致”不是“较细层误差等于该差异”。

参考仍是同一 Gauss–Legendre 家族的不同节点生成器/面板分辨率，没有区间证书；
没有证明其他坐标、其他输入或后续 sweeps 的积分同样准确。
新的可靠接受准则或代理/自适应规则仍须单独设计和绑定精度、预算与失败行为。
本诊断不产生 completed continuous receiver、BER、完整速度优势或自动重跑许可。

## 关键 SHA256

- artifact_manifest.json：
  `81940f9b0e7adcdd8b5220840d2b66187d24483e9e08aab8107c8cc1c3eadb36`
- artifact.tar.gz：
  `d3fcadeb30d07315c1590a61d5b5be042a9ad920e15053b3c0790258a2fe1fbe`
- attempt.json：
  `2f38ff886ba919dbae511a125121fc877d36f812fcce09b43a42d4af54079664`
- quadrature_summary.json：
  `7169e7884631b2bc44099d366cc8cac6f0105638e891e6b9b4da8b12875ca594`

验证：保存文件/身份/数组差异/计数/成本核对 PASS；无需修复 raw。
本轮仅证据审计，Lint/TypeCheck 不适用；未做任何新数值 tests 或生产运行。
