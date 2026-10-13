# RECEIVER_CORE 独立静态审查

2026-10-07。范围仅为 `experiments/afdm_sp_fractional_receiver_20261007/` 的
`__init__.py`、`continuous.py`、`data_step.py`、`receiver.py`、`test_core.py`；
定点核对已审 `PathMoments` 与 frozen QPSK alphabet 的调用契约。
未审尚未冻结的 runtime/study/protocol/engineering harness，未运行数值测试、
SSH 或仿真，未修改代码或提交。本报告不是运行 GO 或性能结论。

## 发现（已修复并静态复核）

**CORE-01：非数值异常被重分类为数值失败。** 主线程先指出此问题，本审查核实：
初版 `continuous.py:88,220`、`data_step.py:100`、`receiver.py:210` 的
`except Exception` 无条件包装为 `CoreFailure`。因此输入 `ValueError`、程序
`TypeError/KeyError` 与资源 `MemoryError` 也会成为文义上的 numerical failure；
若 harness 将其作为可保留的科学失败继续，则会隐藏应使整个 stage 失败的错误。
初版 truth-input test 还固定期待此重分类。

实现者 n128 已修复，本审查核验了四层调用及共同的 `raise_with_evidence`：
仅 `FloatingPointError`（含 `CoreFailure`）及 `np.linalg.LinAlgError` 归入
数值失败；其余保留原异常实例/类型，附部分证据并继续抛出。内层 evidence 嵌入
外层记录，没有丢失失败 proposal。truth-input test 改为 `ValueError`；新增
TypeError/MemoryError/TimeoutError 与 LinAlgError 分类及证据测试。测试尚未运行。
代码由实现者修改，本审查仅写报告；harness 的 fatal 路径仍待其冻结后核验。

## 补充发现（CORE-02 已修复并静态复核）

**式(8)不变量失败不能当作普通回溯。** 主线程补充指出，本审查确认上轮遗漏：
`data_step.py:138–155` 对 identity、curvature、monotonicity、increment_bound
一律普通 reject。式(8)对每个几何 proposal 都成立，不以曲率证书成立为前提；
超过冻结容差的残差表明计算/缓存一致性无法成立，不能缩步后把该违反隐藏。
实现者 n128 已按最小方案修复，本审查核验：先保存完整 proposal；identity 失败立即明确报错，仅
identity 通过且 curvature 不足时普通回溯；曲率已过但其余一致性检查失败也终止。
失败前不得更新旧 `log_q`、objective 或 `gx`。

原 objective−100 注入测试使用单路径，`max_level=0`，不能验证不会继续缩步。
现已改为双路径并断言 `max_level>0`，检查仅一个 proposal、完整残差证据及旧状态
不变。修改的 `data_step.py`、`test_core.py` 独立 Ruff/AST 通过；测试仍未运行。

## 已核对的核心不变量

- **连续密度与积分律**：保存 Fourier 系数/噪声/归一化常数或截断 Gaussian
  参数，不把节点质量称为连续 posterior。节点删质量的显式上界不超过 1e-14，
  特征函数扰动不超过 2e-14；层间比较计入两层删质量界。重复节点拆质量的 padding
  保留正权及积分矩。层间一致性仍只是分辨率诊断。
- **gain 与 Doppler**：联合 Cholesky 解完整协方差，后续使用完整
  `S=C+mmᴴ`；顺序更新的 `S[j,i] R[j,i] conjugate(Δphi[i])` 与 canonical
  坐标势一致。point 仅优化冻结其它因子的 expected-log-likelihood Fourier 势，
  保留旧点、网格峰与端点，不宣称精确 marginal likelihood 或全局最优。
- **数据更新**：`β KL(q_new||q_old)` 为前向罚项，式(8)中的另一项为
  `(1+β) KL(q_old||q_new)`；β=0 不计算无用前向 KL。安全谱界、pilot 项与
  Gram 去对角项一致。实际目标增量、式(8)残差和容差独立保存；容差内微小下降
  可以被接受，但没有裁剪成零或宣称精确单调。有限 log q 始终保留，不加概率 floor。
- **流程与输出**：源码确为 20 sweeps、每轮两次 gain、一次顺序 Doppler、三次
  data step；所有 proposal、拒绝、算子调用及阶段完成数分别计数。bit LLR 来自
  log-domain 两类 bit 边缘，all-I then all-Q、零 LLR 判 0。观测字段白名单严格；
  F1 槽位来源、每 arm 获取与序列化全成本仍须 harness 准入核对。

## 验证与未覆盖边界

- 修订后 13 个 tests 已静态阅读，**未运行**；不能将 assertions 报成数值通过。
- 修订后 5 文件独立 `ruff check` 与 AST 语法解析均通过；AST 不执行模块。
  未做静态类型检查，AST 语法解析不是 TypeCheck；未声称独立数值验证。
- fixture 通过 `verify.fixed_inputs(8)` 重建，不是直接读取保存的 MATH NPZ；
  已提醒实现者在 engineering 层核对保存输入的一致性，再声明其复用。
- CORE-01、CORE-02 均已静态关闭，未发现剩余核心阻塞；仍须与冻结 harness 一起做源码准入。

审查最终绑定源码 SHA256：

| 文件 | SHA256 |
|---|---|
| `__init__.py` | `5447b1faa2235cb542688527ce9325f3e2ff26a399427ff0f2a60423736ad29f` |
| `continuous.py` | `b1f22adb27a419e4f3660e6af4830bac10a13b241c7148f6761708302e4e7e63` |
| `data_step.py` | `b5f6f80822933d2b3e67e7ee7878b308d2d38b5c8e0ba507d3b04b45d6ebe139` |
| `receiver.py` | `bbc106f059ff5b84b14d50acafaa9279b498507a2824fee297611bcff0c4518b` |
| `test_core.py` | `c1c6e74333eba82a1ed196f8479d8cfe43866a72d7de0646b0dc89f447ddd688` |
