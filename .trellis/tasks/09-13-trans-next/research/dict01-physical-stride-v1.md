# DICT-01: 物理位移与枚举宽度解耦

## 根因与失败复现

现用 NumPy/Torch 经典接收机把候选列宽 `K=2W+1` 同时用作路径位移系数。列号必须由 `K` 编排；物理 DAFT 位移必须由 `2Nc1` 决定。N1024、`2Nc1=5`、W3 时，`l=1,k=-3` 的物理位移是 2，旧代码给出 4；新增合成合同首次运行 `test_physical_dictionary_stride.py -x`：W2 通过，W3 的直接 CPP 时域传播对比 1024/1024 元素不一致，最大绝对误差 6.23586852。

## 修复边界

`physical_stride(N,c1)` 在字典和接收机入口验证 `2Nc1` 为有限非负整数，否则抛 `ValueError`，不静默 round。候选列号、支撑解码及容量账本继续使用 `2W+1`；NumPy/Torch OMP 字典、NumPy/Torch H 重建、NumPy/Torch DA-LS、整数 BP 图及固定支撑真值投影使用共同物理 stride。`representation_error` 原先要求 `2Nc1=2W+1`，现改为独立验证物理 stride 与生成器惯例；扩域表示误差不会因 W 增大而被旧参数等式拒绝。旧 `afdm_env` G0 生成器、MATLAB 兼容分支、历史 raw/source snapshot 不修改。

## 本地验证

- `test_physical_dictionary_stride.py`：8 passed。N1024 的 q5/W2、q5/W3、q5/W4、q11/W5 各覆盖负 k、l=0 负位移循环、l=24 最大时延；NumPy/Torch 字典、H 作用与 DA-LS 列均和独立时域 CPP+DAFT 对齐（`atol=rtol=3e-10`）。非法 `2Nc1=5.1` 在 NumPy/Torch 字典、H 和 DA-LS 入口显式拒绝。N32 q5/W3 固定支撑投影回收原增益与 H，扩域表示误差入口在合成生成器合同下返回零残差。
- N32、q5/W3 的真实 Torch CE/BP 调用捕获 sparse COO 索引，图位移与实际支撑的 `5l+k` 集合一致，并通过完整 dense H 图审计。该测试不含编码反馈、FER、SSH 或仿真。
- 变更 Python 文件 `compileall -q` 通过；本地所用 venv 未提供 ruff/mypy。原 `test_integer_graph_receiver.py` 在此 venv 因 `matplotlib` 缺失无法收集，故未声称该现有完整链回归已运行。
- 现有 `test_budgeted_support_diagnostics.py` 中 7 项本地通过；第 8 项依赖旧 `loop9_cache_features` → `afdm_trainer` 导入，因当前 venv 无 `matplotlib` 而在导入处失败，非断言失败。没有安装依赖或重跑物理帧。

## 剩余范围

`afdm_joint_unrolled.py` 的旧二维生成层和 `afdm_env.py` 的原始 G0 构造器保留原样；`standalone/` 旧演示代码也未更改。新几何证据只支持合同/小模型调用，不是 N1024 完整接收性能或 BER 资格。W2 在本次合成合同中与直接传播一致；本地没有冻结完整接收 raw 可重放，完整数值冻结对照仍需在后续接收阶段核对。
