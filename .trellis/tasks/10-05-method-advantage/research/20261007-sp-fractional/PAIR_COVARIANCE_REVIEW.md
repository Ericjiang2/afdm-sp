# PAIR-COVARIANCE-MATH-01 核心与协议审查

结论：**PASS（已修复首轮发现后的静态核心/协议审查）**。没有开放阻断项。尚未审阅主会话正在编写的 diagnostic runner，尚未执行数值阶段；本报告不证明运行结果、BER 收益或完整成本通过。

- 审查时间：2026-10-08T03:29:44.637335+00:00
- 审查会话：`/root/trajectory_identity_review_live`，实际 model/reasoning metadata 不可核验，不声称指定模型或跨模型审查。
- `PAIR_COVARIANCE_PROTOCOL.md` SHA-256：`8fb50097c03b04545a707c66d25ce374289aa192670b25c603bf5ad6ba85bc0c`
- `experiments/afdm_sp_fractional_20261007/moments.py` SHA-256：`32fc0319ba543cdfa554925c16d07daaee9e39e6e1e78051847a69cc081d6c61`
- 范围：读取本次未提交 diff、相关源码及协议；复用已审 FFT/概率推导。只有本报告落盘，没有生产 import、数值执行、SSH 或其他文件修改。

## 发现与闭合

**PC-01：零方差支持不变量不能由 determinant roundoff 代替，已闭合。** 初版仅检查归一化 determinant。`v_u=0,v_v=1,c_uv=1e−6` 或 `1e−6j` 时，归一化平方为 1e−12，小于 ROUNDOFF=1e−10，错误地通过；但零方差坐标的 cross covariance 必须精确为零，也无法按协议的 sparse Cholesky 零分支表示。该反例由代数和代码路径核对得出，未运行数值。

已读回 `moments.py:229–233` 的修复：left/right 任一精确为零时，先要求对应 covariance 精确等于零，然后才检查正方差块的尺度化 determinant。输入未被 clip、投影或替换。主会话已声明把上述实/虚小非零 c 纳入 runner 固定拒绝控制；控制代码与实际执行仍待后续审查。

## 核心实现

1. **默认路径保持同一数学表达式。** 原 mean、inverse DAFT、source responses、variance FFT、energy 计算仍按原顺序执行。未给 pairs 与合法 `(0,2)/(0,)` 空数组都走原 diagonal `_cross_source`，不建 pair IFFT。`_delay_phase` 抽出的表达式与原式相同；默认计数不触发新 pair/query 字段。改为 bytes-backed 存储会增加拷贝或改变内存所有权，不能宣称墙钟成本不变。实际输出字节相等是已注册数值检查，本报告只有静态等价证据。

2. **输入边界与不可变状态。** `_index_pairs` 保留输入元素类型检查，拒绝 float、bool、complex、自环/共享端点/越界等不合法 covariance pairs；query 只检查整数 `(Q,2)` 与范围，因此允许重复、反向和对角。反向 covariance pair 交换索引并共轭 c，方向正确。正方差 PSD 检查以两方差及 c 的实/虚绝对分量最大值缩放，避免直接相乘的极值风险；全零块把计算尺度设 1 只改变检查分母，不修改输入。`_immutable_array` 对 numeric storage 独立复制并由 immutable bytes 支撑，使 ndarray 的写标志不能重新开启；caller 后续修改原输入不能改变内部状态。

3. **owner 与缓存。** SourceMoments 仍由 prepare_source 构造；相关包没有其他直接构造调用需要旧参数签名兼容。`_source` 要求精确 owner，并检查 geometry/characteristic state 身份。source 消费者、Gram operators/query、原 GainColumnMoments.evaluate 都连到该验证，几何/φ 属性替换不能静默使用旧 kernels。W/K cache 在 SourceMoments 上，Z cache 在 PathMoments 上，依赖层次正确；新 source covariance 不需重建同 owner 的 Z，但不能跨 owner 复用 source。缓存存储自身也为 bytes-backed；反向 source 返回的是共轭值，不改 canonical cache。

4. **W 与 K 的方向和常数。** `_symbol_pair_phase` 用原始 u/v 的平方及 delay 项，取共轭后即为 W 的指数。正向 `c_uv` 累加到 `(u−v)%N`，反向 `conj(c_uv)` 到 `(v−u)%N`。稀疏 correction 仅用一次默认 IFFT；diagonal 项已在 variance_fft 中除过 N，所以两者在同一尺度相加，再乘 α。i>j 从 canonical i<j cache 共轭恢复；i==j 的时变 K 正常计算，同路径统计中的积分仍由 energy 提供。gain Gram、expected quadratic、conditional coefficients 与 gain-column 都使用同一 `_cross_source`，没有并行第二套 covariance 业务逻辑。

