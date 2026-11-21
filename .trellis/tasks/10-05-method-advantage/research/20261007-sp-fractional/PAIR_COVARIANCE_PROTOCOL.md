# PAIR-COVARIANCE-MATH-01：冻结前数值合同

## 目标与范围

验证 `PAIR_COVARIANCE_FFT.md` 的精确二阶矩和有限 Gram 元素查询。只扩展现有
`PathMoments/SourceMoments`，不运行 receiver、decoder、数据生成器或新随机流。
这是数学实现资格检查，不能证明 BER、低成本、配对策略或 Transactions 贡献。
主输入来自原 MATH-01 的十个封口文件；原 Pd=.55 数值不改称 receiver 的 Pd=.5。

## 固定构造

N 为 8、16、1024；pilot、data_mean、data_variance、y、gain_mean/covariance、
Doppler nodes/weights 和 c2 读取原件，不调用 `fixed_inputs` 重新生成。
每个 N 固定七种情况，总计 21：

1. saved_diagonal：原双路径、原三点独立 Doppler、无 pair。
2. saved_complex：同上，三组复数 pair covariance。
3. saved_boundary：同上，两个含 rank-one 和 zero-variance 的合法退化块。
4. point_complex：三组 pair，两个 ν 固定为各自原第一个 node。
5. single_complex：三组 pair，只保留原第一路径及对应 gain marginal。
6. same_delay_complex：三组 pair，两个 delay 都等于原第二路径 delay。
7. integer_chirp_complex：三组 pair，原 delay，c1=5/(2N)。

原 c1=5.3/(2N)，所以覆盖非整数 2Nc1 与 integer 对照。same-delay 与
integer-chirp 各三种，是六个新确定性几何配置，不是新随机信道。

complex 输入 pairs 按 `(N−1,0),(1,N/2),(N−2,2)` 给出，按给定方向令
`c_uv=rho*sqrt(v_u v_v)`，rho 顺次 `.3+.2j, −.4j, −.25+.15j`。
接口规范化为 u<v 时必须共轭 c，不能仅交换索引。boundary 使用 `(0,1),(2,3)`，
v0=v1=v3=.25、v2=0，c01=.25、c23=0；其余原 variance 保留。后一 fixture 是
通用合法 PSD 矩测试，不声称该 mean/covariance 由当前 QPSK posterior 产生。

只支持不相交 pairs；每个 symbol 至多一个 partner，因此整体 PSD 可由每个 2×2
块与未配对 variance 检查，未构造 N² 矩阵来做运行时输入验证。
协方差 PSD roundoff 使用当前 `ROUNDOFF` 的明确尺度，不对非法输入 silent clip。

## 独立参考

每个 N 对五组 `(geometry,covariance)` 构造 time-domain source reference：原 diagonal、
原 complex、原 boundary、same-delay complex、integer-chirp complex，共 15 组。
point/P1 仅复用相同 source reference 的列子集；这不复用生产 `SourceMoments` owner。

- N8/N16：用实际 `physical.Channel(...,nu=0).apply(e_u)` 与 inverse DAFT 构造
  T_l U 的完整小矩阵，显式形成 C，再算 `diag(V_i C V_j*)`。C 的 Hermitian/PSD
  也作小矩阵检查。
- N1024：对每个 covariance 的独立 sparse Cholesky 列 z，计算实际
  `Channel(nu=0).apply(z)` 后 inverse DAFT，累加各路径响应外积的时间对角。
  每列最多两个非零值；仅保留一列及 P²N 核，不形成 N×N 的 C、L 或算子。
  因子按 `z_u=sqrt(v_u), z_v=conj(c_uv)/sqrt(v_u)` 与余项构造；零方差单独处理。
  rank-one/zero fixture 的余项在二进制下精确为零，不用数值截断掩盖负值。

所有 reference 均通过原实际 CPP 实现，不使用待测频差分组/IFFT 公式。
对固定和独立离散 ν，枚举既定节点组合计算完整 R/f/residual；conditional scores
在原七个 evaluation_nodes 上枚举其余路径，比较时仅去掉同坐标共同常数。
实际 gain prior 仍是已声明的 Gaussian 工作模型，未改真实生产增益生成器。

Gram 查询固定十二项（含对角、正反、重复与 wrap）：
`(0,0),(N−1,N−1),(0,N−1),(N−1,0),(1,N/2),(N/2,1),`
`(N−2,2),(2,N−2),(0,N−1),(N/2+1,0),(0,N/2+1),(N/2−1,N/2+1)`。
独立参考直接用各路径/ν 的实际 Channel basis columns；小尺寸保留完整 G，
N1024 只取八个涉及的 basis columns。ψ_ii 来自同一路径同一 ν，不能独立拷贝。
空查询不得建 Z；同一查询再次执行必须一致并且不新增 Z FFT。

## 比较及边界控制

每个 case 保留所有 source cross kernels、reference kernels、R/f、完整 expected
quadratic、conditional coefficient/score、finite G entries 以及对应参考原数组。
检查 K_ji=conj(K_ij)、sum K_ii=tr C、R Hermitian/PSD、G 的共轭对称。
saved_diagonal 另逐数组与封口 MATH 的 source responses/variance_fft/coefficients、
structured quadratic/R/f/Gram action/diagonal/adjoint/conditional scores 比较。
未提供 pairs 与显式空 pairs 必须保留原数学路径和字节相同的默认输出。

合同控制覆盖 missing 配对参数、float/bool/错形索引、重复端点、自环、越界、
负索引、错形或 nonfinite c、非 PSD/zero-variance 非零 c；foreign source owner、
几何/φ 替换后的 stale source、调用者数组修改、source 数组不可写；Gram 的非法
索引、空查询和 cache replay。错误必须显式，不做 silent fallback。

归一化误差 `||actual−reference||/max(1,||reference||)`：N8/N16 为 1e−10，
N1024 为 1e−9。Hermitian/PSD 使用原 `ROUNDOFF=1e−10`。输入 PSD 按每个 2×2
块最大方差与 c 实/虚部分量缩放后检查 determinant，不修改通过的输入。
所有 nonzero 最大误差照实报告。

## 额度、冻结与证据

源码实现后，最终 configuration 固定实际 case/参考/控制清单和计数，再经独立
source review、Git 提交、独立 snapshot、import-only 准备和字节准入。
科学阶段最多一次；wall/CPU 各 120 s，进程 timeout 150 s、kill grace 10 s，
单 CPU、CUDA 隐藏、RSS 4 GiB、输出 128 MiB。独立参考、检查和保存都计时。
记录 21 cases、15 covariance references、252 有限 G 查询项（每 case 12，
cache replay 另计 252）、840 节点组合 residual 参考评估；边界控制另表计数。
直接 Channel/basis/DAFT、生产 source/query FFT、缓存命中和所有保存须留实际账本。
最终源码若改变上述分配，必须在首次运行前显式修订并重审，不能事后改额度。

先查已有进程；在 SSH deinlab 登录 shell 中 `conda activate AFDM`。所有远端
source/output/cache/tmp 在独占 `/data/guoyikun/afdm_sp_pair_covariance_*`；不上传
Trellis、STATE、research-assets。不重跑旧阶段，不改旧原件；失败保存，不自动重试。
科学结果回传并核 SHA256/MD5/size 后由独立代理审原件。大于 10 MB 的单文件
留远端并记录绝对路径/MD5；本阶段小数组应分 case 保存，避免不必要大总包。

数值通过后才讨论有限候选生成、block 同步更新及完整接收机成本；这些不在本阶段内。
