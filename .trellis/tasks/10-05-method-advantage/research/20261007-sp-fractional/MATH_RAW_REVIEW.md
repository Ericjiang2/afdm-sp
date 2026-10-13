# MATH-01 保存数组独立审计：实现与待执行合同

日期：2026-10-07。任务：`.trellis/tasks/10-05-method-advantage`。仅新增 `experiments/afdm_sp_fractional_20261007/audit.py` 和本报告；旧六个 package 文件与 source commit `c639a4b0e7b46058175a138be06863aa2657448b` 逐字节一致。本代理没有 SSH、提交或数值执行。

## 当前判定

**审计实现已完成，静态检查 PASS；独立数值审计 NOT RUN。** 本报告不能充当原始数学结果已经独立复算的证明。主线程须先独立核对 audit 源码、提交并绑定新 source snapshot，再执行独立 60 秒 audit stage。

已只读查看原 JSON 和 NPZ ZIP 成员名，没有在本地加载数组做科学运算。原 `attempt.json` 报告 complete、内部 wall 5.636629868997261 秒、CPU 5.618789664 秒、peak RSS 65,630,208 bytes、execution output 1,225,012 bytes。三个 case 报告 23/23/19 checks 通过，另有九项 boundary controls；这些目前是原运行记录，不是本代理新增的数值结论。

## 输入与源码绑定

原 attempt 相对项目路径：

`.mission/20261007-sp-fractional-trans/evidence/artifact/execution/MATH-01/`

原远端路径：

`/data/guoyikun/afdm_sp_fractional_20261007_math01_c639a4b0/artifact/execution/MATH-01`

原 attempt SHA256 在审计源中固定为 `329f39b59b0fe48dfdfaa4f3870deb29320d457ede16a95f77d54b673b787e56`；原 snapshot HEAD 固定为 `ad3b3fa2d0d301e6e4267b51286206db26bb748c`。输入可迁移路径，但内容、manifest、snapshot 和 case 集合不可变。

当前 `audit.py` SHA256：`b1e578fd4e872902c0d637565f6b85cec96c26e0a316be8fe015db825fc04317`。

脚本验证原 attempt 绑定的逐文件 SHA256、完整文件集合、registration/config/result copies、15 个原 Python source hashes 和 source snapshot 文件；再验证每个 NPZ file hash 及每一个保存数组的 dtype/shape/bytes hash。拒绝多根 manifest、路径穿越、symlink、超输入预算、object arrays 和非有限数值。原 hash anchor 是审计的输入信任边界；不是重新认证服务器或测量旧进程。

## 独立重算内容

1. 从保存的四点 QPSK 概率重新计算均值、方差、归一化、恒模与 FFT(v)，核对原保存值；不调用 `fixed_inputs`，不生成新信道、随机样本或新的几何配置。
2. 从保存的节点/概率重算 characteristic moments，核对先验节点、七个 conditional score 节点、c1/c2 和复 gain mean/covariance 与原 registration 的一致性。
3. 将全部 union-node mean responses、variance self/cross trace 向量化重组成二维 expected quadratic grid；从其中按原两路径独立概率重新积分九组合 quadratic、gain Gram/matched vector 和 42 个 conditional expectations。该过程不调用原 `reference` 或 `at_pair`。
4. 用九组合保存的 pair diagonal 和 AF variance 独立交叉校验 variance trace；重新加权出 expected Gram diagonal。检查 unit-path Frobenius norm、self variance trace 与酉守恒。
5. N8/N16 从保存的完整 unit matrices 重新做矩阵乘法，复算全部 elementary responses、自/交叉 variance trace、九个 pair Gram/diagonal、完整 expected Gram、matvec、mean adjoint 及 isotropic/independent-copy covariance。这仍是保存矩阵的复核，不重新调用物理生成器。
6. 从保存的 Fourier coefficients 重算 conditional potentials，并与 independently recomposed conditional expectations 作 additive-constant comparison。
7. 复算 isotropic、independent-copy 与 random-tangent 的解析 trace 及缺陷符号；小 N 另从保存 covariance 矩阵取 trace/action。重算原所有 normalized comparison errors、Hermitian/PSD probes 和原 JSON 的 error 数值一致性，保留所有失败。

