你是严格的通信接收机代码审稿人，在当前目录（AFDM 项目根目录）只读工作，不要修改任何文件，不要跑完整接收机。≤ 4 分钟的第二次跑前快检；上一次你给了 `PRERUN: FIX`（`ideas/reviews/sol-prerun-r8-pn-margin.md`），4 处已改，并且又加了对手臂。只查下面六项，逐项「通过 / 不通过 + 行号与理由」，最后一行 `PRERUN: GO` 或 `PRERUN: FIX — <必须先改的点>`。

待检：`ideas/l2/l2_r8_pn_margin.py` 与 `ideas/l2/PREDICTIONS_r8_pn_margin.md`（含「跑前修订」「跑前修订 2」）。测试帧 53000–53199 尚未运行。

1. 上次的 4 处是否改对：`kalman_phase`（前向卡尔曼 + RTS 的递推与符号、线性化点、观测方差）、`derotate` 的 `kf` 分支、实现门里真参考的归一、`crossing()` 的区间与 `read()` 里判据的三值逻辑（true / false / null）。
2. 新对手 `BESTGA`（`best(..., genie=...)`）：真径只进第 0 轮的导频模型吗？之后的重跟踪、F0、CODELAY 是否全盲？`final()` 是否与 `experiments/data_pilot_fer_20261121/stageA.py::one_arm` 的步骤一致（F0 → 校验不过才 `run_branch(..., 'A1')`），校验重量是否取自最终输出？
3. 盲对手 `best_blind()`：四变体重试的停止条件只用校验重量（观测量），没有用错数或真值？
4. `OPP`（`read()` 里逐键取 `BESTGA` 与 `BEST` 的较小错数）作为判据 1 的对手，是否如预注册所说「只会让判据 1 更难过」？有没有反过来让它更容易过的漏洞（例如帧子集不一致、SNR 子网格导致的门限偏移、`CLEAN` 与对手不在同一批帧上比）？
5. `read()`：各臂的帧 / SNR 子网格（`grid()`、`table()`）、配对的 `CLEAN` 取同一批帧、自助抽样按帧、删失的处理；`run` 分支里各臂的运行条件（`OPP_SNRS`、`SUB`、前 10 帧的 `IGN`）与预注册第 6 条是否一致。
6. 噪声膨胀与软信息来源两个开关（`infl`、`src`）：`o['sigma2']` 的改法是否只影响接收机的噪声方差输入；`arrays['r0_input_llr']` / `r1_input_llr` 是否确为检测器给译码器的外信息（见 `experiments/sp_afdm_native_joint_reviewed_20260921/src/native_twofft.py`）；`moments` 的调用口径是否与接收机自己一致。
另外：你认为在「未知双色散信道 + 接收端维纳相噪 + 叠加导频 + 编码迭代」下，还有没有一件两小时内装得上、且很可能把 `OPP` 的门限再拉低 ≥ 0.3 dB 的现成部件被漏掉？只点名最可能的一件并说理由；没有就写「没有」。
