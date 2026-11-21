# S4 工程检查

主会话按trellis-check执行，子代理仅进行数值/接口研究；无implement/check子代理。

- 31项目标测试通过，命令与新鲜输出：targeted-tests.txt。
- 改动Python模块py_compile通过；项目该Python层未配置lint/type-check/build命令，不冒称这些检查运行过。
- 真实CUDA：温度T1/default回放、Q/C入口默认回放、固定容量新入口旧路径回放均保持H/x/sigma/错误一致；两个有限矩/不确定性目标原型均finite。
- 代数：解析QPSK、均匀/点质量、功率缩放、trace Gram含位移碰撞、冻结增广目标下降、V=0退化、Hermitian正定/算子一致性、非法温度/负方差拒绝。
- 容量：五cap实际GPU展开后硬约束、提名上限、跨臂支撑相同；监督标签与接收容量分离回归测试通过。
- 原始数据：校准fit/validation分离、原Ddev字节保持、旧先验/新cap先验域匹配、全部固定分母与文件哈希检查。
- 复用：共用原softmax、proximal solve、harvest、F2P、cluster expansion；未复制第二个剪枝器。C2-rel只有cand_active_rel，无支撑外H correction。
- 默认历史路径保留；CPU已有gelsy重复差异保留失败证据，没有静默换求解器或放松GPU gate。
- git diff --check仅检查本任务路径，通过。没有暂存/提交用户其他工作；任务源码尚未提交，原始运行快照已版本化冻结。

科学边界：Q是有限工作分布的期望目标，不是精确EM；C仅用于冻结GLS增益。并发耗时不验G2；原正结果依赖legacy容量，固定容量对照必须单独裁决。S1早期预算账本不完整，未追加正式计时。
