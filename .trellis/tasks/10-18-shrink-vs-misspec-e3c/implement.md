# E-3c 执行清单

2026-10-18 最新执行顺序：用户要求先只完成 E3c 看结果；广审计与样本外预测后置，仍保持未完成。按 design A1 和 continuation-contract 执行。冻结前主会话审查已由本次用户“继续、先做E3c”授权继续推进，无需再次请求启动许可。

1. 溯源：记录 E-3/E-3b 文件与冻结核的 md5，写入 SOURCE_MD5.txt。
2. 驱动 `e3c_driver.py`：复用 E-3b 的管线，按 design §2 参数化 Γ_var；在 gate 模式与 run 模式下都计算并记录校准读数（design §3）。
3. 聚合 `e3c_agg.py` 与 `test_e3c_agg.py`：覆盖 design §4 的所有判定分支，以及不可评估的情形。
4. 单测 `test_e3c.py`：G2、G3。
5. 在 deinlab 上跑 G1、G4，外加约 12 个键的 smoke（帧 8400 起），只报告计数。写 `launch_e3c.sh`，模式为 gate | chain，chain = run → agg → gzip/md5，并带成本检查。写 PROTOCOL.md。**到此停止。**
6. 编排者审查后提交冻结，并亲自启动 chain。代理不轮询。
7. 编排者用 ssh 查看 STATUS、回传结果、提交，并写 draft 卡。

## 本轮完成状态

E3c 步骤 1–7 已完成：冻结 e1bfd013，全部门通过，1200/1200 键零主运行错误，独立保存结果核查通过。结果见 `research-assets/res-20261018-01.md`（draft）。总费用 9.507352 core-hours。当前只完成 E3c 优先里程碑；旧实验广审计、统计修订全量比较和样本外预测继续后置，父任务保持 in_progress。
