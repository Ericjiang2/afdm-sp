# QUAD-DIAG-01 独立准入

2026-10-07。复用已完成的 RECEIVER raw 审计与求积数学复核，仅检查保存势的
固定分辨率诊断。**源码与部署字节准入 PASS；按文末生效条件，仅准许冻结的
QUAD-DIAG-01 执行一次。** 本轮未导入生产模块、执行求积、调用接收机、SSH 或提交。

## 源码与数据流

- 审查文件：`experiments/afdm_sp_fractional_receiver_20261007/quadrature_diagnostic.py`。
  SHA256：`ef78858f7cf1f013c5b13943ed4082e55dfa6c0b2378b573c17073c1bd12767f`。
- 同时定点读取原 `continuous.py` 的 Fourier 势与求积公式、私有 `protocol.run`、
  `runtime.preload/observe_operations/save_new`、共享 recorder 和 evidence 加载器。
  未重跑 Trellis 生命周期或前次数学/raw 审计。
- `--print-imports` / `--print-config` 在 preload 后返回；数值回调只由私有
  `protocol.run` 进入，要求 Linux、`/data/guoyikun/` 根、engineering 合同、
  完全相等的 config/source 清单及已提交源码。preload 不构造系统、模型或 LDPC。
- 固定原 attempt 根为
  `/data/guoyikun/afdm_sp_receiver_20261007_dev01_78c41569/artifact/execution/RECEIVER-DEV-01`。
  输入集合恰为 attempt、registration、receiver_seal 与 8 个 continuous raw。
  原路径替换被拒绝，合同哈希在加载数组前检查；旧 attempt 的 artifact 哈希和
  seal 的 raw 哈希再交叉核对。原文件只有读取操作。
- 逐 raw 核验 receiver 身份、block/SNR/arm、numerical_failure/CoreFailure、
  sweep 0 首个 Doppler 坐标、Fourier 类型及 128/256/512/1024 已完成层。
  从确切嵌套路径取出原 coefficients/sigma2，不重算获取、增益、物理信道或数据更新。
  新源码验证 N=1024、有限系数、正有限 sigma2，并把系数副本设为只读。

## 固定规则、门槛与计数

- 原细层回放为 NumPy `leggauss(64)` × 16 等宽面板，支持 [-3,3]；
  Fourier 符号、去常数项、uniform 基密度、logsumexp 和 1e-14 离散删尾
  与原实现一致。保存的 logZ、常数、峰值、保留节点/面板质量及删尾信息用于回放核对。
  原失败层没有保存 phi 向量，因此这里准确称为回放元数据一致，不冒称逐项原 phi 校验。
- SciPy `roots_legendre(64)` × 32/64/128 面板的 2048、4096、8192 三层
  由固定循环全部执行，参考提前一致不会提前退出。没有自适应追加层或跨 case 缓存。
  两种节点生成器独立，均属于 Gauss–Legendre 家族；这不是严格连续积分证书。
- 参考不人为删尾；指数下溢节点及其离散 log 质量上界被记录。
  4096→8192 的 max|Δphi| 与 |ΔlogZ| 必须同时 ≤1e-9。
  回放元数据一致且参考通过时，才分别按原 1e-6 判断原 1024 的 phi/logZ；
  否则为 unknown，不把未通过参考用于准确性结论，也不改变 DEV-01 的失败状态。
- 每 case 固定 1024+2048+4096+8192=15360 个密度节点、1 次采样峰导数探测；
  8 case 合计 122880 个密度节点和 8 次导数探测。phase、Fourier/特征函数
  累加、规则生成、完成/开始计数及保存时间均有记录。完成分支要求全部配额恰好完成。
- 导数探测只在最细层采样最大 log density 节点执行；f′、f″ 与 B2 公式对应
  保存的 Fourier 势。没有优化器寻找新峰，也没有新增观测或有效 backend。
- 源码无 receive、decoder、系统生成或随机样本调用；配置和 guard 的新观测、
  独立 blocks、receiver、decoder、边界拒绝、有效 payload、backend fixture 均为 0。
  所得数据只能解释这 8 个保存势的分辨率，不产生 BER、接收时延或方法收益证据。

