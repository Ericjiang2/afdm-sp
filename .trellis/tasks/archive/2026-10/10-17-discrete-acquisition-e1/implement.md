# E-1 执行清单

顺序执行；每步有验证；失败即停并记录。

## 步骤

1. **溯源**（本地）
   - `md5 experiments/tf_geometry_reopen_20260922/geometry_reopen.py` 及 `run_validation.py`、`twofft.py`、`physical.py`，写入 `experiments/tf_cstate_e1_20261017/SOURCE_MD5.txt`。
   - 验证：md5 与协议记录一致；git status 显示冻结文件未改。
2. **变体模块**（本地）
   - 复制 `geometry_reopen.py` → `experiments/tf_cstate_e1_20261017/geometry_reopen_variant.py`，仅加 `gamma_mode`（默认 `'full'`）与一处分支。
   - 验证：`diff` 只显示新增行；`python -m py_compile` 通过。
3. **单测**（本地）
   - `test_variant.py`：G1（full 与冻结原版在合成帧上逐位一致）、G2（diag 非对角为 0 且结果不同）、G3（确定性）。
   - 验证：三个测试全绿；输出 JSON 存档。
4. **驱动**（本地 → deinlab）
   - `e1_driver.py`：复现 P1 帧 → 跑 F0 → 捕获状态 → 对 F0 失败帧跑 A1–A5 → 行写 gzip。含 G4 断言（触发集合与 ledger 一致）。
   - 验证：本地 8 帧 smoke 通过（含至少 1 个触发帧）；`_argv`/`_config` 指纹写入。
5. **冻结与提交**（本地 git）
   - commit：协议 + 变体 + 驱动 + 单测 + 溯源（消息含 `before E-1 run`）。
   - 验证：`git log -1` 显示该 commit；工作树干净。
6. **运行**（deinlab，tmux `g_e1`）
   - 分片 32–64 单线程；先跑 gate 分片，再跑主分片；`nvidia-smi` 不涉及（纯 CPU）。
   - 验证：0 失败分片；行数 = 帧数 × 臂数；md5 清单生成。
7. **回传**（deinlab → 本地）
   - 小文件：`analysis/*.md`、`*.json`、`REMOTE_ROWS_MD5.txt`、launcher `.sh`。
   - 验证：本地/远端 md5 一致。
8. **分析**
   - `e1_agg.py`：J1–J3 判定、净救回 CI、McNemar、支撑变化、成本表。
   - 验证：与门结果一并输出；异常帧单列。
9. **结果卡**
   - `research-assets/res-20261017-01.md`（draft，含 Limits 与条件化声明）。
   - 验证：卡片引用文件路径与 md5；STATE.md 不改（等用户验收）。

## 回滚点

- 步骤 2–4 任一步失败：删除 `experiments/tf_cstate_e1_20261017/` 即可，冻结文件未动。
- 步骤 6 失败：保留失败分片与日志，按冻结规则报告，不重试不换配置。
- 步骤 8 若 G1–G4 任一不通过：结论为"未定"，不得解读 J1–J3。
