# Implement — genie-support audit

1. 冻结 commit（protocol FROZEN）→ `task.py start`。
2. 写 `gs_driver.py`、`gs_gates.py`、`gs_agg.py`、launchers → 本地 `py_compile`。
3. scp 到 deinlab，跑 S1、S2、S3（帧 0..19）与 20 帧冒烟（S4、S5、S6）→ 回传 gate JSON。任一 FAIL 即停、报告用户。
4. commit `before genie-support run`（代码 + gate JSON）。
5. 正式运行：帧 0..1999，两臂，单线程分片；完成后 gzip + md5。
6. 远程跑 `gs_agg.py`，回传 `GS_RESULTS.md`、`gs_results.json`；检查 H-S3 停止规则。
7. commit `after genie-support run`；draft 卡 + STATE.md + index.md；commit。
回滚点：步骤 4 的 commit；行文件不可变，聚合可重跑。
