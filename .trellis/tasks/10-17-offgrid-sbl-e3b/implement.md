# E-3b 执行清单

1. **溯源**：记录导入的冻结文件与 E-3 文件的 md5，写入 `experiments/tf_e3b_offgrid_20261017/SOURCE_MD5.txt`。
2. **细化模块** `offgrid_refine.py`：按 design §1.3 实现，冻结超参（P=3、±.5、xatol 1e-3、最多 16 次评估）。
3. **驱动** `e3b_driver.py`，提供 gate / run 两种模式：
   - 复用 E-3 的第 1 级、第 1 轮与第 2 级 SBL；
   - 每行写入：四个 off-grid 变体的 FER、info 错误数、decoded sha、输出原子（细化前与细化后）、同时延普查、NMSE、细化接受数、各阶段耗时；
   - 每行附 `_argv` / `_config`。
4. **聚合** `e3b_agg.py`：读 E-3 行（远端路径见 `tf_e3_sbl_20261017/out/main/REMOTE_ROWS_MD5.txt`）做配对；实现 design §3 的判定；用合成数据为每个判定分支写测试 `test_e3b_agg.py`。
5. **单测** `test_e3b.py`：覆盖 G2、G3。
6. **deinlab gate 与 smoke**：G1（20 个键）、G2、G3、约 16 个键的 smoke 与计时、核时估计；写 `launch_e3b.sh`（模式：gate | chain | agg，其中 chain = run → agg → gzip/md5，并带成本检查）；写 `PROTOCOL.md`。**到此停止**，不跑 chain。
7. **冻结**：编排者审查后 commit。
8. **启动 chain**：执行代理确认 chain 已启动后立即返回，**不轮询**。编排者用 ssh 查看 STATUS，回传小文件并 commit。
9. **结果**：写 draft 卡。STATE.md 在用户验收后再更新。
