你是严格的通信接收机代码审稿人，在当前目录（AFDM 项目根目录）只读工作，不要修改任何文件。≤ 3 分钟的跑前快检，只查下面五项，逐项回答「通过 / 不通过 + 具体行号与理由」，最后一行写 `PRERUN: GO` 或 `PRERUN: FIX — <必须先改的点>`。

待检：`ideas/l2/l2_r8_pn_margin.py`（L2 脚本）与 `ideas/l2/PREDICTIONS_r8_pn_margin.md`（预注册）。它只调用冻结的项目接收机（`experiments/data_pilot_fer_20261121/stageA.py` 的 `one_arm`、`experiments/sp_afdm_native_joint_20260921/src/native_twofft.py` 的 `receive` / `pilot_front`），在外面注入接收端维纳相位噪声并比较四条臂的 10% 误帧率门限。判据：`BEST − CLEAN ≥ 1.0 dB` 且 `ORACLE − CLEAN ≤ 0.5 dB`（σ² = 0.0164 rad²/样点）。

五项：
1. **`BEST` 是不是现有部件的最强组合**：它 = 分段非相干找径（`seg_init`）+ 段间公共相位的奇异向量初值 + 导频模型上的前后向相位平滑与 `pilot_front` 重找径交替 3 遍 + 校验失败时用末轮的径与软符号重建信号重跟踪（≤ 3 次）+ CODELAY 重搜。文献里对「未知双色散信道 + 接收端维纳相噪 + 叠加导频」还有没有明显更强、且两小时内能装上的现成部件被漏掉（例如：卡尔曼 / 前后向相位平滑代替单极点平滑、判决阶段每个外轮都重跟踪而不是只在校验失败后、逐径单音做相位参考后合并、分段长与相干时间匹配）？漏了哪一个会让判据 1 高估余量，就点名。
2. 有没有失锁的坏基线充数（`CLEAN` 在该设定下应正常工作；`IGN` 只作健全性对照、不进判据——核对 `read()` 是否确实没有把它算进判据）。
3. 有没有偷读真值：`BEST` 路径里是否用到了 `raw` / `truth` / 真相噪 `theta` / 真 `noiseless`（`ORACLE` 用真信号是声明过的上限臂，不算）；`best()` 把 `truth` 传给 `stageA.one_arm` 只用于计分，请核对 `one_arm` 里 `truth` 是否只进 `score` 与 `support_stats`。
4. 随机数对齐：各臂、各 SNR 是否同一帧同一噪声同一条相噪轨迹（`theta()` 的种子、`key_inputs` 对 `observed` 的重复调用是否给出相同的噪声）；相噪注入的域是否正确（`obs['y']` 在 DAFT 域，先 `daft(..., inverse=True)` 到时域乘 `e^{jθ}` 再变回）。
5. 正负号与归一：`derotate` 的共轭方向、`smooth` 的前后向单极点、`seg_init` 里相位的符号、`crossing()` 的对数线性内插与删失处理、`read()` 里自助抽样按帧。任何你怀疑写反的符号，先在脑内或用 5 行数值算例确认再下结论。
