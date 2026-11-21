# E-2 执行清单

按顺序执行。每步都有验证；某步失败即停止并记录原因。

## 步骤

1. **溯源与帧查证**（本地）
   - 把 E-1 变体及所有导入的冻结文件的 md5 写入 `experiments/tf_cstate_e2_20261017/SOURCE_MD5.txt`。
   - grep 所有 P1 系 launcher 与驱动的帧偏移，确认 3000..3999 从未用过；确认簇生成器 `E2CJ` 熵域为新。
   - 验证：查证结论写入 `PROTOCOL.md` §帧。
2. **内核变体**（本地）
   - 从 E-1 的 `geometry_reopen_variant.py` 与 `geometry_validation_variant.py` 复制，加关键字 `codelay_guard ∈ {'off','all','neardup'}`，作用于候选掩码、局部细化、fallback（design §2）。
   - 验证：`diff` 只显示守卫相关新增；T0 机械检查。
3. **簇信道替换**（本地）
   - `e2_channels.py`：调用 `headroom_ladder_20261008/driver.py` 的簇几何抽取（只读导入，不改冻结文件），把簇信道放进 P1 管线，做数值单位功率归一。
4. **单测**（`test_e2.py`）
   - 内容：T0 diff；G1 合成部分；G2 守卫不变量（合成状态含同时延候选）；G3；CG1；CG2。
   - 验证：全绿，结果 JSON 存档。
5. **驱动与聚合**
   - `e2_driver.py`，模式：calibrate（仅 F0，C 族）、run（R/C）、gate。
   - `e2_agg.py`，内容：D1–D3、信息量门、同时延普查、成本。
   - `test_e2_agg.py`：合成数据覆盖 D1 PASS/FAIL、D2 四类、D3 三类与 UNINFORMATIVE。
6. **deinlab gate + smoke**
   - 内容：G1/G4 真实状态（帧 0..19 共 640 个状态）、G5、R 族与 C 族各约 12 单元 smoke、每臂计时、核时估计（上限 24）。
   - 写 `launch_e2.sh`，模式：gate | calibrate | run_R | run_C。**此时不跑 calibrate 与主跑。**
7. **冻结**（编排者审查后 commit）
   - 提交内容：`PROTOCOL.md`（design 并入执行期事实与偏差）、代码、单测、gate 结果。
   - 提交消息含 `freeze E-2 protocol`。
8. **校准**（deinlab）
   - 按冻结规则跑 C 族校准，把选出的 SNR 网格写入 `out/calibrate/GRID.json`，不得改规则。
   - 验证：commit `after E-2 calibration`。
9. **主跑**
   - R 与 C 并行分片，tmux `g_e2`，保留 ≥ 16 核空闲。
   - 结束后 gzip、生成 md5 清单、运行 agg。
10. **回传**
    - 只回传小文件：md5 一致、行数据留远端、清理 scratch。
    - commit `after E-2 run`。
11. **结果卡**
    - draft 卡，引用 res-20261017-01；事后内容标注清楚。
    - STATE.md 等用户验收后再改。

## 回滚点

- 步骤 2–6 失败：删除新目录即可。
- 步骤 8 若 C 族两个 ρ 都 UNINFORMATIVE：只跑 R，D3 判为 UNINFORMATIVE，不改规则。
- 步骤 9 失败：保留分片与日志，按规则报告，不重试，不换配置。
