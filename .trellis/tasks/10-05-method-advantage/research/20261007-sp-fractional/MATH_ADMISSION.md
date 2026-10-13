# MATH-01 独立静态准入

日期：2026-10-07。任务：`.trellis/tasks/10-05-method-advantage`；CSV：`.mission/20261007-sp-fractional-trans/20261007-sp-fractional-trans.csv`。仅准入指定的确定性数学核验，不选择接收机、不授权新增性能实验，不关闭完整目标。

独立性 medium；runtime 模型标识未暴露。只读审查源码、静态编译/lint、Git/tar/hash；没有导入执行被审模块，没有运行数值测试、RNG、求积、仿真或 SSH。源码由实现代理负责，本代理只写本报告和 `CONTINUOUS_REVIEW.md`。

## 判定

**静态数学与源码：PASS。已绑定单次 MATH-01：静态执行 GO。数值结果：NOT RUN。**

实际 CPP 约定、S 的共轭索引、期望 quadratic、gain Gram/matched vector、expected-Gram matvec/diagonal 和连续坐标 score 均与已审公式一致。N1024 独立参考覆盖完整有限因子法则，未发现数学实现错误。启动器的重复启动日志覆盖问题已由主线程修复并经补审通过。

## Findings (fixed)

被审科学源码无需本代理修复；没有越权修改代码。连续理论的两处边界修订见 `CONTINUOUS_REVIEW.md`。

- File：`control/launch-math01.sh`。Issue：旧版 `process-start/resource/exit/end` 会在 recorder 拒绝既有 stage 之前覆盖旧的完整进程证据。Fix：主线程已改为先原子创建固定 `artifact/process-MATH-01` 新目录，不使用 `mkdir -p`；目录存在即失败，随后才将 stdout/pid/start/resource/exit/end 写入独占目录。独立静态顺序核查与 `bash -n` 通过。主线程另保存 `launcher-check.json`，声明原版 sentinel 覆盖复现和修复版 local-prefix fixture 通过；本代理未重复执行该 fixture，也未执行科学段。

## Findings (not fixed)

无剩余静态准入阻塞。数值阈值尚未执行，不能报告 runtime PASS。连续推断器、真实先验适配、FER/完整成本及创新性不在本次准入范围。

## 源与协议绑定

- 原项目 source commit：`c639a4b0e7b46058175a138be06863aa2657448b`。
- 隔离 snapshot commit：`ad3b3fa2d0d301e6e4267b51286206db26bb748c`；这是独立 snapshot 提交，不伪装成原 source commit。
- `MATH_PROTOCOL.md` SHA256：`e3d0f4f7ab698d85c98acbb3f653b8f934d9b45986297505deddebdccb1c5303`。
- `control/run_contract.json` SHA256：`500424a41553e438073ab1ca94329c568a2b7ed25337bc90312eede217d2125a`。
- `control/source_manifest.json` SHA256：`dd6ce853aa235a06b06e6f020c5e80c3579db3e3a14e71b84261410729304c98`。
- `control/launch-math01.sh` SHA256：`5d5a8089076d67220a41fad636cd8e5e3d192b1a183dc7b5be369989a4ad9bcc`；launcher 在 tar 之外单独绑定，远端也须核对该 hash。
- `dispatch/source-c639a4b0.tar.gz`：62364 bytes；SHA256 `ea895bd5d2efb1aac137469d6ee5b017062b9e575038762638d156f80bc2d9a1`。

独立逐个比对了 manifest 中的 15 个 Python 文件：本地 bytes、原 source commit 的 Git blob、tar 内文件 SHA256 均一致。另解读 tar 内 Git object/tree，snapshot 无 parent history，其完整 tracked tree 恰为这 15 个文件，hash 全部一致。tar 无符号链接、硬链接、绝对成员路径或 `..` 路径穿越，无 `.trellis`、STATE 或 research-assets；两个部署 control JSON 与本地 bytes 一致。

已审新 package 的源 hash：

| 文件 | SHA256 |
|---|---|
| `__init__.py` | `fc11005dc5462e09f23ea0cdcbf402dfc2123f518cbfe124e98181a073af378c` |
| `moments.py` | `65e02ebf5d2798a3a6888d906803f2318662fe0e71a695122bf691f02029d372` |
| `verify.py` | `3c391e8e6f83c71b931f1be84dd91629a22027b923fff9490dbe45265ca8b778` |
| `protocol.py` | `a9a6f40f355cb45b18df85a2e05fd4c81b3e5f906fb0bf3c76f156f99c0e078b` |
| `thread_binding.py` | `a39ce3abd4334c5b237419a78710e476fccd9a9b0a7264d1741cb8dfbf4e3689` |
| `test_moments.py` | `1c36482b8290f07e1b78374b5f913237fedabfa42199cff5cb99957180efa82c` |