## 异常、部分证据与资源边界

- case 与各层先保存 started，层完成后保存节点、权重/log masses、phi、logZ；
  算术错误保存已有层、当前 partial 和累计计数，标为 arithmetic_failure。
  程序/资源错误进入 fatal 并继续抛出，不把失败 case 伪装成完成或重新计算。
- 输出 I/O 错误直接抛出；MemoryError、TimeoutError 和程序错误保留原类。
  **既有输入加载器的边界例外**：`evidence.load_artifact` 将读取 OSError 包为
  ValueError 并保留原始 cause；新诊断仍将它归为 fatal 并抛出。主线程已据本次
  发现修订协议并经定点复核，明确该语义；没有修改 frozen loader。
- 最外 recorder 使用独占 attempt 目录，保留 invalid_partial 与非零退出；
  per-case 算术失败可完成整体计费，但 `diagnostic_complete` 为 false。
  completed 只表示诊断运算完成，reference 不一致仍须报告 unknown。
- 源码复用 engineering 180 秒内核 wall 上限和合同 CPU/RSS/输出限制；
  1 CPU、CUDA 隐藏、RSS≤4 GiB、输出≤128 MiB。完整进程 210 秒及 10 秒
  退出宽限由下述最终 launcher 绑定，已完成静态字节核对。

## 固定输入 SHA256

以下哈希由本地原证据重新读取；同时用标准库 JSON/ZIP/NPY header 解析核对
8 份 metadata 身份、异常层路径及 1024 complex128 系数头/字节长度。
没有执行数组运算或积分。此前完整 raw 审计结论继续有效。

| 原 attempt 内路径 | SHA256 |
|---|---|
| `attempt.json` | `7ff0816dba02ab25ed9e5753a2bdf3f764e25dc4cf858d12212487119a73fc4b` |
| `registration.json` | `b1c6485a9eff598418e54d4afb6b5ad262bf8b78f861389fab9b84fb016d6fc3` |
| `receiver_seal.json` | `53b38cb6458bb01d983a27c6adeec7d2d0efb11644a34ee0421af6318ccf3d8a` |
| `calls/b0_snr6_vb_continuous.npz` | `f6f5ca04bc8e68e76ca58f4426119499c5e5a9639aa21fd0411cc2b1901c64be` |
| `calls/b0_snr8_vb_continuous.npz` | `419044760a084197b04e39d015b8a9c4b55d78f4be667a664107251f2e7f1e13` |
| `calls/b1_snr6_vb_continuous.npz` | `d5a51633f643443e53ca2104ea116b561cf339ca8e6a94d8125c0a97befc5cb9` |
| `calls/b1_snr8_vb_continuous.npz` | `cf7e2bb9fa49e7d893426f579ec579be28d26c87ffada15e1c8e1a58b227208a` |
| `calls/b2_snr6_vb_continuous.npz` | `a0c8fefabcacb16878f30a935b53d33eab21900c235f8c357254c828c845e8a4` |
| `calls/b2_snr8_vb_continuous.npz` | `4fe58515f3d8e1aff95ee1f61b5c37f1987720c117a6919f18b5d2218513548d` |
| `calls/b3_snr6_vb_continuous.npz` | `1210476afba3c98c43e84ade2c3f17a7e8c3da37584c40d86bf6f449bc579387` |
| `calls/b3_snr8_vb_continuous.npz` | `3cc28b3a9dea2ce6e16cc524ae000ead21599ba150f2529eba2e0df8c07094bf` |

## 验证与后续窄核

- Lint：新文件独立 `ruff check` PASS。
- 静态语法：标准库 AST 与内存 `compile` PASS，未执行生成的代码。
- TypeCheck：未执行；AST/compile 不称为类型检查。
- 数值 tests / smoke / SSH：依派工禁止执行。源码静态审查不替代运行验证。
- 未发现算法、样本、预算或错误分类的准入阻塞。协议读取异常措辞已澄清。
- 以下补核仅涉及部署字节与运行边界，没有重做公式审查或新增接收机运行授权。