5. **Z 与有限 G 查询。** Z 的输入是 `conj(phi_i)*phi_j*conj(alpha_ij)`，一次 FFT 后除 N。正向 gain 权重 S_ji，反向 S_ij，且 `Z_ji[k]=conj(Z_ij[−k])`，代码符合已审推导。同路径仅加入 `tr(S)*delta_uv`，避免在随机 Doppler 下错误乘 `|phi_i|²`。空的合法 `(0,2)` query 返回空向量，发生在建 kernel 前；重复/反向保留原输出次序。cache replay 不新增 Z FFT。代码不枚举 symbol candidates，不构造 N² covariance、Cholesky 或 Gram。

6. **计数与成本范围。** lazy source pair IFFT、pair entries、query FFT、query entries/cross terms、cache hits 有独立计数；统计的全程墙钟、CPU、RSS、保存由 runner/protocol 负责。实现的 retained caches 达 O(P²N)，它没有实现理论可选的 streaming scratch 路线，不能报告为实际 O(N+K) 总缓存。现 API 的 Q 为调用者给定有限查询数，不解决 N² 候选扫描。

## 协议与独立参考

- **7×3=21 cases** 覆盖原 diagonal、复 covariance、rank-one/零方差退化、point Doppler、P1、相同 delay 和整数 chirp；原 2Nc1=5.3 与 5 构成明确对照。pair 索引在最小 N8 下也不相交；三个 rho 的模均小于 1。boundary fixture 已声明为通用 PSD 矩测试，不虚称来自保留原 mean 的 QPSK posterior。
- **5×3=15 source references** 成立：source 的 T_l U kernel 与 gain/ν 无关，所以 point/P1 可只复用独立 reference 的原 geometry 列，不能据此复用生产 owner。实际 physical.Channel(ν=0) 后 inverse DAFT 给出 T_l U，参考不调用待测 W/IFFT 分组。
- N1024 sparse Cholesky 的一列 `[sqrt(v_u),conj(c_uv)/sqrt(v_u)]` 产生正确的 C_uv=c_uv；退化分支需按协议显式处理。所有本文固定 complex blocks 严格 PSD，boundary 中 `.25` 及平方根 `.5` 让 rank-one 余项恰为零。没有必要用 tolerance clip 余项；若其他合法但容差接受的输入不能得到精确 PSD factor，应显式区分边界控制与 reference fixture，不能伪造成功参考。
- 十二个 query 在各 N 恰涉及八个 distinct basis indices，含对角、正反、重复及 wrap。每 case 12 项，**21×12=252**；cache replay 另外 252。N8/N16 完整小 G 与 N1024 仅查询涉及列的路径一致。
- **840 残差评估额度可复算。** 每 N 有五个双路径三点 case，各有 9 个完整 node combinations 和 `2×7×3=42` 个 conditional combinations；point case 为 `1+2×7=15`；P1 case 为 `3+7=10`。故每 N 为 `5×51+15+10=280`，三尺寸合计 840。不能把 840 误记成全部工作，physical basis/source/query/控制/保存另计。
- 源 MATH-01 的 source responses、variance FFT、coefficients、structured R/f/quadratic/operators/conditional scores 在原 `verify.py` 的保存数组中确有对应字段。protocol 只读旧十文件，明确 Pd=.55 与 receiver Pd=.5 分开；不调用 fixed_inputs 重造，也不重跑旧阶段。
- 原三点独立 Doppler 已足以暴露 same-path ψ_ii 与 independent-copy `|phi_i|²` 的区别；本文没有声称新增的七 cases 包含连续 uniform ν。若后续 summary 提及 uniform-law 覆盖，应对应既定额外控制的实际证据，不能只凭现 case 名称表述。

## 仍待交付的证据

下一步只审新 diagnostic runner 是否精确落实上述固定参考、控制和账本，然后按最终 source/contract 完成既定一次数值资格检查。本次未运行任何数学 case，未亲自重复 AST/compile/Ruff；实现代理提供的静态检查 PASS 不被写作运行结果。没有要求额外接收机实验、BER 实验或新审查生命周期。


## Dispatch 窄审（2026-10-08T03:36:34.267548+00:00）

