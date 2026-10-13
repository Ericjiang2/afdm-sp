# RECEIVER_HARNESS 独立静态准入审查

2026-10-07；同一 IMPL-01。全文审查新 package 的 `runtime.py`、`study.py`、
`protocol.py`、`thread_binding.py`、`engineering.py`，定点读取共享 recorder、
源码清单、frozen G0/G1、F1/keep-slots/scalar_joint 与 QPSK 映射实际调用链。
复用已完成核心审查，不重做数学核验。本轮仅写本报告，无源码修改、数值运行、
SSH 或提交；工程组件通过也不能代表有效接收机通过。

## 发现（已由实现者修复并静态复核）

1. **HARNESS-01：TimeoutError 的逐调用失败证据被跳过。**
   `study.receive_population` 的 `except OSError: raise` 也匹配 `TimeoutError`，
   因而已有 core 部分 trace/operations 不进入 fatal artifact。现已将 TimeoutError
   独立提前捕获，保存 fatal artifact 后原型抛出；真正磁盘故障保留 started 标记并
   明确无法保证后续写入。监控器也已改为仅在 primitive 正常返回后 post-check，
   不再用 finally 的预算异常覆盖原错误。
2. **HARNESS-02：组件测试的核心操作计数未导出。**
   `engineering` 保存了 unit 的 FFT/solve 等 primitive counts，但各测试局部的
   求积、目标重算、接受/拒绝 proposal 计数会被丢弃。saved 9 步已有计数不等于
   13 个 unit 都留证。现已逐 fixture 保存独立 evidence NPZ，汇总三处 count 别名
   事件并捕获连续积分、point、数据步/目标的成功及失败 trace。包装返回原结果、
   保留原异常，并在 finally 恢复所有别名，不改变数值输入或执行额外数值步骤。
3. **HARNESS-03：saved-N 组件失败时丢失部分数值证据。**
   算子或 `DataStepper.step()` 抛错会跳过 case raw 保存；已完成 checks/steps、
   当前失败 proposal 和局部 counts 只留在内存。现已由 `saved_case` 预置 partial
   容器并逐项填充，异常时保存已完成项、当前 error evidence、counts/operations
   和耗时，再抛原异常；未补成 3 步、7 项通过或完整工程成功。

三项由 n128 修改，本审查直接反馈并抄送主线程，现已全部静态关闭。

## 已核对的实际链

- **生成与先验边界**：`make_frame(..., uncoded=True)` 使用独立 channel/message/noise
  component RNG；4 blocks 分别经 G0 获取归一化物理 gains，再原样传入完整 G1 CPP。
  `reuse_at_snr` 只按 `sigma2=10**(-SNR/10)` 缩放共享 proper 复噪声，未按 G1 能量
  再归一化。6/8 dB 是 8 个观测、4 个独立 blocks，非 8 个独立样本。
- **truth 与接收边界**：生成函数仅返回公共标量配置与已绑定 artifact 路径/哈希。
  逐 arm 仅载入 `y/pilot/sigma2`，各自执行 F1；公共配置限定 N/c1/c2/rho/lmax。
  24 个结果封口并核对原始输出哈希后才读取 truth 评分；无 free truth support、gain
  或生成 seed 进入调用参数。QPSK all-I then all-Q 与三个 arm 的 bit-marginal 判决一致。
- **成本与失败口径**：每 arm 单独计入输入读取、F1、backend 与原始输出保存，且
  outcome 保存后才截取 full wall/CPU。生成/setup 另列，所有调用顺序按 block 轮换。
  数值失败保留为失败项，bit errors 为 null，24/24 完整门槛不把它们删掉或填零；
  每 arm 的 8 次完整调用分别计算中位耗时，point 零错误记无判别空间。
- **冻结依赖与独占尝试**：upstream 模块强制位于 frozen 树；physical/messages
  保持唯一模块身份。实际预载项目源码加 package 全部 Python、工程输入逐文件 SHA
  与合同核对，所有项目 Python 还须逐字节等于 HEAD。共享 recorder 以独占目录与
  exclusive 文件创建登记、快照、结果和失败状态；前后源码清单/哈希漂移导致失败。
- **工程范围**：保存的 N8/N16/N1024 各 7 项算子比较、各 3 次数据步，共 21+9；
  旧保存矩保留 Pd=.55，新增数据步明确用工作 Pd=.5 从保存 probabilities 重算。
  固定 13 个组件测试含 1 次非法 truth 字段 receive：应计 API 边界调用 1、有效
  payload/backend 0、新观测 0、decoder 0。该工程清单没有有效接收、BER 或 G1 性能验证。

## 预算与准入范围

主线程已明确最终 launcher 口径：工程内核 180 秒、进程外层 210 秒；development
内核 1800 秒、进程外层 1830 秒；外层 TERM 后最多 10 秒强制结束。
内层预算不因启动开销而扩展，`/usr/bin/time` 记录包含导入/注册/保存的全进程成本。
源码内部的 threadpool/Torch 检查限定 1 CPU、CUDA 隐藏；RSS≤4 GiB、输出≤128 MiB。
本次不把内核 180/1800 秒表述成全进程上限，最终 commit/tar/contract/launcher 的
逐字节准入仍由主线程完成。本报告不授予运行 GO。

## 验证

- 当前结论：已读新增调用链未发现剩余静态阻塞，可进入主线程的最终字节准入。
- 数值/组件 tests/SSH：均未运行。不得把静态 assertions 当作工程结果。
- 修改后 10 个 package 文件独立 Ruff、AST 语法解析通过；未运行 TypeCheck。
  AST 不导入或执行模块。工作树这 10 文件与 HEAD 无差异。

## 最终源码绑定

源码 commit：`78c4156934746591dfc1385fc92c811f60a28123`。主线程对
`__init__.py`、`thread_binding.py` 仅删尾部空行，以下按当前字节绑定；核心其它
文件沿用已完成的 CORE-01/02 审查。本表不替代尚待核对的完整 imported-source
inventory、工程 MATH 输入、部署 tar 和控制文件。

| 文件 | SHA256 |
|---|---|
| `__init__.py` | `c2bf281817fffe941156135994725dbcdd0e270842866a014772ad6b0fe92a60` |
| `continuous.py` | `b1f22adb27a419e4f3660e6af4830bac10a13b241c7148f6761708302e4e7e63` |
| `data_step.py` | `b5f6f80822933d2b3e67e7ee7878b308d2d38b5c8e0ba507d3b04b45d6ebe139` |
| `receiver.py` | `bbc106f059ff5b84b14d50acafaa9279b498507a2824fee297611bcff0c4518b` |
| `test_core.py` | `c1c6e74333eba82a1ed196f8479d8cfe43866a72d7de0646b0dc89f447ddd688` |
| `runtime.py` | `672a404bb532d243ff3f6f34b3e5a3968779d217f52fa4eb2f3afcd3d9465bd4` |
| `study.py` | `8e22054af415f75a9897ca0bc17c2043635acc0fc53cc52190050504b3aca7c4` |
| `protocol.py` | `5b3c5cff16582afdf78b429649ee226dfb4977f40de03d9b1227ea0080feb165` |
| `thread_binding.py` | `03d5919617e0406f09176c7435e9fc2af2c6f7fa4a989dc476577d929978ac8e` |
| `engineering.py` | `396ebc82efd8db74bcb799d350c47146548078d68ac11b4bb40e5d646f166f40` |

工程附录来源 `RECEIVER_PROTOCOL.md` SHA256：
`6bc2ab6f51b208f7fd5c78abec42874ec502a74b4bab51e76cf93c6961254705`。
