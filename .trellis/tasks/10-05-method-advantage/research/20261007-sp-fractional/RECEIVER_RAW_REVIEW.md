# RECEIVER-DEV-01 独立原始结果审计

2026-10-07。**完整执行/计费记录通过；方法 development screening FAIL。**
24 次调用均留证，但只有 16 个完整接收输出；8 个 continuous 调用在首个 Doppler
坐标求积失败，误码未知。不能把这些失败调用的短耗时解释成性能或成本优势。

## 审计方法与完整性

只用 Python 标准库读取 JSON、ZIP/NPY 和原始 bytes；不导入生产 runner、NumPy
或科学核心。逐元素从保存 LLR 按 `<0` 判 1，核对保存 hard_bits，再与保存真值 bits
重计误码。未生成新观测，未运行 receiver/decoder、矩阵仿真或积分，未修改 raw。

- 回传 manifest SHA256：
  `41c7472d5358613294b39b00d592e3f05e30fa24ad8fe374e375fc64944a1fc8`。
  全部 172 文件的大小/SHA256/MD5 匹配，共 43,133,749 bytes；最大文件 4,106,313 bytes。
- 58 项注册源码与准入合同一致；59 个 source_snapshot（含合同）的索引/文件名/
  哈希逐个对应注册记录。源码原 commit 为 `78c41569`，执行 snapshot HEAD 为
  `559f41654e15b8103a788f5c003939576dd1da00`；两者未混称。控制文件与准入字节相同。
- attempt 内 160 项 artifact hash 全部通过；attempt 为 complete、退出 0，launcher
  退出亦为 0。实际计数为 4 blocks、8 观测、24 payload 调用、0 decoder。
- 8 个 observed archive 只有 y/pilot/sigma2；sigma2 符合 6/8 dB 原口径，每 block
  两 SNR 的 pilot bytes 一致、真值共用；component entropy 符合冻结 namespace。
  三个 arm 的 24 份 F1 获取均有正耗时及 8 次 bank scans，同观测槽位/增益 bytes 一致。
- 24 份 started、outcome、raw 和 seal 一一匹配，轮换顺序正确；raw hash 与评分前
  seal 一致，成功输出中的 LLR 均有限、长度 2048，重判 bits 与保存 bits 全部一致。
  源码绑定的阶段调用顺序及 seal 支持“接收后才读取 truth 评分”的数据流约束；
  原件没有系统调用级 truth-open 时间戳，本审查不声称完成该层 I/O 追踪。

## 误码与完整调用成本（独立重计）

每个完整输出 2048 bits；每 arm 共 16384 bits，每 SNR 8192 bits，独立 blocks 仅 4 个。

| arm | 完整输出 | 6 dB 错误 | 8 dB 错误 | 合计 | 完整 wall 中位 / 合计(s) | CPU 合计(s) | 原始输出保存 wall(s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| f1_scalar | 8/8 | 1043 | 712 | 1755 | 0.586388 / 4.687048 | 4.512280 | 0.392217 |
| vb_point | 8/8 | 1045 | 639 | 1684 | 1.628698 / 13.076639 | 12.713155 | 1.630839 |
| vb_continuous | 0/8 | unknown | unknown | unknown | 不适用；失败支出合计 4.976590 | 4.861484 | 0.192882 |

逐 block 的 `f1 / point` 错误数：

| block | 6 dB | 8 dB |
|---|---|---|
| 0 | 263 / 260 | 180 / 151 |
| 1 | 250 / 253 | 155 / 159 |
| 2 | 272 / 279 | 206 / 165 |
| 3 | 258 / 253 | 171 / 164 |

point 总错误少 71（约 4.05%），但 6 dB 多 2 个错误，完整中位 wall 为 F1 的
2.7775 倍；这不证明完整性能–成本优势，也不能替代 continuous 的未知结果。
原 scores/results 与上述重计完全一致，失败项保持 null，没有删失败或补零。

## 8 个连续调用失败

全部为 `CoreFailure: continuous integration did not agree by 1024 nodes`，发生于
sweep 0。trace 尚无成功 Doppler 项，counter 显示只开始 1 个坐标，因此按已绑定
保序循环可定位 slot 0。每次均为 8 个初始化积分 + 1 个坐标积分，共 9 integrals、
20 quadrature levels、4992 density nodes；1 次 gain 更新、0 次完成 Doppler、0 数据步。
失败坐标均完整保存 128→256→512→1024 四层与系数，最终比较如下：

| block / dB | 最后 Δphi bound | 最后 ΔlogZ | 最细层保留节点 |
|---|---:|---:|---:|
| 0 / 6 | 1.41698e-4 | 1.77663e-3 | 22 |
| 0 / 8 | 2.54365e-3 | 1.82303e-2 | 17 |
| 1 / 6 | 4.67998e-5 | 5.74014e-4 | 35 |
| 1 / 8 | 3.69623e-4 | 5.11699e-3 | 30 |
| 2 / 6 | 1.14352e-4 | 2.68009e-4 | 26 |
| 2 / 8 | 9.98765e-4 | 6.62451e-3 | 20 |
| 3 / 6 | 3.47718e-6 | 6.53013e-5 | 40 |
| 3 / 8 | 3.26380e-4 | 4.56311e-5 | 32 |

两项均未达到 1e-6；各层删质量界≤1e-14、矩扰动界≤2e-14，不能将失败归咎于
尾部删质量阈值超限。证据证明本次冻结积分方案未达到分辨率要求，尚不能判断
continuous 接收误码或不确定性机制是否有益。

## 总账与边界

stage wall 34.009053 s / CPU 33.253036 s；全进程 wall 36.86 s，user+system
CPU 36.08 s；峰值 RSS 605800 KiB = 620339200 bytes。有效 BLAS/OpenMP/Torch
均为 1，CUDA 隐藏，资源未超合同。生成/setup 合计 wall 4.493511 s；全部接收调用
（含失败）wall 22.740276 s / CPU 22.086919 s；其余约 6.775265 s 属阶段登记、
评分/校验及其它开销，未从完整 stage 总账中抹去。保存费用已包含在各调用 wall，
不得再次扣除或把失败中位 0.622339 s 当有效完整接收时延。

attempt SHA256：`7ff0816dba02ab25ed9e5753a2bdf3f764e25dc4cf858d12212487119a73fc4b`。
seal SHA256：`53b38cb6458bb01d983a27c6adeec7d2d0efb11644a34ee0421af6318ccf3d8a`。
原目录 `.mission/20261007-sp-fractional-trans/evidence-receiver-development/artifact`
保持只读；远端原尝试继续保留。此结论不授权自动重试或改变门槛。