其余 manifest 源包含真实 `physical.py`、既有 coherent/phase/efficient/higher-order recorder、thread binding 和 immutable dump helper。定向读过实际调用链，不把静态 AST inventory 自动当作最终 runtime inventory；主线程还须在远端 `--print-imports` 后核对集合与这 15 源一致。

## 数学实现核对

`PathMoments._cross_source` 使用 `FFT(v)[l_i-l_j]/N` 及真实 CPP 相位，保留 mean product 和非均匀 AF 方差项。`expected_quadratic`、`coordinate_coefficients` 的输出交叉项使用 S_ij；`gain_statistics` 使用 R_ji；`gram_matvec`、`gram_diagonal` 使用 S_ji。`np.roll(term,-l_i)` 实现 Pi_i 的伴随，方向正确。

自路径 energy 直接使用 `tr(S)*E||x||²` 或 `tr(S) I`，没有错误乘 `|phi_i|²`。Gram diagonal 的 FFT bin 为 `l_j-l_i`，xi 中 `2Nc1 Delta t_n` 的指数与式 (19) 相符。fixed complex off-diagonal gain covariance 在 structured 与 reference 两侧都保留，没有 diagonalize、强制 real 或暗中投影。

gain covariance 按 Hermitian/PSD roundoff 检查，数据方差检查非负，nodes/weights 检查有限实数、严格正概率及归一化；无静默重归一化。可接受 roundoff 的 real result 不通过 clipping 掩盖负值。测试文件覆盖 covariance 拷贝/复交叉项、invalid covariance/variance/weights、model ownership、noise variance 与 prior support；本次只审代码，不执行这些数值测试。

固定 q 的 finite Doppler nodes 是准确声明的诊断分布，不冒称 production prior 或连续后验求积已收敛。`coordinate_log_density` 只给传入节点上的未归一化 potential，不引入新 prior、不保证积分精度。源中的 AF QPSK 概率产生 mean/variance；未在时域另建独立 QPSK，也未将有限字母表二阶矩冒称完整 Gaussian likelihood。

## 独立参考完整性

三组源内固定几何严格匹配协议：`(8,[0,3])`、`(16,[1,15])`、`(1024,[0,9])`，非整数 `2Nc1=5.3` 与非平凡 c2 保留真实 CPP 检查价值。每条路径三个原节点，九个联合组合全部枚举，权重为两路径概率乘积。

N8/N16：以实际 `Channel.apply(e_k)` 逐列生成独立 dense unit operators，使用真实 unit matrices 的 conjugate products/Gram，与 structured 运算比较。七个条件节点与三个原节点取 union；两条路径各七个 conditional score，每次枚举另一条路径三点，共 **42 次条件期望**，比较时每条 score curve 只减同一个 additive constant。

N1024：逐列 k 流式应用 2 paths × 10 union nodes，只保留该列的 2×10×N responses。累计每节点的 source-variance self trace、全部 node-pair cross trace、九组合的 N 个 diagonal；没有省略 complex covariance 或非均匀 v。conditional scores 继续使用完整 42 次条件期望。原九组合的 Gram matvec 使用实际 mean-channel `apply/adjoint`，再加全部 C_ji 的 unit-channel cross action，独立于 structured FFT(v)/xi 公式。

N1024 不分配 dense unit matrices、dense Gram 或 covariance，只有 N×常数的响应/diagonal/score 数组和 P/Q 维小矩阵；实际 `Channel.apply/adjoint/derivative` 内部也是 FFT+path action。参考路径故意逐 N 列核验，时间可为 O(N² log N)，不能把它算作新方法本身的 O(N log N+NP²) 速度。

负控制使用同一个 uncertain offset 的 exact isotropic covariance，对照错误的 independent-copy 平均算子与 random tangent。N1024 tangent adjoint 为 `U^H A(-iT)A^H`，然后同一个 delta 用于左右两侧，符号正确。检查 loss/inflation 非零并与解析 action/trace 匹配；这些是已知错误模型的诊断，不是竞品接收机。

