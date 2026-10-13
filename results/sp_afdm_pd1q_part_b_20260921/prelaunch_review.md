# Part B 预启动限界审查

范围：仅审查本次 3072 个独立观测、9696 次接收机调用的 producer/preflight/保存/验证链，以及冻结统计合同与离线分析接口；未重审冻结接收机数学，审查过程新增接收机调用 **0**。

已核对：三个 SNR 各 1024 帧配对，三个主臂全量，POINT 首 128 帧、PBi 首 32 帧；941001 独立种子命名空间与旧实际 channel seed 在生成前查碰撞；每帧仅生成一次观测供对应臂使用，truth 仅供离线评分；同源/同机 E1 全 32 帧 EP2 中位数预定 deadline；每次尝试的完整在线成本、数值失败及已完成 checkpoint 入账，完整运行不盲目续跑。离线分析绑定独立 recount 回执和冻结 `statistical_contract.json`，实现六项精确 CP 上界与单独的六项下界、主臂 32 帧及固定子集 16/4 帧配对 circular-block bootstrap、信息帧 FER 与缺失位标记。

本轮发现并已修两项工程问题：`verify.py` 校验 checkpoint 时间时引用未导入的 `math`，现改用已有 `finite_seconds`；`run_chain.sh` 原失败路径只保存退出码，现同时写明阻断阶段与日志的 `RESULTS_BLOCKED.md`，不输出科学结论。相应静态 Python 语法与 shell `bash -n` 检查通过。未发现剩余的数据有效性阻断项。

远端现有 AFDM 环境中的 `test_analyze.py` 合成边界测试仍待执行者提供 exit 回执；它不生成新观测或调用接收机。该回执通过后再冻结并启动真实 Part B。
