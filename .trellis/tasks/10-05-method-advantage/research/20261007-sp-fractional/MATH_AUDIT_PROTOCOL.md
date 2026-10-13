# MATH-01 保存结果的独立复算协议

2026-10-07。这是原单次数学核验之后的只读复算，不增加原 MATH-01 的执行次数，
也不修改它的合同、源码或结果。所属 CSV 仍为同一 MATH-01 行的 regression。

输入固定为已完成的
`/data/guoyikun/afdm_sp_fractional_20261007_math01_c639a4b0/artifact/execution/MATH-01`。
回传包 SHA256 为 `f04b78d4bc07653dd33c148cb54545e53c7d632c9a8338f4b7819584feddbb08`，
MD5 为 `64d4d57ffb860ea147b020039a2ed9ed`；全部 attempt 绑定文件已核对传输一致。

独立实现只读取保存的数组与元数据，不调用被审 moments/reference 计算函数，
不重新构造物理信道、几何、观测或接收机。重组九组合的二次项、gain Gram、
条件 score 及负控 trace；小 N 使用已存 dense 原子重算 Gram，N1024 只核验已存
充分统计量及算子输出的一致性，不声称重新验证未保存的逐基物理 action。

独立新 stage `MATH-AUDIT-01`：60 秒，0 new observations，0 geometry probes，
0 receiver/decoder，seed=none，1 CPU、CUDA 隐藏、RSS≤1 GiB、输出≤8 MiB。
沿用原误差阈值，不因已经看到数值而收紧或放宽；所有检查及失败保留。
使用新隔离 source snapshot/合同及既有不可变 recorder，原 stage 只读。
全新源码提交、静态审查及输入 hash 绑定后执行；不把审计运行当独立样本或性能证据。