reference 的 action/adjoint/derivative、basis columns、dense allocation 和 transform counts 有记录；structured 的 DAFT/FFT 有独立计数。三次 auxiliary control DAFT 另计，未遗漏。小 N 的 full Gram PSD 与大 N 的有限 probe 检查范围不同；N1024 不以几个 probes 宣称证明所有输入上的数值等价，普遍恒等式来自独立代数审查。

## 0 observation 与 immutable recorder

`new_observations=0` 的准确含义是 **没有新增随机或按物理信道生成的观测 realization**。每个几何仍有一个源内解析 y test vector、固定 QPSK 概率、pilot 和 probe；还执行大量 basis actions。它们是三个 deterministic geometry probes 的内部数学核验，不能写成“没有生成任何数值输入”，也不能转用作随机 BER/FER 证据。

新 protocol 通过私有模块实例复用既有 recorder，没有更改共享 module 全局配置。全项目 Python 必须与执行 snapshot HEAD bytes 一致；15 源、contract 和 thread binding 在 registration/source snapshot 中 hash 绑定，并在完成时再查源 hash 与实际 BLAS binding。stage 目录及 JSON 用 exclusive create，任务锁/预算账本拒绝并发或重复 stage；失败消耗完整 reservation，不可静默重试。

每 case 在数值工作前保存 started marker 和 inputs.npz；完成的全部 arrays、checks、数组 hash、文件 hash 逐 case 落盘。数学 failed check 不筛掉：全部 case/control 完成后统一抛错，recorder 写 invalid_partial 并保存已有 artifacts。若执行中断，则只能声称完成到已保存边界，不能把未完成的 case 当通过。

## 单 stage 资源与执行边界

部署根：`/data/guoyikun/afdm_sp_fractional_20261007_math01_c639a4b0`；源码 `/source`，artifacts `/artifact`。入口固定 `python -m experiments.afdm_sp_fractional_20261007.verify --artifact-root <该artifact绝对路径> --stage MATH-01`。

合同为一次 180 秒 scientific stage、累计 reservation 180 秒、3 geometry probes、0 new observations、0 receiver/decoder calls、one CPU thread、CUDA 隐藏、whole-process peak RSS ≤1 GiB、execution output ≤16 MiB。新 protocol 硬编码该科学 wall cap 和计数；余下预算由绑定 run_contract 检查。超限或未完成必须保留 invalid attempt，不调整阈值后续跑。

launcher 通过 login shell 激活 AFDM，设置各线程变量、CUDA 空、禁写 pycache，并将 temp/cache/MPL paths 指向该远程根。运行前须建立这些目录并核对 tar/launcher/control hashes、实际 import inventory 与只读资源预检。资源预检本代理未执行；主线程报告服务器 Python3.10.20/AFDM 与可用资源，不能代替运行后的环境记录。

内部 recorder 的 180 秒计时从其 run 入口开始，包含其注册、快照和数学 calculation；前置解释器导入及外层 admission 不全部包含在内。外层 timeout 210 秒另留这些开销，并在 TERM 后最多 10 秒强停。`/usr/bin/time -v` 保存完整进程 wall/CPU/RSS，不能把内部 kernel/stage 时间表述成完整进程耗时。peak RSS 是全进程 high-water，预算检查不是代码已获 runtime PASS 的证据。

N8/N16 的 normalized threshold 固定 1e-10，N1024 固定 1e-9，Hermitian/PSD roundoff 固定 1e-10×max(1,norm)。本报告不改变这些阈值、几何或资源上限，不授权第二次 stage。

## Verification

- 静态数学：PASS，实际 CPP 与 gain conjugation 核对完成。
- Lint：`ruff check --no-cache experiments/afdm_sp_fractional_20261007` PASS。
- 静态语法：六个文件 `ast.parse` 和 `compile(source, ..., 'exec')` PASS，未 import/exec 目标源码。
- TypeCheck：未运行独立类型分析器；静态 compile 不冒称类型检查。
- 数值 Tests / SSH：NOT RUN。本次静态准入与实际 identity thresholds PASS 必须分别记录。
- 源绑定：15 源原 commit/snapshot tree/tar 字节与 manifest PASS。
- 启动器：修复后 shell syntax/hash/原子目录顺序 PASS；只准一个已绑定 stage，任何失败必须保留并重新准入后才可再运行。
- 文档：报告空白、版本 hash 及必需章节检查；只写授权两份 review，没有改源码/CSV/STATE/已有结果。
