**结论：暂缓开跑。** 我做了源码核对和内存合成检查，未修改文件，未运行完整接收机。下列行号默认指向 [实验脚本](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/l2_r8_pn_margin.py) 和 [预注册](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/PREDICTIONS_r8_pn_margin.md)。

1. **不通过｜上次四处修订。** 第 55–73 行的前向卡尔曼、后向平滑、线性化符号和负相位去旋转都对。若复噪声总方差为 `nv`，相位伪观测的一阶方差就是 `nv/(2|m|²)`。第 244–253、280–285 行的删失区间和三值判定也对。**第 149、223 行的真参考归一仍错**：接收机内部固定 `rho=0.5`，实际观测按试验的 `rho=0.30` 缩放，因此真参考应除以 `√1.4`，当前实际除以 1。这同时影响实现门的噪声比，以及 `ORACLE` 卡尔曼分支的伪观测和权重。[观测归一源码](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/headroom_ladder_20261008/driver.py:209)

2. **通过｜`BESTGA`。** 第 101–128、142–143 行，真径只直接进入第 0 轮导频参考。此后的重跟踪用接收机估计的径和软符号，F0（两轮接收）与 CODELAY（校验失败后的重搜）均未注入真径。第 89–94 行与 `one_arm(..., None)` 的译码路径一致，先跑 F0，校验失败才跑 `A1`，校验重量从最终选中的码字重算。[基线接收流程](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/data_pilot_fer_20261121/stageA.py:80)

3. **通过｜`best_blind()`。** 第 34、132–139 行，四个变体按固定顺序尝试，只在最终校验重量为零时提前停止。真值错数只用于记录所选变体的结果。

4. **不通过｜`OPP` 的保守性。** 第 259–277 行逐键取较小错数，完整账本上两臂与 `CLEAN` 使用同批帧。同一信噪比网格上，合并确实只会让判据 1 更难过。但第 27–28、244–253 行组合起来会漏掉低档首次穿越。合成检查中，`CLEAN` 和 `OPP` 都在 4.0 dB 首次到达 10% 误帧率，`OPP` 随后反弹。截去 4.5 dB 以下各档后，代码把 `OPP` 门限读成 5.25 dB，判据 1 从 `false` 翻成 `true`。要保留预注册的保守性声明，主档对手应补齐 3.5 和 4.0 dB。

5. **不通过｜运行前置条件和读表完整性。** 第 26–35、185–197 行的运行条件符合预注册修订 2 第 6 条。第 265–281 行用同批帧匹配 `CLEAN`，每次自助抽样保留同一帧的两场景与全部信噪比点，删失抽样以网格端点代值，只用于报告区间。两处须修：第 209–210、259–273 行从已有记录推断网格，整帧或整档缺失可静默缩小样本，合成账本仅有 9 帧仍给出了主判据；应核对预注册键集且拒绝重复键。第 194、271、304–305 行依赖的常数文件仍是旧版，缺 `src`、`infl`、`kap`，须先用当前开发流程生成。[当前常数文件](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/ideas/l2/r8_pn_margin_constants.json:1)

6. **通过｜`infl` 与 `src`。** 第 101–119 行，膨胀直接只写入接收机的噪声方差输入，后续信道估计、检测和重搜都会使用它。相位跟踪的噪声下限仍取原始观测方差。两轮的 `input_llr` 都是检测器外信息经裁剪后送给译码器的对数似然比。用 `moments` 重建软符号时，裁剪范围和内部数据功率都与接收机一致。[检测器与译码器接口](/Users/guoyikun/Downloads/share/claode_birain/my-vault/00_Inbox/AFDM-channel-estimation/experiments/sp_afdm_native_joint_reviewed_20260921/src/native_twofft.py:20)

两小时内可接入且很可能再降低至少 0.3 dB 的现成部件：没有。

PRERUN: FIX — 修正实现门和 ORACLE 的真参考归一，补齐主档对手的低信噪比网格，校验读表键覆盖与唯一性，并生成新版开发常数。
