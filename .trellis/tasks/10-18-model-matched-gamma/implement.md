# 执行清单

1. 记录 md5：E-3 文件及冻结核 → `experiments/tf_mm_gamma_20261018/SOURCE_MD5.txt`。
2. `mm_driver.py`：完成 design §1–§4。提供两种模式：
   - gate：跑 G1–G4；
   - run：主跑，每个键一行，写 gzip 行文件。
3. `mm_agg.py`：实现 design §5 的判定；`test_mm_agg.py` 为每个判定分支写合成测试。
4. 在 deinlab 上：
   - 跑完所有门，再做约 6 个键的 smoke，报告计数与计时；
   - 写 `launch_mm.sh`，提供 chain 模式：依次跑 run、agg、gzip/md5，结束时写 DONE 或 STOPPED；
   - 写 PROTOCOL.md。
   - **到此停止。**
5. 编排者冻结并提交，然后亲自启动 chain。
