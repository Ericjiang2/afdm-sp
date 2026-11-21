# E-3 执行清单

按顺序执行。每一步都要验证；任一步失败即停止并记录原因。

1. **溯源与帧查证**
   - 在 `experiments/tf_e3_sbl_20261017/SOURCE_MD5.txt` 记录所有导入的冻结文件的 md5。
   - 确认 P1 帧 4000..4399 与 6000..6099 此前未被使用。
2. **SBL 模块**（`sbl_rx.py`）
   - 实现 EM-SBL，Γ_var 支持三种取值：0、对角、完整。
   - 实现筛选与输出选择。
   - 冻结超参见 design §2。
3. **两轮驱动**（`e3_driver.py`）
   - 模式：`calibrate`（只跑 L-hard）、`run`、`gate`。
   - 每行记录内容：四个变体的 FER、info 错误数、decoded sha、显著原子（时延、Doppler、能量）、n_pair 及 |Δν| / |D_N|、NMSE、各阶段耗时。
   - 记录 `_argv` 与 `_config`。
4. **聚合**（`e3_agg.py`）
   - 判据 X1–X3 与五类判定（design §5）。
   - 用合成数据测试每个判定分支（`test_e3_agg.py`）。
5. **单测**（`test_e3.py`）
   - T1、T2（含蒙特卡罗 Γ 核对）、T4。
6. **deinlab gate + smoke**
   - 内容：T3（真实帧 0..19）；每格约 8 个键的 smoke，SNR 取临时值并标注 smoke-only；计时，核时估计（上限 40）。
   - 写 `launch_e3.sh`，模式为 gate | calibrate | run | agg。此时不跑 calibrate 与 run。
   - 写 `PROTOCOL.md`：design 内容加上执行期事实与偏差。
7. **冻结**：编排者审查后 commit，消息含 `freeze E-3 protocol`。
8. **校准 → 主跑 → 回传**
   - 先校准，`GRID.json` 的 md5 必须在主跑开始前写入 STATUS；然后跑主跑。
   - gzip、生成 md5 清单、运行 agg；只回传小文件。
   - commit：`after E-3 run`。
9. **结果卡**：draft 卡；STATE.md 待用户验收后再改。

## 回滚点

- 步骤 2–6 失败：删除新目录。
- 校准判出 UNINFORMATIVE 的格：按规则不跑主跑，不改规则。
- 主跑失败：保留现场，不重试，不换配置。