## 最终部署字节窄核

- 原源码 commit：`86e7cbcad6620488a48440670c9463a30d7dda4c`。
- 独立 snapshot commit：`2be28b91458d9c41572450992cf776b3c9a6ebd5`。
- archive：`.mission/20261007-sp-fractional-trans/dispatch/quad-source-86e7cbca.tar.gz`。
  SHA256：`aebf611be1279e8cf9eb4cf28f5757e230ef31cc2d3a1c42645f7374653afe00`。
- 逐一核验归档中的 59 个候选源码与原 commit、snapshot Git tree/blob、当前源码
  和 manifest 哈希相同；隔离 snapshot 的 HEAD 正是上述 snapshot commit。
  tar 共 265 个成员，仅 `source/` 下普通文件/目录，无重名、绝对/上跳路径、
  软硬链接、特殊文件或 setuid/setgid；无 Git alternates、无额外非 Git 载荷。
- 本入口实际 inventory 为 **56 源码**，与合同中的相对源码路径集合完全一致；
  加上表中 **11 个固定输入**，合同共 **67 个 SHA256**，均与本地原件匹配。
  归档另外包含旧数学模块 `afdm_sp_fractional_20261007/{protocol,thread_binding,verify}.py`
  三个候选文件，本入口未导入，因此不将 59 冒称实际运行 source 数量。
- 回传 `remote-config.json` 与合同 config 完全相等；`remote-imports.json` 为上述
  56 项；部署 stdout 记录 archive OK 和正确 snapshot HEAD，stderr 为空。
  预检回执记录 67 个 source/input 已检查、BLAS/OpenMP/Torch 全部 1 线程、
  new_numerical_work=0。这些是已读取的远端预检回执，本代理没有自行 SSH。
- 合同 stage/kind、原输入根、全部零调用、122880+8 配额与本报告一致。
  内核 wall/CPU 各 180 秒，完整进程 timeout 210 秒、TERM 后 10 秒 KILL，
  RSS 4 GiB、输出 128 MiB；launcher `bash -n` PASS，保留 PID/start/end/exit、
  stdout 和 `/usr/bin/time -v` 完整进程成本，以独占 mkdir 阻止过程目录覆盖。

控制文件位于 `.mission/20261007-sp-fractional-trans/control-quadrature/`：

| 文件 | SHA256 |
|---|---|
| `source_manifest.json` | `b619bb6d9bb79ff9d20e5276091b36d8b70d2631515426fd63e6b57207988c5d` |
| `run_contract.json` | `a47975ba401ca444ce361488856eb3c40d660685b7525fd2ac8b9b37baa8a92b` |
| `launch.sh` | `59f0c52b8d35ca1a0efe8db39b04dc059a53f6b3f2ab755a6ddcb9ff7f39c48d` |
| `remote-imports.json` | `d496814ae7194739aa1a351905aac7a3e3a0cb2d4ad158c64d1a89b42ea3c910` |
| `remote-config.json` | `427472166adf45b2d6f6279e03260e15e69ea8bb72f39291135ee5c55baef74b` |
| `thread-source-preflight.json` | `9b7be90d9bfb3632f0b6e303164ff9bcf62c38269982db0047af5c39246ece7e` |

## 一次 GO 的生效条件

主线程在唯一目标根
`/data/guoyikun/afdm_sp_quadrature_20261007_diag01_86e7cbca`
最后确认上述合同/launcher/源码及 11 原输入字节未变、即时资源与有效单线程/CUDA
约束仍满足，且 `artifact/process-QUAD-DIAG-01` 与 `artifact/execution/QUAD-DIAG-01`
尚不存在后，在已初始化 conda 的同一 shell 中用 AFDM 环境执行冻结 launcher **一次**。
该阶段只诊断 8 个保存的势，不是接收机/仿真重跑。

任一失败、预算超限、参考不一致或 replay mismatch 均保留首轮原始证据；
不自动重试、追加层、改容差或改输入。参考通过也只形成分辨率诊断，不能据此
撤销原 DEV-01 的失败或宣称 continuous BER、速度优势、严格积分误差认证。
