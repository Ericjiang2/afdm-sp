1. **不通过｜`BEST` 的强度。** [脚本第 31–47、50–78 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_r8_pn_margin.py:31) 实现了所列组合，但最值得在开发帧先补比的是**按逐样点参考可靠度加权的维纳平滑**。现有双向单极点用固定衰减系数，未显式使用相位增量方差和软符号残差方差。可把现有时域重建信号直接接到标量扩展卡尔曼前后向平滑器，无需改冻结接收机。遗漏它可能抬高 `BEST` 门限，幅度尚未实测。另一个候选是在第一轮软判决后就重跟踪，第 71–77 行会等两轮接收结束且校验失败才更新。32／64 样点已覆盖约 61 样点的 1 rad² 相位增量尺度。现有证据不足以把逐径单音列为必补项。`ORACLE` 也用同一固定平滑器，因此 [预注册第 17–18 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_r8_pn_margin.md:17) 的「失败即无余量」超出了该臂能支持的结论。[软判决卡尔曼平滑](https://arxiv.org/abs/1308.3772) · [双色散信道逐轮相噪跟踪](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/iet-com.2014.0900)

2. **通过｜基线。** 脚本第 110–116 行给 `CLEAN` 喂无相噪观测。[实现门第 4–92 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/out_r8_pn_margin/gate.json:4) 的六个开发键中，`CLEAN` 译对五个，唯一失败在 G 场景 4.5 dB。第 188–193 行为 `IGN` 计算门限差供诊断，主判据只取主相噪档的 `BEST` 和 `ORACLE`。

3. **通过｜真值隔离。** 脚本第 63–78 行的 `BEST` 相位估计只用观测、导频、估计径和软符号。`truth` 只在第 78 行交给 `one_arm`，注入参数为 `None`。[`stageA.py` 第 80–95 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA.py:80) 中，`truth` 只进入 `score` 和 `support_stats`，重搜由校验状态触发。真无噪信号只在脚本第 84 行进入 `ORACLE`。

4. **通过｜随机数配对与注入域。** 脚本第 42–43、88–93、100–116 行按帧和场景固定相噪轨迹，跨信噪比复用。同一基础帧重复生成观测时，[`reuse_at_snr` 第 128–138 行](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_frozen_reviewed_20260921/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/supplement_g1.py:128) 复用同一个标准噪声向量，只按信噪比缩放。第 92 行先逆变换到时域，再旋转整个接收样本，随后变回离散仿射傅里叶变换域。合成输入走实际观测函数的算例通过。完整接收机复跑受只读缓存限制。

5. **不通过｜实现门归一与删失判定。** 第 31–60、165–173 行的双向平滑、去旋转和奇异向量相位符号均通过小算例。误帧率从 20% 降到 5% 时，对数内插把 10% 放在两档正中。第 179–186 行也正确按帧抽样，同一抽样保留两场景、各臂和各信噪比。两处须修：
   - 第 143 行从已归一的观测减去未归一的真信号，导致实现门把一部分信号算成噪声。真参考应同样除以 \(\sqrt{2(1-\rho)}\)。第 84 行只取相角，正实数缩放对该处无影响。
   - 第 168–169 行把低于网格的门限记作 4.0 dB，第 183–193 行把高于网格的门限代成 7.5 dB 后直接判定。后者符合预注册的记账规则，但判据应使用删失界。例如真实 `CLEAN` 为 3.7 dB、`ORACLE` 为 4.4 dB 时，代码会把 0.7 dB 判成 0.4 dB。应在开跑前规定，删失界无法确定是否过线时记为未定。

PRERUN: FIX — 先在开发帧补比可靠度加权维纳平滑，收紧 ORACLE 的失败结论，并修正实现门的参考归一与主判据的删失处理。