固定阈值继续为 N8/N16 的 1e-10、N1024 的 1e-9、Hermitian/PSD 的 1e-10。报告 error 数值复现另用固定 absolute 1e-14 元数据比较容差；它不改变数学 identity 的通过阈值。original boundary-control JSON 完备性会核对，审计不重新运行其 invalid-input fixtures。

## N1024 的明确限制

N1024 没有保存逐基向量 unit responses，也没有 dense H/G。审计以保存的 mean responses、self/cross variance traces 和九组合 diagonal 为充分统计量来源，能够发现概率加权、共轭索引、trace/Gram/conditional 组合和报告误差计算的问题。

**它不能重新验证这些充分统计量由原逐基物理动作正确生成。** 特别是 N1024 的 saved Gram matvec 与 mean-adjoint vectors 只重算原 structured/reference comparison，不重新独立构造这些向量。脚本在每个 case 的输出中记录 `unsaved_basis_actions_revalidated=False`，并区分 `saved dense matrices` 与 `saved sufficient statistics only`。不得把这次 audit 升格为第二次完整物理仿真。

## 执行接口、资源与隔离

源码只导入 NumPy、标准库与既有 protocol/thread-binding/immutable dump helpers。它显式拒绝已导入 `verify`、`moments` 或 `physical` 科学执行模块的进程。`physical.py` 仅作 source provenance 绑定；旧数学核函数从不调用。

只列源码清单的接口：

```text
python -m experiments.afdm_sp_fractional_20261007.audit --print-imports
```

执行接口：

```text
python -m experiments.afdm_sp_fractional_20261007.audit \
  --source-attempt <原MATH-01绝对路径> \
  --artifact-root <独立audit artifact绝对路径> \
  --stage AUDIT-01
```

源与输出必须不互为祖先目录。新 audit root 必须有独立 run_contract；不能放宽或重用原 MATH 的 180 秒 reservation。审计固定 `new_observations=0`、`new_geometry_probes=0`、receiver/decoder calls=0、seed='none'，用 `protocol.adapter().run(..., wall_seconds=60)`，不调用硬编码三几何的 `protocol.run`。

主线程应保持 one CPU thread、CUDA 隐藏、1 GiB peak RSS、16 MiB output 的独立资源合同，并绑定全部当前源码（旧 15 源加 audit，共 16 源）和全部只读输入文件。脚本在数值工作前调用 `committed_project_sources`，由复用 recorder 执行 source/data fingerprints、snapshot、锁、累计预算、异常与实际资源记录。

每个 case 的重算数组写入新 audit 的 `nN_recomputed.npz`，全部 check 写 `nN_audit.json`，最后写 `audit.json`。任何数学失败在保存全部完成的 case 后抛出；文件/hash/schema 错误立即显式失败，由 recorder 保存 invalid attempt。没有自动重试、threshold 修改或对原 MATH attempt 的写入。

## Findings (fixed)

仅新增审计脚本。静态自查将 variance-trace 重组中的行/列索引写成先取向量、再加 `[:,None]` / `[None,:]`，消除了 NumPy 混合 advanced indexing 的轴位置歧义；这不是旧科学实现的修复。

## Findings (not fixed)

独立 audit 数值结果仍待主线程提交、准入和 SSH 执行。N1024 未保存逐基向量动作的再验证不在本次输入能力范围内，已明确披露；不以偷偷再生成几何来补齐。

## Verification

- Lint：`ruff check --no-cache experiments/afdm_sp_fractional_20261007/audit.py` PASS。
- 静态语法：`ast.parse` / `compile(source, ..., 'exec')` PASS；没有 import/exec 审计源码。
- 静态依赖：无 verify/moments/physical 科学模块导入；旧六个源文件与原 source commit bytes 一致。
- TypeCheck：未运行独立类型分析器；静态 compile 不冒称类型检查。
- 数值 Tests / audit stage：NOT RUN。没有新增随机 observation 或 geometry，也没有性能/创新结论。
- 本次只交付上述两个授权文件；不修改原 MATH 合同、CSV、STATE、源码或旧结果。MATH 及该审计都不能关闭 SELECT 或完整研究目标。