结论：**PASS（四个部署脚本的静态审查）**。没有执行这四个文件、SSH、scp、import-only 或科学阶段。runner 的 print 分支与完整数值账本尚未审阅；不把本节理解为已经通过真实远端字节准入。

本节是**独立于前述 core/protocol 的 SHA 集合**，均位于 `.mission/20261007-sp-fractional-trans/dispatch/`：

- `build-pair-covariance.py`：`672dbb8d22ff6c80ba768b41ca25f4b9581f9d7b015ba036ac72737689c5c661`
- `prepare-pair-covariance.py`：`5675d5e7468bd57e1b3059c1811b4bddc8c2a595e40edcf819ad64664388a068`
- `preflight-pair-covariance.py`：`071ff1fd19dab3453732cb4015a7b4e58e78080b81a44a6d9c51ab4800125c81`
- `harvest-pair-covariance.py`：`eb643300ad5fe3d9a291d2d980534bec0564339369bec1dba84166b9e8739264`

- **源码冻结。** build 使用指定 commit 的 Git 对象，取旧 manifest 的源码路径与当前 commit 内 receiver package 的直接 Python children 并集，要求新 runner 已提交。读取文件时仍按指定 commit 的完整 vault prefix，源码 snapshot 自有 Git，归档及目标目录独占创建。实际只读检查确认旧 whitelist 是 68 个路径；最终约 70 个文件仍以构建时确定的集合和 import inventory 相等为准。没有把工作区未提交文件或 Trellis/STATE/research-assets 加入包。
- **旧输入。** 十个 input path/hash 来自原已封口 collapsed-math manifest，不上传或重造它们。本次独立读取该 JSON，确认恰为同一 MATH-01 父目录的 attempt.json 与三尺寸 inputs/arrays/checks 九文件；preflight 会在服务器核每个实际摘要。没有重读或计算 archive 数值。
- **目录与准备。** build 生成专用 `/data/guoyikun/afdm_sp_pair_covariance_20261008_math01_<commit8>`；prepare 用独占 mkdir，source/archive/artifact/tmp/cache/mpl 都在此目录。源码归档在本地及远端解包前均核 SHA256。ssh 使用 deinlab 和登录 bash，shell 数据通过 shlex.quote 处理。source phase 只调用 runner 的 `--print-imports`、`--print-config`，随后核 import path 集合精确相等；这些 flags 是否真正避免 case 计算，须在 runner review 中确认。
- **合同和资源。** prepare 的 config 检查绑定 21 cases、15 source refs、252+252 query entries、840 residual 评估及 11626 reference Channel calls。新加的 reference Channel 计数也可由协议推出：source refs 为 `(90+170+10246)=10506`（每个 reference 另有两次均值动作；N1024 boundary 少两个非零 Cholesky columns），Gram refs 为 `35×(8+16+8)=1120`。合同阶段 wall/CPU 各 120 秒，whole-process timeout 150 秒、TERM 后 10 秒 KILL grace，单 CPU、隐藏 CUDA、RSS 4 GiB、输出 128 MiB。启动器记录 pid/start/end/exit/resource，但 prepare 不运行它；tmux 启动仍由主会话完成。
- **失败与实际准入。** 本地 record 文件、control/snapshot/remote root、launcher process directory 都使用存在即失败的方式，失败 stdout/stderr/exit 被保留，没有自动重试循环。preflight 验来源摘要、archive、snapshot HEAD/root/clean 状态、未运行标记及指定 AFDM 进程模式，且自身只用标准库与 Git/ps。它输出的 contract/launcher SHA 是实际字节回执，主会话仍应与本地冻结文件的 SHA 比对；打印 passed 不等于已核验尚未提供给脚本的外部期望摘要。实际启动应在已初始化 conda 的登录 shell 内执行/source launcher，非登录 shebang 本身不会初始化 conda。
- **回传。** harvest 只在 process exit.txt 存在后收集，允许收集失败证据而不宣称科学成功。远端逐文件流式计算 SHA256/MD5/size，大于 10000000 字节的文件只保留远端绝对路径及摘要；小文件独占归档和本地新目录接收，拒绝绝对/父路径/非普通 tar members，再核每个复制文件三项身份。脚本的远端写入均落在专用 /data 根内。

尚待同一轮整合的只有 runner print/config/calculate 与最终冻结字节对应；本节不新增实验或任务生命周期，也未亲自重复主会话已完成的 AST/compile/Ruff 或 ls-tree 检查。
